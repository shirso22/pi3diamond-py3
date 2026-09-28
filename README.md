# pi3diamond (Python 3)

Control and measurement software for the NV-centre confocal / diamond-AFM setup
(Kern group, MPI for Solid State Physics). Originally written for Python 2.7 and
32-bit Windows around 2011–2019; ported to **64-bit Python 3.13** in 2026.

The port has been validated on the real instrument: confocal scanning,
autofocus, time trace, autocorrelation, ODMR and pulsed measurements run, and
measurements repeated on both stacks agree with the historical Python 2 data.
The old Python 2 installation was left untouched and still works as a fallback.

Three documents cover this repository:

| Document | Read it when |
|---|---|
| `README.md` (this file) | Setting up, launching, configuring, or bringing the rig up |
| `PY3_PORT_NOTES.md` | You want to know what changed in the port, and why |
| `TROUBLESHOOTING.md` | Something is broken and you want the likely cause and fix |

---

## Requirements

**Python 3.13, 64-bit.** Not 3.12 and not 3.14. The TimeTagger extension is
compiled as `cp313-win_amd64` and loads on nothing else, and `enable` has no
3.14 wheel. Check with:

```
python -c "import sys; print(sys.version)"
```

You want `3.13.x` and `64 bit (AMD64)`.

**Python packages:** `pip install -r requirements.txt` inside a virtual
environment. The pins are the versions the port was executed against. Keep the
Enthought packages (`traits`, `traitsui`, `pyface`, `chaco`, `enable`) pinned
together; upgrading one of them alone is the fastest way to break the GUI.

**Vendor drivers, installed separately (not pip packages):**

- **NI-DAQmx**, 64-bit. `hardware/nidaq.py` loads `nicaiu.dll` through ctypes.
- **Opal Kelly FrontPanel USB driver**, 64-bit, for the two XEM3010 FPGA boards.
  The matching 64-bit `okFrontPanel.dll` is in the repository root.
- **Vaunix LabBrick** runtime (`vnx_fsynth.dll`, 64-bit) for the microwave
  synthesizers; see `hardware/labbrick_driver/`.
- A **VISA** implementation (NI-VISA) for GPIB instruments.

**To rebuild the TimeTagger extension only:** Visual Studio Build Tools with the
C++ workload, SWIG on `PATH`, and `setuptools`. See *Rebuilding the TimeTagger
extension* below. You do not need these to run the software.

---

## Launching

Always launch **from the repository root** — the folder containing
`pi3diamond.py`. Several files, notably the Time Tagger FPGA bitfile
`TimeTaggerController.bit`, are loaded by relative path. Launching from anywhere
else fails quietly (see `TROUBLESHOOTING.md`).

```
python -i pi3diamond.py
```

`-i` keeps an interactive prompt after the GUI opens. If startup fails partway,
you keep everything that was already constructed, which makes it easy to see
how far it got.

If the Manager window is closed while the session is alive, reopen it with:

```python
manager.edit_traits()
```

If the window appears but is blank or frozen, the Qt event loop is not running;
use `ipython --gui=qt -i pi3diamond.py` instead.

### Shutting down

```python
pulse_generator.Night()   # park the FPGA: outputs low, core halted
shutdown()                # stop the job manager, cron daemon and measurement threads
exit()
```

`Night()` matters. The pulse generator is an independent device playing a
sequence from its own memory; **it keeps running after Python exits.** If you
skip `Night()`, the AOM and microwave lines keep toggling until someone
reconfigures or power-cycles the board. Confirm with
`pulse_generator.getState()`, which should return `'IDLE'`.

---

## Configuration

Everything site-specific lives near the top of `pi3diamond.py`.

