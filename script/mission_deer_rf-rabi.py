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
import time

from tools.emod import Job

# modified version to vary tau_RF instead of f_RF -> DEER-Rabi

spin_state = []
# frequency = np.arange(130e+06, 400e+06, 3e+06)
rf_pulse_length = np.arange(21, 50, 4)


# ToDo: maybe introduce lock for 'state' variable on each job?

class ForAllNvs(Job):

    def _run(self):

        try:
            self.state = 'run'

            for target in list(auto_focus.targets.keys()):

                auto_focus.periodic_focus = False
                while auto_focus.state != 'idle':
                    threading.current_thread().stop_request.wait(1.0)
                    if threading.current_thread().stop_request.is_set():
                        break
                auto_focus.current_target = target
                auto_focus.submit()
                auto_focus.periodic_focus = True

                for t in rf_pulse_length:
                    # for f in frequency:
                    # do a deer measurement and add to spin state!
                    # deer.rf_frequency = f
                    deer.t_rf_pi = t
                    # print('submitting Deer with t=' + str(f) + ' to queue')
                    print(('submitting Deer with tau_RF=' + str(t) + ' to queue'))
                    deer.submit()
                    while deer.state != 'done':
                        threading.current_thread().stop_request.wait(1.0)
                        if threading.current_thread().stop_request.is_set():
                            break
                    time.sleep(0.5)
                    spin_state.append(deer.spin_state)
                    # save data to file, in case of software crash...
                    file = open("Z:/python_data_temp/DEER_backup.txt", 'a')
                    line = ''
                    # line += '%f\t' %deer.rf_frequency
                    line += '%f\t' % deer.t_rf_pi
                    line += '%s\t' % deer.spin_state[0]
                    line += '%s\t' % deer.spin_state[1]
                    line += '%s\t' % deer.spin_state[2]
                    line += '%s\t' % deer.spin_state[3]
                    file.write(line + '\n')
                    file.close()
            self.state = 'done'
        finally:
            self.state = 'error'


if __name__ == '__main__':
    mission_deer = ForAllNvs()

    mission_deer.start()
