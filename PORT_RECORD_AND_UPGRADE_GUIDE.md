# pi3diamond: project record, maintenance risks and Windows 11 migration

A complete account of the 2026 Python 3 port: what was done, what can go wrong
afterwards, how to debug it, and what to plan for before upgrading the control
PC from Windows 10 to Windows 11.

Companion documents: `README.md` (setup and daily use), `PY3_PORT_NOTES.md`
(technical detail of the port), `TROUBLESHOOTING.md` (symptom → fix lookup).
This document is the overview and the handover record; where it summarises, the
others hold the detail.

---

# Part 1 — What was done

## 1.1 Starting point

pi3diamond controls an NV-centre confocal microscope and diamond AFM: two Opal
Kelly XEM3010 FPGA boards (a photon time tagger and a pulse generator), an
NI-DAQ card (scanner and counters), two Vaunix LabBrick microwave sources, an
R&S SMIQ, lasers, a power meter, a vector magnet and an AWG.

It was written for Python 2.7 on 32-bit Windows, with development effectively
ending in 2019. The reason to port it was not fashion: Python 2 reached end of
life in 2020, and the 32-bit ecosystem around it (NumPy, SciPy, the Enthought
GUI stack, vendor drivers) has been unsupported for years. Every year of delay
made the eventual move harder.

## 1.2 Phases of work

**1. Static audit.** The proposed port was reviewed before any hardware was
involved. This found failures that would have stopped work immediately (the job
manager deadlocking with the laser on; the pulse generator unable to build any
sequence) and, more importantly, failures that would have produced *wrong data
silently* — changed rounding of pulse lengths, and integer division altering
tick counts.

**2. Systematic fixes.** Roughly forty fixes across the hardware and measurement
layers, grouped in `PY3_PORT_NOTES.md` by cause: 32→64-bit ctypes issues,
Python 2→3 semantics, bytes/str boundaries, and library upgrades.

**3. Rebuilding the native extension.** The Time Tagger C++ extension was a
32-bit Python 2.7 binary. It was rebuilt 64-bit for Python 3.13 from the SWIG
sources, replacing boost with the C++11 standard library, and repairing three
latent problems in the original code (a data race on the worker stop flag,
worker exceptions killing the interpreter, and C++ exceptions not reaching
Python).

**4. Proving sequence equivalence.** Because a silently different pulse pattern
is the worst possible outcome, the rounding function and the byte-packing
routine were compared against Python 2 behaviour exhaustively (80,000 values and
hundreds of random patterns respectively). `seq_regression.py` then froze that
behaviour as a regression test.

**5. Hardware bring-up.** One subsystem at a time, with the beam blocked and the
microwave in a dummy load: board enumeration, FPGA configuration, the Time
Tagger, the pulse generator, NI-DAQ, the microwave sources, then measurements.

**6. Baseline correction.** Partway through, it emerged that the lab PC was
running the 2019 commit **plus about 1,500 lines of uncommitted changes** —
calibration, new measurements, analysis fixes. The port had been built on the
wrong baseline. The lab tree was merged in by three-way merge, keeping the lab's
experiment logic in every conflict.

**7. Fixes found by running it.** Two lab sessions produced real failures that
static review had missed — most notably a 64-bit pointer bug that only appears
when a counter is actually read — plus GUI-level problems (autofocus markers, T1
sequences) traced to a Traits behaviour change and a NumPy strictness change.

**8. Orange laser integration.** The 594 nm Cobolt laser work lived on a
2022–2023 branch that was otherwise *behind* the current code. Rather than
merging the branch, five pieces were cherry-picked onto the current tree.

**9. Validation.** Measurements were repeated with the Python 3 stack and
compared against the lab's historical Python 2 data: they agree. The Python 2
stack was then run again afterwards and still works.

## 1.3 Inventory of changes

