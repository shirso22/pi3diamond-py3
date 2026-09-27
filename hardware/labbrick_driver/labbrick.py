"""
labbrick.py -- ctypes replacement for the Vaunix Lab Brick LSG binding.

PY3-PORT: drop-in replacement for hardware/labbrick_driver/labbrick.py and
_labbrick.pyd.

WHY THIS EXISTS

_labbrick.pyd is a SWIG 2.0.4 binding, x86 32-bit, linked against python27.
Unlike the TimeTagger, there are NO SOURCES in the repo -- no .i, no .cpp, no
header -- so it cannot be rebuilt. The labbrick.py next to it looks like
source but is SWIG *output*: every function in it is a one-line forward into
the .pyd. The interface file it was generated from was never committed.

So the binding is a black box. The vendor DLL underneath it is not: Vaunix
ships vnx_fsynsth.dll in both 32- and 64-bit, the LSG series is still a
current product line, and the C API is published. This talks to the DLL
directly, the same approach used for hardware/ok.py.

That also makes it version-proof: no compiler, no SWIG, no cp-tag, and it
keeps working across future Python upgrades.

SIGNATURES

Taken from vnx_fsynsth.h (Vaunix, "Include file for Vaunix Lab Brick Frequency
Synthesizers"). The typedefs that matter:

    #define DEVID    unsigned int      -> c_uint
    #define LVSTATUS int               -> c_int
    bool                               -> c_bool     (see note below)

NOTE ON bool, because this bit me once already. Opal Kelly's header declares
`typedef int Bool` -- four bytes -- and using ctypes.c_bool there passed one
byte where the DLL read four. Vaunix uses the actual C++ `bool` type, which
MSVC lays out as ONE byte. So c_bool is correct here and c_int would be
wrong. Same-looking parameter, opposite answer. Always read the header.

CALLING CONVENTION

CDLL, not WinDLL. `__declspec(dllimport)` says nothing about calling
convention and MSVC defaults C++ to __cdecl. It is moot on x64 -- 64-bit
Windows has a single calling convention -- but it matters if anyone ever runs
this 32-bit.

TWO SWIG BEHAVIOURS THAT MUST BE PRESERVED

labbrick_controller.py was written against the SWIG binding and depends on
two of its conventions:

  1. fnLSG_GetModelName(dev)[1]
     The C function is `int fnLSG_GetModelName(DEVID, char *ModelName)`.
     SWIG turned the output buffer into a second return value, so the call
     returns a (status, name) TUPLE and the caller indexes [1]. Returning a
     bare string here would break every caller.

  2. fnLSG_GetDevInfo(devs)
     Called with a numpy uint32 array that the function fills in place.

INSTALLATION

Put the 64-bit vnx_fsynsth.dll next to this file, on PATH, or point
VNX_FSYNSTH_DLL at it. Then rename _labbrick.pyd out of the way -- it is the
32-bit Python 2.7 binary and nothing should load it again.

VERIFY BEFORE HARDWARE

Nothing here has been run against a Lab Brick. Check fnLSG_GetNumDevices()
and fnLSG_GetModelName() first: if the model name comes back as mojibake or
the device count is absurd, a signature is wrong and you should stop rather
than let it set a frequency.
"""

import ctypes
import os
import sys

MAXDEVICES = 64
MAX_MODELNAME = 32

# Status returns, from vnx_fsynsth.h
STATUS_OK = 0
BAD_PARAMETER = 0x80010000      # frequency outside min/max, etc.
BAD_HID_IO = 0x80020000         # I/O failure inside the device
DEVICE_NOT_READY = 0x80030000   # device not open

# DevStatus bits
INVALID_DEVID = 0x80000000
DEV_CONNECTED = 0x00000001
DEV_OPENED = 0x00000002
SWP_ACTIVE = 0x00000004
SWP_UP = 0x00000008
SWP_REPEAT = 0x00000010

# Mode bit masks
MODE_RFON = 0x00000010
MODE_INTREF = 0x00000020
MODE_SWEEP = 0x0000000F

# The SDK renamed the DLL: the 2011-era file bundled with pi3diamond is
# vnx_fsynSth.dll, the 2025 SDK ships vnx_fsynth.dll. One letter. That is why
# nothing in the repo appeared to match the SDK. Both are tried, new first.
_DLL_NAMES = ['vnx_fsynth.dll', 'vnx_fsynsth.dll',
              'libvnx_fsynth.so', 'libvnx_fsynsth.so']


