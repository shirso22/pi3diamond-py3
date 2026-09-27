'''
Created on 01.03.2012

@author: bernhard
'''

import logging
import time

import numpy as np
from traits.api import Range, Float, Button
from traitsui.api import View, Item, HGroup, VGroup, Group

from . import hameg
from tools.utility import GetSetItemsMixin


def cartesian_to_spherical(r, unit='deg'):
    b = np.linalg.norm(r)
    if b == 0:
        return np.array([0, 0, 0])
    theta = np.arccos(r[2] / b)
    phi = np.arctan2(r[1], r[0])
    if unit == 'deg':
        theta = np.degrees(theta)
        phi = np.degrees(phi)
    elif unit != 'rad':
        raise ValueError('Undefined unit.')
    return np.array([b, theta, phi])


def spherical_to_cartesian(r, unit='deg'):
    b, theta, phi = r
    if unit == 'deg':
        theta = np.radians(theta)
        phi = np.radians(phi)
    elif unit != 'rad':
        raise ValueError('Undefined unit.')
    if not 0 <= theta <= np.pi or not (-np.pi) <= phi <= (np.pi):
        raise ValueError('Wrong angle. Chose theta between 0..180(0..pi) and phi between -180..180(-pi..pi)')
    x = b * np.sin(theta) * np.cos(phi)
    y = b * np.sin(theta) * np.sin(phi)
    z = b * np.cos(theta)
    return np.array([x, y, z])


