# Python 3 port notes

What changed when pi3diamond moved from Python 2.7 / 32-bit to Python 3.13 /
64-bit, why each change was needed, and what was learned along the way. Written
for whoever maintains this next.

Changes in the code are marked with comments so they can be found:
`PY3-PORT` (the original port), `HW-FIX` (fixes found during audit and on
hardware), and `ORANGE-LASER` (the 594 nm laser integration).

---

## 1. Where this code came from

The history matters, because the first attempt at this port started from the
wrong baseline.

| Source | Date | What it is |
|---|---|---|
| GitLab `pi3diamond-master` | July 2019 | Last commit. No longer maintained. |
| Lab PC working tree | up to Sept 2026 | The 2019 commit plus ~1,500 lines of **uncommitted** changes (calibration, new measurements, analysis fixes). This is what actually ran the experiments. |
| Orange-laser branch | 2022–2023 | An older fork carrying the Cobolt laser work. Otherwise *behind* the working tree. |

The port was first done against the 2019 commit. The lab's real code was only
discovered when features were found missing. It was then merged in by a
three-way merge (2019 commit as the common base, the lab tree and the port as
the two sides). Eight small conflicts arose across the merges, all where the port and the lab had
edited the same lines; the lab's experiment logic was kept in every case, with
Python 3 spelling where the two collided. The orange-laser work was then
cherry-picked from its branch rather than taken wholesale, because taking the
branch would have reverted three years of later work.

**Lesson:** establish the real baseline before porting anything. Ask where the
running copy lives, and diff it against the repository. A `.git` directory with
uncommitted changes is common on lab machines.

---

## 2. Changes by category

### 2.1 Native code: the TimeTagger extension

The original `_TimeTagger.pyd` was a 32-bit Python 2.7 binary and cannot load in
any Python 3. The C++ source was in the repository, so it was rebuilt.

- **boost → C++11.** `boost::mutex`, `boost::thread` and the sleep calls were
  replaced by their standard-library equivalents, removing the dependency on
  boost 1.47. `<cassert>`, `<map>` and others, previously pulled in indirectly by
  boost, are now included explicitly.
- **`std::atomic<bool> run`.** The worker-thread stop flag was a plain `bool`
  written by one thread and read by another. Under C++11 that is undefined
  behaviour and can hang shutdown.
- **Worker try/catch.** An exception escaping a worker thread used to kill the
  whole interpreter with no message. It now stops that worker and prints
  `TimeTagger worker thread stopped: ...` to stderr.
- **SWIG `%exception`.** C++ exceptions on wrapped calls now arrive in Python as
  `RuntimeError` (for example `Could not load FrontPanel DLL.`) instead of
  terminating the process. This does not cover worker threads, which is why the
  try/catch above exists.
- **Flattened wrappers restored.** SWIG 4 no longer generates module-level
  functions such as `_Tagger_setSerial`, which `pi3diamond.py` calls.
  `build_timetagger.py` re-adds them as aliases after every build. An early
  version of that script tested for the name with a plain substring search,
  which always matched and so never added them; it now looks for a module-level
  assignment.
- **`_DISABLE_CONSTEXPR_MUTEX_CONSTRUCTOR`.** Guards against a known crash when a
  binary built with recent Visual Studio meets an older `msvcp140.dll` already
  loaded by another package.
- **`numpy.i` pinned** to the NumPy release in `requirements.txt` instead of
  being fetched from NumPy's development branch.

The FPGA bitfile was not changed and does not need to be.

### 2.2 32-bit → 64-bit ctypes

Everything that talks to a vendor DLL through ctypes needed attention, because
code that happened to work on 32-bit is often wrong on 64-bit.

- **NI-DAQ task handles** were `c_ulong` (4 bytes on Windows). On 64-bit
  DAQmx a `TaskHandle` is a pointer (8 bytes), so the DLL wrote past the end of
  the variable. Now `c_void_p`.
- **Strings passed to DAQmx** were Python 3 `str`, which ctypes sends as wide
  characters; DAQmx read `'/Dev1/Ctr0'` as `'/'`. A small wrapper encodes every
  string argument to bytes.
- **Buffer addresses.** `array.ctypes.data` is the address as a plain integer.
  On 32-bit it fitted in a C `int`; on 64-bit it overflows. This killed ODMR on
  the first hardware run. All buffers are now passed with
  `array.ctypes.data_as(pointer_type)`.
- **Read buffers are never copied.** Where DAQmx fills a buffer, the code
  asserts the buffer's type rather than converting it, because a converted copy
  would be filled and then thrown away, returning zeros with no error.
- **Opal Kelly and LabBrick** bindings were rewritten from 32-bit SWIG modules
  to ctypes against the 64-bit vendor DLLs.

### 2.3 Python 2 → 3 semantics

The dangerous changes are the ones that run without error but compute a
different result.

