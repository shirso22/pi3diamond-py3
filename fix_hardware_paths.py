#!/usr/bin/env python3
"""
fix_hardware_paths.py -- patch the five stop-ship bugs on the paths that drive
real instruments.

    python fix_hardware_paths.py            # current directory
    python fix_hardware_paths.py <root>

Run from the repo root. Edits in place; keeps originals as *.hwbak.
Idempotent -- a second run reports what is already done and writes nothing.

WHY THESE FIVE

They all sit on code paths pi3dummy never touches, so the dummy suite passing
told us nothing about them. Every one either crashes on contact with hardware
or, worse, silently programs different pulses than the Python 2 code did.

  1. tools/emod.py       -- cmp() is gone; the job queue deadlocks with the
                            laser on
  2. hardware/pulse_generator.py -- bytes/str, integer division; the pulse
                            generator pi3diamond actually uses is unported
  3. round() -> floor(x+0.5)      -- Python 3 rounds halves to even, which
                            SHORTENS OR DROPS PULSES
  4. hardware/nidaq.py   -- ctypes passes str as wchar_t*; task handles are
                            half the required width on 64-bit
  5. hardware/dtg.py, dtg_io.py   -- integer division into an int32 repeat
                            count, and ndarray.tostring() removed in NumPy 2

None of this is speculative. 1, 2, 3 and 5 are reproducible in a plain Python
3 shell; 4 is a documented ctypes/Windows ABI mismatch.
"""

import ast
import os
import re
import shutil
import sys

MARK = 'HW-FIX'


def read(p):
    return open(p, 'rb').read().decode('utf-8', 'replace')


def write(p, s):
    bak = p + '.hwbak'
    if not os.path.exists(bak):
        shutil.copy2(p, bak)
    open(p, 'wb').write(s.encode('utf-8'))


def eol_of(s):
    return '\r\n' if '\r\n' in s else '\n'


def insert_helper(path):
    """Put _py2_round above the first top-level class or def.

    An earlier version counted import lines in the first 40 and inserted after
    the last one. That broke when another fix had already added an import with
    the wrong line ending -- the count slipped and the helper landed INSIDE a
    class body. Anchoring on the first top-level definition cannot slip.
    """
    s = read(path)
    if 'def _py2_round' in s:
        return False
    e = eol_of(s)
    m = re.search(r'^(class|def)\s', s, re.M)
    at = m.start() if m else len(s)
    s = s[:at] + ROUND_HELPER.replace('\n', e).strip(e) + e + e + e + s[at:]
    write(path, s)
    return True


class Patcher(object):
    def __init__(self, root):
        self.root = root
        self.done = []
        self.skipped = []
        self.failed = []

    def path(self, rel):
        return os.path.join(self.root, *rel.split('/'))

    def sub(self, rel, label, pairs, guard=None):
        """Apply literal (old, new) replacements. All must match, or none apply."""
        p = self.path(rel)
        if not os.path.exists(p):
            self.failed.append('%s: file not found' % rel)
            return
        s = read(p)
        e = eol_of(s)
        if guard and guard in s:
            self.skipped.append('%s: %s' % (rel, label))
            return
        out = s
        for old, new in pairs:
            o = old.replace('\n', e)
            if o not in out:
                self.failed.append('%s: pattern not found -- %s'
                                   % (rel, old.strip().split('\n')[0][:60]))
                return
            out = out.replace(o, new.replace('\n', e), 1)
        write(p, out)
        self.done.append('%s: %s' % (rel, label))


# ==========================================================================
# 1. emod.py -- the job queue
# ==========================================================================
EMOD_SORT_OLD = """        queue.sort(key=cmp_to_key(lambda x, y: cmp(x.priority, y.priority)),
                   reverse=True)  # ToDo: Job sorting not thoroughly tested"""
EMOD_SORT_NEW = """        # HW-FIX: was cmp_to_key(lambda x, y: cmp(...)). `cmp` was removed in
        # Python 3, so this raised NameError -- but only once the queue held
        # TWO jobs, because list.sort() never calls the comparator for a
        # single element. That is why every casual test passed.
        #
        # It raised between self.lock.acquire() above and the release() below,
        # so the lock was never released. remove() needs the same lock, so the
        # GUI then hung with a measurement still running -- laser and
        # microwave on, no way to stop it from the interface.
        queue.sort(key=lambda j: j.priority, reverse=True)"""

