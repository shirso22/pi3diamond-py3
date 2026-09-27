# PY3-PORT: threading camelCase aliases (currentThread, isSet,
# setDaemon, ...) were deprecated in Python 3.10 and REMOVED in 3.13.
# Rewritten to the snake_case names, which have worked since 2.6.
"""
There are several distinct ways to go through different NVs and perform
certain measurement tasks. 

1. using the queue and 'SwitchTarget' and 'SaveJob' and 'SetJob'

  For each task, create a job and submit it to the queue.
  Provide a 'special' job for switching the NV. I.e., a queue might
  look like this: [ ODMR, Rabi, SwitchTarget, ODMR, Rabi, SwitchTarget, ...]

  pro: - very simple
       - a different set of Jobs can be submitted for individual NVs
       - every part of the 'code' is basically tested separately (uses only
         existing jobs) --> very low chance for errors
       - queue can be modified by user on run time, e.g., if an error in the tasks
         is discovered, it can be corrected
       - the submitted jobs can be run with lower priority than all the usual
         jobs, i.e., the queue can be kept during daily business and will
         automatically resume during any free time
         
  con: - no complicated decision making on how subsequent tasks are executed,
         e.g., no possibility to do first a coarse ESR, then decide in which range
         to do a finer ESR, etc. 
       - it is easy to forget save jobs. If everything goes well this is not a problem,
         because the jobs can be saved later at any time, but if there is a crash,
         unsaved jobs are lost

2. using an independent MissionControl job that is not managed by the JobManager

  Write a new job, that is not managed by the JobManager, i.e., that runs independently
  of the queue. This Job will submit jobs to the queue as needed.
  
  pro: - allows complex ways to submit jobs, e.g., depending on the result of previous
         measurement, with analysis performed in between, etc.

  con: - cannot be changed after started
       - control job will often be 'new code' and thus may have errors. It is
         difficult to test --> error prone
"""

import threading

from tools.emod import Job
from tools.utility import timestamp


# ToDo: maybe introduce lock for 'state' variable on each job?

class ForAllNvsDD(Job):

    def _run(self):

        try:
            self.state = 'run'

            # list of NV Parameters, each element is of the form [f, tpi2, tpi, tpi32]
            # NV_param = [[2.6312e+09, 67.5, 133.5, 201.0],
            # [2.6312e+09, 60.0, 120.0, 180.0],
            # [2.8277e+09, 34.5, 67.5, 102.0],
            # [2.8274e+09, 36.0, 73.5, 111.0]
            # ]
            # i = 0

            for target in sorted(auto_focus.targets.keys()):

                auto_focus.periodic_focus = False
                while auto_focus.state != 'idle':
                    threading.current_thread().stop_request.wait(1.0)
                    if threading.current_thread().stop_request.is_set():
                        break
                auto_focus.current_target = target
                auto_focus.submit()
                auto_focus.periodic_focus = True

                # start xy8 2 measurement:
                xy8.n_sequences = 2
                xy8.tau_begin = 1100
                xy8.submit()
                while xy8.state != 'done':
                    threading.current_thread().stop_request.wait(1.0)
                    if threading.current_thread().stop_request.is_set():
                        break
                xy8.save(timestamp() + '_' + target + '_100G_xy8-2.pys')

                # start xy8 4 measurement:
                xy8.n_sequences = 4
                xy8.tau_begin = 2200
                xy8.submit()
                while xy8.state != 'done':
                    threading.current_thread().stop_request.wait(1.0)
                    if threading.current_thread().stop_request.is_set():
                        break
                xy8.save(timestamp() + '_' + target + '_100G_xy8-4.pys')

                # start xy8 6 measurement:
                xy8.n_sequences = 6
                xy8.tau_begin = 3300
                xy8.submit()
                while xy8.state != 'done':
                    threading.current_thread().stop_request.wait(1.0)
                    if threading.current_thread().stop_request.is_set():
                        break
                xy8.save(timestamp() + '_' + target + '_100G_xy8-6.pys')

                # start xy8 8 measurement:
                xy8.n_sequences = 8
                xy8.tau_begin = 4400
                xy8.submit()
                while xy8.state != 'done':
                    threading.current_thread().stop_request.wait(1.0)
                    if threading.current_thread().stop_request.is_set():
                        break
                xy8.save(timestamp() + '_' + target + '_100G_xy8-8.pys')

                # start T1 measurement
                # t1pi.frequency = NV_param[i][0]
                # t1pi.t_pi = NV_param[i][2]
                # t1pi.submit()
                # while t1pi.state != 'done':
                # threading.current_thread().stop_request.wait(1.0)
                # if threading.current_thread().stop_request.is_set():
                # break
                # t1pi.save(timestamp()+'_'+target+'_T1.pys')

                # start T2 measurment
                # hahn.frequency = NV_param[i][0]
                # hahn.t_pi2 = NV_param[i][1]
                # hahn.t_pi = NV_param[i][2]
                # hahn.t_3pi2 = NV_param[i][3]
                # hahn.submit()
                # while hahn.state != 'done':
                # threading.current_thread().stop_request.wait(1.0)
                # if threading.current_thread().stop_request.is_set():
                # break
                # hahn.save(timestamp()+'_'+target+'_T2.pys')

                # start Autocorrelation measurement
                # First set the Laser to a very low power
                # laser.voltage = -8.1

                # autocorrelation.submit()
                # while autocorrelation.state != 'done':
                # threading.current_thread().stop_request.wait(1.0)
                # if threading.current_thread().stop_request.is_set():
                # break
                # autocorrelation.save(timestamp()+'_'+target+'_g2.pys')

                # Finally set the Laser to a high power again
                # laser.voltage = -7.0

                i += 1

            self.state = 'done'
        finally:
            self.state = 'error'


if __name__ == '__main__':
    mission_dd = ForAllNvsDD()

    # mission.start()