| Area | Change |
|---|---|
| Native extension | Rebuilt 64-bit for Python 3.13; boost → C++11; atomic stop flag; worker exception handling; SWIG exception translation; compatibility aliases restored on every build |
| ctypes / 64-bit | Task handles as pointers; string arguments encoded; buffer addresses passed as typed pointers; read buffers never copied |
| Vendor bindings | Opal Kelly and LabBrick rewritten from 32-bit SWIG modules to ctypes against 64-bit DLLs |
| Pulse generation | Python 2 rounding preserved (`_py2_round`); byte packing rewritten and verified byte-identical |
| Python semantics | Integer division reviewed throughout; `None` comparisons; sorting mixed types; `cmp()` removal; explicit relative imports |
| Libraries | NumPy 2 removals; pyvisa ≥ 1.9 API; pyserial 3 bytes; Traits 7 notification behaviour |
| Data | Python 2 pickles (`*.pys`) load through an encoding-aware loader |
| Robustness | Locks in `try/finally`; measurements release hardware on failure; destructors guarded; clearer analysis error messages |
| Merged from the lab | Scanner y-range, SMIQ address, power-meter factor, `invert_x`, per-instrument error handling, new measurements and analysis |
| Added | Orange laser driver, charge-state measurement, `aom2` pulse channel |
| Tooling | Build scripts, sequence regression, board probe, this documentation |

## 1.4 What was deliberately not done

- The FPGA bitfiles were not rebuilt. They target a Spartan-3, which needs the
  discontinued Xilinx ISE toolchain. They did not need changing.
- The Python 2 installation was left untouched, and remains a working fallback.
- Unused modules (DTG, analog pulser, HMP2030, AFM client) were repaired enough
  not to be broken, but not tested on hardware.
- The Thorlabs APT stage remains unusable: `APT.dll` is 32-bit only.

---

# Part 2 — Risks and how to debug them

## 2.1 The general method

The port is finished, but this remains 2011-era code driving 2011-era hardware.
When something breaks, this order saves the most time:

1. **Read the first error, not the loudest one.** A single failure can leave DAQ
   tasks reserved, after which every later measurement fails with a different
   and misleading message.
2. **Decide whether it is software at all.** Run the same measurement on the
   Python 2 stack. If it fails there too, the problem is hardware or its state.
3. **Isolate the subsystem.** `ok_probe.py` for the FPGA boards; a bare counter
   read for the Time Tagger; `getState()` for the pulse generator. Each can be
   exercised without the GUI.
4. **Check what the software believes.** Read values back (`getPower()`,
   `getFrequency()`, `getState()`) rather than assuming the last command took.
5. **Restart the session before concluding anything.** Leftover hardware state
   from a crashed measurement imitates a much worse problem.

## 2.2 Standing risks

**Silent numerical change is the dangerous failure mode.** Crashes are cheap;
wrong numbers that look plausible are expensive. The protections are
`seq_regression.py`, the `_py2_round` function, and the habit of comparing new
measurements against historical data. Run the regression after any change to
`hardware/` or `measurements/`, and treat a difference as a fault until
explained.

**Dependency upgrades.** Pins in `requirements.txt` are deliberate. The
Enthought stack must move as a unit; NumPy removes deprecated names in minor
releases; `Pillow` is pinned because newer versions broke a Qt drawing path.
Upgrade one thing at a time, and run the verification tools afterwards.

**The Python version and the native extension are coupled.** The extension is
built for one Python minor version. Moving Python means rebuilding it, which
means having Visual Studio Build Tools and SWIG available. Do not move Python
casually.

**Instrument identity is not guaranteed.** The two LabBricks are distinguished
by the order the driver enumerates them, not by serial number. A driver update
or a replug can swap them. Confirm with `getFrequency()` before a campaign; the
robust fix is to select by serial.

**Microwave power calibration is assumed, not measured.** The wrapper converts
the device's level to dBm as `0.25 × (40 − level)`, implying a −40 dBm floor.
Vaunix's published specification for the LSG series gives the LSG-402 a 55 dB
control range (−45 to +10 dBm), so this mapping may be off by 5 dB at the bottom
of the range. Measurements agree with historical data, so any offset is at least
*consistent* with what the lab has always used — but if absolute microwave power
ever matters, verify against a power meter before trusting the number.

**Hardware with no software safety net.** The APD protection circuit latches in
the FPGA and its reset line is disconnected in the Verilog: no software can
clear it. DAQ analog outputs hold their last value when a session ends. The
pulse generator keeps playing after Python exits. None of these are port
artefacts; they are properties of the setup worth remembering.

