#!/usr/bin/env python3
"""
build_timetagger.py -- compile the TimeTagger extension for Python 3.

    python3 build_timetagger.py <path-to-timetagger/backend>

Run `modernize_timetagger.py` on the directory first.

REQUIREMENTS

  Windows:  Visual Studio Build Tools (C++ workload) + SWIG on PATH
            https://visualstudio.microsoft.com/visual-cpp-build-tools/
            https://swig.org/download.html   (unzip, add to PATH)
  Linux:    g++ and swig

  Both:     pip install numpy setuptools

No boost. No OpalKelly SDK download -- okFrontPanelDLL.cpp is a dynamic
loader shim and is already in the repo; it opens okFrontPanel.dll at runtime,
which is also in the repo.

BITNESS

Build 64-bit. The original .pyd was 32-bit only because that is what 2011
looked like, and inheriting that decision would pin your NI-DAQmx install,
your Python, and everything else to 32-bit forever. This script builds for
whatever interpreter runs it, so run it with the 64-bit Python you intend to
use.

AFTER BUILDING

Copy the resulting _TimeTagger.pyd (Windows) or _TimeTagger.so (Linux) and
the SWIG-generated TimeTagger.py next to hardware/, replacing the Python 2
binaries. Then verify against real hardware before trusting any of it -- this
script proves the code compiles and imports, nothing more. Nobody here has
touched an XEM3010.
"""

import os
import subprocess
import sys
import sysconfig

CORE = ['TimeTagger.cpp', 'okFrontPanelDLL.cpp', 'Iterator.cpp', 'Histogram.cpp',
        'Counter.cpp', 'Pulsed.cpp', 'PulsedAFM.cpp', 'PulsedExtTrig.cpp',
        'CountBetweenMarkers.cpp']


def run(cmd, cwd):
    print('  $ %s' % ' '.join(cmd[:6] + (['...'] if len(cmd) > 6 else [])))
    r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    if r.returncode:
        print(r.stdout[-3000:])
        print(r.stderr[-3000:])
    return r.returncode == 0


