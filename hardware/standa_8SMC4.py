import time
from ctypes import *


class StatusStruct(Structure):
    _fields_ = [('MoveSts', c_uint),
                ('MvCmdSts', c_uint),
                ('PWRSts', c_uint),
                ('EncSts', c_uint),
                ('WindSts', c_uint),
                ('CurPosition', c_int),
                ('uCurPosition', c_int),
                ('EncPosition', c_longlong),
                ('CurSpeed', c_int),
                ('uCurSpeed', c_int),
                ('Ipwr', c_int),
                ('Upwr', c_int),
                ('Iusb', c_int),
                ('Uusb', c_int),
                ('CurT', c_int),
                ('Flags', c_uint),
                ('GPIOFlags', c_uint),
                ('CmdBufFreeSpace', c_uint),
                ]


import os

DLL_PATH = os.path.join(os.path.dirname(__file__), 'libximc.dll')

def _lazy_dll(loader, name):
    """PY3-PORT: defer a vendor DLL load until something actually calls into it.

    Returns a proxy that loads on first attribute access, so importing this
    module works on a machine without the driver installed. Only real use
    raises, and with a message saying which DLL and why.
    """
    import ctypes as _ctypes

    class _LazyDLL(object):
        _dll = None

        def __getattr__(self, attr):
            if _LazyDLL._dll is None:
                try:
                    _LazyDLL._dll = loader(name)
                except OSError as exc:
                    bits = 64 if _ctypes.sizeof(_ctypes.c_void_p) == 8 else 32
                    raise OSError(
                        "%s could not be loaded, so %r is unavailable. Install the "
                        "vendor driver and check that its bitness matches this "
                        "Python interpreter (%d-bit). Original error: %s"
                        % (name, attr, bits, exc))
            return getattr(_LazyDLL._dll, attr)

    return _LazyDLL()


# PY3-PORT: was a module-level DLL load, which made importing this
# module require the vendor driver to be installed.
dll = _lazy_dll(windll.LoadLibrary, DLL_PATH)

# dll = windll.LoadLibrary(r'libximc.dll')

dll.enumerate_devices.restype = c_uint32
dll.get_device_name.restype = c_char_p


# dll.command_move (device, cur_pos + 100, 0)

# dll.get_status(c_long(axis),byref(params))

class Stage(object):
    """Provides control over a Standa 8SMC4-USB stepper motor stage controller box."""

    def __init__(self, device_names=None):
        devenum = dll.enumerate_devices(0)
        names_count = dll.get_device_count(devenum)

        if device_names:
            self.device_names = device_names
        else:
            self.device_names = [dll.get_device_name(devenum, i) for i in [0, 2, 3]]

        self.open_devices()

        self.state = StatusStruct()

    def open_devices(self):
        self.devices = [dll.open_device(name) for name in self.device_names]

    def close_devices(self):
        [dll.close_device(device) for device in self.devices]

    def set_position(self, axis, position, timeout=60):
        moving = self.get_move_state(axis)
        dll.command_move(self.devices[axis], position, 0)
        if not moving:  # wait for stage to start moving
            start_time = time.time()
            while self.get_move_state(axis) == 0 and (time.time() - start_time) < timeout:
                time.sleep(0.1)
        start_time = time.time()  # wait for stage to finish moving
        while self.get_move_state(axis) != 0 and (time.time() - start_time) < timeout:
            time.sleep(0.1)
        actual_position = self.get_position(axis)
        if actual_position != position:
            raise RuntimeError('Position not reached. Current position: %i' % actual_position)

    def get_position(self, axis):
        dll.get_status(self.devices[axis], byref(self.state))
        return self.state.CurPosition

    def get_move_state(self, axis):
        dll.get_status(self.devices[axis], byref(self.state))
        return self.state.MoveSts

    def go_home(self, axis):
        dll.command_home(self.devices[axis])

    def set_zero(self, axis):
        dll.command_zero(self.devices[axis])

    def null(self, axis, timeout=60):
        moving = self.get_move_state(axis)
        dll.command_home(self.devices[axis])
        if not moving:  # wait for stage to start moving
            start_time = time.time()
            while self.get_move_state(axis) == 0 and (time.time() - start_time) < timeout:
                time.sleep(0.1)
        start_time = time.time()  # wait for stage to finish moving
        while self.get_move_state(axis) != 0 and (time.time() - start_time) < timeout:
            time.sleep(0.1)
        # set home position as zero
        dll.command_zero(self.devices[axis])


"""

set new z:

get current 


"""


