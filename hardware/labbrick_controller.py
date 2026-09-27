"""
This file is part of pi3diamond.

pi3diamond is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

pi3diamond is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with diamond. If not, see <http://www.gnu.org/licenses/>.

Copyright (C) 2009-2011 Helmut Fedder <helmut.fedder@gmail.com>
"""

import logging
import time

import numpy as np

from .labbrick_driver.labbrick import *

SWEEP_SINGLE = 0
SWEEP_REPEAT = 1

SWEEP_DOWN = 0
SWEEP_UP = 1


# note: some of these functions must not be run while a device is open, so they should
# be run only once at startup and not in the constructor of the class
def init():
    """
    Get a list of LabBrick devices. We account for double devices with an addition of '-2' in the
    dictionary. Needs to be fixed for more than 2 devices of the same kind.
    :return: dict with names and integers for identifiers.
    """
    fnLSG_SetTestMode(0)
    n = fnLSG_GetNumDevices()
    devs = np.zeros(n, dtype=np.uint32)
    fnLSG_GetDevInfo(devs)
    names = {}
    for dev in devs:
        dev_name = fnLSG_GetModelName(int(dev))[1]
        if dev_name in names:
            names[dev_name + '-2'] = int(dev)
        else:
            names[dev_name] = int(dev)
    logging.getLogger().debug('Detected devices: ' + str(names))
    return names


def init_multiple():
    fnLSG_SetTestMode(0)
    n = fnLSG_GetNumDevices()
    devs = np.zeros(n, dtype=np.uint32)
    fnLSG_GetDevInfo(devs)
    names = []
    for dev in devs:
        dev_name = fnLSG_GetModelName(int(dev))[1]
        names.append([dev_name, int(dev)])
    logging.getLogger().debug('Detected devices: ' + str(names))
    return names


labbrick_devices = init()


class LabBrick():
    trigger_from_ni = False

    on_threshold = -40

    def __init__(self, name):
        if not name in labbrick_devices:
            raise ValueError('Device not found')
        self.dev = labbrick_devices[name]
        fnLSG_InitDevice(self.dev)
        self.max_power = fnLSG_GetMaxPwr(self.dev)

    #    def __del__(self):
    #        self.setPower(-40)
    #        fnLSG_SaveSettings(self.dev)
    #        fnLSG_CloseDevice(self.dev)

    def getPower(self):
        return .25 * (40 - fnLSG_GetPowerLevel(self.dev))

    def setPower(self, power):
        fnLSG_StartSweep(self.dev, 0);  # stop all running sweeps
        # HW-FIX: odmr.py calls setOutput(None, f) to mean "frequency only".
        # Under Python 2, `None > -40` was False, so None fell through to the
        # else branch and the power was set to the -40 dBm floor. Python 3
        # raises TypeError instead, which took out the ODMR cleanup path -- and
        # the one in its own `except` handler, so the original error was buried.
        # The Python 2 behaviour is reproduced exactly: None means the floor.
        if power is not None and power > -40:
            fnLSG_SetPowerLevel(self.dev, int(power / .25))
            fnLSG_SetRFOn(self.dev, 1)
        else:
            fnLSG_SetPowerLevel(self.dev, int(-40 / .25))
            """This function is causing problems! Apparently switching the device off completely
            fucks up the usb connection... Thats why we opt just to set the power to -40"""
            # fnLSG_SetRFOn(self.dev, 0)

    def getFrequency(self):
        return fnLSG_GetFrequency(self.dev) * 1e5

    def setFrequency(self, f):
        fnLSG_StartSweep(self.dev, 0);  # stop all running sweeps
        fnLSG_SetFrequency(self.dev, int(f / 1e5))

    def setOutput(self, power, frequency):
        self.setPower(power)
        self.setFrequency(frequency)

    def Sweep(self, f_start, f_stop, df, dt=20):
        usbdelay = .01  # seconds
        # print "setting start frequency"
        time.sleep(usbdelay)
        fnLSG_SetStartFrequency(self.dev, int(f_start / 1e5))
        # print "setting end frequency"
        time.sleep(usbdelay)
        fnLSG_SetEndFrequency(self.dev, int(f_stop / 1e5))
        # print "setting frequency step "
        time.sleep(usbdelay)
        fnLSG_SetFrequencyStep(self.dev, int(df / 1e5))
        # print "setting dwell time"
        time.sleep(usbdelay)
        fnLSG_SetDwellTime(self.dev, dt)
        # print "setting sweep mode"
        time.sleep(usbdelay)
        fnLSG_SetSweepMode(self.dev, SWEEP_SINGLE);
        # print "setting sweep direction"
        time.sleep(usbdelay)
        fnLSG_SetSweepDirection(self.dev, SWEEP_UP)
        # print "starting sweep ..."
        time.sleep(usbdelay)
        fnLSG_StartSweep(self.dev, 1);
        # print "sweep running"


#    def initSweep(self, frequency, power):
#        self.f_start = frequency[0]
#        self.f_stop = frequency[-1]
#        self.df = len(frequency)

#    def resetListPos(self):
#        self.Sweep(self.f_start, self.f_stop, self.df)


if __name__ == '__main__':
    pass
    # microwave = LabBrick('LSG-402')
    # rf = LabBrick('LSG-451')
