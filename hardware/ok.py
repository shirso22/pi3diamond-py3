"""
ok.py -- ctypes replacement for the Opal Kelly FrontPanel Python binding.

PY3-PORT: drop-in replacement for hardware/ok.py + hardware/_ok.pyd.

WHY THIS EXISTS

The original _ok.pyd was a SWIG binding compiled against python27, 32-bit.
FrontPanel 4.5.6 ships replacements, but only for Python 2.7 and 3.5 -- and a
CPython C extension is not ABI-compatible across minor versions, so a cp35
binary cannot load in 3.13 any more than the cp27 one could.

Rather than rebuild a binding that will break again at the next interpreter
bump, this talks to okFrontPanel.dll through its flat C API using ctypes. That
API is stable, documented, and version-independent: this file works on 3.13,
on 3.20, and on whatever comes after, with no compiler and no SWIG.

It implements exactly the fourteen calls this codebase makes -- deliberately.
It is not a general FrontPanel binding and does not try to be. If you need
something not here, add it: each method is three lines, and the C signatures
are in okFrontPanelDLL.h from the SDK.

USED BY

    hardware/pulse_generator.py
    hardware/pulse_generator_breakout.py
    hardware/analog_pulser.py

INSTALLATION

Put okFrontPanel.dll (64-bit, from the FrontPanel SDK) somewhere findable:
next to this file, on PATH, or point OK_FRONTPANEL_DLL at it. Then delete
hardware/_ok.pyd -- the 32-bit Python 2.7 one -- so nothing picks it up by
accident.

SIGNATURES VERIFIED

All 19 entry points were diffed against okFrontPanelDLL.h from FrontPanel SDK
4.5.6 (API/include/). Every name and parameter list matches. The typedefs that
matter:

    okFrontPanel_HANDLE / okPLL22150_HANDLE   void*          -> c_void_p
    UINT32                                    unsigned int   -> c_uint32
    Bool                                      int            -> c_int
    ok_ErrorCode                              enum, has -1   -> c_int
    ok_ClockSource_22150                      enum           -> c_int
    length / return of WriteToBlockPipeIn     long (32-bit
                                              on Win64)      -> c_long

The `Bool` one caught a bug in the first draft of this file, which used
c_bool -- one byte against the SDK's four. See the comment at _BOOL.

ok_ClkSrc22150_Div2By2 == 5, which is what pulse_generator.py passes to
SetOutputSource as a bare integer.
"""

import ctypes
import os
import sys

__all__ = ['FrontPanel', 'PLL22150', 'okCFrontPanel', 'okCPLL22150',
           'ok_ClkSrc22150_Ref', 'ok_ClkSrc22150_Div1ByN',
           'ok_ClkSrc22150_Div1By2', 'ok_ClkSrc22150_Div1By3',
           'ok_ClkSrc22150_Div2ByN', 'ok_ClkSrc22150_Div2By2',
           'ok_ClkSrc22150_Div2By4']

# ok_ClockSource_22150, from okFrontPanelDLL.h. pulse_generator.py passes the
# bare integer 5, which is Div2By2.
ok_ClkSrc22150_Ref = 0
ok_ClkSrc22150_Div1ByN = 1
ok_ClkSrc22150_Div1By2 = 2
ok_ClkSrc22150_Div1By3 = 3
ok_ClkSrc22150_Div2ByN = 4
ok_ClkSrc22150_Div2By2 = 5
ok_ClkSrc22150_Div2By4 = 6

# ok_ErrorCode. 0 is success; callers test `!= 0`.
ok_NoError = 0

_DLL_NAMES = ['okFrontPanel.dll', 'libokFrontPanel.so', 'libokFrontPanel.dylib']


def _load_dll():
    """Locate okFrontPanel.dll. Explicit override first, then the usual places."""
    override = os.environ.get('OK_FRONTPANEL_DLL')
    candidates = [override] if override else []
    here = os.path.dirname(os.path.abspath(__file__))
    for name in _DLL_NAMES:
        candidates += [os.path.join(here, name),
                       os.path.join(here, '..', name),
                       name]                       # let the OS search PATH
    tried = []
    for path in candidates:
        if not path:
            continue
        try:
            if sys.platform == 'win32':
                return ctypes.WinDLL(path)
            return ctypes.CDLL(path)
        except OSError as exc:
            tried.append('%s (%s)' % (path, exc))
    bits = 64 if ctypes.sizeof(ctypes.c_void_p) == 8 else 32
    raise OSError(
        'okFrontPanel.dll could not be loaded. This Python is %d-bit, so the '
        'DLL must be %d-bit too -- the copy bundled with pi3diamond is 32-bit '
        'and will not work here. Install the FrontPanel SDK, or set '
        'OK_FRONTPANEL_DLL to the right file.\nTried:\n  %s'
        % (bits, bits, '\n  '.join(tried)))