class MagCoilControl(GetSetItemsMixin):
    """Provides Control over the magnetic field of all three coils with HMP2030 and USBRelais"""

    # magcoil_calibration = Instance( MagCoilCalibration )

    def __init__(self, device, serPort, delta_current, diff_current, voltage_max, current_max, fuse_voltage_max,
                 fuse_current_max, ampere_to_gauss, ampere_to_gauss_vec=(0., 0., 0.), reset=True):

        super(MagCoilControl, self).__init__()

        self.hmp = hameg.HMP2030(device, voltage_max, current_max, fuse_voltage_max, fuse_current_max, reset=reset)
        self.hmpbipolar = hameg.USBRelais(serPort)

        # start powersupply
        if reset:
            for ch in [1, 2, 3]:
                self.hmp.set_ch(ch)
                time.sleep(0.1)
                self.hmp.OVP(fuse_voltage_max)
                time.sleep(0.1)
                # self.hmp.FUSE(fuse_current_max) #not working yet
                self.hmp.set_current(0.0)  # A
                time.sleep(0.1)
                self.hmp.set_voltage(voltage_max)  # V proper voltage has to be set\
                time.sleep(0.1)
            # start polarity changer
            self.hmpbipolar.reset()
            self.hmpbipolar.setPort([1, 0, 1, 0, 1, 0, 0, 0])
            self.hmp.run_all()

        if not self.hmpbipolar.NOP():
            raise RuntimeError(
                'NOP failed on relais card. Shut down the field, and try ONCE with reset=True passed to __init__. All your field settings will be lost.')

        bit = self.hmpbipolar.getPort()
        if bit[0] == bit[1] or bit[2] == bit[3] or bit[4] == bit[5]:
            raise RuntimeError(
                'Bad port state on relais card. Shut down the field, and try ONCE with reset=True passed to __init__. All your field settings will be lost.')

            # internal values
        self.current_max = current_max
        self.delta_current = delta_current
        self.diff_current = diff_current

        # calibration values
        self.set_calibration(ampere_to_gauss, ampere_to_gauss_vec)

        for i in range(2):
            self.hmp.beep()

        self.update_all()

    def set_calibration(self, ampere_to_gauss, ampere_to_gauss_vec=(0., 0., 0.)):
        """set the calibration matrix (offset vector defaults to <0>)"""
        # set a,p to gauss conversion
        self.ampere_to_gauss = np.array(ampere_to_gauss)
        self.ampere_to_gauss_vec = np.array(ampere_to_gauss_vec)
        # calculate inverse gauss to ampere conversion matrices
        self.gauss_to_ampere = np.linalg.inv(self.ampere_to_gauss)
        self.gauss_to_ampere_vec = np.dot(self.gauss_to_ampere, -1 * self.ampere_to_gauss_vec)

    # funktions to reverse the polarity
    def _get_polarity(self, ch):
        """returns the polarity p of a given channel ch.
           The polarity is 1 for (+ -> 1, - -> 2 | [1,0,1,0,1,0,0,0])
           and -1 for (+ -> 2, - -> 1 | [0,1,0,1,0,1,0,0])."""
        r = self.hmpbipolar.getPort()
        if ch not in [1, 2, 3]:
            raise ValueError('Wrong channel number. Chose 1, 2 or 3.')
        elif r[2 * ch - 2] == r[2 * ch - 1]:
            raise ValueError('Undefined polarity.')
        elif r[2 * ch - 2] == 1 and r[2 * ch - 1] == 0:
            return 1
        elif r[2 * ch - 2] == 0 and r[2 * ch - 1] == 1:
            return -1
        else:
            raise ValueError("Couldn't get the polarity.")

    def _set_polarity(self, ch, p):
        """sets the polarity p of a given channel ch.
           It ramps down the current and changes the polarity.
           The output is turned off when the polarity is switched"""
        r = self._get_polarity(ch)
        if ch not in [1, 2, 3]:
            raise ValueError('Wrong channel number. Chose 1, 2 or 3.')
        elif p not in [-1, 1]:
            raise ValueError('Undefined polarity.')
        elif r != p:
            # ramp down current
            self.hmp.set_ch(ch)
            current_set = self.hmp.get_current()
            while current_set > self.delta_current:
                self.hmp.set_current(current_set - self.delta_current)
                current_set = self.hmp.get_current()
            self.hmp.set_current(0.0)

            # control
            time.sleep(0.5)  # add a timeout for the current to settle
            current_set = self.hmp.get_current()
            if current_set > self.diff_current:
                raise ValueError("cannot set current to 0A")

            self.hmp.stop()
            time.sleep(0.1)
            x = [0, 0, 0, 0, 0, 0, 0, 0]
            x[2 * ch - 2] = 1
            x[2 * ch - 1] = 1
            self.hmpbipolar.Toggle(x)

            # control
            time.sleep(0.1)
            s = self._get_polarity(ch)
            if s != p:
                raise ValueError("cannot change polarity")

    # functions to control a single coil

    def set_current(self, ch, curr, timeout=10.):
        """function to set a current (curr) at the desired coil (ch). The calibrations is done with the 'field_to_current()'.
           The current can have positive and negative values. 
           New Version, no ramping"""

        timeout = timeout * 60  # in seconds

        # check
        if ch in [1, 2, 3]:
            current_target = abs(curr)
        else:
            print('Wrong channel number. Chose 1, 2 or 3.')

        # change of polarity p
        polarity = np.sign(curr)
        if polarity == 0:
            polarity = 1
        self._set_polarity(ch, polarity)

        # change current
        self.hmp.set_ch(ch)
        self.hmp.run()
        start_time = time.time()
        self.hmp.set_current(current_target)
        while abs(self.hmp.get_current() - current_target) > self.diff_current and abs(
                start_time - time.time()) < timeout:
            time.sleep(0.1)
        time.sleep(1.)
        if abs(self.hmp.get_current() - current_target) > self.diff_current:
            self.save_stop()
            raise RuntimeError('Failed to set current! Ramping back down!')

    def set_all_currents(self, c1, c2, c3):
        self.set_current(1, c1)
        self.set_current(2, c2)
        self.set_current(3, c3)

    def get_current(self, ch):
        """function to get the current which is set on a channel (ch)"""
        # get polarity
        p = self._get_polarity(ch)
        # get current
        self.hmp.set_ch(ch)
        if ch in [1, 2, 3]:
            return p * self.hmp.get_current()
        else:
            print('Wrong channel number. Chose 1, 2 or 3.')

    def get_all_currents(self):
        return np.array([self.get_current(ch) for ch in range(1, 4)])

    ########Start obsolete methods
    def get_field(self, ch):
        """Deprecated method, use get_current instead!"""
        logging.getLogger().debug('Deprecated method, use get_current instead!')
        return self.get_current(ch)

    def set_field(self, ch, curr):
        """Deprecated method, use set_current instead!"""
        logging.getLogger().debug('Deprecated method, use set_current instead!')
        self.set_current(ch, curr)

    ########End  obsolete methods

    # functions to control all coils
    def save_stop(self):
        """ramps down the magnetic field and stops output"""
        self.set_all_currents(0.0, 0.0, 0.0)
        self.hmp.stop_all()

    def emergency_stop(self):
        """stops all channels"""
        self.hmp.stop_all()

    def off(self):
        """function to shut down the magnetic field"""
        # stop and close powersupply
        self.save_stop()
        # stop and close polarity changer
        self.hmpbipolar.setPort([0, 0, 0, 0, 0, 0, 0, 0])

        for i in range(3):
            self.hmp.beep()
        self.hmp.close()

    # functions to control the b field in 3D
    def field_to_current(self, field):
        """converts a b-field ([x,y,z]) to values of electrical current at all coils ([curr1,curr2,curr3])"""
        return np.dot(self.gauss_to_ampere, field) + self.gauss_to_ampere_vec

    def current_to_field(self, current):
        """converts the electrical current from all coils ([curr1,curr2,curr3]) to a b-field ([x,y,z])"""
        return np.dot(self.ampere_to_gauss, current) + self.ampere_to_gauss_vec

    def set_field_cartesian(self, bx, by, bz):
        """applies a b field in an arbitrary direction, which is specified via b1, b2 and b3 in crystal coordinates"""
        self.set_all_currents(*self.field_to_current([bx, by, bz]))

    def get_field_cartesian(self):
        """gives the applied field in cartesian crystal coordinates"""
        return self.current_to_field(self.get_all_currents())

    def set_field_spherical(self, b, theta, phi, unit='deg'):
        """applies a b field in an arbitrary direction, which is specified via theta and phi"""
        self.set_field_cartesian(*spherical_to_cartesian((b, theta, phi), unit=unit))

    def get_field_spherical(self, unit='deg'):
        """gives the applied field in spherical crystal coordinates"""
        return cartesian_to_spherical(self.get_field_cartesian(), unit=unit)
        # return [round(b,3),round(theta,2),round(phi,2)]

    # Gui to control the magnetic field
    get_current_1 = Float(value=0.0, desc='actual current of first coil [A]', label='I_1 [A]')
    get_current_2 = Float(value=0.0, desc='actual current of second coil [A]', label='I_2 [A]')
    get_current_3 = Float(value=0.0, desc='actual current of third coil [A]', label='I_3 [A]')
    get_bx = Float(value=0.0, desc='actual magnitude of the x-component [G]', label='b_x [G]')
    get_by = Float(value=0.0, desc='actual magnitude of the y-component [G]', label='b_y [G]')
    get_bz = Float(value=0.0, desc='actual magnitude of the z-component [G]', label='b_z [G]')
    get_b = Float(value=0.0, desc='actual magnitude of the b-field [G]', label='|B| [G]')
    get_theta = Float(value=90.0, desc='actual theta angle of the b-field vector [deg]', label='theta [deg]')
    get_phi = Float(value=0.0, desc='actual phi angle of the b-field vector [deg]', label='phi [deg]')

    set_current_1 = Range(low=-3.0, high=3.0, value=0.0, desc='current of first coil [A]', label='I_1 [A]', mode='text',
                          auto_set=False, enter_set=True)
    set_current_2 = Range(low=-3.0, high=3.0, value=0.0, desc='current of second coil [A]', label='I_2 [A]',
                          mode='text', auto_set=False, enter_set=True)
    set_current_3 = Range(low=-3.0, high=3.0, value=0.0, desc='current of third coil [A]', label='I_3 [A]', mode='text',
                          auto_set=False, enter_set=True)
    set_bx = Range(low=-40.0, high=40.0, value=0.0, desc='b_x component of the b-field in crystal coordinates [G]',
                   label='b_x [G]', mode='text', auto_set=False, enter_set=True)
    set_by = Range(low=-40.0, high=40.0, value=0.0, desc='b_y component of the b-field in crystal coordinates [G]',
                   label='b_y [G]', mode='text', auto_set=False, enter_set=True)
    set_bz = Range(low=-40.0, high=40.0, value=0.0, desc='b_z component of the b-field in crystal coordinates [G]',
                   label='b_z [G]', mode='text', auto_set=False, enter_set=True)
    set_b = Range(low=0.0, high=70.0, value=0.0, desc='Magnitude of the b-field [G]', label='|B| [G]', mode='text',
                  auto_set=False, enter_set=True)
    set_theta = Range(low=0.0, high=180.0, value=90.0, desc='theta angle of the b-field vector [deg]',
                      label='theta [deg]', mode='text', auto_set=False, enter_set=True)
    set_phi = Range(low=-180.0, high=180.0, value=0.0, desc='phi angle of the b-field vector [deg]', label='phi [deg]',
                    mode='text', auto_set=False, enter_set=True)

    set_currents_button = Button(label='Set I1,I2,I3', desc='Sets the coil currents.')
    set_field_button_cartesian = Button(label='Set B(bx,by,bz)',
                                        desc='Sets the b-field to the desired value in cartesian coordinates.')
    set_field_button_spherical = Button(label='Set B(|B|,theta, phi)',
                                        desc='Sets the b-field to the desired value in spherical coordinates.')

    save_stop_button = Button(label='Stop', desc='Safely stops the b-field.')
    emerg_stop_button = Button(label='Emerg-Stop',
                               desc='Immediately stops the b-field. Without ramping down the current.')
    update_button = Button(label='Update', desc='readout current coil states and update magnetic field values')

    # off_button = Button(label='Off', desc='Turns the b-field off and closes the connection.')
    # calibration_button = Button(label='Calibration', desc='Opens the calibration window.')

    def update_all(self):
        currents = self.get_all_currents()
        cartesian = self.current_to_field(currents)
        spherical = cartesian_to_spherical(cartesian)
        self.get_current_1, self.get_current_2, self.get_current_3 = currents
        self.get_bx, self.get_by, self.get_bz = cartesian
        self.get_b, self.get_theta, self.get_phi = spherical

    def _set_currents_button_fired(self):
        self.set_all_currents(self.set_current_1, self.set_current_2, self.set_current_3)
        self.update_all()

    def _set_field_button_cartesian_fired(self):
        self.set_field_cartesian(self.set_bx, self.set_by, self.set_bz)
        self.update_all()

    def _set_field_button_spherical_fired(self):
        self.set_field_spherical(self.set_b, self.set_theta, self.set_phi)
        self.update_all()

    def _save_stop_button_fired(self):
        self.save_stop()
        self.get_field_cartesian()
        self.get_field_spherical()

    def _emerg_stop_button_fired(self):
        self.emergency_stop()

    # def _off_button_fired(self):
    #    self.off()

    def _update_button_fired(self):
        self.update_all()

    #    def _calibration_button_fired(self):
    #        from magcoil_calibration import MagCoilCalibration
    #        magcoilcalib = MagCoilCalibration(mag_coil=self)
    #        magcoilcalib.edit_traits()

    traits_view = View(VGroup(Group(Item('get_current_1', width=-70, style='readonly'),
                                    Item('get_current_2', width=-70, style='readonly'),
                                    Item('get_current_3', width=-70, style='readonly'),
                                    Item('get_bx', width=-70, style='readonly'),
                                    Item('get_by', width=-70, style='readonly'),
                                    Item('get_bz', width=-70, style='readonly'),
                                    # Item('get_b', width=-70, style='readonly'),
                                    # Item('get_theta', width=-70, style='readonly'),
                                    # Item('get_phi', width=-70, style='readonly'),
                                    orientation='vertical', columns=3
                                    ),
                              HGroup(Item('update_button', show_label=False),
                                     ),
                              Group(Item('set_current_1', width=-60),
                                    Item('set_current_2', width=-60),
                                    Item('set_current_3', width=-60),
                                    Item('set_currents_button', show_label=False),
                                    Item('set_bx', width=-60),
                                    Item('set_by', width=-60),
                                    Item('set_bz', width=-60),
                                    Item('set_field_button_cartesian', show_label=False),
                                    # Item('set_b', width=-60),
                                    # Item('set_theta', width=-60),
                                    # Item('set_phi', width=-60),
                                    # Item('set_field_button_spherical', show_label=False),
                                    orientation='vertical', columns=4
                                    ),
                              HGroup(Item('save_stop_button', show_label=False),
                                     Item('emerg_stop_button', show_label=False),
                                     # Item('off_button', show_label=False),
                                     # Item('calibration_button', show_label=False),
                                     ),
                              ),
                       title='Magnetic field control', width=530, height=150, buttons=[], resizable=True
                       )

    get_set_items = ['set_current_1', 'set_current_2', 'set_current_2',
                     'set_bx', 'set_by', 'set_bz',
                     'set_b', 'set_theta', 'set_phi',
                     '__doc__']
