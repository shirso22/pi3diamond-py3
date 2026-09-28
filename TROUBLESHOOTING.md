# Troubleshooting

Symptom → likely cause → fix. Grouped by where the problem shows up. The second
half covers what is likely to break in future and how to change things safely.

**First, three general rules:**

1. **Read the whole traceback, starting from the first error.** One failed
   measurement can leave hardware tasks open and cause every later measurement
   to fail with unrelated-looking errors. Fix the first error, then restart the
   session.
2. **Silence is not failure.** Many calls (`Night()`, `setSequence()`) return
   nothing on success. Use the read-back calls (`getState()`, `getPower()`) to
   confirm.
3. **When in doubt, compare with the Python 2 stack.** It still works. If the
   same measurement fails there too, the problem is the hardware or its state,
   not the port.

---

## Startup

### `%1 is not a valid Win32 application`, or an `ImportError` for `_TimeTagger`
**Cause:** the old 32-bit `hardware/_TimeTagger.pyd` is present, or the Python
running is not 3.13 64-bit.
**Fix:** delete any bare `hardware/_TimeTagger.pyd` (keep
`_TimeTagger.cp313-win_amd64.pyd`). Check `python -c "import sys; print(sys.version)"`.
This commonly reappears after copying the repository between machines.

### `AttributeError: module 'hardware.TimeTagger' has no attribute '_Tagger_setSerial'`
**Cause:** the TimeTagger extension was rebuilt and the generated
`TimeTagger.py` lacks the compatibility aliases.
**Fix:** rebuild with the current `build_timetagger.py` and confirm it prints
four names under `flattened:`. Then copy `TimeTagger.py` into `hardware/` again.

### `Opening of USB connection failed` / `RuntimeError: failed to open USB connection`
**Cause:** an FPGA board is not visible or is held by another process.
**Fix:** run `python ok_probe.py`.
- *0 devices:* board unpowered or unplugged, or the 64-bit Opal Kelly USB driver
  is missing (check Device Manager).
- *Devices listed but open fails:* another program holds the board — another
  Python session (including the Python 2 stack) or the FrontPanel application.
  Opal Kelly boards open exclusively.
- *Serial not listed:* the serial in `pi3diamond.py` does not match the board.
On a machine with no boards attached (a laptop), this error is expected.

### Time Tagger counts are all zero, and nothing is printed
**Cause:** the Time Tagger FPGA was not configured. The bitfile
`TimeTaggerController.bit` is loaded **relative to the current directory**, and
the failure is reported only as a line on stdout that is easy to miss.
**Fix:** launch from the repository root. Look for
`Uploading FPGA configuration failed` in the console.

### `ModuleNotFoundError: No module named 'serial'` (or `pyvisa`)
**Cause:** the virtual environment on this machine is missing a dependency.
Each machine has its own venv.
**Fix:** `pip install -r requirements.txt` in that venv.

### A GUI window appears but is blank or frozen
**Cause:** no Qt event loop is running.
**Fix:** `ipython --gui=qt -i pi3diamond.py`.

### Warning: `Autodetect resources is off`
**Cause:** `autodetect_resources = False`. Informational.
**Effect:** `rf` (SMIQ), `vector_magnet` and `pm100d` are `None`, because their
addresses only come from the scan. Set it to `True` to use them.

### `Exception ignored in ... __del__` at exit
**Cause:** a destructor ran on an object whose constructor never finished
(typically an absent instrument). Harmless.
**Fix:** guard the destructor with `getattr(self, 'attr', None)` before closing.

---

## Time Tagger

### `Countrate.getTotalCounts()` returns `-1`
**Cause:** `-1` is a sentinel meaning *no tag has arrived on that channel since
the counter was created* — not zero counts, no data at all. In a dark setup
(beam blocked, laser off) this is the correct answer.
**Fix:** nothing, if the system is dark. Otherwise check light, APD power, and
cabling into the Time Tagger.

### Counts are zero and stderr shows `TimeTagger worker thread stopped: ...`
**Cause:** a worker thread hit an error and shut itself down rather than crash
the interpreter. The message says why.
**Fix:** address the reported error, then restart the session.

### No counts, and the APD appears dead
**Cause (possible):** the APD protection circuit in the FPGA has latched. Its
reset input is commented out in the Verilog, so **there is no software reset**,
and `FuseReset` in the C++ is stubbed out.
**Fix:** hardware-level reset or power cycle of the relevant electronics.

---

## Pulse generator

### Outputs keep toggling after Python has exited
**Cause:** the FPGA plays sequences from its own memory independently of Python.
**Fix:** always `pulse_generator.Night()` before exiting. To stop it after the
fact, start a session, construct the pulse generator, and call `Night()`.