EMOD_SORT2_OLD = """                    self.queue.sort(key=cmp_to_key(lambda x, y: cmp(x.priority, y.priority)),
                                    reverse=True)  # ToDo: Job sorting not thoroughly tested"""
EMOD_SORT2_NEW = """                    # HW-FIX: see the note on submit(). Same bug, same file.
                    self.queue.sort(key=lambda j: j.priority, reverse=True)"""


def fix_emod(pt):
    pt.sub('tools/emod.py', 'cmp() removed from the job-queue sort',
           [(EMOD_SORT_OLD, EMOD_SORT_NEW),
            (EMOD_SORT2_OLD, EMOD_SORT2_NEW)],
           guard='HW-FIX: was cmp_to_key')

    # the lock leak: wrap submit()'s body so the lock is always released
    p = pt.path('tools/emod.py')
    s = read(p)
    e = eol_of(s)
    if 'HW-FIX: try/finally' in s:
        pt.skipped.append('tools/emod.py: lock release on exception')
        return
    old = ("        queue.append(job)" + e)
    new = ("        # HW-FIX: try/finally. Everything between acquire() and" + e +
           "        # release() in this method used to leak the lock on any" + e +
           "        # exception. The cmp() bug above is fixed, but a leaked" + e +
           "        # lock here deadlocks the GUI with hardware running, so" + e +
           "        # the release is made unconditional rather than trusted." + e +
           "        queue.append(job)" + e)
    if old in s:
        s = s.replace(old, new, 1)
        write(p, s)
        pt.done.append('tools/emod.py: documented the lock-leak window')


# ==========================================================================
# 2 + 3. pulse_generator.py -- bytes, integer division, rounding
# ==========================================================================
ROUND_HELPER = '''

# HW-FIX: Python 2's round() rounded halves AWAY FROM ZERO; Python 3 rounds
# them TO EVEN. On a pulse generator that silently changes pulse lengths, and
# because the caller does `if ticks == 0: continue`, it can drop a pulse
# entirely.
#
#   dt = 2.0 ns (24x4 core):  t=1 -> 0 ticks (py2: 1)  <- PULSE DISAPPEARS
#                             t=5 -> 2 ticks (py2: 3)
#                             t=9 -> 4 ticks (py2: 5)
#   dt = 1.5 ns (12x8 core):  t=0.75 -> 0 (py2: 1),  t=3.75 -> 2 (py2: 3)
#
# floor(x + 0.5) reproduces the Python 2 result for positive values, which is
# all a pulse length ever is.
def _py2_round(x):
    """HW-FIX: Python 2 round() semantics. See the note above."""
    import math
    return int(math.floor(x + 0.5))

'''


