"""

Example of usage:

1. create an instance of a rabi measurement and set the desired parameters
2. create an instance of an ODMR measurement and set the desired parameters
3. in the '__main__' section below, change the names of 'odmr' and 'rabi' to reflect the names of your instances
4. execute this script from the ipython shell by typing

    run -i script/power_log

"""

import logging

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
    A mini job that sets the frequency of 'rabi' with the
    fit result from 'odmr'.
    """

    def __init__(self, odmr, rabi):
        super(SetJob, self).__init__()
        self.odmr = odmr
        self.rabi = rabi

    def _run(self):
        try:
            self.state = 'run'
            f_new = odmr.fit_frequencies[0]
            f_begin = odmr.frequency_begin
            f_end = odmr.frequency_end
            f_old = rabi.measurement.frequency
            period = rabi.fit_result[0][1]
            # run_str = str(int(self.cpmg.measurement.run_time))
            ts = timestamp()
            path = 'log/power_log.txt'
            if f_begin < f_new < f_end:
                self.rabi.measurement.frequency = f_new
                datastring = ts + ', ' + str(f_old) + ', ' + str(period) + '\n'
                string_to_file(datastring, path)
            else:
                string_to_file('#Warning! Invalid frequency received from odmr, not passing to rabi!\n', path)
            logging.getLogger().info('ESR: %e' % f_new)
            # self.rabi.save_figure('log/odmr_freqs/'+ts+'_rabi.png')
            # d = rabi.get_items()
            # d['frequency_history']=frequencies
            # self.rabi.save('defaults/rabi_current.pys')

        finally:
            self.state = 'idle'

    def __repr__(self):
        return 'Set frequency of ' + str(self.rabi) + ' with result from ' + str(self.odmr)


class AdjustFrequency(object):
    """
    Adjusts the frequency of rabi measurement 'rabi' with the
    result from an odmr measurement 'odmr'.
    
    Example of Usage:
    
       adjust_frequency = AdjustFrequency(odmr, rabi)
       adjust_frequency()
       
    Explanation:
    
    Upon instantiation, we need to pass the odmr and rabi measurements
    on which AdjustFrequency should act. When Called, adjust_frequency
    sets the priority of the odmr job to 5 and calls its .submit() method.
    In addition, it creates a mini job also with priority 5 that does nothing
    but setting the frequency of the rabi job with the result from the
    odmr job. This mini job gets executed as soon as odmr is done. After the mini job
    is finished, the rabi job is first in the queue and continues as usual.
    """

    def __init__(self, odmr, rabi):
        self.odmr = odmr
        self.rabi = rabi

    def __call__(self):
        self.rabi.measurement.stop()
        # self.odmr.priority = 5
        # self.odmr.number_of_resonances = 1
        # self.odmr.submit()
        # set_job = SetJob(self.odmr, self.rabi)
        # set_job.priority = 5
        # set_job.submit()
        f_old = rabi.measurement.frequency
        period = rabi.fit_result[0][1]
        ts = timestamp()
        path = 'log/power_log.txt'
        datastring = ts + ', ' + str(f_old) + ', ' + str(period) + '\n'
        string_to_file(datastring, path)
        self.rabi.measurement.submit()


if __name__ == '__main__':
    from tools.cron import CronDaemon, CronEvent

    adjust_frequency_event = CronEvent(AdjustFrequency(odmr, rabi), min=list(range(0, 60, 6)))
    CronDaemon().register(adjust_frequency_event)
    # CronDaemon().remove( adjust_frequency_event )
