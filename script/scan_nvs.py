# PY3-PORT: threading camelCase aliases (currentThread, isSet,
# setDaemon, ...) were deprecated in Python 3.10 and REMOVED in 3.13.
# Rewritten to the snake_case names, which have worked since 2.6.
"""
Run through a dictionary of NV centers and perform Autocorrelation, T1, T2 measurements
"""

import threading

import global_vars
from tools.emod import Job


# ToDo: maybe introduce lock for 'state' variable on each job?

class NvScanner(Job):
    dir = 'Z:\\data\\20170609_NC60_013pc\\RT\\'
    area = '9002_clean_'

    nv_list = {
        'NV4H04': [2.755239e9, 90, 182, 275],
        'NV4H05': [2.8105e9, 93, 181, 269],
        'NV4H08': [2.7635e9, 28, 56, 84],
        'NV4H09': [2.7511e9, 38, 77, 117],
        'NV4H10': [2.7042e9, 36, 71, 106],
        'NV4H11': [2.7593e9, 31, 75, 118],
        'NV4H12': [2.8102e9, 43, 89, 135],
        'NV4H13': [2.7634e9, 34, 72, 110],
    }

    def _run(self):

        try:
            self.state = 'run'

            for target in sorted(auto_focus.targets.keys()):

                auto_focus.periodic_focus = False
                while auto_focus.state != 'idle':
                    threading.current_thread().stop_request.wait(1.0)
                    if threading.current_thread().stop_request.is_set():
                        break
                auto_focus.current_target = target
                auto_focus.submit()
                auto_focus.periodic_focus = True

                # Set global variables from dict
                try:
                    nv_params = self.nv_list[target]
                    global_vars.mw_frequency = nv_params[0]
                    global_vars.mw_x_t_pi2 = nv_params[1]
                    global_vars.mw_x_t_pi = nv_params[2]
                    global_vars.mw_x_t_3pi2 = nv_params[3]
                except Exception as e:
                    print('ERROR: Somehting wnet wrong when trying to set global_variables from' \
                          ' nv_list \\n')
                    raise e

                # Measure Autocorrelation
                #   autocorrelation.submit()
                #   while autocorrelation.state != 'done':
                #       threading.current_thread().stop_request.wait(1.0)
                #       if threading.current_thread().stop_request.is_set():
                #           break
                #   autocorrelation.save(self.dir + target + '\\' + self.area + target +
                #                        '_autocorrelation.pys')

                # Measure T1
                #   t1pi.get_global_vars()
                #   t1pi.submit()
                #   while t1pi.state != 'done':
                #       threading.current_thread().stop_request.wait(1.0)
                #       if threading.current_thread().stop_request.is_set():
                #           break
                #   t1pi.save(self.dir + target + '\\' + self.area + target +'_T1.pys')

                # Measure T2
                hahn.get_global_vars()
                hahn.submit()
                while hahn.state != 'done':
                    threading.current_thread().stop_request.wait(1.0)
                    if threading.current_thread().stop_request.is_set():
                        break
                hahn.save(self.dir + self.area + target + '_T2.pys')

                self.state = 'done'
        finally:
            self.state = 'error'


if __name__ == '__main__':
    nv_scanner = NvScanner()

    # mission.start()