| Setting | Where | Notes |
|---|---|---|
| Time Tagger serial | `_Tagger_setSerial('11130000UV')` | XEM3010 board serial |
| Pulse generator serial | `PulseGenerator(serial='fQWpZoZxWc', ...)` | XEM3010 board serial |
| Pulse generator channel map | `channel_map={...}` | See table below |
| Scanner setup | `Scanner(..., setup='rt')` | `'rt'` or `'cryo'`; changes ranges and autofocus defaults |
| Scanner x inversion | `Scanner(..., invert_x=...)` | See the note on cryo below |
| Instrument autodetect | `autodetect_resources = ...` | See below |
| Orange laser | `laser2 = ...` block | See below |

### Pulse generator channels (12×8 core, 1.5 ns resolution)

| Channel | Names |
|---|---|
| 0 | `detect` |
| 1 | `mw`, `microwave`, `mw_x` |
| 2 | `rf` |
| 3 | `sequence` |
| 4 | `mwy`, `mw_y` |
| 5 | `aom`, `ch5` (green laser AOM) |
| 6 | `ch6`, `awgTrigger` |
| 7 | `microwave2`, `mw2` |
| 8 | `aom2` (orange laser AOM) |

Helper states on the pulse generator: `Night()` drives everything low;
`Light()` opens both AOMs (`aom`, `aom2`); `Open()` opens both AOMs and the
microwave gate.

### `autodetect_resources`

When `True`, startup opens **every** VISA resource on the bus and sends
`*IDN?`, then uses the replies to find the SMIQ, the vector magnet and the
PM100D power meter. When `False`, the scan is skipped and those three
instruments are left as `None` (the rest of the software still runs).

Two consequences to keep in mind:

- The addresses for `rf`, `vector_magnet` and `pm100d` **only** come from this
  scan. Turning it off removes those instruments.
- Opening a serial port asserts its DTR/RTS lines, which can reset home-built
  controllers. Run with autodetect on at the bench, where you can see what
  happens, not remotely.

Each instrument is constructed inside its own `try/except`, so a missing device
no longer prevents startup.

### Scanner setup: RT vs cryo

The comment block in `pi3diamond.py` documents the physical re-cabling needed to
switch between the room-temperature and cryostat scanners. In software,
`setup='cryo'` selects the cryo piezo ranges and loads
`defaults/auto_focus_cryo.pys`; `setup='rt'` loads `defaults/auto_focus_rt.pys`.
Both `.pys` files must be present or the confocal/autofocus window fails to
load.

> **Cryo has not been run under Python 3.** Treat the first cryo session as a
> bring-up. Before it, confirm the correct `invert_x` value for the cryo stage:
> the configuration comment says `False`, but an older lab branch used `True`
> with `setup='cryo'`. Getting it wrong mirrors every x coordinate while every
> scan still looks plausible.

### Orange (594 nm Cobolt) laser

The driver is `hardware/huebner_orange_laser.py`, and the laser's AOM is gated
by pulse generator channel 8 (`aom2`). By default the laser object is **not**
constructed; `laser2 = None` and the Orange Laser panel in the Manager is empty.

To drive the laser from pi3diamond, edit the block in `pi3diamond.py`:

```python
laser2 = CoboltLaser()          # or CoboltLaser(port='COMn')
laser2.open_connection()
laser2.turn_off()
# laser2 = None                 # must be commented out, or it discards the laser
```

Close the **Cobolt Monitor** application first: both want the laser's COM port
(COM5 on the lab PC) and only one process can hold it. A warning
`Laser port was open. Closing and re-opening.` on every launch is normal.

---

## Safe bring-up checklist

Use this after any change to the software, the drivers or the wiring, and for
the first session on new hardware (for example, cryo).

**Physical state first:**

1. Laser beam blocked.
2. Microwave outputs disconnected from the amplifier and terminated into a
   power meter or dummy load.
3. Objective retracted from the sample.
4. Magnet supply off.
5. Other programs that own hardware closed: any other Python session, the
   FrontPanel application, and Cobolt Monitor if the orange laser is to be
   used. Leave the Nanonis software alone; do not touch its Motor Control
   window.

**Then software, one subsystem at a time:**

