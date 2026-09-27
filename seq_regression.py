#!/usr/bin/env python
"""
seq_regression.py -- compare the PULSE PATTERNS the code generates under
Python 2 and Python 3, without any hardware attached.

    # in the OLD Python 2.7 tree, with the original code:
    python2 seq_regression.py capture seq_baseline.pkl

    # in the PORTED tree, under Python 3:
    python  seq_regression.py compare seq_baseline.pkl

WHY THIS IS THE TEST THAT MATTERS

pys_regression.py compares STORED DATA. It cannot see anything computed at
acquisition time -- and that is exactly where the dangerous changes live. A
pulse generator turns a sequence description into bit patterns and block
data in pure Python, then pushes the bytes down a USB cable. If the port
programs different bits, no stored file will ever tell you; the measurement
just quietly means something else.

These functions need no hardware:

    PulseGenerator.convertSequenceToBinary()   hardware/pulse_generator.py
    AnalogPulser.convertSequenceToBinary()     hardware/analog_pulser.py
    DTG.sequence_to_dtg_data()                 hardware/dtg.py

so both interpreters can build the same sequences on a laptop and the bytes
can be diffed directly.

WHAT IT WOULD HAVE CAUGHT

Every bug an independent audit found on this path, before any of it reached
an instrument:

  * `buf = ''` and byte-string building -- TypeError, no sequence at all
  * `repetitions = ticks / CHANNEL_WIDTH` -- float into struct.pack('>I')
  * `int(round(t/dt))` -- Python 3 rounds halves to even, so on the 24x4 core
    a 1 ns pulse becomes 0 ticks and `if ticks == 0: continue` DROPS IT
  * `rep = (ticks - fill) / 1000` in dtg.py -- truncated into an int32 repeat
    count, silently shortening a 2500-tick pulse to 2000

The rounding and the dtg one are the frightening pair: they do not raise.

This file runs on BOTH 2.7 and 3.x. No f-strings, no annotations. Do not
modernise it -- phase one has to execute on the old interpreter.
"""

from __future__ import print_function

import hashlib
import os
import pickle
import sys
import traceback
import types

# --------------------------------------------------------------------------
# Test sequences. Deliberately chosen to land on the boundaries where the
# interpreters disagree: odd nanosecond times against dt = 1.5 and 2.0, times
# that straddle a block, and repeat counts either side of 1000 ticks.
# --------------------------------------------------------------------------
SEQUENCES = [
    ('trivial',
     [(['aom'], 1000.), ([], 1000.)]),

    ('odd_ns_rounding',
     # 1, 3, 5, 7, 9 ns: py2 round() and py3 round() disagree on several of
     # these for both dt values. A 1 ns pulse vanishes on the 24x4 core.
     [(['mw_x'], 1.), ([], 3.), (['mw_x'], 5.), ([], 7.), (['mw_x'], 9.),
      ([], 1000.)]),

    ('quarter_ns_rounding',
     # exposes dt = 1.5 (12x8 core): 0.75, 2.25, 3.75 ...
     [(['mw_x'], 0.75), ([], 2.25), (['mw_x'], 3.75), ([], 5.25),
      (['mw_x'], 6.75), ([], 1000.)]),

    ('block_straddle',
     # times chosen so pulses cross the 8-tick CHANNEL_WIDTH boundary
     [(['aom'], 12.), (['mw'], 4.), ([], 20.), (['detect', 'aom'], 7.),
      ([], 1000.)]),

    ('long_repeat',
     # > 1000 ticks, so dtg.py's repeat-block path is exercised either side
     # of the /1000 division
     [(['aom'], 1500.), ([], 3750.), (['mw_x'], 2500.), ([], 999.),
      (['aom'], 1001.)]),

    ('rabi_like',
     # roughly what measurements/rabi.py emits
     [(['mw_x'], 25.), ([], 300.), (['detect', 'aom'], 3000.), ([], 1000.),
      (['mw_x'], 50.), ([], 300.), (['detect', 'aom'], 3000.), ([], 1000.)]),

    ('many_channels',
     [(['aom', 'mw', 'mw_x', 'detect'], 100.), ([], 100.),
      (['rf', 'sequence'], 50.), ([], 1000.)]),
]

