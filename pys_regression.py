#!/usr/bin/env python
"""
pys_regression.py -- catch silent numerical drift between the Python 2 and
Python 3 versions of pi3diamond.

The Tier A divisions in DIVISION_REVIEW.md do not raise. They return a number.
The number may differ from every measurement you have ever taken, and nothing
will tell you. This is the only thing that will tell you.

Two phases:

  1. CAPTURE, run under your existing Python 2.7 install:

         python2 pys_regression.py capture /path/to/data baseline/

     Walks every .pys/.pyd under /path/to/data, unpickles it with the
     Python 2 interpreter that wrote it, and freezes the contents to .npz.

  2. COMPARE, run under Python 3 with the ported code:

         python3 pys_regression.py compare /path/to/data baseline/

     Reloads the same files through the ported loader and diffs against the
     frozen baseline.

This file is deliberately written to run on BOTH 2.7 and 3.x. No f-strings,
no keyword-only arguments, no pathlib. Do not "modernise" it -- phase 1 has to
execute on the old interpreter or the whole exercise is pointless.

Exit codes: 0 clean, 1 mismatches found, 2 usage/IO error.


WHAT THIS COVERS, AND WHAT IT DOES NOT
--------------------------------------

Covers: the loader path. Every stored array in your archive, read by the old
interpreter and by the new one, compared element by element. If the pickle
changes, the encoding fallback misfires, or an array comes back with a
different dtype or shape, you find out here.

Does NOT cover: anything computed at acquisition time. `int(round(time / dt))`
in the three pulse generators never touches a .pys file -- it produces a tick
count that goes straight down a USB cable. No amount of comparing stored data
will catch it.

For that path, do the same trick against the pure-Python half of the drivers.
`dtg.sequence_to_dtg_data()`, `pulse_generator.convert_sequence()` and
`analog_pulser`'s equivalent all turn a sequence description into blocks and
bit patterns without talking to hardware. Call them under both interpreters
with an identical input sequence, pickle the returned structures, and diff.
`hardware/dtg.py:288` (`rep = (ticks - fill) / 1000`, which then lands in an
int32 repeat count) shows up immediately under that test and under no other.
"""

from __future__ import print_function

import os
import sys
import traceback

import numpy as np

try:
    import cPickle as pickle_mod           # Python 2
    PY2 = True
except ImportError:
    import pickle as pickle_mod            # Python 3
    PY2 = False

DATA_SUFFIXES = ('.pys', '.pyd')

# Tolerances. Exact equality is checked first; these only decide whether a
# difference gets reported as DRIFT (probably float noise) or MISMATCH
# (something actually changed).
RTOL = 1e-12
ATOL = 0.0


# --------------------------------------------------------------------------
def load_any(path):
    """Unpickle under either interpreter.

    Under Python 3 the latin-1 fallback matters: Python 2 pickled `str` as
    bytes, so without an explicit codec every string in a historical file
    either raises UnicodeDecodeError or comes back as bytes. latin-1 maps
    bytes 0-255 one-to-one, so numpy arrays and ASCII dict keys both survive.
    """
    fil = open(path, 'rb')
    try:
        data = fil.read()
    finally:
        fil.close()

    if PY2:
        return pickle_mod.loads(data)

    try:
        return pickle_mod.loads(data)
    except (UnicodeDecodeError, TypeError):
        return pickle_mod.loads(data, encoding='latin1')


def flatten(obj, prefix=''):
    """Walk a nested dict/list into a flat {dotted.key: leaf} mapping."""
    out = {}
    if isinstance(obj, dict):
        for k in obj:
            key = k.decode('latin1') if isinstance(k, bytes) else str(k)
            out.update(flatten(obj[k], prefix + key + '.'))
    elif isinstance(obj, (list, tuple)) and obj and not _is_numeric(obj[0]):
        for i, v in enumerate(obj):
            out.update(flatten(v, prefix + str(i) + '.'))
    else:
        out[prefix.rstrip('.')] = obj
    return out


def _is_numeric(v):
    return isinstance(v, (int, float, complex, np.generic, np.ndarray))


def to_array(v):
    """Coerce a leaf to something np.savez can store, or None to skip it."""
    if isinstance(v, np.ndarray):
        return v if v.dtype != np.dtype('O') else None
    if isinstance(v, (int, float, complex, np.generic)):
        return np.array(v)
    if isinstance(v, (list, tuple)):
        try:
            a = np.array(v)
            return a if a.dtype != np.dtype('O') else None
        except Exception:
            return None
    return None


def data_files(root):
    found = []
    for dirpath, dirnames, filenames in os.walk(root):
        for f in sorted(filenames):
            if f.endswith(DATA_SUFFIXES):
                found.append(os.path.join(dirpath, f))
    return sorted(found)


