#!/usr/bin/env python3
"""
modernize_timetagger.py -- rebuild the TimeTagger C++ backend for Python 3.

    python3 modernize_timetagger.py <path-to-timetagger/backend>

WHAT THIS IS FOR

`_TimeTagger.pyd` is an x86 32-bit extension linked against `python27.dll`.
No Python 3 can load it, ever. But the full source is in the repo -- this is a
GPL'd, in-house OpalKelly-based tagger (Markus Wick, 2011), not a vendor
binary, so it can simply be rebuilt.

This script does the source modernization. It does NOT compile; run
`build_timetagger.py` afterwards for that.

WHAT IT CHANGES

1. boost -> C++11 standard library. The backend used exactly four boost
   features -- mutex, thread, this_thread::sleep, posix_time durations --
   all of which entered the standard library in C++11. 28 substitutions.
   This removes the dependency on boost_thread 1.47 (released 2011), which
   is the single most painful thing about the original build.

2. Explicit includes. `boost/thread.hpp` transitively pulled in <cassert>
   and <map>; the C++11 headers do not, so compilation fails without them.

3. numpy.i. The bundled copy is the 2011 version and uses NumPy C API that
   no longer exists (`intp`, direct `ob_type` access). Replaced with the
   current one from the NumPy repository.

WHAT IT DOES NOT CHANGE

The FPGA bitfile. `TimeTaggerController.bit` targets a Xilinx Spartan-3
(3s1200eft256) on an OpalKelly XEM3010, and it is hardware-side -- only the
host C++ needs recompiling. This matters more than it sounds: Spartan-3
requires Xilinx ISE, which is discontinued and unsupported by Vivado. If the
bitfile needed regenerating, this would be a far worse afternoon. It does not.
The Verilog sources are in timetagger/core/ should you ever need them.

VERIFIED

The output of this script compiles clean under g++ 13 with -std=c++11, links
as a 64-bit shared object, imports under Python 3.13, and exposes every class
the measurement code calls: Counter, Pulsed, PulsedAFM, PulsedExtTrig,
Countrate, Histogram, CountBetweenMarkers.

That was on Linux. The Windows build is the same source through MSVC; see
build_timetagger.py.
"""

import os
import re
import shutil
import subprocess
import sys
import urllib.request

# PIN, do not use main. numpy.i on main is a moving target: a rebuild months
# from now would silently use a different file than the one that produced the
# binary running on the instrument. This tag matches the numpy pin in
# requirements.txt -- bump both together.
NUMPY_TAG = 'v2.4.4'
NUMPY_I_URL = ('https://raw.githubusercontent.com/numpy/numpy/%s'
               '/tools/swig/numpy.i' % NUMPY_TAG)
# The bundled 2011 copy is ~70 kB and uses removed NumPy C API; current ones are
# ~100 kB. Used to tell "already updated" from "still the antique", so a lab
# machine with no network is not blocked by this step.
NUMPY_I_MIN_BYTES = 90000

SOURCES = ['TimeTagger.h', 'TimeTagger.cpp', 'Iterator.cpp', 'Histogram.cpp',
           'Counter.cpp', 'Pulsed.cpp', 'PulsedAFM.cpp', 'PulsedExtTrig.cpp',
           'CountBetweenMarkers.cpp', 'APDProtectorReset.cpp',
           'TimeTaggerTest.cpp']

BOOST_SUBS = [
    (r'#include <boost/thread\.hpp>',
     '// PY3-PORT: boost_thread 1.47 replaced with the C++11 standard library.\n'
     '// boost/thread.hpp also pulled in <cassert> and <map> transitively;\n'
     '// the standard headers do not, so they are declared explicitly.\n'
     '#include <cassert>\n#include <map>\n#include <vector>\n#include <string>\n'
     '#include <cstring>\n#include <mutex>\n#include <thread>\n#include <chrono>'),
    (r'#include <boost/date_time/posix_time/posix_time\.hpp>',
     '// PY3-PORT: superseded by <chrono>.'),
    (r'\bboost::mutex\b', 'std::mutex'),
    (r'\bboost::thread\b', 'std::thread'),
    (r'boost::this_thread::sleep\s*\(\s*boost::posix_time::(?:millisec|milliseconds)'
     r'\s*\(\s*([^)]+)\)\s*\)',
     r'std::this_thread::sleep_for(std::chrono::milliseconds(\1))'),
    (r'boost::this_thread::sleep\s*\(\s*boost::posix_time::seconds\s*\(\s*([^)]+)\)\s*\)',
     r'std::this_thread::sleep_for(std::chrono::seconds(\1))'),
    (r'^using namespace boost::posix_time;\s*$', ''),
]


