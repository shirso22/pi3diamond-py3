#!/usr/bin/env python3
"""
patch_dummy_backend.py -- OPTIONAL. Not part of the port.

`hardware/dummy.py` has drifted behind the measurement code. It is missing
methods and whole classes that `measurements/` calls, so `pi3dummy.py` builds
every window and then errors the moment you press submit:

    AttributeError: 'PulseGenerator' object has no attribute 'setSequence'
    AttributeError: 'TimeTagger' object has no attribute 'PulsedExtTrig'

This is a pre-existing gap, not a Python 3 problem -- the same failure happens
under Python 2. The real driver `hardware/pulse_generator.py` grew
`setSequence()`, `hardware/nidaq.py` grew a start/read/stop counter protocol,
and the real microwave sources grew `Sweep()`; nobody mirrored any of it into
the dummy.

Kept separate from `port_pipeline.py` on purpose. Porting means "same
behaviour on a new interpreter". This adds behaviour that was never there.
Run it only if you want pi3dummy to actually execute a measurement rather than
just open its windows.

    python3 patch_dummy_backend.py            # current directory
    python3 patch_dummy_backend.py /path/to/ported/tree

Run it from the repo root -- the one containing pi3dummy.py and hardware/.

Idempotent: a second run reports "already present" and writes nothing. It
prints the full path of the file it modified; check that line to confirm it
found the tree you meant.
"""

import os
import sys

MARKER = 'DUMMY-SHIM'

PULSE_GENERATOR = '''
    def setSequence(self, sequence, loops=-1, triggered=False, padding=[]):
        """DUMMY-SHIM: mirrors hardware/pulse_generator.py:setSequence().

        The dummy only ever had Sequence(sequence, loop). The real driver
        signature grew `triggered` and `padding`; both are accepted and
        ignored here, since nothing is being pulsed.
        """
        return self.Sequence(sequence, loops)
'''

COUNTER = '''
    def start(self):
        """DUMMY-SHIM: measurements drive a start/read/stop protocol that
        hardware/nidaq.py provides and the dummy never grew. There is nothing
        to arm here, so this just resets the accumulator."""
        self.clear()

    def read(self):
        """DUMMY-SHIM: returns (counts, analog_in), matching nidaq's counter.

        The dummy's own run() is what produces a sweep, so read() delegates to
        it. The second element is the AI trace; measurements unpack it as
        `counts, self.ai = self.counter.read()` and tolerate None.
        """
        return self.run(), None

    def stop(self):
        """DUMMY-SHIM: no hardware to quiesce."""
        return
'''

TIMETAGGER = '''
    class PulsedExtTrig(Pulsed):
        """DUMMY-SHIM: externally triggered Pulsed measurement.

        Signature mirrors the real C++ class in
        timetagger/backend/PulsedExtTrig.cpp:36 --

            PulsedExtTrig(int length, long long binwidth, int sequence_length,
                          int channel, int channel2, int shot_trigger=-1,
                          int sequence_trigger=-1, int bin_trigger=-1,
                          int trig1=-1, int trig2=-1, bool dual_sequence=true)

        Inheriting Pulsed's 7-argument __init__ is not enough: the call in
        deer_spectroscopy.py passes 11 and raised
            TypeError: Pulsed.__init__() takes from 7 to 8 positional
                       arguments but 12 were given

        hardware/dummy.py's TimeTagger only ever had Pulsed, Counter and
        Countrate. measurements/deer_spectroscopy.py calls PulsedExtTrig, so
        both DEER Spectroscopy variants died with

            AttributeError: 'TimeTagger' object has no attribute 'PulsedExtTrig'

        The real class waits on an external trigger and tracks sweep state.
        With no hardware there is nothing to trigger on, so this inherits the
        Pulsed dummy's synthetic data and adds the extra methods the
        measurement calls.
        """

        def __init__(self, n_bins, bin_width, sequence_length, channel_apd_0,
                     channel_apd_1, shot_trigger=-1, sequence_trigger=-1,
                     bin_trigger=-1, trig1=-1, trig2=-1, dual_sequence=True):
            # super(), not Pulsed.__init__: these are classes nested inside
            # TimeTagger, and a nested class body is not an enclosing scope for
            # its own methods, so the bare name `Pulsed` is unresolvable here
            # even though it works as a base class in the class statement.
            super().__init__(n_bins, bin_width, sequence_length,
                             channel_apd_0, channel_apd_1, shot_trigger,
                             sequence_trigger)
            self.bin_trigger = bin_trigger
            self.trig1 = trig1
            self.trig2 = trig2
            self.dual_sequence = dual_sequence

        def resetSweep(self):
            self.clear()

        def getSequenceNumber(self):
            return 0

        def getPulse(self):
            return self.getData()

    class PulsedAFM(Pulsed):
        """DUMMY-SHIM: AFM variant. Same reasoning as PulsedExtTrig."""
        pass
'''