def _load_dll():
    override = os.environ.get('VNX_FSYNSTH_DLL')
    candidates = [override] if override else []
    here = os.path.dirname(os.path.abspath(__file__))
    for name in _DLL_NAMES:
        candidates += [os.path.join(here, name),
                       os.path.join(here, '..', name),
                       os.path.join(here, '..', '..', name),
                       name]
    tried = []
    for path in candidates:
        if not path:
            continue
        try:
            return ctypes.CDLL(path)
        except OSError as exc:
            tried.append('%s (%s)' % (path, exc))
    bits = 64 if ctypes.sizeof(ctypes.c_void_p) == 8 else 32
    raise OSError(
        'vnx_fsynsth.dll could not be loaded. This Python is %d-bit, so the '
        'DLL must be %d-bit too -- the copy bundled with pi3diamond is 32-bit '
        'and will not work here. Install the Vaunix Lab Brick SDK, or set '
        'VNX_FSYNSTH_DLL to the right file.\nTried:\n  %s'
        % (bits, bits, '\n  '.join(tried)))


_dll = _load_dll()

DEVID = ctypes.c_uint
LVSTATUS = ctypes.c_int
# C++ bool -- ONE byte under MSVC. Not the same as Opal Kelly's
# `typedef int Bool`. See the module docstring.
BOOL = ctypes.c_bool


def _bind(name, restype, argtypes):
    fn = getattr(_dll, name)
    fn.restype = restype
    fn.argtypes = argtypes
    return fn


# --- discovery ------------------------------------------------------------
_SetTestMode = _bind('fnLSG_SetTestMode', None, [BOOL])
_GetNumDevices = _bind('fnLSG_GetNumDevices', ctypes.c_int, [])
_GetDevInfo = _bind('fnLSG_GetDevInfo', ctypes.c_int, [ctypes.POINTER(DEVID)])
# fnLSG_GetModelName was split into ...NameA (ANSI) and ...NameW (wide) in
# the current SDK; the unsuffixed name no longer exists. Older DLLs only have
# the unsuffixed one, so try both rather than pinning to either.
def _bind_model_name():
    for candidate in ('fnLSG_GetModelNameA', 'fnLSG_GetModelName'):
        if hasattr(_dll, candidate):
            return _bind(candidate, ctypes.c_int, [DEVID, ctypes.c_char_p])
    raise AttributeError(
        'Neither fnLSG_GetModelNameA nor fnLSG_GetModelName is exported by '
        'this DLL. It is probably not a Lab Brick LSG library.')


_GetModelName = _bind_model_name()
_InitDevice = _bind('fnLSG_InitDevice', ctypes.c_int, [DEVID])
_CloseDevice = _bind('fnLSG_CloseDevice', ctypes.c_int, [DEVID])
_GetSerialNumber = _bind('fnLSG_GetSerialNumber', ctypes.c_int, [DEVID])
_GetDeviceStatus = _bind('fnLSG_GetDeviceStatus', ctypes.c_int, [DEVID])

# --- setters --------------------------------------------------------------
_SetFrequency = _bind('fnLSG_SetFrequency', LVSTATUS, [DEVID, ctypes.c_int])
_SetStartFrequency = _bind('fnLSG_SetStartFrequency', LVSTATUS, [DEVID, ctypes.c_int])
_SetEndFrequency = _bind('fnLSG_SetEndFrequency', LVSTATUS, [DEVID, ctypes.c_int])
_SetFrequencyStep = _bind('fnLSG_SetFrequencyStep', LVSTATUS, [DEVID, ctypes.c_int])
_SetDwellTime = _bind('fnLSG_SetDwellTime', LVSTATUS, [DEVID, ctypes.c_int])
_SetPowerLevel = _bind('fnLSG_SetPowerLevel', LVSTATUS, [DEVID, ctypes.c_int])
_SetRFOn = _bind('fnLSG_SetRFOn', LVSTATUS, [DEVID, BOOL])
_SetUseInternalRef = _bind('fnLSG_SetUseInternalRef', LVSTATUS, [DEVID, BOOL])
_SetSweepDirection = _bind('fnLSG_SetSweepDirection', LVSTATUS, [DEVID, BOOL])
_SetSweepMode = _bind('fnLSG_SetSweepMode', LVSTATUS, [DEVID, BOOL])
_StartSweep = _bind('fnLSG_StartSweep', LVSTATUS, [DEVID, BOOL])
_SaveSettings = _bind('fnLSG_SaveSettings', LVSTATUS, [DEVID])

