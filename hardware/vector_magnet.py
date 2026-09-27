"""
3D Vector Magnet consisting of 3 current carrying coils.

This module controls a 3D adjustable magnetic field that is induced through the current in 3
solenoids. The control is achieved by serial connection via visa and subsequent DA conversion in a
self build voltage to current Amplifier.
The maximum current output per solenoid is +/-185 mA, which is split into 2 bytes
(=16 bits -> resolution = 0.006 mA). Special care should be paid to the Hysteresis of the iron
solenoid cores (= magnetic field might not be reproducible) and that currents above 100 mA introduce
substantial heat into the cryogenic system and therefore have (small) effects on Temperature and
large effects on LHe consumption.
"""

import numpy as np
import pyvisa as visa
from traits.api import HasTraits, Range, Button, Bool
from traitsui.api import View, Item


class Magnet(HasTraits):
    """
    Control of 3 current outputs that are fed into 3 solenoids containing iron cores, thus
    controlling the magnetic field.
    TODO: Warnings are issued for increasing the current above 100 mA.
    """

    _u_ref = 5.0
    _readout_status = 0
    i_rel_coil_1 = Range(low=0.0, high=1.0, value=0.5, desc='Relative Current Coil 1', label='I1 ')
    i_rel_coil_2 = Range(low=0.0, high=1.0, value=0.5, desc='Relative Current Coil 2', label='I2 ')
    i_rel_coil_3 = Range(low=0.0, high=1.0, value=0.5, desc='Relative Current Coil 3', label='I3 ')
    magnet_state = Bool(True, label="State")
    set_field_button = Button(label='Set Field',
                              desc='Sets the specified field by setting the current accordingly')
    traits_view = View(
        Item('magnet_state', show_label=True),
        Item('i_rel_coil_1', show_label=True),
        Item('i_rel_coil_2', show_label=True),
        Item('i_rel_coil_3', show_label=True),
        Item('set_field_button', show_label=False, enabled_when='magnet_state'),
        title='Vector Magnet', width=400, buttons=[], resizable=True
    )

    def __init__(self, visa_address):
        try:
            self.rm = visa.ResourceManager()
            self.visa_address = visa_address
            self.instrument = self.rm.open_resource(self.visa_address)
            self.instrument.end_input = visa.constants.SerialTermination.none
            self.instrument.read_termination = None
            self.instrument.write_termination = None
        except Exception as e:
            print("Error opening serial connection to port " + visa_address + "/n")
            print(type(e))
            print(e.args)
            print(e)

        self._field_orientations()

    def __del__(self):
        try:
            self.instrument.close()
        except Exception as e:
            print("Error closing connection. /n")
            print(type(e))
            print(e.args)
            print(e)

    def _voltage_to_hex(self, voltage, max_voltage=5.0):
        """Float to hex string conversion.
        This point is important, since any error in the maximum output voltage will result in errors
        for magnetic field.
        :param voltage: voltage in V
        :param max_voltage: maximum output voltage in V
        :return: hex string in '0000' format
        """
        binary_voltage = int(((-1. * voltage) + max_voltage) * (2 ** 16 - 1) / (2. * max_voltage))
        if binary_voltage > 65535:
            binary_voltage = 65535
        if binary_voltage < 0:
            binary_voltage = 0
        return format(binary_voltage, '04X')

    def _rel_voltage_to_hex(self, u_r):
        """Return a hex number corresponding that correspons to a float between 0 and 1 with given
        resolution.

        The resolution is 4 bytes, so the hex goes from 0000 to FFFF.
        :param u_r: relative voltage from 0 to 1
        :return: hex string with 4 hexadecimals
        """
        binary_voltage = int(u_r * (2 ** 16 - 1))
        return format(binary_voltage, '04X')

    def _hex_to_rel_voltage(self, hex_string):
        """Convert the LTC2422 readout into a voltage.

        The readout sends 24 bits, the first 4 are status information bits, the remaining 20 bits
        are the readout data. The data is returned in hex logic -> 6 hex digits.
        The returned Voltage is with respect to a reference Voltage U_ref, which in our case is ????
        Status bits: 1. 0 if conversion is complete.
                     2. channel indicator
                     3. Sign indicator, 0 if U_in < 0; 1 if U_in > 0
                     4. Extended input range indicator (0 for 0 < U_in < U_ref; 1 otherwise)
                     5. - 24. 20-bit conversion result. Thus the readout voltage is returned in the
                              resolution U_ref/2**20
        Check the manual on http://cds.linear.com/docs/en/datasheet/24212f.pdf for further info.
        :param hex_string: string containing exactly 6 hex digits.
        :return: readout voltage
        """
        if len(hex_string) == 6:
            self._readout_status = int(hex_string[0])
            readout_bits = hex_string[1:6]
            u_in = (int(readout_bits, 16) / float(2 ** 20)) * self._u_ref
            return u_in
        else:
            raise IOError(1, 'The given string does not have exactly 6 entries or is not a string.')

    def _read_adc(self):
        """Readout the ADC "LTC2422".

        The readout sends 24 bits, the first 4 are status information bits, the remaining 20 bits
        are the readout data. The data is returned in hex logic -> 6 hex digits.
        Check the manual on http://cds.linear.com/docs/en/datasheet/24212f.pdf for further info.
        :return: integer number in hex logic.
        """
        # HW-FIX: write_raw() takes bytes in pyvisa 1.x, and visalib.read()
        # returns (bytes, status), so the old `'' + bytes` raised TypeError and
        # the magnet readout never worked. Bytes are collected and decoded once.
        self.instrument.write_raw(b'MSxrrrX')
        readout_bytes = b''
        try:
            for i in range(6):
                chunk = self.instrument.visalib.read(self.instrument.session, 1)[0]
                if isinstance(chunk, str):          # some visalib backends decode for us
                    chunk = chunk.encode('ascii', 'replace')
                readout_bytes += chunk
        except Exception as e:
            print('Error in LTC2422 Readout. Possibly too few bytes were returned.')
            raise
        readout_string = readout_bytes.decode('ascii', 'replace')
        return readout_string, self._hex_to_rel_voltage(readout_string)

    def _set_dac(self, voltage, channel):
        """Sets Voltages on the 3 outputs.

        Commands to the instrument must be in the format 'S SLAVEADDRESS W A 1ST DATABYTE A 2ND
        DATABYTE A 3RD DATABYTE A P'.
        Address is 0x20 in the current jumper settings, 1st data byte sets the operation mode
        (0x2channel) for write and power up, 2nd and 3rd determine the voltage to be set
        (0V = 0x8000).
        See the documentation for LAC2609 on linear.com for further info.
        :param voltage: relative setpoint from 0 to 1; 0.5 being zero Voltage.
        :param channel: 1, 2, 3 or 4=all
        :return: nothing
        """
        if voltage < 0. or voltage > 1.:
            raise ValueError('Voltage must be between 0 and 1!')
        if channel == 1 or channel == 2 or channel == 3:
            channel -= 1
        else:
            if channel == 4:
                channel = 'F'
            else:
                raise ValueError('Channel does not exist.')
        hex_voltage = self._rel_voltage_to_hex(voltage)
        lac_string = 'MIsS20S2' + str(channel) + 'S' + hex_voltage[0:2] + 'S' + hex_voltage[2:4] \
                     + 'p'
        self.instrument.write(lac_string)

    def _set_field_button_fired(self):
        """Set the specified voltages.

        :return: static
        """
        self._set_dac(self.i_rel_coil_1, 1)
        self._set_dac(self.i_rel_coil_2, 2)
        self._set_dac(self.i_rel_coil_3, 3)

    def _magnet_state_changed(self):
        """

        """
        if self.magnet_state:
            self._set_field_button_fired()
        else:
            self._set_dac(0.5, 1)
            self._set_dac(0.5, 2)
            self._set_dac(0.5, 3)

    def _field_orientations(self):
        """Predefined magnetic field orientations for [100] NV diamond.
        Sets values in 3 arrays - beins, bzwei and bdrei.
        """
        B0 = np.array([2.5, 2.5, 2.5])
        B1 = np.array([0.3058, -0.2548, -0.9173])
        B2 = np.array([0.0398964, -0.99741, 0.0598446])
        B3 = np.array([-0.75376066, 0.13019502, -0.64412275])
        B4 = np.array([0.890043, 0.445021, -0.0988936])
        b1 = (B1 + B0) / (2. * B0)
        b2 = (B2 + B0) / (2. * B0)
        b3 = (B3 + B0) / (2. * B0)
        b4 = (B4 + B0) / (2. * B0)

        self.beins = (b1 - np.array([0.5, 0.5, 0.5])) * 1.6 + np.array([0.5, 0.5, 0.5])
        self.bzwei = (b2 - np.array([0.5, 0.5, 0.5])) * 1.6 + np.array([0.5, 0.5, 0.5])
        self.bdrei = (b3 - np.array([0.5, 0.5, 0.5])) * 1.6 + np.array([0.5, 0.5, 0.5])
        self.bvier = (b4 - np.array([0.5, 0.5, 0.5])) * 1.8 + np.array([0.5, 0.5, 0.5])

    def set_field(self, field_index):
        """Control the vector magnetic field using predefined
        values for diamond.

        :param field_index: which vector magnetic field orientation to use
        """

        if field_index == 1:
            self.i_rel_coil_1 = self.beins[0]
            self.i_rel_coil_2 = self.beins[1]
            self.i_rel_coil_3 = self.beins[2]
        elif field_index == 2:
            self.i_rel_coil_1 = self.bzwei[0]
            self.i_rel_coil_2 = self.bzwei[1]
            self.i_rel_coil_3 = self.bzwei[2]
        elif field_index == 3:
            self.i_rel_coil_1 = self.bdrei[0]
            self.i_rel_coil_2 = self.bdrei[1]
            self.i_rel_coil_3 = self.bdrei[2]
        elif field_index == 4:
            self.i_rel_coil_1 = self.bvier[0]
            self.i_rel_coil_2 = self.bvier[1]
            self.i_rel_coil_3 = self.bvier[2]
        else:
            self.i_rel_coil_1 = 0.5
            self.i_rel_coil_2 = 0.5
            self.i_rel_coil_3 = 0.5

        self._set_field_button_fired()

        print(("Magnetic field set to: ({}, {}, {})".format(self.i_rel_coil_1, self.i_rel_coil_2,
                                                           self.i_rel_coil_3)))
