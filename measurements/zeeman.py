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

import logging
import threading
import time

import numpy as np
from chaco.api import ArrayPlotData
from enable.api import ComponentEditor
from traits.api import Array, File, Instance, Button, Bool
from traitsui.api import View, Item, HGroup, VGroup, InstanceEditor

from measurements.odmr import ODMR
from tools.chaco_addons import SavePlot as Plot, SaveTool
from tools.emod import Job


# ToDo: maybe introduce lock for 'state' variable on each job?


class Zeeman(Job):  # , GetSetItemsMixin ):

    """Zeeman measurement."""

    start_button = Button(label='start', desc='Start the measurement.')
    stop_button = Button(label='stop', desc='Stop the measurement.')

    def _start_button_fired(self):
        """React to submit button. Submit the Job."""
        self.start()

    def _stop_button_fired(self):
        """React to remove button. Remove the Job."""
        self.stop()

    current = Array(dtype=float)
    basename = File()

    odmr = Instance(ODMR, factory=ODMR)

    frequency = Array()

    track = Bool(False)

    line_data = Instance(ArrayPlotData)
    line_plot = Instance(Plot, editor=ComponentEditor())

    traits_view = View(VGroup(HGroup(Item('start_button', show_label=False),
                                     Item('stop_button', show_label=False),
                                     Item('state', style='readonly'),
                                     Item('odmr', editor=InstanceEditor(), show_label=False),
                                     Item('track'),
                                     ),
                              VGroup(Item('basename'),
                                     ),
                              Item('line_plot', show_label=False, resizable=True),
                              ),
                       title='Zeeman', buttons=[], resizable=True
                       )

    get_set_items = ['current', 'frequency', 'odmr', '__doc__']

    def __init__(self, coil, **kwargs):
        self.coil = coil
        super(Zeeman, self).__init__(**kwargs)
        self._create_line_plot()
        self.on_trait_change(self._update_plot, 'frequency', dispatch='ui')

    def _run(self):

        try:
            self.state = 'run'

            if self.basename == '':
                raise ValueError('Filename missing. Please specify a filename and try again.')

            odmr = self.odmr
            odmr.perform_fit = self.fit
            if odmr.stop_time == np.inf:
                raise ValueError('ODMR stop time set to infinity.')

            delta_f = (odmr.frequency_end - odmr.frequency_begin)

            self.frequency = np.array(())

            for i, current_i in enumerate(self.current):

                basename = self.basename + '_' + str(current_i * 1000)

                self.coil.set_current(1, current_i[0])
                self.coil.set_current(2, current_i[1])
                self.coil.set_current(3, current_i[2])
                odmr.filename = basename + '.pys'
                odmr.submit()
                while odmr.state != 'done':
                    threading.current_thread().stop_request.wait(1.0)
                    if threading.current_thread().stop_request.is_set():
                        odmr.remove()
                        break
                if threading.current_thread().stop_request.is_set():
                    break
                if odmr.perform_fit:  # wait to be sure the fit is done before saving the figure
                    time.sleep(1.0)
                odmr.line_plot.save(basename + '.png')

                if odmr.perform_fit:
                    f = odmr.fit_frequencies[0]
                    self.frequency = np.append(self.frequency, f)
                else:
                    self.frequency = np.append(self.frequency, 0.0)

                if self.track:
                    try:
                        odmr.frequency_begin = f - 0.5 * delta_f
                        odmr.frequency_end = odmr.frequency_begin + delta_f
                    except:
                        logging.getLogger().warning('Failed to track frequency.')

            self.state = 'done'
        except:
            logging.getLogger().exception('Error in Zeeman.')
            self.state = 'error'

    def _create_line_plot(self):
        line_data = ArrayPlotData(current=np.array(()), frequency=np.array(()), )
        plot = Plot(line_data, padding=8, padding_left=64, padding_bottom=36)
        plot.plot(('current', 'frequency'), color='blue', name='zeeman')
        plot.index_axis.title = 'current [mA]'
        plot.value_axis.title = 'frequency [MHz]'
        plot.tools.append(SaveTool(plot))
        self.line_data = line_data
        self.line_plot = plot

    def _update_plot(self, new):
        n = len(new)
        self.line_data.set_data('current', np.array([np.linalg.norm(v) for v in self.current[:n]]))
        self.line_data.set_data('frequency', new * 1e-6)

    def save_line_plot(self, filename):
        self.save_figure(self.line_plot, filename)


if __name__ == '__main__':
    #    logging.getLogger().addHandler(logging.StreamHandler())
    #    logging.getLogger().setLevel(logging.DEBUG)
    #    logging.getLogger().info('Starting logger.')
    #
    #    from hardware.dummy import Counter, Microwave, Coil
    #    microwave = Microwave()
    #    counter = Counter()
    #    coil = Coil()
    #
    #    from tools.emod import JobManager
    #    JobManager().start()
    #
    #    from measurements.odmr import ODMR
    #
    #    odmr = ODMR(microwave, counter)

    current = np.arange(0.0, 3.0, 0.5)
    zeros = np.zeros_like(current)

    zeeman = Zeeman(mag_coil, odmr=odmr, current=np.vstack((current, zeros, zeros)).transpose())
    zeeman.edit_traits()
    zeeman.basename = 'C:\\data\\LabBook\\2013-02-27\\Zeeman\\2013-02-27_Zeeman'

# zeeman.start()