SQUAREWAVE_CLASS = '''

class SquareWave(object):
    """DUMMY-SHIM: stand-in for hardware/nidaq.py's SquareWave.

    measurements/deer_spectroscopy.py is the one measurement that does NOT
    take its hardware by injection -- every other dependency arrives through
    __init__ (pulse_generator, time_tagger, microwave, rf), but line 28 does

        from hardware.nidaq import SquareWave

    and constructs it directly. So the measurement reaches into a real NI-DAQ
    driver no matter what pi3dummy passes it, and on a machine without
    NI-DAQmx installed it dies with

        OSError: nicaiu.dll could not be loaded

    That is pre-existing: the same failure happens under Python 2. Only
    output() is ever called on the object.
    """

    def __init__(self, square_wave_device, length=100, seconds_per_point=1e-3,
                 duty_cycle=0.5):
        self._square_wave_device = square_wave_device
        self._length = length
        self._seconds_per_point = seconds_per_point
        self._duty_cycle = duty_cycle

    def set_timing(self, seconds_per_point, duty_cycle=0.5):
        self._seconds_per_point = seconds_per_point
        self._duty_cycle = duty_cycle

    def get_timing(self):
        return self._seconds_per_point, self._duty_cycle

    def setLength(self, length):
        self._length = length

    def getLength(self):
        return self._length

    def output(self):
        """No hardware to drive. Sleep for the duration the real pulse train
        would have taken, so the measurement's timing still looks plausible."""
        import time as _time
        _time.sleep(min(self._length * self._seconds_per_point, 1.0))
'''

MICROWAVE = '''
    def Sweep(self, begin, end, delta, power):
        """DUMMY-SHIM: the real sources expose Sweep(); the dummy only had
        initSweep(). Delegates so the frequency list is still built."""
        import numpy
        frequencies = numpy.arange(begin, end + delta, delta)
        return self.initSweep(frequencies, power * numpy.ones(frequencies.shape))
'''


def patch(path, classname, body):
    """Insert `body` at the end of `classname`. Idempotent, AST-based.

    An earlier text-matching version of this check reported "already present"
    for Counter because the word `start` occurs elsewhere in the file. Locate
    the class properly instead.
    """
    import ast

    src = open(path, 'rb').read().decode('utf-8')
    eol = '\r\n' if '\r\n' in src else '\n'
    tree = ast.parse(src)

    node = None
    for n in tree.body:
        if isinstance(n, ast.ClassDef) and n.name == classname:
            node = n
            break
    if node is None:
        print('  !! class %s not found in %s' % (classname, path))
        return src, False

    have = {m.name for m in node.body
            if isinstance(m, (ast.FunctionDef, ast.ClassDef))}
    # Only the definitions at the OUTERMOST indent of `body` become direct
    # members of the class. An earlier version scanned every `def` line,
    # which picked up methods nested inside PulsedExtTrig -- those are never
    # members of TimeTagger, so the check never matched and the block was
    # appended on every run.
    defs = [ln for ln in body.splitlines()
            if ln.strip().startswith(('def ', 'class '))]
    base = min((len(ln) - len(ln.lstrip()) for ln in defs), default=0)
    wanted = set()
    for ln in defs:
        if len(ln) - len(ln.lstrip()) != base:
            continue
        kw = 'def ' if ln.strip().startswith('def ') else 'class '
        wanted.add(ln.split(kw, 1)[1].split('(')[0].rstrip(':').strip())
    if wanted <= have:
        print('  already present: %s (%s)' % (classname, ', '.join(sorted(wanted))))
        return src, False

    lines = src.split(eol)
    insert_at = node.end_lineno          # 1-based, exclusive end of the class
    block = body.replace('\n', eol).strip(eol)
    lines[insert_at:insert_at] = [''] + block.split(eol)
    return eol.join(lines), True