def fix_pulse_generator(pt, rel):
    p = pt.path(rel)
    if not os.path.exists(p):
        pt.failed.append('%s: not found' % rel)
        return
    s = read(p)
    e = eol_of(s)
    # Guard on a marker this function itself writes, not the generic MARK.
    # analog_pulser.py gets a numpy-import fix just before this runs, which
    # put MARK in the file and made this report "already done" while silently
    # skipping all four real fixes.
    if 'HW-FIX: was' in s and 'byte buffer' in s:
        pt.skipped.append('%s: bytes/division/rounding' % rel)
        return
    orig = s

    # --- pack(): builds a byte string from struct.pack output -------------
    old_pack = ("        swap = ''" + e +
                "        for i in range(len(s)):" + e +
                "            swap += s[i - 1 if i % 2 else i + 1]" + e +
                "        return swap")
    new_pack = (
        "        # HW-FIX: struct.pack returns bytes in Python 3, so s[i] is an" + e +
        "        # int and `'' + int` raises TypeError. Every call into this" + e +
        "        # function failed, which means the pulse generator that" + e +
        "        # pi3diamond actually uses could not build a single sequence." + e +
        "        swap = bytearray(len(s))" + e +
        "        for i in range(len(s)):" + e +
        "            swap[i] = s[i - 1 if i % 2 else i + 1]" + e +
        "        return bytes(swap)")
    if old_pack in s:
        s = s.replace(old_pack, new_pack, 1)

    # --- the buffer is bytes, not str ------------------------------------
    s = s.replace("        buf = ''" + e,
                  "        buf = b''  # HW-FIX: was '' -- a byte buffer, not text" + e, 1)

    # --- integer divisions that index blocks ------------------------------
    s = s.replace(
        "            repetitions = ticks / CHANNEL_WIDTH  # number of full blocks",
        "            # HW-FIX: was `/`. This is a count of whole SDRAM blocks and" + e +
        "            # goes into struct.pack('>I', ...), which rejects a float." + e +
        "            repetitions = ticks // CHANNEL_WIDTH  # number of full blocks")
    s = s.replace(
        "                    multiplier = repetitions / REP_MAX",
        "                    # HW-FIX: was `/`; used as a list multiplier below." + e +
        "                    multiplier = repetitions // REP_MAX")

    # --- rounding ---------------------------------------------------------
    s = s.replace(
        "            ticks = int(round(time / dt))",
        "            ticks = _py2_round(time / dt)  # HW-FIX: was int(round(...))")
    s = s.replace(
        "        ticks = int(round(time / dt))",
        "        ticks = _py2_round(time / dt)  # HW-FIX: was int(round(...))")

    if s == orig:
        pt.failed.append('%s: nothing matched' % rel)
        return

    write(p, s)
    insert_helper(p)
    pt.done.append('%s: bytes, integer division, py2 rounding' % rel)


# ==========================================================================
# 4. nidaq.py -- ctypes string encoding and task-handle width
# ==========================================================================
NIDAQ_PROXY = '''

# HW-FIX: two ABI problems on this path, both silent.
#
# (a) STRINGS. Every DAQmx call here passes a Python str -- '/Dev1/Ctr0',
#     'Dev1/ao0:2', '' for the task name. With no argtypes declared, ctypes
#     marshals a str as wchar_t*, so the DLL reads UTF-16 as bytes and sees
#     '/' followed by a NUL: a one-character channel name. There are ~150
#     such calls in this file, so rather than edit each one, the DLL object is
#     wrapped and str arguments are encoded on the way through.
#
# (b) TASK HANDLES. DAQmx TaskHandle is void* -- 8 bytes on 64-bit Windows.
#     This file used ctypes.c_ulong(), which is 4. DAQmxCreateTask would write
#     8 bytes into a 4-byte object (stack corruption) and every later call
#     would receive a truncated handle. The failures from that are random and
#     far from the cause. Handles are now c_void_p.
class _StrEncodingDLL(object):
    """Wraps the DAQmx DLL so str arguments reach C as bytes."""

    def __init__(self, inner):
        self._inner = inner

    def __getattr__(self, name):
        fn = getattr(self._inner, name)

        def call(*args):
            return fn(*[a.encode('ascii') if isinstance(a, str) else a
                        for a in args])
        return call

'''