def main(backend):
    backend = os.path.abspath(backend)
    if not os.path.isdir(backend):
        print('not a directory: %s' % backend)
        return 2

    # Check for real usage, not the word: modernize_timetagger.py leaves a
    # comment explaining the boost removal, and a bare substring match trips
    # on its own success notice.
    header = open(os.path.join(backend, 'TimeTagger.h'),
                  encoding='utf-8', errors='replace').read()
    if 'boost::' in header or '<boost/' in header:
        print('TimeTagger.h still references boost.')
        print('Run modernize_timetagger.py on this directory first.')
        return 1

    import numpy
    bits = 64 if sys.maxsize > 2 ** 32 else 32
    print('building for Python %s, %d-bit\n' % (sysconfig.get_python_version(), bits))
    if bits == 32:
        print('  WARNING: this is a 32-bit interpreter. See the docstring --')
        print('  you almost certainly want 64-bit.\n')

    print('1. SWIG')
    # Print the version: the generated wrapper differs between SWIG 3 and 4
    # (that is where the flattened _Tagger_* wrappers went), so a build that
    # behaves oddly should start by being blamed on the generator on PATH.
    try:
        v = subprocess.run(['swig', '-version'], capture_output=True, text=True)
        line = [l for l in v.stdout.splitlines() if l.strip()]
        print('  %s' % (line[0].strip() if line else 'version unknown'))
    except FileNotFoundError:
        print('SWIG not found on PATH.')
        return 1
    if not run(['swig', '-Wall', '-c++', '-python', 'TimeTagger.i'], backend):
        print('SWIG failed.')
        return 1

    py_inc = sysconfig.get_paths()['include']
    np_inc = numpy.get_include()
    win = sys.platform == 'win32'

    print('2. compile')
    if win:
        from setuptools import Extension, setup
        ext = Extension(
            '_TimeTagger',
            sources=[os.path.join(backend, f) for f in CORE]
                    + [os.path.join(backend, 'TimeTagger_wrap.cxx')],
            include_dirs=[backend, py_inc, np_inc],
            # _DISABLE_CONSTEXPR_MUTEX_CONSTRUCTOR: since the port replaced
            # boost::mutex with std::mutex, this binary is exposed to the VS
            # 2022 17.10 std::mutex ABI change. If an older msvcp140.dll is
            # loaded into the process first -- plenty of Python wheels ship one
            # -- the first lock crashes with an access violation and no usable
            # traceback. This define opts out of the new constructor and keeps
            # the binary compatible with whichever runtime turns up.
            define_macros=[('WIN32', None),
                           ('_DISABLE_CONSTEXPR_MUTEX_CONSTRUCTOR', None)],
            libraries=[],
        )
        cwd0 = os.getcwd()
        os.chdir(backend)
        build_lib = os.path.join(backend, 'build', 'lib')
        try:
            setup(name='TimeTagger', ext_modules=[ext],
                  script_args=['build_ext',
                               '--build-lib', build_lib,
                               '--build-temp', os.path.join(backend, 'build', 'temp')])
        except SystemExit as exc:
            # setuptools exits the process on a compiler error, which would skip
            # the deployment notes below and leave no hint about what to check.
            if exc.code:
                print('\nMSVC build failed (exit %s).' % exc.code)
                print('Check: Build Tools installed with the C++ workload, and')
                print('that this is an x64 Native Tools prompt (or that cl.exe')
                print('is otherwise on PATH).')
                return 1
        finally:
            os.chdir(cwd0)

        # Copy the result next to the sources ourselves. --inplace resolved
        # the destination to an empty string here, because the Extension name
        # has no package prefix -- the build reported
        #     copying build\...\_TimeTagger.cp313-win_amd64.pyd ->
        # with nothing after the arrow, and the .pyd was left in build/.
        import glob
        import shutil
        built = glob.glob(os.path.join(build_lib, '_TimeTagger*.pyd'))
        if not built:
            print('build produced no .pyd under %s' % build_lib)
            return 1
        for src in built:
            dst = os.path.join(backend, os.path.basename(src))
            shutil.copy2(src, dst)
            print('   -> %s' % dst)
    else:
        objs = []
        for src in CORE + ['TimeTagger_wrap.cxx']:
            obj = os.path.splitext(src)[0] + '.o'
            cmd = ['g++', '-c', '-std=c++11', '-O2', '-fPIC', '-DLINUX', '-w',
                   '-I' + backend, '-I' + py_inc, '-I' + np_inc, src, '-o', obj]
            if not run(cmd, backend):
                return 1
            objs.append(obj)
        print('3. link')
        if not run(['g++', '-shared'] + objs + ['-o', '_TimeTagger.so', '-ldl'],
                   backend):
            return 1

    # --- restore the flattened module-level wrappers ----------------------
    # SWIG 3.0.7 emitted a module-level function for every static method
    # alongside the class attribute. SWIG 4 dropped them, so
    # `time_tagger._Tagger_setSerial(...)` -- pi3diamond.py:59 and
    # tools/automation.py:59 -- raises AttributeError.
    #
    # This has to happen on every build: TimeTagger.py is GENERATED, so adding
    # the aliases by hand works until the next rebuild silently removes them.
    print('3b. restoring the SWIG 3.x flattened wrappers')
    wrapper = os.path.join(backend, 'TimeTagger.py')
    if os.path.exists(wrapper):
        src = open(wrapper, 'rb').read().decode('utf-8', 'replace')
        # Check for a MODULE-LEVEL assignment, not the bare name. SWIG 4 emits
        # `return _TimeTagger._Tagger_setSerial(s)` inside the staticmethod, so
        # a substring test for '_Tagger_setSerial' is always satisfied and the
        # aliases were never actually written -- which is why they had to be
        # added to hardware/TimeTagger.py by hand, and why re-running this
        # build and copying the result over would have silently removed them
        # again and broken pi3diamond.py:59.
        has_aliases = any(l.startswith('_Tagger_setSerial')
                          for l in src.splitlines())
        if not has_aliases:
            eol = '\r\n' if '\r\n' in src else '\n'
            aliases = eol.join([
                '',
                '',
                '# PY3-PORT: SWIG 3.0.7 emitted these flattened wrappers for the static',
                '# methods of _Tagger; SWIG 4 does not. Restored as aliases so existing',
                '# call sites keep working. Regenerated on every build by',
                '# build_timetagger.py -- do not rely on editing this file by hand, it',
                '# is overwritten each time SWIG runs.',
                '_Tagger_setSerial = _Tagger.setSerial',
                '_Tagger_getTagger = _Tagger.getTagger',
                '_Tagger_getDistributionCount = _Tagger.getDistributionCount',
                '_Tagger_SetWireIn = _Tagger.SetWireIn',
                '',
            ])
            open(wrapper, 'wb').write((src.rstrip() + aliases).encode('utf-8'))
            print('   restored the flattened _Tagger_* module-level wrappers')

    print('\n4. verify it imports')
    r = subprocess.run(
        [sys.executable, '-c',
         'import _TimeTagger, TimeTagger; '
         'print("classes:", sorted(n for n in dir(TimeTagger) '
         'if n[0].isupper() and not n.startswith("_"))); '
         'print("flattened:", [n for n in dir(TimeTagger) '
         'if n.startswith("_Tagger_")])'],
        cwd=backend, capture_output=True, text=True)
    print(r.stdout or r.stderr)
    if r.returncode:
        return 1
    # An import that works but is missing a class the measurement code calls is
    # a failure discovered much later, at the instrument. Check here instead.
    need = ['Counter', 'Countrate', 'Histogram', 'Pulsed', 'PulsedAFM',
            'PulsedExtTrig', 'CountBetweenMarkers']
    missing = [n for n in need if ("'%s'" % n) not in r.stdout]
    if missing:
        print('MISSING classes the measurement code calls: %s' % ', '.join(missing))
        return 1
    if '_Tagger_setSerial' not in r.stdout:
        print('MISSING _Tagger_setSerial -- pi3diamond.py:59 will fail on import.')
        return 1

    print('Built in %s' % backend)
    print()
    print('NOW DEPLOY IT -- the build does not do this for you:')
    print('  1. move the old 32-bit binaries aside in hardware/')
    print('       ren hardware\\_TimeTagger.pyd _TimeTagger.pyd.py27bak')
    print('       ren hardware\\TimeTagger.py   TimeTagger.py.swig307bak')
    print('       ren hardware\\_TimeTagger.py  _TimeTagger.py.stray')
    print('  2. copy the new ones in')
    print('       copy %s\\_TimeTagger*.pyd hardware\\' % backend)
    print('       copy %s\\TimeTagger.py    hardware\\' % backend)
    print('  3. verify')
    print('       python -c "from hardware import _TimeTagger;'
          ' print(_TimeTagger.__file__)"')
    print()
    print('If step 3 says "%1 is not a valid Win32 application", the old')
    print('32-bit .pyd is still there and step 1 did not happen.')
    return 0


if __name__ == '__main__':
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(2)
    sys.exit(main(sys.argv[1]))