class TiltPlate(Stage):

    def any_moving(self):
        """Return True is any axis is moving"""
        return any([self.get_move_state(axis) for axis in range(3)])

    def get_all_positions(self):
        self.positions = tuple([self.get_position(axis) for axis in range(3)])
        return self.positions

    def set_all_positions(self, positions, timeout=60):
        if self.get_all_positions() == positions:
            return
        [dll.command_move(self.devices[axis], positions[axis], 0) for axis in range(3)]
        start_time = time.time()
        while self.get_all_positions() != positions:
            if (time.time() - start_time) > timeout:
                raise RuntimeError('Position not reached. Current position: ' + str(self.get_all_positions()))
            time.sleep(0.1)

    #    def set_all_positions(self, positions, timeout=60):
    #        if self.get_all_positions() == positions:
    #            return
    #        moving = self.any_moving()
    #        [dll.command_move(self.devices[axis], positions[axis], 0) for axis in range(3) ]
    #        if not moving: # wait for stage to start moving
    #            start_time = time.time()
    #            while not self.any_moving() and (time.time() - start_time ) < timeout:
    #                time.sleep(0.1)
    #        start_time = time.time() # wait for stage to finish moving
    #        while self.any_moving() and (time.time() - start_time ) < timeout:
    #            time.sleep(0.1)
    #        actual_positions = self.get_all_positions()
    #        if actual_positions != positions:
    #            raise RuntimeError('Position not reached. Current position: '+str(actual_positions))

    def pos_to_tip_tilt_z(self, pos):
        z = (pos[0] + (pos[1] + pos[2]) / 2) / 2
        tip = pos[0] - z
        tilt = (pos[1] - pos[2]) / 2
        return tip, tilt, z

    def tip_tilt_z_to_pos(self, r):
        tip, tilt, z = r
        p0 = z + tip
        p1 = z - tip + tilt
        p2 = z - tip - tilt
        return p0, p1, p2

    def get_tip_tilt_z(self):
        pos = self.get_all_positions()
        return self.pos_to_tip_tilt_z(pos)

    def set_tip_tilt_z(self, r):
        pos = self.tip_tilt_z_to_pos(r)
        self.set_all_positions(pos)

    def set_tip(self, tip, timeout=60):
        r = self.get_tip_tilt_z()
        r = tip, r[1], r[2]
        self.set_tip_tilt_z(r)

    def set_tilt(self, tilt, timeout=60):
        r = self.get_tip_tilt_z()
        r = r[0], tilt, r[2]
        self.set_tip_tilt_z(r)

    def set_z(self, z, timeout=60):
        r = self.get_tip_tilt_z()
        r = r[0], r[1], z
        self.set_tip_tilt_z(r)


from traits.api import HasTraits, Int
from traitsui.api import View, Item, VGrid


class TiltPlateTraits(TiltPlate, HasTraits):
    z = Int(default_value=0., mode='text', auto_set=False, enter_set=True)
    tip = Int(default_value=0, mode='text', auto_set=False, enter_set=True)
    tilt = Int(default_value=0, mode='text', auto_set=False, enter_set=True)

    actual_z = Int()
    actual_tip = Int()
    actual_tilt = Int()

    def __init__(self, *args, **kwargs):
        super(TiltPlateTraits, self).__init__(*args, **kwargs)
        #        TiltPlate.__init__(self)
        #        HasTraits.__init__(self)
        tip, tilt, z = self.get_tip_tilt_z()
        self.z = self.actual_z = z
        self.tip = self.actual_tip = tip
        self.tilt = self.actual_tilt = tilt
        self.on_trait_change(self.on_z_change, 'z')
        self.on_trait_change(self.on_tip_change, 'tip')
        self.on_trait_change(self.on_tilt_change, 'tilt')

    def on_tip_change(self, new):
        self.set_tip(new)
        self.actual_tip = self.get_tip_tilt_z()[0]

    def on_tilt_change(self, new):
        self.set_tilt(new)
        self.actual_tilt = self.get_tip_tilt_z()[1]

    def on_z_change(self, new):
        self.set_z(new)
        self.actual_z = self.get_tip_tilt_z()[2]

    traits_view = View(VGrid(Item('z'),
                             Item('actual_z', style='readonly', show_label=False),
                             Item('tip'),
                             Item('actual_tip', style='readonly', show_label=False),
                             Item('tilt'),
                             Item('actual_tilt', style='readonly', show_label=False)),
                       title='Tilt Plate', buttons=[], resizable=True
                       )


if __name__ == '__main__':
    # stage = Stage(device_names=['\\\\.\\COM6', '\\\\.\\COM7', '\\\\.\\COM5'])
    # plate = TiltPlate(device_names=['\\\\.\\COM6', '\\\\.\\COM7', '\\\\.\\COM5'])
    plate = TiltPlateTraits(device_names=['\\\\.\\COM6', '\\\\.\\COM7', '\\\\.\\COM5'])
    plate.edit_traits()
