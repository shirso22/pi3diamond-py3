# PY3-PORT: threading camelCase aliases (currentThread, isSet,
# setDaemon, ...) were deprecated in Python 3.10 and REMOVED in 3.13.
# Rewritten to the snake_case names, which have worked since 2.6.
"""
Utilises the NV center as a DC magnetometer.

We use ODMR measurements of the 15N hyperfine transitions and subsequent fitting to the S=1
Hamiltonian to determine the magnetic field from one NV center.
"""

import threading

import numpy as np

from analysis.level_splitting import find_b
from tools.emod import Job


# ToDo: maybe introduce lock for 'state' variable on each job?


class DCMagnetometer(Job):
    b_field = []
    f_start_lower = 2.58e+09
    f_start_upper = 2.61e+09
    frequency_delta = 0.5e6
    stop_time = 120.0
    file = 'Z:\\data\\20170105\\4K\\NV5G01\\78K\\magnetometer'

    def _run(self):

        try:
            self.state = 'run'

            odmr.frequency_begin = self.f_start_lower
            odmr.frequency_end = self.f_start_upper
            odmr.frequency_delta = self.frequency_delta
            odmr.power = -24.0
            odmr.stop_time = self.stop_time
            odmr.calculate_center = True
            odmr.submit()
            while odmr.state != 'done':
                threading.current_thread().stop_request.wait(1.0)
                if threading.current_thread().stop_request.is_set():
                    break
            if odmr.fit_frequencies.shape[0] == 2:
                self.df_down = odmr.center
            else:
                if odmr.fit_frequencies[0] == np.nan:
                    self.df_down = 2.87e9
                else:
                    self.df_down = odmr.fit_frequencies[0]
            odmr.save(self.file + '_lower_transition')
            odmr.frequency_begin = (2.87e9 - self.df_down) + 2.88e9 - 0.02e9
            odmr.frequency_end = (2.87e9 - self.df_down) + 2.88e9 + 0.04e9
            odmr.frequency_delta = self.frequency_delta
            odmr.power = -20.0
            odmr.stop_time = self.stop_time
            odmr.submit()
            while odmr.state != 'done':
                threading.current_thread().stop_request.wait(1.0)
                if threading.current_thread().stop_request.is_set():
                    break
            if odmr.fit_frequencies.shape[0] == 2:
                self.df_up = odmr.center
            else:
                if odmr.fit_frequencies[0] == np.nan:
                    self.df_up = 2.87e9
                else:
                    self.df_up = odmr.fit_frequencies[0]
            odmr.save(self.file + '_upper_transition')
            # Fit the two transition frequencies to the Hamiltonian
            self.b_field = find_b([self.df_down, self.df_up], D=2.88e9)
            print('Magnetic Field is B = ' + str(self.b_field) + ' \n The absolute value is ' \
                  + str(np.sqrt(self.b_field[0] ** 2 + self.b_field[1] ** 2 + self.b_field[2] ** 2)))

            self.state = 'done'
        finally:
            self.state = 'error'


if __name__ == '__main__':
    magnetometer = DCMagnetometer()
