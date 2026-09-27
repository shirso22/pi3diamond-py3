#!/usr/bin/env python3
"""
ok_probe.py -- ask okFrontPanel.dll what boards it can see.

    python ok_probe.py

Run from the pi3diamond root, with nothing else holding the boards (close any
other Python, and the FrontPanel application if it is open -- Opal Kelly
devices open exclusively).

This answers, in order:
  1. which DLL is being used, and whether it loads at all
  2. how many devices the driver enumerates
  3. their serials and models
  4. whether the serials pi3diamond.py asks for are among them
  5. what OpenBySerial actually returns

Enumeration is a driver-level question, so a count of 0 means the host cannot
see the hardware -- that is a cable, power or driver problem, not a Python one.
"""

import ctypes
import os
import sys

# pi3diamond.py's expectations. Edit if yours differ.
WANTED = {
    '11130000UV': 'TimeTagger FPGA (pi3diamond.py:59)',
    'fQWpZoZxWc': 'pulse generator (pi3diamond.py:64)',
    '': 'any device (OpenBySerial with an empty string takes the first free one)',
}

sys.path.insert(0, os.getcwd())
try:
    from hardware import ok as ok_module
except Exception as exc:
    print('could not import hardware.ok: %s: %s' % (type(exc).__name__, exc))
    sys.exit(1)

dll = getattr(ok_module, '_dll', None)
if dll is None:
    print('hardware.ok imported but exposes no _dll handle; check ok.py')
    sys.exit(1)
print('DLL in use : %s' % getattr(dll, '_name', '<unknown>'))

H = ctypes.c_void_p


def bind(name, restype, argtypes):
    try:
        f = getattr(dll, name)
    except AttributeError:
        return None
    f.restype, f.argtypes = restype, argtypes
    return f


construct = bind('okFrontPanel_Construct', H, [])
destruct = bind('okFrontPanel_Destruct', None, [H])
count = bind('okFrontPanel_GetDeviceCount', ctypes.c_int, [H])
serial_at = bind('okFrontPanel_GetDeviceListSerial', ctypes.c_int,
                 [H, ctypes.c_int, ctypes.c_char_p])
model_at = bind('okFrontPanel_GetDeviceListModel', ctypes.c_int,
                [H, ctypes.c_int])
open_by = bind('okFrontPanel_OpenBySerial', ctypes.c_int, [H, ctypes.c_char_p])

if not construct or not count:
    print('this DLL does not export the enumeration entry points -- unexpected;')
    print('report the DLL path above.')
    sys.exit(1)

hnd = construct()
n = count(hnd)
print('devices enumerated by the driver: %d' % n)

found = []
for i in range(n):
    buf = ctypes.create_string_buffer(64)
    if serial_at:
        serial_at(hnd, i, buf)
    model = model_at(hnd, i) if model_at else -1
    s = buf.value.decode('ascii', 'replace')
    found.append(s)
    print('  [%d] serial %-16s model id %s' % (i, s or '<empty>', model))

if n == 0:
    print('')
    print('Nothing is visible to the driver. In order of likelihood:')
    print('  * board unpowered or USB unplugged')
    print('  * Opal Kelly USB driver not installed for 64-bit Windows')
    print('    (Device Manager -> is there an Opal Kelly device, or an unknown')
    print('     device with a yellow mark?)')
    print('  * another process holds the boards -- Opal Kelly opens exclusively')
    print('  * DLL newer than the installed driver, or vice versa')
    destruct and destruct(hnd)
    sys.exit(2)

print('')
for want, who in WANTED.items():
    if not want:
        continue
    print('%-14s %s -- %s' % (want, 'PRESENT' if want in found else 'NOT FOUND', who))

print('')
for serial in [s for s in found] + ['']:
    h2 = construct()
    rc = open_by(h2, serial.encode('ascii'))
    print('OpenBySerial(%-16r) -> %d %s'
          % (serial, rc, '(success)' if rc == 0 else '(failure)'))
    destruct and destruct(h2)

destruct and destruct(hnd)