### `getState()` returns `'READ_2'`
This is normal: the core is playing a sequence. `'IDLE'` means halted.

### `checkUnderflow()` returns `True`
**Cause:** the flag is latched — it reports an underflow at any time since it
was last read, including during sequence loading. Read it twice; only the second
result is current. A persistent `True` was observed on a very short (2 µs) test
loop without affecting real measurements.
**Fix:** if pulse timing is in doubt, look at the output on a scope.

### A pulse is shorter than requested, or missing
**Cause:** times are rounded to the 1.5 ns clock. A request of 1000 ns becomes
667 ticks = 1000.5 ns, which is correct. If pulses are genuinely wrong, check
that nothing replaced `_py2_round` with Python's built-in `round()`.
**Fix:** run `python seq_regression.py compare seq_py3.pkl`.

---

## NI-DAQ and scanner

### `ctypes.ArgumentError: ... OverflowError: int too long to convert`
**Cause:** a buffer passed as `array.ctypes.data` (a raw integer address) instead
of `array.ctypes.data_as(pointer_type)`. On 64-bit, addresses do not fit in a C
`int`.
**Fix:** use `data_as(...)`. For buffers DAQmx *reads into*, do not convert the
array first; assert its type instead.

### DAQmx errors `-50103` (resource reserved), `-200479` (task running), `-200557` (cannot set property while running)
**Cause:** almost always collateral damage. An earlier measurement failed
without releasing its counter or output task, so everything after it collides
with the leftover task.
**Fix:** find the *first* error in the log and fix that. Restart the Python
session to release the tasks.

### The first scan or move jumps the stage
**Cause:** at startup the software assumes the scanner is at the origin, but the
piezo is wherever the previous session left it (DAQ outputs keep their last
value).
**Fix:** command a known z position before scanning. Retract the objective
during bring-up.

### Scans look plausible but are mirrored or offset
**Cause:** wrong `setup`, `invert_x` or scanner range for the stage in use.
**Fix:** compare `pi3diamond.py` against the RT/cryo notes in its comment block
and against a known sample.

---

## Microwave sources (LabBrick)

### `TypeError: '>' not supported between instances of 'NoneType' and 'int'`
**Cause:** `setPower(None)` without the Python 3 fix. `None` means "minimum
power" (−40 dBm).
**Fix:** use the current `hardware/labbrick_controller.py`.

### The two sources appear swapped
**Cause:** `LabBrick('LSG-402')` and `LabBrick('LSG-402-2')` are assigned by the
order the driver enumerates devices, not by identity. That order can change
after replugging or a driver update.
**Fix:** read each source's frequency with `getFrequency()` to tell them apart.
The robust fix is to select by serial number.

### Microwave is already on at startup, or stays on after exit
**Cause:** the LabBricks power up in their last saved state, and nothing turns
them off on exit.
**Fix:** expected behaviour. Terminate the outputs into a dummy load during
bring-up, and set the power explicitly before measurements.

---

## Lasers

### Orange laser: `PermissionError(13, 'Access is denied.')`
**Cause:** the port is correct but another program holds it — normally Cobolt
Monitor.
**Fix:** close Cobolt Monitor. Do not change the port.

### Orange laser: `could not open port 'COMn'` / file not found
**Cause:** that COM port does not exist on this machine.
**Fix:** find the right one with `python -m serial.tools.list_ports -v`
(unplug the laser and run it again: the port that disappears is the laser), or
in Device Manager under *Ports (COM & LPT)*. Pass it as
`CoboltLaser(port='COMn')` in `pi3diamond.py`.

### Orange Laser panel in the Manager is empty
**Cause:** `laser2 = None`, the default. If the three construction lines were
uncommented, the `laser2 = None` line after them was probably left active and
discards the laser.
**Fix:** comment out `laser2 = None`.

### Warning: `Laser port was open. Closing and re-opening.`
Normal on every launch of the orange laser; not an error.

---

## Measurements and analysis

### ODMR: `found an uneven number of edges`, or `no peak survived the minimum-width filter`
**Cause:** there is no resonance in the data wide enough to fit — for example,
the microwave is terminated into a dummy load, the beam is blocked, or the sweep
window misses the resonance. The fit runs after every data update, so one
missing peak prints many lines.
**Fix:** check the microwave actually reaches the sample and the frequency
window covers the resonance; adjust the threshold.

### `TypeError: 'float' object cannot be interpreted as an integer`, or `slice indices must be integers`
**Cause:** a float used where an integer is required — a point count
(`np.logspace`, `np.linspace`) or an index/slice, typically from `/` where `//`
was meant.
**Fix:** wrap point counts in `int(...)`; use `//` for index arithmetic.