CHANNEL_MAP = {'detect': 0, 'mw': 1, 'microwave': 1, 'mw_x': 1, 'rf': 2,
               'sequence': 3, 'mwy': 4, 'mw_y': 4, 'aom': 5, 'ch5': 5,
               'ch6': 6, 'awgTrigger': 6, 'microwave2': 7, 'mw2': 7}

CORES = [('12x8', 1.5, 12, 8), ('24x4', 2.0, 24, 4)]


# --------------------------------------------------------------------------
def stub_hardware():
    """Put fakes in sys.modules for the vendor bindings, so the pure-Python
    sequence code can be imported without a board or a DLL."""

    class _Any(object):
        def __init__(self, *a, **k):
            pass

        def __call__(self, *a, **k):
            return 0

        def __getattr__(self, n):
            return _Any()

    for name in ('hardware.ok', 'ok'):
        m = types.ModuleType(name)
        m.FrontPanel = _Any
        m.PLL22150 = _Any
        m.okCFrontPanel = _Any
        m.okCPLL22150 = _Any
        sys.modules.setdefault(name, m)


def make_pulse_generator(core, dt, n_channels, channel_width):
    """Build a PulseGenerator without running __init__, which opens the FPGA."""
    from hardware.pulse_generator import PulseGenerator
    pg = PulseGenerator.__new__(PulseGenerator)
    pg.core = core
    pg.dt = dt
    pg.n_channels = n_channels
    pg.channel_width = channel_width
    pg.channel_map = dict(CHANNEL_MAP)
    return pg


def digest(obj):
    """Stable fingerprint for bytes or a list of (int, ndarray) tuples."""
    h = hashlib.sha256()
    if isinstance(obj, bytes):
        h.update(obj)
        return h.hexdigest(), len(obj)
    try:
        import numpy as np
        for item in obj:
            if isinstance(item, tuple):
                mult, pattern = item
                h.update(str(int(mult)).encode('ascii'))
                h.update(np.asarray(pattern).astype('int64').tobytes())
            else:
                h.update(repr(item).encode('ascii'))
        return h.hexdigest(), len(obj)
    except Exception:
        h.update(repr(obj).encode('ascii'))
        return h.hexdigest(), -1


def collect():
    """Generate every (core, sequence) pattern. Returns a plain dict."""
    stub_hardware()
    out = {}

    for core, dt, n_ch, width in CORES:
        try:
            pg = make_pulse_generator(core, dt, n_ch, width)
        except Exception:
            out[('pulse_generator', core, '<import>')] = (
                'FAILED: ' + traceback.format_exc().strip().split('\n')[-1])
            continue

        for name, seq in SEQUENCES:
            key = ('pulse_generator', core, name)
            try:
                buf = pg.convertSequenceToBinary(seq, loops=-1)
                dig, size = digest(buf)
                raw_dig, n_raw = digest(pg.raw)
                out[key] = {'buf_sha': dig, 'buf_len': size,
                            'raw_sha': raw_dig, 'n_raw': n_raw,
                            'buf_head': _hexhead(buf)}
            except Exception:
                out[key] = ('FAILED: '
                            + traceback.format_exc().strip().split('\n')[-1])

            # tick counts alone, which is where rounding shows up most clearly
            try:
                ticks = []
                for channels, t in seq:
                    ticks.append(_ticks(pg, t))
                out[('ticks', core, name)] = ticks
            except Exception:
                out[('ticks', core, name)] = ('FAILED: '
                    + traceback.format_exc().strip().split('\n')[-1])

    return out


def _ticks(pg, t):
    """Reproduce the conversion the generator does, whatever it currently is."""
    try:
        from hardware.pulse_generator import _py2_round
        return _py2_round(t / pg.dt)
    except ImportError:
        return int(round(t / pg.dt))


def _hexhead(buf, n=32):
    try:
        return buf[:n].hex()
    except AttributeError:                      # Python 2
        return buf[:n].encode('hex')