def baseline_path(out_dir, data_root, path):
    rel = os.path.relpath(path, data_root)
    safe = rel.replace(os.sep, '__') + '.npz'
    return os.path.join(out_dir, safe)


# --------------------------------------------------------------------------
def capture(data_root, out_dir):
    if not PY2:
        print('WARNING: capture is running under Python 3. The point of this')
        print('phase is to read the files with the interpreter that WROTE')
        print('them. Run it under python2 or the baseline proves nothing.\n')

    if not os.path.isdir(out_dir):
        os.makedirs(out_dir)

    files = data_files(data_root)
    print('%d data files under %s\n' % (len(files), data_root))

    ok = skipped = failed = 0
    for path in files:
        try:
            flat = flatten(load_any(path))
        except Exception:
            print('FAILED  %s' % path)
            traceback.print_exc()
            failed += 1
            continue

        arrays = {}
        dropped = []
        for k in flat:
            a = to_array(flat[k])
            if a is None:
                dropped.append(k)
            else:
                arrays[k] = a

        if not arrays:
            skipped += 1
            continue

        np.savez_compressed(baseline_path(out_dir, data_root, path), **arrays)
        ok += 1
        if dropped:
            print('  %s: %d non-numeric key(s) not frozen: %s'
                  % (os.path.basename(path), len(dropped),
                     ', '.join(sorted(dropped)[:4])))

    print('\ncaptured %d, skipped %d (nothing numeric), failed %d'
          % (ok, skipped, failed))
    return 0 if failed == 0 else 1


# --------------------------------------------------------------------------
def compare(data_root, base_dir):
    if PY2:
        print('ERROR: compare must run under Python 3, against the ported code.')
        return 2

    files = data_files(data_root)
    print('%d data files under %s\n' % (len(files), data_root))

    checked = clean = drift = mismatch = missing = 0
    problems = []

    for path in files:
        bpath = baseline_path(base_dir, data_root, path)
        if not os.path.exists(bpath):
            missing += 1
            continue

        try:
            flat = flatten(load_any(path))
        except Exception as exc:
            problems.append((path, '<file>', 'load failed: %s' % exc))
            mismatch += 1
            continue

        base = np.load(bpath, allow_pickle=False)
        checked += 1
        file_bad = False

        for key in base.files:
            want = base[key]
            if key not in flat:
                problems.append((path, key, 'key absent after port'))
                file_bad = True
                continue

            got = to_array(flat[key])
            if got is None:
                problems.append((path, key, 'no longer numeric'))
                file_bad = True
                continue

            if got.shape != want.shape:
                problems.append((path, key, 'shape %s -> %s'
                                 % (want.shape, got.shape)))
                file_bad = True
                continue

            if np.array_equal(got, want):
                continue

            # Not bit-identical. How bad?
            try:
                if np.allclose(got, want, rtol=RTOL, atol=ATOL, equal_nan=True):
                    problems.append((path, key, 'DRIFT within %g rtol' % RTOL))
                    drift += 1
                    continue
                diff = np.abs(np.asarray(got, dtype=float)
                              - np.asarray(want, dtype=float))
                scale = np.maximum(np.abs(np.asarray(want, dtype=float)), 1e-30)
                problems.append((path, key,
                                 'MISMATCH  max abs %.6g  max rel %.6g'
                                 % (np.nanmax(diff), np.nanmax(diff / scale))))
            except Exception:
                problems.append((path, key, 'MISMATCH (uncomparable dtypes)'))
            file_bad = True

        if not file_bad:
            clean += 1

    for path, key, msg in problems:
        print('%s\n    [%s] %s' % (path, key, msg))

    print('\n--- summary ---')
    print('  compared        %d' % checked)
    print('  identical       %d' % clean)
    print('  drifting        %d key(s)' % drift)
    print('  no baseline     %d file(s)' % missing)
    print('  problem files   %d' % (checked - clean))

    if checked - clean:
        print('\nCross-reference the affected modules against Tier A in')
        print('DIVISION_REVIEW.md. Integer division is the first thing to')
        print('suspect, and `int(round(x / y))` is the first idiom to check.')
        return 1
    return 0


# --------------------------------------------------------------------------
def main(argv):
    if len(argv) != 4 or argv[1] not in ('capture', 'compare'):
        print(__doc__)
        return 2
    if not os.path.isdir(argv[2]):
        print('not a directory: %s' % argv[2])
        return 2
    if argv[1] == 'capture':
        return capture(argv[2], argv[3])
    if not os.path.isdir(argv[3]):
        print('baseline directory does not exist: %s' % argv[3])
        return 2
    return compare(argv[2], argv[3])


if __name__ == '__main__':
    sys.exit(main(sys.argv))