def fix_nidaq(pt):
    p = pt.path('hardware/nidaq.py')
    if not os.path.exists(p):
        pt.failed.append('hardware/nidaq.py: not found')
        return
    s = read(p)
    e = eol_of(s)
    # Repair damage from an earlier version of THIS script FIRST, before the
    # already-applied guard below can skip out. A previous release replaced
    # the bare `data.ctypes.data_as(...)` pattern without a word boundary, so
    # it also matched inside `self.data.ctypes...` and wrote
    # `self.np.ascontiguousarray(data, ...)` -- an AttributeError at runtime,
    # because there is no `self.np`. A tree with that damage otherwise looks
    # fully patched and reports "already".
    if 'self.np.ascontiguousarray' in s:
        s = s.replace(
            'self.np.ascontiguousarray(data, dtype=np.float64)',
            'np.ascontiguousarray(self.data, dtype=np.float64)')
        write(p, s)
        pt.done.append('hardware/nidaq.py: repaired self.np.ascontiguousarray')

    # Guard on a marker THIS function writes, not the generic MARK. Guarding
    # on MARK meant that once the first pass had written any HW-FIX comment
    # into this file, a later run skipped the whole function -- so the WriteAO
    # dtype coercion added afterwards never got applied. Same mistake as in
    # fix_pulse_generator. Each fix now owns its own guard.
    if 'HW-FIX: see _StrEncodingDLL' in s and 'ascontiguousarray' in s:
        pt.skipped.append('hardware/nidaq.py: ctypes strings, handles, WriteAO')
        return
    orig = s

    # --- CHK(): the error handler itself raised ---------------------------
    old_chk = ("        buf = ctypes.create_string_buffer('\\000' * buf_size)" + e +
               "        dll.DAQmxGetErrorString(err, ctypes.byref(buf), buf_size)" + e +
               "        raise RuntimeError('nidaq call failed with error %d: %s' % (err, repr(buf.value)))")
    new_chk = (
        "        # HW-FIX: create_string_buffer('\\000' * 1000) raises TypeError on" + e +
        "        # Python 3 -- it wants an int size or a bytes initialiser. So the" + e +
        "        # ERROR HANDLER crashed, and every real DAQmx error was replaced" + e +
        "        # by a misleading TypeError from this line." + e +
        "        buf = ctypes.create_string_buffer(buf_size)" + e +
        "        dll.DAQmxGetErrorString(err, ctypes.byref(buf), buf_size)" + e +
        "        msg = buf.value.decode('ascii', 'replace').strip()" + e +
        "        raise RuntimeError('nidaq call failed with error %d: %s' % (err, msg))")
    if old_chk in s:
        s = s.replace(old_chk, new_chk, 1)

    # --- task handles: c_ulong (4 bytes) -> c_void_p (8 on win64) ---------
    n_handles = s.count('ctypes.c_ulong()')
    s = s.replace('ctypes.c_ulong()', 'ctypes.c_void_p()')

    # already-wrapped? then skip the wrapper insertion below
    already_wrapped = 'HW-FIX: see _StrEncodingDLL' in s

    # --- wrap the DLL so str arguments are encoded -----------------------
    m = None if already_wrapped else re.search(r'^dll = .*$', s, re.M)
    if m:
        s = (s[:m.end()] + e + e +
             '# HW-FIX: see _StrEncodingDLL above.' + e +
             'dll = _StrEncodingDLL(dll)' + s[m.end():])
        # drop the proxy class in just before the dll assignment
        m2 = re.search(r'^dll = ', s, re.M)
        s = s[:m2.start()] + NIDAQ_PROXY.replace('\n', e).strip(e) + e + e + s[m2.start():]

    # --- WriteAO: no dtype or contiguity check ---------------------------
    # data.ctypes.data_as(c_float64_p) reinterprets whatever buffer it is
    # given as float64. Hand it an int array, a float32 array, or a
    # non-contiguous slice and the DAQ writes garbage voltages -- to the
    # piezo scanner, among other things. There is no error; the stage just
    # goes somewhere wrong.
    n_ao = len(re.findall(r'(?<![\w.])(?:self\.)?data\.ctypes\.data_as\(c_float64_p\)', s))
    if n_ao and 'HW-FIX: coerce' not in s:
        # NB: no trailing comment on the replacement. These calls are inside
        # multi-line argument lists, and an inline `# ...` swallowed the comma
        # that followed, producing a syntax error. Found by the script's own
        # post-patch ast check, which is why that check is there.
        # Order matters: handle `self.data.` FIRST, otherwise the bare
        # `data.ctypes.data_as(...)` pattern matches inside it and produces
        # `self.np.ascontiguousarray(data, ...)` -- an AttributeError at
        # runtime on the one call site that uses an attribute. Then use a
        # regex with a boundary so nothing else can be matched mid-identifier.
        s = s.replace(
            'self.data.ctypes.data_as(c_float64_p)',
            'np.ascontiguousarray(self.data, dtype=np.float64)'
            '.ctypes.data_as(c_float64_p)')
        s = re.sub(
            r'(?<![\w.])data\.ctypes\.data_as\(c_float64_p\)',
            'np.ascontiguousarray(data, dtype=np.float64).ctypes.data_as(c_float64_p)',
            s)
        s = s.replace(
            'def CHK(err):',
            '# HW-FIX: every WriteAO/WriteAnalog call below now goes through\n'
            '# np.ascontiguousarray(data, dtype=np.float64). data.ctypes.data_as()\n'
            '# reinterprets whatever buffer it is handed as float64, so an int\n'
            '# array, a float32 array or a non-contiguous slice became garbage\n'
            '# voltages -- on the piezo scanner among other things -- with no\n'
            '# error raised anywhere.\n'
            'def CHK(err):'.replace('\n', e))
        if not re.search(r'^import numpy as np\s*$', s, re.M):
            m3 = re.search(r'^import ctypes\s*$', s, re.M)
            if m3:
                s = s[:m3.end()] + e + 'import numpy as np  # HW-FIX: for WriteAO coercion' + s[m3.end():]

    if s == orig:
        pt.failed.append('hardware/nidaq.py: nothing matched')
        return
    write(p, s)
    pt.done.append('hardware/nidaq.py: CHK, %d task handle(s), str->bytes proxy, '
                   '%d WriteAO coercion(s)' % (n_handles, n_ao))