# --------------------------------------------------------------------------
def capture(out_path):
    py = sys.version_info[0]
    print('running under Python %d.%d' % sys.version_info[:2])
    if py != 2:
        print('')
        print('WARNING: capture is meant to run under Python 2.7, in the OLD')
        print('tree with the ORIGINAL code. Run there, or the baseline is')
        print('just Python 3 compared against itself.')
        print('')

    data = collect()
    fil = open(out_path, 'wb')
    try:
        pickle.dump({'python': sys.version, 'data': data}, fil, protocol=2)
    finally:
        fil.close()

    ok = sum(1 for v in data.values() if not isinstance(v, str))
    bad = len(data) - ok
    print('%d pattern(s) captured, %d failed -> %s' % (ok, bad, out_path))
    for k, v in sorted(data.items(), key=lambda kv: str(kv[0])):
        if isinstance(v, str):
            print('  FAILED %s: %s' % ('/'.join(map(str, k)), v[:90]))
    return 0


def compare(base_path):
    if not os.path.exists(base_path):
        print('no baseline at %s' % base_path)
        return 2
    fil = open(base_path, 'rb')
    try:
        try:
            blob = pickle.load(fil)
        except UnicodeDecodeError:
            fil.seek(0)
            blob = pickle.load(fil, encoding='latin1')
    finally:
        fil.close()

    base = blob['data']
    print('baseline built by: %s' % blob['python'].split()[0])
    print('comparing under  : %s' % sys.version.split()[0])
    print('')

    now = collect()
    same = diff = gone = 0
    problems = []

    for key in sorted(base, key=lambda k: str(k)):
        want = base[key]
        got = now.get(key)
        label = '/'.join(map(str, key))
        if got is None:
            problems.append((label, 'absent in the ported code'))
            gone += 1
            continue
        if isinstance(want, str) or isinstance(got, str):
            if isinstance(want, str) and isinstance(got, str):
                same += 1                       # failed in both; not a change
            else:
                problems.append((label,
                                 'py2: %s\n        py3: %s'
                                 % (_short(want), _short(got))))
                diff += 1
            continue
        if want == got:
            same += 1
            continue
        diff += 1
        problems.append((label, _explain(want, got)))

    for label, msg in problems:
        print('  %s\n        %s' % (label, msg))

    print('')
    print('--- summary ---')
    print('  identical   %d' % same)
    print('  DIFFERENT   %d' % diff)
    print('  missing     %d' % gone)
    if diff or gone:
        print('')
        print('A difference here means the ported code programs different')
        print('pulses than the Python 2 code did. Do not run this on hardware')
        print('until every one is explained.')
        return 1
    print('')
    print('The ported code generates byte-identical pulse patterns.')
    return 0


def _short(v):
    s = v if isinstance(v, str) else repr(v)
    return s if len(s) < 90 else s[:90] + '...'


def _explain(want, got):
    if isinstance(want, list) and isinstance(got, list):
        rows = []
        for i, (a, b) in enumerate(zip(want, got)):
            if a != b:
                rows.append('index %d: py2=%s py3=%s' % (i, a, b))
        extra = ''
        if len(want) != len(got):
            extra = ' (length %d -> %d)' % (len(want), len(got))
        return 'tick counts differ%s\n        %s' % (extra,
                                                     '\n        '.join(rows[:6]))
    if isinstance(want, dict) and isinstance(got, dict):
        rows = []
        for k in sorted(want):
            if want.get(k) != got.get(k):
                rows.append('%s: py2=%s py3=%s'
                            % (k, _short(want.get(k)), _short(got.get(k))))
        return '\n        '.join(rows)
    return 'py2=%s py3=%s' % (_short(want), _short(got))


def main(argv):
    if len(argv) != 3 or argv[1] not in ('capture', 'compare'):
        print(__doc__)
        return 2
    sys.path.insert(0, os.getcwd())
    if argv[1] == 'capture':
        return capture(argv[2])
    return compare(argv[2])


if __name__ == '__main__':
    sys.exit(main(sys.argv))