### A Traits handler seems never to run (dropdown or plot not updating)
**Cause:** exceptions inside Traits change handlers are caught and logged, not
raised, so the handler may be failing silently. Separately, Traits 7 drops a
notification if a container was mutated in place and announced with the same
object.
**Fix:** check the console for a logged exception. When announcing an in-place
change, use `self.trait_property_changed('name', None, self.name)`.

### `Caught attribute error after trying to save plot of the class.`
**Cause:** the measurement's plot attribute is named something other than
`figure_container`, `line_plot` or `plot`, which are the names
`tools/utility.save_figure` looks for.
**Fix:** add the new name to `save_figure`'s fallbacks.

### A measurement freezes the GUI, or Stop does nothing
**Cause:** the job manager's lock is held. This was the symptom of the old
`cmp()` bug.
**Fix:** check the log for an exception inside `emod`. Every lock acquisition
must be in `try/finally`.

---

## Rebuilding the TimeTagger extension

### Build fails: `SWIG not found`, compiler errors, or `ModuleNotFoundError: setuptools`
**Fix:** install Visual Studio Build Tools with the C++ workload and use an
*x64 Native Tools* prompt; put SWIG on `PATH`; `pip install setuptools`.

### The extension crashes with an access violation on first use
**Cause:** mismatch between the Visual C++ runtime the extension was built for
and an older `msvcp140.dll` already loaded by another package.
**Fix:** make sure the build defines `_DISABLE_CONSTEXPR_MUTEX_CONSTRUCTOR`
(it does in the current `build_timetagger.py`).

### Built fine, but `pi3diamond.py` fails at `_Tagger_setSerial`
See *Startup* above: the flattened wrappers are missing.

---

# What is likely to break in future

These are the changes most likely to cause problems, roughly in order of
likelihood.

### Upgrading Python
The TimeTagger extension is compiled for exactly one Python version (currently
3.13). **Any** minor-version upgrade requires rebuilding it. Also check that
every package in `requirements.txt` has a wheel for the new version — `enable`
is typically the last to catch up.

### Upgrading NumPy
NumPy removes deprecated names in minor releases. After an upgrade, run the
verification tools and grep for anything the release notes mention. Keep
`numpy.i` in `timetagger/backend/` pinned to the same version.

### Upgrading the Enthought packages
Upgrade `traits`, `traitsui`, `pyface`, `chaco` and `enable` together, never
individually. Traits changes notification behaviour between major versions; the
in-place `Dict` issue above is an example. Test autofocus targets and plot
saving afterwards, since they depend on it.

### Upgrading `Pillow`
Pinned deliberately: newer versions removed `PIL.ImageQt`, which the Qt
drawing backend still uses. The failure shows up when a plot is painted.

### Updating vendor drivers or DLLs
- **NI-DAQmx:** generally safe; re-run a scan and a counter read.
- **Opal Kelly FrontPanel:** the DLL and the USB driver must match. Run
  `ok_probe.py` afterwards. Note that the XEM3010 is an old board; check the new
  release still supports it before upgrading.
- **Vaunix LabBrick:** may change device enumeration order (sources swapping)
  and power conventions. Verify power with a power meter after any update.

### Windows updates or moving to a new PC
Serial port numbers can change (orange laser, green laser on COM4 by default).
Drivers need reinstalling in 64-bit form. The stale 32-bit `_TimeTagger.pyd` can
come back with a copied tree. Follow the safe bring-up checklist in `README.md`.

### Hardware changes
- Rewiring pulse-generator channels: update `channel_map` in `pi3diamond.py`,
  and remember `Light()`/`Open()` in `hardware/custom_pulse_generator.py` name
  channels explicitly.
- New or re-addressed GPIB instruments: update addresses (and the `names`
  dictionary used by autodetect).
- Switching RT/cryo: follow the comment block in `pi3diamond.py`; check
  `invert_x`.

### Editing measurement code
- Use `//` for any index or count arithmetic.
- Never use built-in `round()` for pulse timing; use `_py2_round`.
- Serial, socket and VISA raw I/O takes and returns **bytes**.
- Don't compare or sort values that may be `None`.
- When a Traits container is changed in place, announce it with a distinct old
  value.
- After changing anything in `hardware/` or `measurements/`, run
  `seq_regression.py`. If a change to sequences is intended, regenerate the
  baseline deliberately with `python seq_regression.py capture seq_py3.pkl` and
  commit it with the change. The script will warn that capture is meant to run
  under Python 2; that refers to the original port and can be ignored here.

### Data files
`defaults/*.pys` and older saved data are Python 2 pickles. Load them with
`tools/data_toolbox.load_pickle`, which handles the encoding. Never open `.pys`
files in a text editor: saving them can silently corrupt them.