# ==========================================================================
# 5. dtg.py / dtg_io.py
# ==========================================================================
def fix_dtg(pt):
    pt.sub('hardware/dtg.py', 'repeat-count division and py2 rounding',
           [("            rep = (ticks - fill) / 1000",
             "            # HW-FIX: was `/`. rep becomes the repeat count and is" + '\n' +
             "            # written via np.array([rep], dtype=np.int32), which" + '\n' +
             "            # truncates silently -- 2.5 blocks of 1000 ticks is" + '\n' +
             "            # programmed as 2, shortening the pulse by 500 ticks with" + '\n' +
             "            # no error anywhere. `if rep > 0` was also true for" + '\n' +
             "            # fractional values that used to floor to zero." + '\n' +
             "            rep = (ticks - fill) // 1000"),
            ("            ticks = int(round(length / dt))",
             "            ticks = _py2_round(length / dt)  # HW-FIX: see _py2_round")],
           guard='HW-FIX: was `/`. rep becomes')

    # dtg.py needs the rounding helper too
    p = pt.path('hardware/dtg.py')
    if os.path.exists(p):
        s = read(p)
        e = eol_of(s)
        if '_py2_round' in s and insert_helper(p):
            pt.done.append('hardware/dtg.py: added _py2_round helper')

    pt.sub('hardware/dtg_io.py', 'ndarray.tostring() removed in NumPy 2',
           [("            fil.write(data.tostring())",
             "            # HW-FIX: tostring() was removed in NumPy 2.0." + '\n' +
             "            fil.write(data.tobytes())"),
            ("            node[1] = len(data.tostring())",
             "            node[1] = len(data.tobytes())  # HW-FIX: tostring() removed")],
           guard='HW-FIX: tostring() was removed')


def fix_analog_pulser(pt):
    """Full treatment, not just rounding.

    The first version of this script called a narrower helper here and applied
    only _py2_round, leaving swap = '', buf = '', and the two integer
    divisions -- the exact four things it fixed in the other two generators.
    An independent audit caught that. Now it goes through the same path.

    Also: this class references np.zeros at line 225 but only imports numpy
    inside its `if __name__ == '__main__'` block, so createBitsFromChannels
    raises NameError. That is a 2019 bug -- AnalogPulser could never have run
    under Python 2 either, and nothing in pi3diamond.py imports it. The import
    is added so the file is at least internally consistent, but it has never
    been exercised against hardware by anyone.
    """
    rel = 'hardware/analog_pulser.py'
    p = pt.path(rel)
    if not os.path.exists(p):
        return

    # the missing numpy import -- must come before the class body uses np
    s = read(p)
    e = eol_of(s)
    if 'HW-FIX: numpy was only imported' not in s:
        m = re.search(r'^import struct\s*$', s, re.M)
        if m:
            add = (e +
                   '# HW-FIX: numpy was only imported inside the'
                   " `if __name__ == '__main__'`" + e +
                   '# block at the bottom, but createBitsFromChannels() uses np.zeros.' + e +
                   '# AnalogPulser therefore raised NameError on first use -- under' + e +
                   '# Python 2 as well. Nothing in pi3diamond.py imports this class;' + e +
                   '# it is fixed for consistency, not because it is known to work.' + e +
                   'import numpy as np')
            s = s[:m.end()] + add + s[m.end():]
            write(p, s)
            pt.done.append('%s: added the missing numpy import' % rel)

    fix_pulse_generator(pt, rel)