def main(root):
    path = os.path.join(root, 'hardware', 'dummy.py')
    if not os.path.exists(path):
        print('not found: %s' % path)
        return 2

    changed = 0
    # SquareWave is a whole top-level class, not a method on an existing one
    dummy_src = open(path, 'rb').read().decode('utf-8')
    if 'class SquareWave' not in dummy_src:
        eol = '\r\n' if '\r\n' in dummy_src else '\n'
        open(path, 'wb').write(
            (dummy_src.rstrip(eol) + eol + eol +
             SQUAREWAVE_CLASS.replace('\n', eol).strip(eol) + eol).encode('utf-8'))
        print('  added SquareWave')
        changed += 1
    else:
        print('  already present: SquareWave')

    # and route deer_spectroscopy at it when the NI driver is absent
    ds = os.path.join(root, 'measurements', 'deer_spectroscopy.py')
    if os.path.exists(ds):
        src = open(ds, 'rb').read().decode('utf-8')
        old = 'from hardware.nidaq import SquareWave'
        if old in src and 'DUMMY-SHIM' not in src:
            eol = '\r\n' if '\r\n' in src else '\n'
            new = (
                '# DUMMY-SHIM: this is the only measurement that reaches for a real'
                + eol +
                '# hardware driver directly instead of taking it by injection. Probe'
                + eol +
                '# for the NI-DAQmx runtime and fall back to the dummy when it is not'
                + eol +
                '# installed, so pi3dummy can run this measurement on a plain laptop.'
                + eol +
                '# On the real rig the probe succeeds and the real driver is used.'
                + eol +
                'try:' + eol +
                '    import ctypes as _ctypes' + eol +
                '    _ctypes.windll.LoadLibrary(\'nicaiu.dll\')' + eol +
                '    from hardware.nidaq import SquareWave' + eol +
                'except Exception:' + eol +
                '    import logging as _logging' + eol +
                '    _logging.getLogger().info(' + eol +
                '        \'NI-DAQmx not available; using the dummy SquareWave.\')' + eol +
                '    from hardware.dummy import SquareWave')
            open(ds, 'wb').write(src.replace(old, new, 1).encode('utf-8'))
            print('  routed deer_spectroscopy.SquareWave to the dummy fallback')
            changed += 1
        else:
            print('  already present: deer_spectroscopy SquareWave fallback')

    for classname, body in (('PulseGenerator', PULSE_GENERATOR),
                            ('Counter', COUNTER),
                            ('Microwave', MICROWAVE),
                            ('TimeTagger', TIMETAGGER)):
        src, did = patch(path, classname, body)
        if did:
            open(path, 'wb').write(src.encode('utf-8'))
            print('  patched %s' % classname)
            changed += 1

    print('\n%d class(es) patched in %s' % (changed, path))
    print('Verify with:  python3 -c "import ast;ast.parse(open(%r).read())"' % path)
    return 0


if __name__ == '__main__':
    # Defaults to the current directory, matching fix_numpy2_aliases.py.
    # An earlier version required the argument and printed usage without it,
    # which reads exactly like a successful no-op if you are not looking
    # closely -- the run reports nothing patched and nothing wrong.
    if len(sys.argv) > 2:
        print(__doc__)
        sys.exit(2)
    sys.exit(main(sys.argv[1] if len(sys.argv) == 2 else '.'))