_dll = _load_dll()

# Types, verified against okFrontPanelDLL.h from FrontPanel SDK 4.5.6.
#   typedef void* okFrontPanel_HANDLE;   typedef void* okPLL22150_HANDLE;
#   typedef unsigned int UINT32;         typedef int Bool;
#   ok_ErrorCode is an enum with negative members (ok_Failed = -1), so int.
_HANDLE = ctypes.c_void_p
_U32 = ctypes.c_uint32

# NOT ctypes.c_bool. The SDK declares `typedef int Bool` -- four bytes, not
# one. c_bool would pass a single byte where the DLL reads four (leaving the
# upper three as whatever was in the register) and would read only the low
# byte of a return value, so a nonzero result ending in 0x00 would read as
# False. Neither raises. This is the kind of mismatch that corrupts silently.
_BOOL = ctypes.c_int


def _bind(name, restype, argtypes):
    fn = getattr(_dll, name)
    fn.restype = restype
    fn.argtypes = argtypes
    return fn


# --- FrontPanel -----------------------------------------------------------
_fp_Construct = _bind('okFrontPanel_Construct', _HANDLE, [])
_fp_Destruct = _bind('okFrontPanel_Destruct', None, [_HANDLE])
_fp_OpenBySerial = _bind('okFrontPanel_OpenBySerial', ctypes.c_int,
                         [_HANDLE, ctypes.c_char_p])
_fp_ConfigureFPGA = _bind('okFrontPanel_ConfigureFPGA', ctypes.c_int,
                          [_HANDLE, ctypes.c_char_p])
_fp_SetWireInValue = _bind('okFrontPanel_SetWireInValue', ctypes.c_int,
                           [_HANDLE, ctypes.c_int, _U32, _U32])
_fp_UpdateWireIns = _bind('okFrontPanel_UpdateWireIns', None, [_HANDLE])
_fp_UpdateWireOuts = _bind('okFrontPanel_UpdateWireOuts', None, [_HANDLE])
_fp_GetWireOutValue = _bind('okFrontPanel_GetWireOutValue', _U32,
                            [_HANDLE, ctypes.c_int])
_fp_ActivateTriggerIn = _bind('okFrontPanel_ActivateTriggerIn', ctypes.c_int,
                              [_HANDLE, ctypes.c_int, ctypes.c_int])
_fp_UpdateTriggerOuts = _bind('okFrontPanel_UpdateTriggerOuts', None, [_HANDLE])
_fp_IsTriggered = _bind('okFrontPanel_IsTriggered', _BOOL,
                        [_HANDLE, ctypes.c_int, _U32])
_fp_WriteToBlockPipeIn = _bind('okFrontPanel_WriteToBlockPipeIn', ctypes.c_long,
                               [_HANDLE, ctypes.c_int, ctypes.c_int,
                                ctypes.c_long, ctypes.POINTER(ctypes.c_ubyte)])
_fp_GetPLL22150Configuration = _bind('okFrontPanel_GetPLL22150Configuration',
                                     ctypes.c_int, [_HANDLE, _HANDLE])
_fp_SetPLL22150Configuration = _bind('okFrontPanel_SetPLL22150Configuration',
                                     ctypes.c_int, [_HANDLE, _HANDLE])

# --- PLL22150 -------------------------------------------------------------
_pll_Construct = _bind('okPLL22150_Construct', _HANDLE, [])
_pll_Destruct = _bind('okPLL22150_Destruct', None, [_HANDLE])
_pll_SetVCOParameters = _bind('okPLL22150_SetVCOParameters', _BOOL,
                              [_HANDLE, ctypes.c_int, ctypes.c_int])
_pll_SetOutputSource = _bind('okPLL22150_SetOutputSource', None,
                             [_HANDLE, ctypes.c_int, ctypes.c_int])
_pll_SetOutputEnable = _bind('okPLL22150_SetOutputEnable', None,
                             [_HANDLE, ctypes.c_int, _BOOL])


def _as_bytes(s):
    """The C API takes char*; callers pass str. Python 2 didn't care."""
    if isinstance(s, bytes):
        return s
    return str(s).encode('utf-8')