- **Integer division.** `/` between integers now returns a float. Every use near
  timing, sample counts or indexing was reviewed; the ones that meant integer
  division became `//`. Where a float is passed to something that needs an
  integer (a slice, `np.logspace`'s point count), Python 3 now raises instead of
  silently truncating.
- **`round()` rounds halves to even.** On the pulse generator this changed tick
  counts: a 1 ns pulse on the 2 ns core became 0 ticks and was dropped. The
  sequence code uses `_py2_round`, which reproduces Python 2's half-away-from-zero
  rounding. Verified identical to Python 2 over 80,000 values.
- **bytes vs str.** Every serial port, socket and VISA raw read/write now
  encodes on the way out and decodes on the way in. The pulse generator's
  byte-packing was rewritten on `bytearray` and verified byte-identical to the
  Python 2 output.
- **Ordering comparisons.** Python 2 let you compare `None` with numbers, and
  sort lists mixing `None` and strings. Python 3 raises. Two places depended on
  it: `LabBrick.setPower(None)` (Python 2 treated it as "minimum power", which is
  now explicit) and the autofocus target list (sorted with `None` first).
- **Removed builtins.** `cmp()` was used to sort the job queue; its absence
  deadlocked the job manager whenever two jobs were queued, and prevented
  stopping a running measurement. Now sorted by key, and every lock acquisition
  is in `try/finally`.
- **Imports.** Implicit relative imports (`from rabi import Rabi` inside a
  package) became explicit (`from .rabi import Rabi`).
- **Python 2 pickles.** The `defaults/*.pys` files are Python 2 pickles.
  `tools/data_toolbox.load_pickle` falls back to `latin1` decoding so their
  string keys load as `str`, not `bytes`.

### 2.4 Library upgrades

- **NumPy 2** removed `np.NaN`, `np.float`, `ndarray.tostring()` and others, and
  no longer accepts a float as a point count. All occurrences were updated.
- **pyvisa ≥ 1.9** dropped the top-level `visa` module and takes bytes in
  `write_raw`. Timeouts are in milliseconds.
- **pyserial 3** writes bytes and rejects integer port numbers.
- **Traits 7** drops a change notification when the old and new values are the
  same object. The autofocus code mutated its `targets` dictionary in place and
  then announced the change with the same object, so the handler never ran: no
  marker, and the target never appeared in the dropdown. The notification now
  passes a distinct old value. Array traits are not affected, which is why the
  same pattern elsewhere kept working.

### 2.5 Calibration and configuration carried over from the lab

These came from the lab's uncommitted working tree and change what the numbers
mean. They are easy to lose because none of them raises an error if wrong.

- Scanner y-range `(9., 51.)` instead of `(0., 60.)`.
- SMIQ at `GPIB0::28` instead of `GPIB0::4`.
- A spurious ×10 removed from the power-meter reading.
- `invert_x` scanner option.
- Each instrument in `pi3diamond.py` constructed in its own `try/except`.

### 2.6 Bugs that predated the port

Several modules were broken under Python 2 as well and were fixed while in them:
the HMP2030/relay-card driver, the vector magnet readout (which could never
have run), `analog_pulser.py` (missing its NumPy import), plot saving for
classes whose plot is called `plot` (autocorrelation, ODMR), and several
destructors raising at exit.

---

## 3. How equivalence was established

1. **Pulse sequences, statically.** The rounding function was compared with true
   Python 2 rounding over 80,000 values, and the byte-packing routine with a
   Python 2 emulation over hundreds of random patterns. No differences.
2. **Pulse sequences, as a regression guard.** `seq_regression.py` fingerprints
   28 generated patterns; `seq_py3.pkl` is the validated baseline.
3. **On hardware, step by step.** Board enumeration, FPGA configuration, the
   Time Tagger, pulse-generator readback, NI-DAQ, microwave sources, then full
   measurements.
4. **Against history.** Measurements repeated with the Python 3 stack agree with
   the lab's existing Python 2 data, and the Python 2 stack still runs correctly
   afterwards.

---

## 4. Status

**Verified on hardware:** confocal scanning, autofocus (including targets and
markers), time trace, autocorrelation, ODMR, T1-family and pulsed measurements,
both FPGA boards, NI-DAQ, both LabBrick sources, the green laser.

**Not yet run under Python 3:**

- The **cryo** scanner setup (`setup='cryo'`). Confirm `invert_x` first.
- The **orange laser** driven from software (`laser2` is left as `None`).
  Channel 8 (`aom2`) is active in `Light()`, `Open()` and any sequence that
  names it.
- `ChargeStateDynamics` (the orange-laser measurement).
- The **vector magnet** readout, SMIQ and PM100D (only present with
  `autodetect_resources = True`).
- Modules outside the active configuration; see the end of `README.md`.

**Open observation:** during bring-up, the pulse generator's underflow flag
stayed set while playing a very short (2 µs) repeating test sequence. Real
measurements are unaffected. If pulse timing is ever in doubt, check the output
on a scope before chasing it in software.

---

## 5. Files the port added

| File | Purpose |
|---|---|
| `modernize_timetagger.py`, `build_timetagger.py` | Rebuild the TimeTagger extension |
| `seq_regression.py`, `seq_py3.pkl` | Pulse-sequence regression guard |
| `ok_probe.py` | List the FPGA boards the driver can see |
| `pys_regression.py` | Compare stored data files between stacks |
| `hardware/ok.py` | ctypes binding for the Opal Kelly FrontPanel DLL |
| `fix_numpy2_aliases.py`, `fix_hardware_paths.py`, `apply_*.py` | One-off patch scripts used during the port. Safe to delete. |

**Backup files** left by the patch scripts: `*.py2bak` (C++ originals),
`*.np2bak`, `*.hwbak`, `*.labbak`, `*.lab2bak`. Once the current version has
been committed they can be deleted. Note that some carry a `.pyd` extension
(for example `_TimeTagger_old.py27bak.pyd`); nothing imports them, but they are
not inert by name alone.

---

## 6. Housekeeping still worth doing

- **Commit this tree to version control.** The lab's working tree was never
  committed, and for a time the only copy of years of work was one PC.
- The last paragraph of `requirements.txt` still describes the TimeTagger as
  32-bit; it has been rebuilt. Its reference to "step 11" of these notes also
  predates this document.