**Untested paths.** The cryo scanner configuration, the orange laser driven from
software, the charge-state measurement, and the vector magnet readout have not
been run under Python 3. Treat each first use as a bring-up, following the
checklist in `README.md`.

**Single copy of the code.** The lab's changes were uncommitted for years, and
for a period the only copy of both the port and that work was one PC. Put this
tree under version control and keep a copy elsewhere.

## 2.3 Fast diagnosis table

| Symptom | First thing to check |
|---|---|
| Won't start, USB error | `ok_probe.py`; another process holding the boards |
| Counts always zero | Launched from the repository root? Is the setup dark? |
| `-1` on all Time Tagger channels | No tags at all — dark system or no signal path |
| DAQmx `-50103` / `-200479` / `-200557` | An earlier failure left tasks open; restart the session |
| `OverflowError: int too long` | A buffer passed as an address instead of a typed pointer |
| `'float' object cannot be interpreted as an integer` | `/` where `//` was meant, or a float point count |
| GUI element never updates | Exception swallowed inside a Traits handler; in-place container change |
| ODMR fit errors repeating | No resonance in the data; check microwave path and sweep window |
| Pulses wrong length | `seq_regression.py`; confirm `_py2_round` is still in use |

---

# Part 3 — Upgrading the control PC from Windows 10 to Windows 11

Windows 10 reached end of support in October 2025, so this upgrade is a matter
of when rather than whether. The software itself is not the risk: Python 3.13,
NumPy, Qt and the pi3diamond code are all fully supported on Windows 11. **The
risk is entirely in the drivers and in the old fallback stack.**

## 3.1 Before anything: take an inventory

Record, from the machine as it currently runs:

- Windows edition and version (`winver`).
- NI-DAQmx version, NI-VISA version, and the GPIB interface driver version
  (NI MAX shows all three).
- Opal Kelly FrontPanel SDK and USB driver version.
- Vaunix LabBrick driver/DLL version.
- COM port assignments for every serial instrument (green laser, orange laser,
  any relay boards) — Device Manager, *Ports (COM & LPT)*.
- The Python 2.7 installation path and its 32-bit driver dependencies.
- Anything else on the PC that owns hardware: the Nanonis software, Cobolt
  Monitor, the FrontPanel application.

Save this list somewhere outside the machine.

## 3.2 Known compatibility positions

**NI-DAQmx** — NI's stated minimum for Windows 11 is **NI-DAQmx 2022 Q3**. Older
versions are not supported there, and reports exist of older versions failing on
Windows 11 even when they worked on Windows 10. If the lab is running a driver
older than that, the upgrade requires a driver upgrade too, which means
re-testing the scanner and counters afterwards. Check the current version first.

**Opal Kelly FrontPanel** — good news: FrontPanel (5.3.6 and the FrontPanel 6
platform) officially targets Windows 10/11 x64, and the XEM3010 is still listed
among supported devices despite its age. The 64-bit DLL bundled with this
repository stays as it is; what matters is that the **USB driver** installed on
the PC is a Windows 11-capable version from Opal Kelly.

**Vaunix LabBrick** — no explicit Windows 11 statement was found; some product
literature still lists Windows 7 era support. Confirm with Vaunix before the
upgrade and obtain a current driver package. Note that a driver update may
change device enumeration order (see 2.2).

**Nanonis, Cobolt and other vendor applications** — check each vendor's
compatibility statement. These are outside pi3diamond but share the machine.

## 3.3 Windows 11 specific hazards

**Machine eligibility.** Windows 11 requires TPM 2.0, Secure Boot and a CPU on
Microsoft's supported list. An older lab PC may simply not qualify, which turns
this into a hardware replacement — a much larger project, and one where a clean
install means reinstalling every driver from scratch.

**Memory integrity / core isolation (HVCI).** Enabled by default on many
Windows 11 installations, it blocks drivers that do not meet current
requirements. Older instrument drivers are exactly the category affected. If a
device disappears after the upgrade, check core isolation before anything else.