class PLL22150(object):
    """PY3-PORT: replaces ok.PLL22150 from the SWIG binding."""

    def __init__(self):
        self._handle = _pll_Construct()
        if not self._handle:
            raise RuntimeError('okPLL22150_Construct failed')

    def SetVCOParameters(self, p, q):
        return bool(_pll_SetVCOParameters(self._handle, int(p), int(q)))

    def SetOutputSource(self, output, clksrc):
        _pll_SetOutputSource(self._handle, int(output), int(clksrc))

    def SetOutputEnable(self, output, enable):
        _pll_SetOutputEnable(self._handle, int(output), 1 if enable else 0)

    def __del__(self):
        try:
            if getattr(self, '_handle', None):
                _pll_Destruct(self._handle)
                self._handle = None
        except Exception:
            pass


class FrontPanel(object):
    """PY3-PORT: replaces ok.FrontPanel from the SWIG binding.

    Return values match the C API, so existing `if xem.OpenBySerial(s) != 0`
    checks keep working unchanged.
    """

    def __init__(self):
        self._handle = _fp_Construct()
        if not self._handle:
            raise RuntimeError('okFrontPanel_Construct failed')

    # --- device ---------------------------------------------------------
    def OpenBySerial(self, serial=''):
        return _fp_OpenBySerial(self._handle, _as_bytes(serial))

    def ConfigureFPGA(self, filename):
        return _fp_ConfigureFPGA(self._handle, _as_bytes(filename))

    # --- wires ----------------------------------------------------------
    def SetWireInValue(self, ep, val, mask=0xFFFFFFFF):
        return _fp_SetWireInValue(self._handle, int(ep),
                                  int(val) & 0xFFFFFFFF, int(mask) & 0xFFFFFFFF)

    def UpdateWireIns(self):
        _fp_UpdateWireIns(self._handle)

    def UpdateWireOuts(self):
        _fp_UpdateWireOuts(self._handle)

    def GetWireOutValue(self, ep):
        return _fp_GetWireOutValue(self._handle, int(ep))

    # --- triggers -------------------------------------------------------
    def ActivateTriggerIn(self, ep, bit):
        return _fp_ActivateTriggerIn(self._handle, int(ep), int(bit))

    def UpdateTriggerOuts(self):
        _fp_UpdateTriggerOuts(self._handle)

    def IsTriggered(self, ep, mask):
        return bool(_fp_IsTriggered(self._handle, int(ep),
                                    int(mask) & 0xFFFFFFFF))

    # --- pipes ----------------------------------------------------------
    def WriteToBlockPipeIn(self, ep, blockSize, data):
        """`data` may be bytes, bytearray, or a numpy array.

        PY3-PORT: the SWIG binding accepted a Python 2 str here. On Python 3
        a str is unicode and must not be passed through -- callers should hand
        over bytes. numpy arrays are accepted directly since the pulse
        generator builds its sequence that way.
        """
        if hasattr(data, 'tobytes'):
            buf = data.tobytes()
        elif isinstance(data, (bytes, bytearray)):
            buf = bytes(data)
        else:
            raise TypeError(
                'WriteToBlockPipeIn needs bytes or a numpy array, got %s. '
                'A Python 3 str is unicode and cannot be sent to hardware.'
                % type(data).__name__)
        arr = (ctypes.c_ubyte * len(buf)).from_buffer_copy(buf)
        return _fp_WriteToBlockPipeIn(self._handle, int(ep), int(blockSize),
                                      len(buf), arr)

    # --- PLL ------------------------------------------------------------
    def GetPLL22150Configuration(self, pll):
        return _fp_GetPLL22150Configuration(self._handle, pll._handle)

    def SetPLL22150Configuration(self, pll):
        return _fp_SetPLL22150Configuration(self._handle, pll._handle)

    def __del__(self):
        try:
            if getattr(self, '_handle', None):
                _fp_Destruct(self._handle)
                self._handle = None
        except Exception:
            pass


# The SWIG binding exposed these names too; some code may reference them.
okCFrontPanel = FrontPanel
okCPLL22150 = PLL22150


if __name__ == '__main__':
    print('okFrontPanel.dll loaded: %s' % _dll)
    print('interpreter: %d-bit' % (64 if ctypes.sizeof(ctypes.c_void_p) == 8 else 32))
    fp = FrontPanel()
    rc = fp.OpenBySerial('')
    print('OpenBySerial("") -> %d (%s)'
          % (rc, 'device opened' if rc == 0 else 'no device / error'))
