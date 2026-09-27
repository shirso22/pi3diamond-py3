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

class ForAllNvs(Job):
    nv_list = {'NV01': [1.835416e9, 57., 114., 171.],
               'NV02': [1.836140e9, 60, 120, 180],
               'NV03': [1.835288e9, 60, 120, 180],
               'NV04': [1.836222e9, 59, 118, 176],
               'NV05': [1.839465e9, 55, 110, 165],
               'NV06': [1.838181e9, 56, 112, 168],
               'NV07': [1.835923e9, 60, 120, 179],
               'NV08': [1.835907e9, 57, 113, 169],
               'NV09': [1.835955e9, 59, 118, 176],
               'NV10': [1.835877e9, 53, 106, 159],
               'NV11': [1.836126e9, 57, 115, 172],
               'NV12': [1.835122e9, 57, 114, 172],
               'NV13': [1.839622e9, 54, 108, 162],
               'NV14': [1.835978e9, 58, 116, 175],
               'NV15': [1.836014e9, 53, 106, 159],
               'NV16': [1.8358625e9, 49, 99, 148],
               'NV17': [1.835960e9, 54, 107, 161],
               'NV18': [1.835871e9, 54, 108, 162],
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
                # generate a t_pi list to sweep
                t_pi_sweep = np.arange(10, 300, 20)
                for t in t_pi_sweep:
                    t1pi.t_pi = t
                    t1pi.submit()
                    while t1pi.state != 'done':
                        threading.current_thread().stop_request.wait(1.0)
                        if threading.current_thread().stop_request.is_set():
                            break
                    t1pi.save(timestamp() + '_' + target + '_pi_' + str(t) + 'ns_T1.pys')
                self.state = 'done'
        finally:
            self.state = 'error'


if __name__ == '__main__':
    mission_tonepi = ForAllNvs()

    # mission.start()