# --- getters --------------------------------------------------------------
_GetFrequency = _bind('fnLSG_GetFrequency', ctypes.c_int, [DEVID])
_GetStartFrequency = _bind('fnLSG_GetStartFrequency', ctypes.c_int, [DEVID])
_GetEndFrequency = _bind('fnLSG_GetEndFrequency', ctypes.c_int, [DEVID])
_GetDwellTime = _bind('fnLSG_GetDwellTime', ctypes.c_int, [DEVID])
_GetFrequencyStep = _bind('fnLSG_GetFrequencyStep', ctypes.c_int, [DEVID])
_GetRF_On = _bind('fnLSG_GetRF_On', ctypes.c_int, [DEVID])
_GetUseInternalRef = _bind('fnLSG_GetUseInternalRef', ctypes.c_int, [DEVID])
_GetPowerLevel = _bind('fnLSG_GetPowerLevel', ctypes.c_int, [DEVID])
_GetMaxPwr = _bind('fnLSG_GetMaxPwr', ctypes.c_int, [DEVID])
_GetMinPwr = _bind('fnLSG_GetMinPwr', ctypes.c_int, [DEVID])
_GetMaxFreq = _bind('fnLSG_GetMaxFreq', ctypes.c_int, [DEVID])
_GetMinFreq = _bind('fnLSG_GetMinFreq', ctypes.c_int, [DEVID])

# Present in the current SDK, absent from the 2011 DLL. Optional.
_GetPowerLevelAbs = (_bind('fnLSG_GetPowerLevelAbs', ctypes.c_int, [DEVID])
                     if hasattr(_dll, 'fnLSG_GetPowerLevelAbs') else None)
_GetDLLVersion = (_bind('fnLSG_GetDLLVersion', ctypes.c_int, [])
                  if hasattr(_dll, 'fnLSG_GetDLLVersion') else None)


# ==========================================================================
# Module-level functions, named and shaped exactly as the SWIG binding was.
# labbrick_controller.py calls these directly.
# ==========================================================================

def fnLSG_SetTestMode(testmode):
    _SetTestMode(bool(testmode))


def fnLSG_GetNumDevices():
    return _GetNumDevices()


def fnLSG_GetDevInfo(ActiveDevices):
    """Fill a caller-supplied array with the active device IDs.

    labbrick_controller.py passes a numpy uint32 array and expects it filled
    in place, which is what the SWIG typemap did. A plain list is also
    accepted and filled by assignment.
    """
    n = len(ActiveDevices)
    buf = (DEVID * max(n, MAXDEVICES))()
    count = _GetDevInfo(buf)
    for i in range(min(n, count)):
        ActiveDevices[i] = buf[i]
    return count


def fnLSG_GetModelName(deviceID):
    """Return (status, name).

    The C signature is `int fnLSG_GetModelName(DEVID, char *ModelName)`.
    SWIG turned the output buffer into a second return value, and
    labbrick_controller.py does `fnLSG_GetModelName(int(dev))[1]`. Returning a
    bare string here would break every caller, so the tuple is preserved.
    """
    buf = ctypes.create_string_buffer(MAX_MODELNAME + 1)
    status = _GetModelName(DEVID(deviceID), buf)
    return status, buf.value.decode('latin-1').strip()


def fnLSG_InitDevice(deviceID):
    return _InitDevice(DEVID(deviceID))


def fnLSG_CloseDevice(deviceID):
    return _CloseDevice(DEVID(deviceID))


def fnLSG_GetSerialNumber(deviceID):
    return _GetSerialNumber(DEVID(deviceID))


def fnLSG_GetDeviceStatus(deviceID):
    return _GetDeviceStatus(DEVID(deviceID))


def fnLSG_SetFrequency(deviceID, frequency):
    return _SetFrequency(DEVID(deviceID), int(frequency))


def fnLSG_SetStartFrequency(deviceID, startfrequency):
    return _SetStartFrequency(DEVID(deviceID), int(startfrequency))


def fnLSG_SetEndFrequency(deviceID, endfrequency):
    return _SetEndFrequency(DEVID(deviceID), int(endfrequency))


def fnLSG_SetFrequencyStep(deviceID, frequencystep):
    return _SetFrequencyStep(DEVID(deviceID), int(frequencystep))


