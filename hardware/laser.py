import logging

import numpy as np
import serial
from traits.api import HasTraits, Range, Float, Str, on_trait_change, Bool
from traitsui.api import View, Item, HGroup

from hardware.nidaq import AOTask


class Laser(HasTraits):
    ao_channel = Str('/Dev1/ao3')
    voltage_min = Float(-10.)
    voltage_max = Float(1.)

    voltage = Range(low='voltage_min', high='voltage_max', value='voltage_min',
                    desc='output voltage', label='Voltage [V]')

    def __init__(self, **kwargs):
        super(Laser, self).__init__(**kwargs)
        self._create_task()
        self.update_voltage(self.voltage)
        self.on_trait_change(self.update_voltage, 'voltage')

    def _create_task(self):
        self.ao_task = AOTask(Channels=self.ao_channel, range=(self.voltage_min, self.voltage_max))

    def update_voltage(self, new):
        self.ao_task.Write(np.array((new,)))

    view = View(Item('voltage'),
                title='Laser', width=400, buttons=[], resizable=True, x=0, y=800)


class IBeamSmart(HasTraits):
    laser_state = Bool(False, label="State")
    power = Range(low=0., high=100., value=2., desc='power', label='Power [mW]')
    external_state = Bool(True, label="External")

    def __init__(self,
                 port="COM4",
                 baud_rate=115200,
                 databits=serial.EIGHTBITS,
                 stop_bit=serial.STOPBITS_ONE,
                 parity=serial.PARITY_NONE,
                 handshake=False,
                 termination="\r\n",
                 read_timeout=5.,
                 write_timeout=5.,
                 max_power=100.,
                 **kwargs):

        super(IBeamSmart, self).__init__(**kwargs)

        self.baudrate = baud_rate
        self.port = port
        self.databits = databits
        self.stopbits = stop_bit
        self.parity = parity
        self.handshake = handshake
        self.termination = termination
        self.read_timeout = read_timeout
        self.write_timeout = write_timeout
        self.max_power = max_power

        self.connection = serial.Serial(port=self.port, baudrate=self.baudrate,
                                        bytesize=self.databits, parity=self.parity,
                                        stopbits=self.stopbits, xonxoff=self.handshake,
                                        rtscts=self.handshake, dsrdtr=self.handshake,
                                        timeout=self.read_timeout, write_timeout=self.write_timeout)

    def open_connection(self):
        if self.connection.isOpen():
            logging.warning("WARNING: Laser port was open. Closing and re-opening.")
            self.close_connection()

        self.connection.open()

    def close_connection(self):
        if self.connection.isOpen():
            self.connection.close()

    def _write(self, string):
        self.connection.write(string.encode())

    def _read_all(self):
        answer = b""
        while self.connection.in_waiting > 0:
            answer += self.connection.read(1)
        answer = answer.split(b"\r\n")
        while b"" in answer:
            answer.remove(b"")
        self._last_responce = answer
        return answer

    def _send_command(self, command):
        self._write(command + self.termination)

    def _send_commands(self, command_list):
        command = " ".join(command_list)
        # print("Sending command: " + command)
        self._send_command(command)

    def enable_external(self):
        self._send_command("en ext")

    def disable_external(self):
        self._send_command("di ext")

    def _external_state_changed(self):
        if self.external_state:
            self.enable_external()
        else:
            self.disable_external()

    def _laser_on(self, enable=True):
        if enable:
            enable_string = "on"
        else:
            enable_string = "off"
        return self._send_commands((["laser", enable_string]))

    def _laser_state_changed(self):
        if self.laser_state:
            self.on()
        else:
            self.off()

    def on(self):
        return self._laser_on(enable=True)

    def off(self):
        return self._laser_on(enable=False)

    def _channel(self, power, channel):
        if not (isinstance(channel, float) or isinstance(channel, int)):
            raise TypeError
        if power < 0 or power > self.max_power:
            raise ValueError()
        if channel < 1 or channel > 2:
            raise ValueError()

        self._send_commands(["ch", str(channel), "pow", "{}".format(power), ""])

    def _enable(self, channel):
        if not isinstance(channel, int):
            raise TypeError()
        if channel < 1 or channel > 2:
            raise ValueError()

        return self._send_command("enable {}".format(channel))

    def enable_ch2(self):
        return self._enable(channel=2)

    @on_trait_change("power")
    def set_power(self, power):
        return self._channel(power, channel=2)

    def get_power(self):
        return self.power

    view = View(
        HGroup(
            Item('laser_state'),
            Item('external_state'),
        ),
        Item('power', enabled_when='laser_state'),
        title='Laser', width=400, buttons=[], resizable=True,
    )


if __name__ == '__main__':
    laser = Laser(voltage_min=-10, voltage_max=10)
    laser.edit_traits()