**Driver signing.** Windows 11 will not load unsigned kernel drivers, and
workarounds are neither permanent nor advisable on a shared lab machine. Any
instrument whose only driver is old and unsigned needs a vendor update or a
different plan.

**USB power management.** Windows power settings can suspend USB devices.
Both FPGA boards, the LabBricks and USB-serial adapters are on USB. If devices
drop out intermittently after the upgrade, disable USB selective suspend and
uncheck "allow the computer to turn off this device" for those ports.

**Fast startup / hibernation.** Leaves devices in partially initialised states
between sessions and produces confusing, irreproducible faults. Consider
disabling it on an instrument PC.

**COM port renumbering.** Serial assignments can change. The orange laser
defaults to COM5 and the green laser to COM4 in the code; both may need updating
in `pi3diamond.py`.

## 3.4 The Python 2 fallback will probably not survive

This deserves emphasis. The rollback path that made this whole port safe — the
Python 2 stack — depends on 32-bit drivers and a 32-bit Python 2.7 installation.
After an OS upgrade, and especially after a clean install or a new machine, that
stack may not be reconstructible: the old driver versions may not install, may
not be signed acceptably, or may not be downloadable any more.

Plan on the assumption that **after the Windows 11 migration, the Python 3 stack
is the only stack.** That is an argument for doing the migration *after* a period
of confident Python 3 operation, not during it — and for making a full disk image
first.

## 3.5 Suggested procedure

1. **Image the disk.** A full image, verified, stored off the machine. This is
   the real rollback, and the only one that covers driver state.
2. **Commit and back up the code**, including this repository and the Python 2
   tree.
3. **Check machine eligibility** and the four driver compatibility positions in
   3.2. Resolve any that need vendor updates *before* upgrading.
4. **Pick the timing.** Not mid-campaign. Allow a day for bring-up.
5. **Prefer an in-place upgrade** over a clean install: it preserves drivers and
   COM assignments. Accept that a clean install may be forced if the machine is
   replaced.
6. **After the upgrade, verify in dependency order**, not by launching the GUI
   and hoping:
   - Device Manager: every instrument present, no warning marks.
   - NI MAX: the DAQ card enumerates and self-tests.
   - `python ok_probe.py`: both FPGA serials, opening successfully.
   - `python -m compileall -q hardware measurements analysis tools pi3diamond.py`
   - `python seq_regression.py compare seq_py3.pkl` → 28 identical.
   - Then the full bring-up checklist in `README.md`, beam blocked and microwave
     terminated.
   - Finally, reproduce a known measurement and compare with historical data.
7. **Record what changed** — driver versions, COM ports, any settings altered —
   in this document, for whoever does this next.

## 3.6 If something breaks after the upgrade

| Symptom | Likely cause |
|---|---|
| A USB instrument is missing in Device Manager | Driver blocked by core isolation, or needs a Windows 11-capable version |
| DAQ card present but DAQmx calls fail | NI-DAQmx older than 2022 Q3 |
| FPGA boards enumerate zero devices | Opal Kelly USB driver not reinstalled, or not the 64-bit/Win11 version |
| Serial instrument cannot be opened | COM port renumbered; update `pi3diamond.py` |
| Intermittent device dropouts | USB selective suspend; fast startup |
| Python stack broken outright | Virtual environment lost; recreate with `requirements.txt` |
| Microwave sources swapped | Driver update changed enumeration order; check `getFrequency()` |

---

# Part 4 — Sources and further reading

- NI, Windows 11 compatibility: minimum NI-DAQmx version 2022 Q3 —
  <https://www.ni.com/en/support/downloads/drivers/download.ni-daq-mx.html> and
  NI's Windows 11 product compatibility page.
- Opal Kelly FrontPanel, supported platforms (Windows 10/11 x64) and supported
  devices including XEM3010 — <https://www.opalkelly.com/products/frontpanel/>,
  <https://docs.opalkelly.com/fpsdk/release-notes/>
- Vaunix LabBrick LSG series specifications (control range) —
  <https://vaunix.com/>

Vendor statements change; check them at the time of the upgrade rather than
relying on this snapshot (compiled September 2026).
