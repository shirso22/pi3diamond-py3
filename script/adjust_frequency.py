"""

Example of usage:

1. create an instance of a CPMG measurement and set the desired parameters
2. create an instance of an ODMR measurement and set the desired parameters
3. in the '__main__' section below, change the names of 'odmr' and 'cpmg' to reflect the names of your instances
4. execute this script from the ipython shell by typing

    run -i script/adjust_frequency

"""

intervals = list(range(0, 60, 20))

import logging
import time

from tools.emod import ManagedJob
from tools.utility import timestamp


def string_to_file(datastring, path):
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


class SetJob(ManagedJob):
    """
    A mini job that sets the frequency of 'cpmg' with the
    fit result from 'odmr'.
    """

    def __init__(self, odmr, cpmg):
        super(SetJob, self).__init__()
        self.odmr = odmr
        self.cpmg = cpmg

    def _run(self):
        try:
            self.state = 'run'
            self.odmr.perform_fit = True
            time.sleep(1.0)
            f_new = odmr.fit_frequencies[0]
            f_begin = odmr.frequency_begin
            f_end = odmr.frequency_end
            # run_str = str(int(self.cpmg.measurement.run_time))
            ts = timestamp()
            path = 'log/adjust_frequency_log.txt'
            if f_begin < f_new < f_end:
                self.cpmg.measurement.frequency = f_new
                datastring = ts + ', ' + str(self.cpmg.measurement.frequency) + '\n'
                string_to_file(datastring, path)
            else:
                string_to_file('#Warning! Invalid frequency received from odmr, not passing to cpmg!\n', path)
            logging.getLogger().info('ESR: %e' % f_new)
            # self.odmr.save('log/odmr_freqs/'+ts+'_odmr_refocus.pys')
            # d = cpmg.get_items()
            # d['frequency_history']=frequencies
            self.cpmg.save('defaults/cpmg_current.pys')
            self.odmr.save('log/odmr/odmr_' + ts + '.pys')

        finally:
            self.state = 'idle'

    def __repr__(self):
        return 'Set frequency of ' + str(self.cpmg) + ' with result from ' + str(self.odmr)


class AdjustFrequency(object):
    """
    Adjusts the frequency of cpmg measurement 'cpmg' with the
    result from an odmr measurement 'odmr'.
    
    Example of Usage:
    
       adjust_frequency = AdjustFrequency(odmr, cpmg)
       adjust_frequency()
       
    Explanation:
    
    Upon instantiation, we need to pass the odmr and cpmg measurements
    on which AdjustFrequency should act. When Called, adjust_frequency
    sets the priority of the odmr job to 5 and calls its .submit() method.
    In addition, it creates a mini job also with priority 5 that does nothing
    but setting the frequency of the cpmg job with the result from the
    odmr job. This mini job gets executed as soon as odmr is done. After the mini job
    is finished, the cpmg job is first in the queue and continues as usual.
    """

    def __init__(self, odmr, cpmg):
        self.odmr = odmr
        self.cpmg = cpmg

    def __call__(self):
        self.odmr.priority = 5
        self.odmr.number_of_resonances = 1
        self.odmr.perform_fit = False
        self.odmr.submit()
        set_job = SetJob(self.odmr, self.cpmg)
        set_job.priority = 5
        set_job.submit()


if __name__ == '__main__':
    from tools.cron import CronDaemon, CronEvent

    adjust_frequency_event = CronEvent(AdjustFrequency(odmr, cpmg_tool), min=intervals)
    CronDaemon().register(adjust_frequency_event)
    # CronDaemon().remove( adjust_frequency_event )
