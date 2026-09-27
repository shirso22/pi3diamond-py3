# PY3-PORT: threading camelCase aliases (currentThread, isSet,
# setDaemon, ...) were deprecated in Python 3.10 and REMOVED in 3.13.
# Rewritten to the snake_case names, which have worked since 2.6.
'''
Created on 01.03.2012

@author: bernhard
'''

import logging
import threading
import time

import numpy as np
from traits.api import File, Instance, Button, Enum, Range
from traitsui.api import View, Item, HGroup, VGroup

import analysis.magcoil_calibration_bfield as mcb
from hardware.magcoil_control import MagCoilControl
from measurements.odmr import ODMR
from tools.emod import Job
from tools.utility import GetSetItemsMixin  # , GetSetItemsHandler


class MagCoilCalibration(Job, GetSetItemsMixin):
    """This is an automation of the calibration process. The current is ramped up and the splitting is calculated from odmrs.

        Input:  ch_a: Channel (coil respectively) for which the calibration is done.
                curr_min_a: Minimal current which is set. Should be high enough that there is a splitting.
                curr_max_a: Maximal current which is set.
                curr_stepsize_a: Stepsize for the calibration.
                path_set: Path where the odmr settings are saved (.pys).
                path_save: Path where the calibration values should be saved (.txt will be added).
                
        Output:    txt-file for each channel, where the calibration values are listed.
                   first column --> current (A) secound column --> splittings (MHz)"""

    mag_coil = Instance(MagCoilControl)

    # Gui
    ch_a = Enum(['all', 1, 2, 3])

    curr_min_a = Range(low=-5.0, high=5.0, value=1.5,
                       desc='Minimal current which is set. Should be high enough that there is a splitting.',
                       label='|Min Curr_a| [A]', mode='text', auto_set=False, enter_set=True)
    curr_max_a = Range(low=-5.0, high=5.0, value=3.5, desc='Maximal current which is set.', label='|Max Curr_a| [A]',
                       mode='text', auto_set=False, enter_set=True)
    curr_stepsize_a = Range(low=0.0, high=5.0, value=0.5, desc='Stepsize for coil a.', label='|Stepsize_a| [A]',
                            mode='text', auto_set=False, enter_set=True)

    path_set = File()
    path_save = File()

    start_button = Button(label='start', desc='Start the calibration.')
    stop_button = Button(label='stop', desc='Stop the calibration.')
    analyse_button = Button(label='analyse', desc='Start the calibration.')

    def _start_button_fired(self):
        """React to submit button. Submit the Job."""
        self.start()

    def _stop_button_fired(self):
        """React to remove button. Remove the Job."""
        self.stop()

    def _analyse_button_fired(self):
        """React to analyse button. Starts instance of analysis."""
        magcoilcalibana = mcb.MagCoilCalibration_BField()
        magcoilcalibana.edit_traits()

    odmr = Instance(ODMR)

    traits_view = View(VGroup(HGroup(Item('ch_a'),
                                     Item('curr_min_a', width=-30, enabled_when='state != "run"'),
                                     Item('curr_max_a', width=-30, enabled_when='state != "run"'),
                                     Item('curr_stepsize_a', width=-30, enabled_when='state != "run"'),
                                     ),
                              HGroup(Item('start_button', show_label=False),
                                     Item('stop_button', show_label=False),
                                     # Item('odmr', editor=InstanceEditor(), show_label=False),
                                     Item('analyse_button', show_label=False),
                                     Item('state', style='readonly'),
                                     ),
                              VGroup(Item('path_set'),
                                     Item('path_save'),
                                     ),
                              ),
                       title='Magnetic field calibration', buttons=[], resizable=True
                       )

    get_set_items = ['ch_a', 'curr_min_a', 'curr_max_a', 'curr_stepsize_a',
                     'path_set', 'path_save', '__doc__']

    def _run(self):
        """runs the calibration as specified with traits variables"""
        try:
            self.state = 'run'

            if self.path_set == '':
                raise ValueError('Filename missing. Please specify a filename and try again.')
            if self.path_save == '':
                raise ValueError('Filename missing. Please specify a filename and try again.')

            if self.ch_a == 'all':
                curr_steps_a = int(abs(self.curr_max_a - self.curr_min_a) / self.curr_stepsize_a)
                calib_matrix = np.zeros((3, curr_steps_a + 1, 2))
                for i in range(3):
                    calib_matrix[i] = self.calibration((i + 1), self.path_set, self.path_save, self.curr_min_a,
                                                       self.curr_max_a, self.curr_stepsize_a)
                    if threading.current_thread().stop_request.is_set():
                        break
            else:
                calib_matrix = self.calibration(self.ch_a, self.path_set, self.path_save, self.curr_min_a,
                                                self.curr_max_a, self.curr_stepsize_a)

            self.state = 'done'
        except:
            logging.getLogger().exception('Error in MagCoilCalibration.')
            self.state = 'error'

            # Calibration helper functions

    def string_to_file(self, datastring, path):
        """writes datastring to file"""
        try:
            f = open(path, 'a')
            try:
                f.write(datastring)
            finally:
                f.close()
        except IOError:
            print('Error exporting data')
            return False
        return True

    def list_to_file(self, list, path):
        """writes simple list to file"""
        datastring = ''
        for m in range(len(list)):
            datastring = datastring + ', ' + str(list[m])
        datastring = datastring.strip(', ') + '\n'
        self.string_to_file(datastring, path)

    def make_odmr(self):
        """performs an odmr  with the odmr instance 'self.odmr' and returns the frequency splitting"""
        try:
            self.odmr.perform_fit = False
            time.sleep(10)
            self.odmr.submit()
            time.sleep(15)
            while self.odmr.state in ['idle', 'run', 'wait']:
                time.sleep(2)
                if threading.current_thread().stop_request.is_set():
                    self.odmr.remove()
                    return np.nan
            if self.odmr.state == 'error':
                raise ValueError("Error in ODMR.")
            time.sleep(15)  # maybe longer, because the odmr takes a while until it is done
            self.odmr.perform_fit = True
            time.sleep(15)
            if len(self.odmr.fit_frequencies) not in [2, 6]:
                return np.nan
            if self.odmr.number_of_resonances == '2':
                f_Lm = self.odmr.fit_frequencies[0]
                f_Rm = self.odmr.fit_frequencies[1]
            elif self.odmr.number_of_resonances in ['6', 'auto']:
                f_Lm = (self.odmr.fit_frequencies[1] + self.odmr.fit_frequencies[0] + self.odmr.fit_frequencies[2]) / 3.
                f_Rm = (self.odmr.fit_frequencies[3] + self.odmr.fit_frequencies[4] + self.odmr.fit_frequencies[5]) / 3.
            else:
                raise ValueError("Error in ODMR.")
            if not self.odmr.frequency_begin < f_Lm <= f_Rm < self.odmr.frequency_end:
                raise ValueError('Invalid frequency received from odmr, could not complete calibration.')
            f_split = f_Rm - f_Lm
            return f_split
        except:
            return np.nan

    # Calibration functions
    def calibration(self, ch_a, path_set, path_save, curr_min_a=1, curr_max_a=4.5, curr_stepsize_a=0.3):
        """ramps up the current and takes odmrs"""
        # preconditions
        self.mag_coil.save_stop()
        self.odmr.load(path_set)

        curr_steps_a = int(abs(curr_max_a - curr_min_a) / curr_stepsize_a)
        calib_matrix = np.zeros((curr_steps_a + 1, 2))
        path_save = path_save + '_ch' + str(ch_a) + '.txt'

        # start calibration
        for i in range(curr_steps_a + 1):
            curr_a = np.sign(curr_max_a) * ((curr_stepsize_a * i) + abs(curr_min_a))
            self.mag_coil.set_field(ch_a, curr_a)
            time.sleep(5)  # maybe longer, because the b-field might change if the coils get warm
            l = list(range(2))
            l[0] = curr_a
            f_split_a = self.make_odmr()
            l[1] = f_split_a
            calib_matrix[i] = l

            self.list_to_file(l, path_save)
            if threading.current_thread().stop_request.is_set():
                break

        self.mag_coil.save_stop()
        return calib_matrix