1. `python ok_probe.py` — both FPGA serials listed, `OpenBySerial` returning 0.
2. `python -i pi3diamond.py`.
3. `pulse_generator.Night()` and `pulse_generator.getState()` → `'IDLE'`.
4. Check the microwave sources report sensible settings:
   `microwave.getPower(), microwave.getFrequency()` (and the same for
   `microwave2`).
5. Before the first scanner move, command a known, safe z. The software assumes
   the stage is at the origin while it is actually wherever the last session
   left it, so the first move can be a full-range jump.
6. Only then unblock the beam (at low power), reconnect the microwave, and run a
   measurement you can compare against existing data.

Why the physical steps come first: the FPGA outputs float while the bitfile is
loading on every launch; the LabBricks power up in their last saved state and
may be emitting before you touch anything; and DAQ analog outputs hold their
last value when a session ends.

---

## Rolling back to Python 2

The original Python 2 installation is unchanged and still works. To switch:

1. Park and close the Python 3 session (`Night()`, `shutdown()`, `exit()`).
2. Launch the Python 2 stack as before.

Never run both at once: the Opal Kelly boards open exclusively, and each stack
reconfigures both FPGAs when it starts. Switching back and forth leaves no
lasting state behind — this was tested.

---

## Verification tools

Run these from the repository root after changing code, dependencies or
drivers. None of them touch hardware except `ok_probe.py`, which only
enumerates the FPGA boards and opens and closes a handle.

| Command | What it proves |
|---|---|
| `python -m compileall -q hardware measurements analysis tools pi3diamond.py` | Every module parses (silence = pass) |
| `python seq_regression.py compare seq_py3.pkl` | Pulse sequences are byte-identical to the validated baseline (expect 28 identical) |
| `python ok_probe.py` | The FPGA boards are visible to the 64-bit driver and can be opened |
| `python -c "from hardware import _TimeTagger; print(_TimeTagger.__file__)"` | The correct 64-bit TimeTagger extension is the one that loads |

`seq_py3.pkl` is a Python 3 baseline: it proves the sequence code has not
changed since the port was validated. Equivalence with the original Python 2
sequence generation was established separately during the port (see
`PY3_PORT_NOTES.md`).

---

## Rebuilding the TimeTagger extension

Only needed if the C++ sources in `timetagger/backend/` change, or if you move
to a different Python minor version.

```
python modernize_timetagger.py timetagger\backend
python build_timetagger.py timetagger\backend
```

Both take the **backend directory**, not the repository root.
`modernize_timetagger.py` is idempotent and safe to re-run. The build must report
four flattened wrappers:

```
flattened: ['_Tagger_SetWireIn', '_Tagger_getDistributionCount', '_Tagger_getTagger', '_Tagger_setSerial']
```

If that list is empty, **stop**: `pi3diamond.py` calls `_Tagger_setSerial` and
will fail on startup.

Then deploy by copying the new `_TimeTagger*.pyd` and `TimeTagger.py` from
`timetagger\backend\` into `hardware\`. Make sure no bare `_TimeTagger.pyd`
(the old 32-bit binary) exists in `hardware\`.

The FPGA bitfile does **not** need rebuilding. It targets a Spartan-3, which
requires the discontinued Xilinx ISE toolchain; the Verilog sources are in
`timetagger/core/` for reference only.

---

## Unused or partially supported modules

These were ported so they are not broken, but they are not in the active
configuration and have not been run on hardware:

- `hardware/dtg.py` and `hardware/socket_instrument.py` — Tektronix DTG pulse
  generator. The FPGA pulse generator is the one in use.
- `hardware/analog_pulser.py` — only meaningful on a 12-channel, 8-bit-wide core.
- `hardware/hameg.py` — HMP2030 power supply and relay card.
- `measurements/pulsedAFMclient.py` — requires wxPython (commented out in
  `requirements.txt`).
- Thorlabs APT stage — `APT.dll` is still 32-bit and cannot load under 64-bit
  Python.
- `timetagger/backend/test.py`, `test2.py` — Python 2 scratch files, never
  imported.