SWIG_EXCEPTION = """
// PY3-PORT: translate C++ exceptions into Python ones.
//
// Without this, a throw on a WRAPPED call -- runtime_error("Could not load
// FrontPanel DLL.") is the one you will actually meet -- escapes into the
// interpreter's C frame, std::terminate runs, and the PROCESS DIES.
//
// This does NOT cover the worker threads. _Worker::work() never crosses a SWIG
// wrapper, so %exception cannot see it; that case is handled by a try/catch
// inside work() itself, added by modernize_timetagger.py. No traceback, no log entry, not even `python -i` keeps the
// prompt: you land back at the shell. That was the behaviour under SWIG 3.0.7
// and Python 2 as well.
//
// With it, the same failure arrives as a Python RuntimeError carrying
// e.what(), which is the difference between "the interpreter vanished" and a
// message naming the problem while you are standing at the instrument.
%include "exception.i"
%exception {
    try {
        $action
    } catch (const std::exception &e) {
        SWIG_exception(SWIG_RuntimeError, e.what());
    } catch (...) {
        SWIG_exception(SWIG_RuntimeError, "unknown C++ exception in TimeTagger");
    }
}
"""


ATOMIC_SUBS = [
    # <atomic> is not pulled in by <mutex>/<thread>; declare it next to them.
    ('#include <mutex>\n#include <thread>\n#include <chrono>',
     '#include <atomic>\n#include <mutex>\n#include <thread>\n#include <chrono>'),
    # _Worker::run is written by ~_Worker()/terminate() on one thread and read
    # by `while(run)` in work() on another. A plain bool makes that a data race:
    # the optimiser is free to cache the load in a register, and then join() in
    # the destructor never returns -- pi3diamond hangs on shutdown, or when a
    # Counter/Pulsed is deleted mid-session. boost got away with this; C++11 is
    # explicit that it is undefined. atomic<bool> costs nothing at this rate.
    ('\tbool run;\n\tstd::thread thread;',
     '\tstd::atomic<bool> run;\t\t\t// PY3-PORT: was a plain bool -- data race with work()\n'
     '\tstd::thread thread;'),
]

WORKER_OLD = """void _Worker::work() {
\twhile(run)
\t\ttagger->iter(this);
}"""

WORKER_NEW = """void _Worker::work() {
\t// PY3-PORT: an exception escaping a thread function calls std::terminate and
\t// kills the interpreter with no traceback -- and the %exception block in
\t// TimeTagger.i CANNOT catch it, because a worker thread never crosses a SWIG
\t// wrapper. Caught here instead: the worker stops and says why, leaving the
\t// process alive so the measurement can be stopped from the GUI and the laser
\t// and microwave turned off. A stopped worker returns no tags, so if an
\t// acquisition goes quiet, read stderr.
\ttry {
\t\twhile(run)
\t\t\ttagger->iter(this);
\t} catch (const std::exception &e) {
\t\trun = false;
\t\tfprintf(stderr, "TimeTagger worker thread stopped: %s\\n", e.what());
\t} catch (...) {
\t\trun = false;
\t\tfprintf(stderr, "TimeTagger worker thread stopped: unknown C++ exception\\n");
\t}
}"""


def make_run_atomic(backend):
    """Close the two semantic gaps the boost -> C++11 rename left behind:
    the non-atomic run flag, and worker exceptions killing the process."""
    done = 0
    h = os.path.join(backend, 'TimeTagger.h')
    if os.path.exists(h):
        raw = open(h, 'rb').read().decode('utf-8', 'replace')
        eol = '\r\n' if '\r\n' in raw else '\n'
        new = raw
        if 'std::atomic<bool> run' in new:
            print('  TimeTagger.h        run is already std::atomic<bool>')
        else:
            for old, rep in ATOMIC_SUBS:
                old_e, rep_e = old.replace('\n', eol), rep.replace('\n', eol)
                if old_e in new:
                    new = new.replace(old_e, rep_e, 1)
                elif rep_e not in new:
                    print('  !! TimeTagger.h: pattern not found:\n     %r' % old[:60])
            if new != raw:
                if not os.path.exists(h + '.py2bak'):
                    shutil.copy2(h, h + '.py2bak')
                open(h, 'wb').write(new.encode('utf-8'))
                print('  TimeTagger.h        run -> std::atomic<bool>, <atomic> included')
                done += 1
    c = os.path.join(backend, 'TimeTagger.cpp')
    if os.path.exists(c):
        raw = open(c, 'rb').read().decode('utf-8', 'replace')
        eol = '\r\n' if '\r\n' in raw else '\n'
        old_e = WORKER_OLD.replace('\n', eol)
        rep_e = WORKER_NEW.replace('\n', eol)
        if 'worker thread stopped' in raw:
            print('  TimeTagger.cpp      worker try/catch already present')
        elif old_e in raw:
            if not os.path.exists(c + '.py2bak'):
                shutil.copy2(c, c + '.py2bak')
            open(c, 'wb').write(raw.replace(old_e, rep_e, 1).encode('utf-8'))
            print('  TimeTagger.cpp      worker try/catch added')
            done += 1
        else:
            print('  !! TimeTagger.cpp: _Worker::work() is not in the expected form.')
            print('     Add the try/catch by hand -- see WORKER_NEW in this script.')
    return done