if __name__ == '__main__':
    #    from magcoil_control import MagCoilControl
    #    mag_coil=MagCoilControl(#connection to HMP2030 and BipolarHMP2030
    #                                                   device='169.254.10.10:50000',#ip-address and port
    #                                                   serPort=2,#COM-port
    #                                                   #difference between two current values
    #                                                   delta_current=0.1,#A current step size
    #                                                   diff_current=0.005,#A current difference to the desired value
    #                                                   #values for maximal voltage and current
    #                                                   voltage_max=32.0,#V high enough that it is always CC mode
    #                                                   current_max=4.5,#A (no heating); depending on the diameter of the used wire
    #                                                   #values for over voltage protection and FUSE
    #                                                   fuse_voltage_max=32.0,#V; 32V is maximum HMP2030 can supply
    #                                                   fuse_current_max=5.0,#A (no heating); 5A is maximum HMP2030 can supply
    #                                                   #calibration values (G/A) to convert a current in a magnetic field (Gauss) 07/25/12
    #                                                   AtoG=np.matrix([[-3.549, 5.331, -1.798],
    #                                                                   [-5.144, -0.539, 5.289],
    #                                                                   [-3.624, -2.592, -3.146]]),
    #                                                   #calibration values (G) offset 08/06/12
    #                                                   AtoG_vec=np.matrix([[0.170],
    #                                                                       [0.176],
    #                                                                       [0.044]])
    #                                                   )
    #    from hardware.dummy import Microwave, Counter
    #    microwave = Microwave()
    #    counter = Counter()
    #    from measurements.odmr import ODMR
    #    odmr = ODMR(microwave, counter)
    magcoilcalib = MagCoilCalibration(mag_coil=mag_coil, odmr=odmr)
    magcoilcalib.edit_traits()