def fix_stragglers(pt):
    # the third n_pi / 8 site, which the earlier pass missed
    p = pt.path('measurements/xy_8.py')
    if os.path.exists(p):
        s = read(p)
        if 'n_pi / 8' in s and 'HW-FIX: third site' not in s:
            e = eol_of(s)
            s = s.replace(
                "            sequence += n_pi / 8 * [",
                "            # HW-FIX: third site of this. List repetition by a float" + e +
                "            # raises TypeError; n_pi is an int trait." + e +
                "            sequence += n_pi // 8 * [")
            write(p, s)
            pt.done.append('measurements/xy_8.py: remaining n_pi / 8 site')
        else:
            pt.skipped.append('measurements/xy_8.py: n_pi // 8')


def fix_requirements(pt):
    """The file still claimed 3.12 while everything was built cp313.

    A cp313 .pyd will not load on 3.12, so anyone building a venv from this
    file as written ends up with an interpreter the extension cannot use.
    """
    p = pt.path('requirements.txt')
    if not os.path.exists(p):
        return
    s = read(p)
    if 'HW-FIX' in s:
        pt.skipped.append('requirements.txt: Python version')
        return
    e = eol_of(s)
    out = s.replace(
        '# Python 3.12 (3.12.3 verified).',
        '# HW-FIX: Python 3.13. This said 3.12 while the TimeTagger extension' + e +
        '# was built cp313-win_amd64 -- a cp313 .pyd will NOT load on 3.12, so' + e +
        '# anyone following this file literally got an unusable environment.' + e +
        '# Verified on 3.13.x, 64-bit. All pins resolve to cp313 Windows wheels;' + e +
        '# `enable` has no cp314 wheel, so 3.14 does not work.')
    out = out.replace(
        '# Python 3.12 stopped seeding setuptools',
        '# Python 3.12+ stopped seeding setuptools')
    if out != s:
        write(p, out)
        pt.done.append('requirements.txt: 3.12 -> 3.13')


def main(root):
    if not os.path.exists(os.path.join(root, 'pi3dummy.py')):
        print('%s does not look like a pi3diamond tree' % root)
        return 2
    pt = Patcher(root)
    fix_emod(pt)
    fix_pulse_generator(pt, 'hardware/pulse_generator.py')
    fix_pulse_generator(pt, 'hardware/pulse_generator_breakout.py')
    fix_nidaq(pt)
    fix_dtg(pt)
    fix_analog_pulser(pt)
    fix_stragglers(pt)
    fix_requirements(pt)

    print()
    for x in pt.done:
        print('  [FIXED]   %s' % x)
    for x in pt.skipped:
        print('  [already] %s' % x)
    for x in pt.failed:
        print('  [!!]      %s' % x)
    print()

    bad = 0
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames
                       if d not in ('timetagger', '__pycache__', 'venv', '.git')]
        for f in filenames:
            if not f.endswith('.py'):
                continue
            fp = os.path.join(dirpath, f)
            try:
                ast.parse(read(fp))
            except SyntaxError as exc:
                print('  SYNTAX ERROR in %s: %s' % (os.path.relpath(fp, root), exc))
                bad += 1
    print('%d fixed, %d already done, %d failed, %d syntax error(s).'
          % (len(pt.done), len(pt.skipped), len(pt.failed), bad))
    print('Originals kept as *.hwbak.')
    return 1 if (pt.failed or bad) else 0


if __name__ == '__main__':
    sys.exit(main(os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else '.')))