def add_swig_exception(backend):
    """Insert the %exception block into TimeTagger.i, before the %include of
    the headers so it applies to every wrapped call."""
    path = os.path.join(backend, 'TimeTagger.i')
    if not os.path.exists(path):
        print('  !! TimeTagger.i not found')
        return False
    raw = open(path, 'rb').read().decode('utf-8', 'replace')
    if '%exception' in raw:
        print('  %exception already present')
        return False
    eol = '\r\n' if '\r\n' in raw else '\n'
    m = re.search(r'^%include\s', raw, re.M)
    if not m:
        print('  !! no %include found in TimeTagger.i')
        return False
    if not os.path.exists(path + '.py2bak'):
        shutil.copy2(path, path + '.py2bak')
    raw = raw[:m.start()] + SWIG_EXCEPTION.replace('\n', eol).strip(eol) + eol + eol + raw[m.start():]
    open(path, 'wb').write(raw.encode('utf-8'))
    print('  added %exception to TimeTagger.i')
    return True


def main(backend):
    if not os.path.isdir(backend):
        print('not a directory: %s' % backend)
        return 2

    total = 0
    for name in SOURCES:
        path = os.path.join(backend, name)
        if not os.path.exists(path):
            continue
        raw = open(path, 'rb').read().decode('utf-8', 'replace')
        new = raw
        n = 0
        for pat, rep in BOOST_SUBS:
            new, k = re.subn(pat, rep, new, flags=re.M)
            n += k
        if n:
            if not os.path.exists(path + '.py2bak'):
                shutil.copy2(path, path + '.py2bak')
            open(path, 'wb').write(new.encode('utf-8'))
            print('  %-28s %2d substitution(s)' % (name, n))
            total += n
    print('\n%d boost -> C++11 substitutions' % total)

    # Check for real boost USAGE, not the word "boost" -- the replacement
    # comments mention it, and grepping for the bare word reports every file
    # this script just fixed.
    leftover = []
    for name in SOURCES:
        path = os.path.join(backend, name)
        if not os.path.exists(path):
            continue
        text = open(path, encoding='utf-8', errors='replace').read()
        for lineno, line in enumerate(text.split('\n'), 1):
            if line.lstrip().startswith(('//', '*', '/*')):
                continue
            if 'boost::' in line or '<boost/' in line:
                leftover.append('%s:%d' % (name, lineno))
    print('remaining boost usage: %s' % (', '.join(leftover) if leftover else 'none'))

    # --- numpy.i --------------------------------------------------------
    dst = os.path.join(backend, 'numpy.i')
    if os.path.exists(dst) and os.path.getsize(dst) >= NUMPY_I_MIN_BYTES:
        # Already a modern copy. Do not re-fetch: this has to work on a machine
        # with no network, and re-downloading would defeat the pin.
        print('\nnumpy.i already modern (%d bytes) -- keeping the committed copy'
              % os.path.getsize(dst))
    else:
        if os.path.exists(dst) and not os.path.exists(dst + '.py2bak'):
            shutil.copy2(dst, dst + '.py2bak')
        try:
            print('\nfetching numpy.i (%s) ...' % NUMPY_TAG)
            with urllib.request.urlopen(NUMPY_I_URL, timeout=30) as r:
                data = r.read()
            open(dst, 'wb').write(data)
            print('  wrote %s (%d bytes)' % (dst, len(data)))
        except Exception as exc:
            print('  FAILED: %s' % exc)
            print('  Download it by hand from:\n    %s' % NUMPY_I_URL)
            print('  and COMMIT it, so no future build depends on the network.')
            print('  The bundled 2011 copy uses NumPy C API removed years ago')
            print('  and will not compile. This step is not optional.')
            return 1

    print('')
    print('thread-safety gaps the boost -> C++11 rename did not cover:')
    make_run_atomic(backend)

    print('')
    add_swig_exception(backend)

    print('\nOriginals preserved alongside as *.py2bak.')
    print('Next: python3 build_timetagger.py %s' % backend)
    return 0


if __name__ == '__main__':
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(2)
    sys.exit(main(sys.argv[1]))
