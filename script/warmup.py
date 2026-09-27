# PY3-PORT: threading camelCase aliases (currentThread, isSet,
# setDaemon, ...) were deprecated in Python 3.10 and REMOVED in 3.13.
# Rewritten to the snake_case names, which have worked since 2.6.
"""
Script for performing measurements during warumup of the cryo, measuring the temperature and saving
everything in a combined file.

TO START THE WARM UP SCRIPT:

run -i script/warmup.py
warmup.start()

TO STOP THE WARM UP SCRIPT:
warmup.stop()
"""

import threading

from hardware.nidaq import AITask
from tools.emod import Job
from tools.utility import timestamp


class LakeShoreTSensor(AITask):
    """
    Readout of a Voltage given by the LakeShore Tempreature monitor and calculation of the measured
    Temperature
    """

    def Read(self):
        self.Start()
        self.Wait()
        try:
            data = AITask.Read(self)
        except Exception as e:
            print('Unexpected error in Readout of LakeShore Temperature Sensor!')
            print(str(e))
        T = 40. * data.sum() / self.N
        self.Stop()
        return T


class WarmUp(Job):

    def __init__(self, t_sensor, folder):
        self.t_sensor = t_sensor
        self.folder = folder

    def _run(self):
        """
        Measurement loop. Here we start the measurements, wait for them to end and save them with
        the readout from t_sensor

        IMPORTANT: The class and this loop have to live in the main namespace of pi3diamond. Else
        the calls to classes executed here will fail miserably! Also there has to be at least one
        target set in auto_focus!
        :return: None
        """
        try:
            self.state = 'run'
            while self.state == 'run':
                # Check for stop request of thread
                threading.current_thread().stop_request.wait(1.0)
                if threading.current_thread().stop_request.is_set():
                    break

                # First, focus on the NV again
                auto_focus.periodic_focus = False
                while auto_focus.state != 'idle':
                    threading.current_thread().stop_request.wait(1.0)
                    if threading.current_thread().stop_request.is_set():
                        break
                auto_focus.submit()
                auto_focus.periodic_focus = True

                # Now, readout the Temperature, perform T2 measurement and readout the Temperature
                # again
                t_hahn_start = t_sensor.Read()
                time_hahn_start = timestamp()
                hahn.stop_time = 10. * 60.
                hahn.submit()
                while hahn.state != 'done':
                    threading.current_thread().stop_request.wait(1.0)
                    if threading.current_thread().stop_request.is_set():
                        break
                t_hahn_stop = t_sensor.Read()
                time_hahn_stop = timestamp()
                # Calculate Temperature of measurement and save everything
                t_hahn = (t_hahn_start + t_hahn_stop) / 2.0
                t_hahn_error = t_hahn_start - t_hahn_stop
                hahn.save(folder + time_hahn_stop + '_hahn_T=' + '{:.3f}'.format(t_hahn) + 'K pm ' +
                          '{:.3f}'.format(t_hahn_error) + 'K.pys')
                f = open(folder + 'temperatures.txt', 'a')
                f.writelines(time_hahn_start + '    ' + str(t_hahn_start) + ' K \n')
                f.writelines(time_hahn_stop + '    ' + str(t_hahn_stop) + ' K \n')
                f.close()

                # Check for stop request of thread
                threading.current_thread().stop_request.wait(1.0)
                if threading.current_thread().stop_request.is_set():
                    break

                # Now, readout the Temperature, perform Generic measurement and readout again
                # t_generic_start = t_sensor.Read()
                # time_generic_start = timestamp()
                # generic.stop_time = 60.*60.
                # generic.submit()
                # while generic.state != 'done':
                #     threading.current_thread().stop_request.wait(1.0)
                #     if threading.current_thread().stop_request.is_set():
                #         break
                # t_generic_stop = t_sensor.Read()
                # time_generic_stop = timestamp()
                # # Calculate Temperature of measurement and save everything
                # t_generic = (t_generic_start + t_generic_stop)/2.0
                # t_generic_error = t_generic_start - t_generic_stop
                # generic.save(folder + time_generic_stop + '_generic_T=' + '{:.3f}'.format(t_generic) + 'K pm ' +
                #           '{:.3f}'.format(t_generic_error) + 'K.pys')
                # f = open(folder + 'temperatures.txt', 'a')
                # f.writelines(time_generic_start + '    ' + str(t_generic_start) + ' K \n')
                # f.writelines(time_generic_stop + '    ' + str(t_generic_stop) + ' K \n')
                # f.close()
                #
                # # Check for stop request of thread
                # threading.current_thread().stop_request.wait(1.0)
                # if threading.current_thread().stop_request.is_set():
                #     break

                # Now, readout the Temperature, perform Dark Spin Hahn measurement and readout again
                t_darkspin_hahn_start = t_sensor.Read()
                time_darkspin_hahn_start = timestamp()
                darkspin_hahn.stop_time = 60. * 60.
                darkspin_hahn.submit()
                while darkspin_hahn.state != 'done':
                    threading.current_thread().stop_request.wait(1.0)
                    if threading.current_thread().stop_request.is_set():
                        break
                t_darkspin_hahn_stop = t_sensor.Read()
                time_darkspin_hahn_stop = timestamp()
                # Calculate Temperature of measurement and save everything
                t_darkspin_hahn = (t_darkspin_hahn_start + t_darkspin_hahn_stop) / 2.0
                t_darkspin_hahn_error = t_darkspin_hahn_start - t_darkspin_hahn_stop
                darkspin_hahn.save(folder + time_darkspin_hahn_stop + '_darkspin_hahn_T=' + '{:.3f}'.format(
                    t_darkspin_hahn) + 'K pm ' +
                                   '{:.3f}'.format(t_darkspin_hahn_error) + 'K.pys')
                f = open(folder + 'temperatures.txt', 'a')
                f.writelines(time_darkspin_hahn_start + '    ' + str(t_darkspin_hahn_start) + ' K \n')
                f.writelines(time_darkspin_hahn_stop + '    ' + str(t_darkspin_hahn_stop) + ' K \n')
                f.close()

                # # Check for stop request of thread
                threading.current_thread().stop_request.wait(1.0)
                if threading.current_thread().stop_request.is_set():
                    break

                # Now, readout the Temperature, perform DEER spectroscopy and readout the
                # Temperature again
                t_deer_start = t_sensor.Read()
                time_deer_start = timestamp()
                deer_spectroscopy.stop_time = 90. * 60.
                deer_spectroscopy.submit()
                while deer_spectroscopy.state != 'done':
                    threading.current_thread().stop_request.wait(1.0)
                    if threading.current_thread().stop_request.is_set():
                        break
                t_deer_stop = t_sensor.Read()
                time_deer_stop = timestamp()
                # Calculate Temperature of measurement and save everything
                t_deer = (t_deer_start + t_deer_stop) / 2.0
                t_deer_error = t_deer_start - t_deer_stop
                deer_spectroscopy.save(folder + time_deer_stop + '_DEER_T='
                                       + '{:.3f}'.format(t_deer) + 'K_pm_'
                                       + '{:.3f}'.format(t_deer_error) + 'K.pys')
                f = open(folder + 'temperatures.txt', 'a')
                f.writelines(time_deer_start + '    ' + str(t_deer_start) + ' K \n')
                f.writelines(time_deer_stop + '    ' + str(t_deer_stop) + ' K \n')
                f.close()

            self.state = 'done'
        finally:
            self.state = 'error'


if __name__ == '__main__':
    folder = 'Z:\\data\\20170105\\4K\\NV5G01\\warmup\\'
    t_sensor = LakeShoreTSensor('Dev1/ai1', 10, 100)
    warmup = WarmUp(t_sensor, folder)
