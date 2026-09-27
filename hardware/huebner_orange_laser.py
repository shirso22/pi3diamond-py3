
from traitsui.api import View, Item, HGroup
from traits.api import HasTraits, Range, Bool, on_trait_change
import serial
import logging
logger = logging.getLogger(__name__)


class CoboltLaser(HasTraits):
    laser_state = Bool(False, label="State")
    power = Range(low=0, high=75, value=1, desc='Power', label='Power [mW]')
    laser_precision = 4

    def __init__(self,
                 port="COM5",
                 baud_rate=115200,
                 databits=serial.EIGHTBITS,
                 stop_bit=serial.STOPBITS_ONE,
                 parity=serial.PARITY_NONE,
                 handshake=False,
                 termination=" ",
                 read_timeout=1.,
                 write_timeout=1.,
                 max_power=75.,
                 **kwargs):

        super(CoboltLaser, self).__init__(**kwargs)

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

        self.connection = serial.Serial(port=self.port,
                                        baudrate=self.baudrate,
                                        bytesize=self.databits,
                                        parity=self.parity,
                                        stopbits=self.stopbits,
                                        xonxoff=self.handshake,
                                        rtscts=self.handshake,
                                        dsrdtr=self.handshake,
                                        timeout=self.read_timeout,
                                        write_timeout=self.write_timeout
                                        )

    def open_connection(self):
        if self.connection.isOpen():
            logging.warning("WARNING: Laser port was open. Closing and re-opening.")
            self.close_connection()
        self.connection.open()
        print(self.connection.name)

    def close_connection(self):
        if self.connection.isOpen():
            self.connection.close()

    def _read_all(self):
        answer = b""
        while self.connection.in_waiting > 0:
            answer += self.connection.readline()
        answer = answer.split(b" ")
        while b"" in answer:
            answer.remove(b"")
        self._last_response = answer
        # PY3-PORT: print statement -> function. The responses collected above
        # are BYTES (b"..."), which is correct for pyserial 3, so they are
        # decoded here for display only.
        print("Message received: {}".format(
            [a.decode("ascii", "replace") for a in answer]))

    def send_cmd(self, message):
        message += "\r"
        utf8_msg = message.encode()
        self.connection.write(utf8_msg)
        answer = self.connection.readline().decode()
        if len(answer) > 1:
            while (answer[-1] == "\n") or (answer[-1] == "\r"):
                answer = answer[0:-1]
                if len(answer) < 1:
                    break
        return answer

    def check(self):
        """Check if communication is working"""
        return self.send_cmd("?")

    def identify(self):
        """Fetch serial number"""
        return self.send_cmd("sn?")

    def is_connected(self):
        """Ask if laser is connected"""
        if self.connection.isOpen():
            return True
        else:
            return False

    def turn_on(self):
        """Turn on the laser with the autostart sequence"""
        logging.info("Turning on laser")
        return self.send_cmd("l1")

    def turn_off(self):
        """Turn off the laser"""
        logging.info("Turning off laser")
        return self.send_cmd("l0")

    def is_on(self):
        """Ask if laser is turned on"""
        answer = self.send_cmd("l?")
        if answer == "1":
            return True
        else:
            return False

    def _laser_on(self, enable=True):
        if enable:
            return self.send_cmd("l1")
        else:
            return self.send_cmd("l0")

    def _laser_state_changed(self):
        if self.laser_state:
            self.on()
        else:
            self.off()

    def on(self):
        return self._laser_on(enable=True)

    def off(self):
        return self._laser_on(enable=False)

    def interlock(self):
        """Returns: 0 if closed, 1 if open"""
        itl_states = {
            "0": "0 - Closed Interlock",
            "1": "1 - Open Interlock",
        }
        itl_state = self.send_cmd("ilk?")
        return itl_states.get(itl_state)

    def get_fault(self):
        """Get laser fault"""
        faults = {
            "0": "0 - No errors",
            "1": "1 - Temperature error",
            "3": "3 - Interlock error",
            "4": "4 - Constant power time out",
        }
        fault = self.send_cmd("f?")
        return faults.get(fault, fault)

    def clear_fault(self):
        """Clear laser fault"""
        return self.send_cmd("cf")

    def get_state(self):
        """Get autostart state"""
        states = {
            "0": "0 - Off",
            "1": "1 - Waiting for key",
            "2": "2 - Continuous",
            "3": "3 - On/Off Modulation",
            "4": "4 - Modulation",
            "5": "5 - Fault",
            "6": "6 - Aborted",
        }
        state = self.send_cmd("gom?")
        return states.get(state, state)

    @on_trait_change("power")
    def set_power(self, power):
        """Set laser power in mW"""
        return self.send_cmd("p {}".format(float(power) / 1000))

    def get_power(self):
        """Get laser power in mW"""
        return float(self.send_cmd("pa?")) * 1000

    def get_power_setpoint(self):
        """Get laser power setpoint in mW"""
        return float(self.send_cmd("p?")) * 1000

    def get_ophours(self):
        """Get laser operational hours"""
        return self.send_cmd("hrs?")

    view = View(
        HGroup(
            Item('laser_state'),
        ),
        Item('power', enabled_when='state'),
        title='Orange Laser', width=400, buttons=[], resizable=True,
    )

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.turn_off()
        self.close_connection()