def fnLSG_SetDwellTime(deviceID, dwelltime):
    return _SetDwellTime(DEVID(deviceID), int(dwelltime))


def fnLSG_SetPowerLevel(deviceID, powerlevel):
    return _SetPowerLevel(DEVID(deviceID), int(powerlevel))


def fnLSG_SetRFOn(deviceID, on):
    return _SetRFOn(DEVID(deviceID), bool(on))


def fnLSG_SetUseInternalRef(deviceID, internal):
    return _SetUseInternalRef(DEVID(deviceID), bool(internal))


def fnLSG_SetSweepDirection(deviceID, up):
    return _SetSweepDirection(DEVID(deviceID), bool(up))


def fnLSG_SetSweepMode(deviceID, mode):
    return _SetSweepMode(DEVID(deviceID), bool(mode))


def fnLSG_StartSweep(deviceID, go):
    return _StartSweep(DEVID(deviceID), bool(go))


def fnLSG_SaveSettings(deviceID):
    return _SaveSettings(DEVID(deviceID))


def fnLSG_GetFrequency(deviceID):
    return _GetFrequency(DEVID(deviceID))


def fnLSG_GetStartFrequency(deviceID):
    return _GetStartFrequency(DEVID(deviceID))


def fnLSG_GetEndFrequency(deviceID):
    return _GetEndFrequency(DEVID(deviceID))


def fnLSG_GetDwellTime(deviceID):
    return _GetDwellTime(DEVID(deviceID))


def fnLSG_GetFrequencyStep(deviceID):
    return _GetFrequencyStep(DEVID(deviceID))


def fnLSG_GetRF_On(deviceID):
    return _GetRF_On(DEVID(deviceID))


def fnLSG_GetUseInternalRef(deviceID):
    return _GetUseInternalRef(DEVID(deviceID))


def fnLSG_GetPowerLevel(deviceID):
    return _GetPowerLevel(DEVID(deviceID))


def fnLSG_GetMaxPwr(deviceID):
    return _GetMaxPwr(DEVID(deviceID))


def fnLSG_GetMinPwr(deviceID):
    return _GetMinPwr(DEVID(deviceID))


def fnLSG_GetMaxFreq(deviceID):
    return _GetMaxFreq(DEVID(deviceID))


def fnLSG_GetMinFreq(deviceID):
    return _GetMinFreq(DEVID(deviceID))


def fnLSG_GetPowerLevelAbs(deviceID):
    """Absolute power in 0.25 dB steps. Newer SDKs only.

    fnLSG_GetPowerLevel returns power as ATTENUATION BELOW MAXIMUM, which is
    why Vaunix's own example computes (max_power - value) / 4. This one
    returns the absolute figure directly and avoids the arithmetic.

    Relevant because labbrick_controller.getPower() hardcodes the max as 40
    (i.e. +10 dBm) rather than using the fnLSG_GetMaxPwr value it already
    fetched into self.max_power and then never uses. If your LSG model has a
    different maximum, every power readback is silently offset.
    """
    if _GetPowerLevelAbs is None:
        raise NotImplementedError(
            'fnLSG_GetPowerLevelAbs is not in this DLL; use '
            '(fnLSG_GetMaxPwr(dev) - fnLSG_GetPowerLevel(dev)) * 0.25 instead.')
    return _GetPowerLevelAbs(DEVID(deviceID))


def fnLSG_GetDLLVersion():
    if _GetDLLVersion is None:
        return None
    return _GetDLLVersion()


if __name__ == '__main__':
    print('DLL loaded: %s' % _dll)
    v = fnLSG_GetDLLVersion()
    if v is not None:
        print('DLL version: %s' % v)
    print('interpreter: %d-bit'
          % (64 if ctypes.sizeof(ctypes.c_void_p) == 8 else 32))
    fnLSG_SetTestMode(False)
    n = fnLSG_GetNumDevices()
    print('devices found: %d' % n)
    if n:
        import array
        devs = array.array('I', [0] * n)
        fnLSG_GetDevInfo(devs)
        for d in devs:
            status, name = fnLSG_GetModelName(int(d))
            print('  id=%d  model=%r  serial=%d  status=0x%08X'
                  % (d, name, fnLSG_GetSerialNumber(int(d)),
                     fnLSG_GetDeviceStatus(int(d)) & 0xFFFFFFFF))
