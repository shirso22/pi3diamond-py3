# PY3-PORT: threading camelCase aliases (currentThread, isSet,
# setDaemon, ...) were deprecated in Python 3.10 and REMOVED in 3.13.
# Rewritten to the snake_case names, which have worked since 2.6.
import logging
import threading
import time

import numpy as np
from chaco.api import ArrayPlotData, Spectral, PlotLabel
from enable.api import ComponentEditor
# PY3-PORT: implicit relative import across packages; 2to3 only rewrites siblings.
from ..pulsed import sequence_remove_zeros, sequence_union
from traits.api import Trait, Instance, String, Range, Float, Int, Bool, Array, Button
from traitsui.api import View, Item, HGroup, VGroup, VSplit, Tabbed, TextEditor

from analysis.odmr_analysis import fit_odmr, n_lorentzians
from tools.chaco_addons import SavePlot as Plot, SaveTool
from tools.emod import ManagedJob
from tools.utility import GetSetItemsMixin


class DEER(ManagedJob, GetSetItemsMixin):
    """ This program sweeps a RF frequency souce to find a DEER coupling"""

    resubmit_button = Button(label='resubmit',
                             desc='Submits the measurement to the job manager. Tries to keep previously acquired data. Behaves like a normal submit if sequence or time bins have changed since previous run.')

    # Measurements parameters:
    mw_frequency = Range(low=1, high=6e9, value=2.870000e9, desc='microwave frequency', label='MW frequency [Hz]',
                         mode='text', auto_set=False, enter_set=True)
    mw_power = Range(low=-100., high=0., value=-28, desc='microwave power', label='MW power [dBm]', mode='text',
                     auto_set=False, enter_set=True)
    mw_t_pi2 = Range(low=1., high=100000., value=50., desc='length of pi/2 pulse of MW[ns]', label='MW pi/2 [ns]',
                     mode='text', auto_set=False, enter_set=True)
    mw_t_pi = Range(low=1., high=100000., value=100., desc='length of pi pulse of MW[ns]', label='MW pi [ns]',
                    mode='text', auto_set=False, enter_set=True)
    mw_tau = Range(low=1., high=100000., value=800., desc='length of tau in the NV echo sequence', label='NV tau [ns]',
                   mode='text', auto_set=False, enter_set=True)

    rf_power = Range(low=-130., high=10., value=-28, desc='RF power', label='RF power [dBm]', mode='text',
                     auto_set=False, enter_set=True)
    rf_begin = Range(low=1, high=3.e9, value=0.80e9, desc='Start Frequency [Hz]', label='RF Begin [Hz]', mode='text',
                     auto_set=False, enter_set=True)
    rf_end = Range(low=1, high=3.0e9, value=0.82e9, desc='Stop Frequency [Hz]', label='RF End [Hz]', mode='text',
                   auto_set=False, enter_set=True)
    rf_delta = Range(low=1e-3, high=200e6, value=2.0e6, desc='frequency step [Hz]', label='Delta [Hz]', mode='text',
                     auto_set=False, enter_set=True)
    rf_t_pi = Range(low=1., high=100000., value=1.e2, desc='length of pi pulse of RF[ns]', label='RF pi [ns]',
                    mode='text', auto_set=False, enter_set=True)
    rf_delay = Range(low=0., high=1.e7, value=100, desc='distance between the NV pi pulse and the RF pi pulse [ns]',
                     label='RF delay [ns]', mode='text', auto_set=False, enter_set=True)
    rf_pulse_delay = Range(low=0., high=1.e7, value=3.2, desc='delay between sequences [ns]',
                           label='RF pulse delay [ns]', mode='text', auto_set=False, enter_set=True)

    laser = Range(low=1., high=10000., value=3000., desc='laser [ns]', label='laser [ns]', mode='text', auto_set=False,
                  enter_set=True)
    wait = Range(low=1., high=10000., value=1000., desc='wait [ns]', label='wait [ns]', mode='text', auto_set=False,
                 enter_set=True)
    seconds_per_point = Range(low=20e-3, high=1, value=20e-3, desc='Seconds per point', label='Seconds per point',
                              mode='text', auto_set=False, enter_set=True)
    stop_time = Range(low=1., value=np.inf, desc='Time after which the experiment stops by itself [s]',
                      label='Stop time [s]', mode='text', auto_set=False, enter_set=True)
    n_lines = Range(low=1, high=10000, value=50, desc='Number of lines in Matrix', label='Matrix lines', mode='text',
                    auto_set=False, enter_set=True)

    # control data fitting
    perform_fit = Bool(False, label='perform fit')
    number_of_resonances = Trait('auto', String('auto', auto_set=False, enter_set=True),
                                 Int(10000., desc='Number of Lorentzians used in fit', label='N', auto_set=False,
                                     enter_set=True))
    threshold = Range(low=-99, high=99., value=-50.,
                      desc='Threshold for detection of resonances [%]. The sign of the threshold specifies whether the resonances are negative or positive.',
                      label='threshold [%]', mode='text', auto_set=False, enter_set=True)

    # fit result
    fit_parameters = Array(value=np.array((np.nan, np.nan, np.nan, np.nan)))
    fit_frequencies = Array(value=np.array((np.nan,)), label='frequency [Hz]')
    fit_line_width = Array(value=np.array((np.nan,)), label='line_width [Hz]')
    fit_contrast = Array(value=np.array((np.nan,)), label='contrast [%]')

    # measurement data    
    frequency = Array()
    counts = Array()
    counts_matrix = Array()
    run_time = Float(value=0.0, desc='Run time [s]', label='Run time [s]')

    # plotting
    line_label = Instance(PlotLabel)
    line_data = Instance(ArrayPlotData)
    matrix_data = Instance(ArrayPlotData)
    line_plot = Instance(Plot, editor=ComponentEditor())
    matrix_plot = Instance(Plot, editor=ComponentEditor())

    def __init__(self, rf_source, microwave, counter, pulse_generator=None, **kwargs):

        super(DEER, self).__init__(**kwargs)
        self.rf_source = rf_source
        self.microwave = microwave
        self.counter = counter
        self.pulse_generator = pulse_generator

        # For ploting:
        self._create_line_plot()
        self._create_matrix_plot()
        self.on_trait_change(self._update_line_data_index, 'frequency', dispatch='ui')
        self.on_trait_change(self._update_line_data_value, 'counts', dispatch='ui')
        self.on_trait_change(self._update_line_data_fit, 'fit_parameters', dispatch='ui')
        self.on_trait_change(self._update_matrix_data_value, 'counts_matrix', dispatch='ui')
        self.on_trait_change(self._update_matrix_data_index, 'n_lines,frequency', dispatch='ui')
        self.on_trait_change(self._update_fit, 'counts,perform_fit,number_of_resonances,threshold', dispatch='ui')

    # Auxiliar functions:
    def _counts_matrix_default(self):
        return np.zeros((self.n_lines, len(self.frequency)))

    def _frequency_default(self):
        return np.arange(self.rf_begin, self.rf_end + self.rf_delta, self.rf_delta)

    def _counts_default(self):
        return np.zeros(self.frequency.shape)

    def generate_sequence(self):

        # Now using the defined sequence:
        # Begining defining the part of the sequence related to the NV MW spin echo:
        mw_tau = self.mw_tau
        laser = self.laser
        wait = self.wait
        mw_t_pi2 = self.mw_t_pi2
        mw_t_pi = self.mw_t_pi

        # Defining the RF sequence:
        rf_t_pi = self.rf_t_pi
        rf_delay = float(self.rf_delay)
        rf_pulse_delay = float(self.rf_pulse_delay)
        pulse_difference = rf_t_pi - mw_t_pi

        sequence_rf = []
        sequence_NV = []

        if rf_delay != 0.0:
            sequence_rf += [([], wait + mw_t_pi2 + mw_tau + mw_t_pi + rf_delay + rf_pulse_delay), (['rf'], rf_t_pi),
                            ([], mw_tau - rf_delay - rf_pulse_delay - rf_t_pi + mw_t_pi2 + laser)]
            sequence_NV += [([], wait), (['mw'], mw_t_pi2), ([], mw_tau), (['mw'], mw_t_pi), ([], mw_tau),
                            (['mw'], mw_t_pi2), (['detect', 'aom'], laser)]
        else:
            sequence_rf += [([], wait + rf_pulse_delay + mw_t_pi2 + mw_tau), (['rf'], rf_t_pi),
                            ([], mw_tau - rf_t_pi + mw_t_pi - rf_pulse_delay + mw_t_pi2 + laser)]
            sequence_NV += [([], wait), (['mw'], mw_t_pi2), ([], mw_tau), (['mw'], mw_t_pi), ([], mw_tau),
                            (['mw'], mw_t_pi2), (['detect', 'aom'], laser)]

        sequence_NV += [(['sequence'], 100)]
        sequence_rf += [(['sequence'], 100)]

        # Removing zeros from sequences:
        sequence_NV = sequence_remove_zeros(sequence_NV)
        sequence_rf = sequence_remove_zeros(sequence_rf)

        # Mixing both MW and RF sequences:
        sequence = sequence_union(sequence_rf, sequence_NV)

        return sequence

    # Starting data aquisition:

    def apply_parameters(self):
        """ The program will read the given parameters and decide whether to keep previous data"""

        # Creating the frequency array:
        frequency = np.arange(self.rf_begin, self.rf_end + self.rf_delta, self.rf_delta)
        sequence = self.generate_sequence()

        if not self.keep_data or np.any(frequency != self.frequency):
            self.frequency = frequency
            self.counts = np.zeros(frequency.shape)
            self.run_time = 0.0

        self.sequence = sequence

        # When the job manager starts or stops the measurement the data must be kept (only new submission clears the data).
        self.keep_data = True

    def _run(self):

        try:
            self.state = 'run'
            self.apply_parameters()

            if self.rf_t_pi > self.mw_tau:
                logging.getLogger().exception('Error in DEER: PI from RF is longer than the NV tau.')
                self.state = 'error'
                return

            if self.run_time >= self.stop_time:
                self.state = 'done'
                return

            if self.pulse_generator:
                self.pulse_generator.Sequence(self.sequence)

            n = len(self.frequency)

            self.microwave.setOutput(self.mw_power, self.mw_frequency)
            self.rf_source.setPower(self.rf_power)
            self.rf_source.initSweep(self.frequency, self.rf_power * np.ones(self.frequency.shape))
            self.counter.configure(n, self.seconds_per_point, DutyCycle=0.8)
            time.sleep(0.5)

            while self.run_time < self.stop_time:
                start_time = time.time()

                if threading.current_thread().stop_request.is_set():
                    break

                self.rf_source.resetListPos()
                counts = self.counter.run()
                self.run_time += time.time() - start_time
                self.counts += counts

                self.counts_matrix = np.vstack((counts, self.counts_matrix[:-1, :]))
                self.trait_property_changed('counts', self.counts)

            self.rf_source.setOutput(None, self.rf_begin)

            if self.pulse_generator:
                self.pulse_generator.Light()
            self.counter.clear()

        except:
            logging.getLogger().exception('Error in DEER frequency scan.')
            self.rf_source.setOutput(None, self.rf_begin)
        else:
            if self.run_time < self.stop_time:
                self.state = 'idle'
            # else:
            # self.state = 'done'

    # Fitting the data:

    def _update_fit(self):

        if self.perform_fit:

            N = self.number_of_resonances

            if N != 'auto':
                N = int(N)
            try:
                p, dp = fit_odmr(self.frequency, self.counts, threshold=self.threshold * 0.01, number_of_lorentzians=N)
            except Exception:
                logging.getLogger().debug('DEED fit failed.', exc_info=True)
                p = np.nan * np.empty(4)

        else:
            p = np.nan * np.empty(4)

        self.fit_parameters = p
        self.fit_frequencies = p[1::3]
        self.fit_line_width = p[2::3]

        N = len(p) // 3

        contrast = np.empty(N)
        c = p[0]
        pp = p[1:].reshape((N, 3))

        for i, pi in enumerate(pp):
            a = pi[2]
            g = pi[1]
            A = np.abs(a / (np.pi * g))

            if a > 0:
                contrast[i] = 100 * A / (A + c)
            else:
                contrast[i] = 100 * A / c
        self.fit_contrast = contrast

    # Plotting the data:

    def _create_line_plot(self):
        line_data = ArrayPlotData(frequency=np.array((0., 1.)), counts=np.array((0., 0.)), fit=np.array((0., 0.)))
        line_plot = Plot(line_data, padding=8, padding_left=64, padding_bottom=32)
        line_plot.plot(('frequency', 'counts'), style='line', color='blue')
        line_plot.index_axis.title = 'Frequency [MHz]'
        line_plot.value_axis.title = 'Fluorescence counts'
        line_label = PlotLabel(text='', hjustify='left', vjustify='bottom', position=[64, 128])
        line_plot.overlays.append(line_label)
        line_plot.tools.append(SaveTool(line_plot))
        self.line_label = line_label
        self.line_data = line_data
        self.line_plot = line_plot

    def _create_matrix_plot(self):
        matrix_data = ArrayPlotData(image=np.zeros((2, 2)))
        matrix_plot = Plot(matrix_data, padding=8, padding_left=64, padding_bottom=32)
        matrix_plot.index_axis.title = 'Frequency [MHz]'
        matrix_plot.value_axis.title = 'line #'
        matrix_plot.img_plot('image',
                             xbounds=(self.frequency[0], self.frequency[-1]),
                             ybounds=(0, self.n_lines),
                             colormap=Spectral)
        matrix_plot.tools.append(SaveTool(matrix_plot))
        self.matrix_data = matrix_data
        self.matrix_plot = matrix_plot

    def _perform_fit_changed(self, new):
        plot = self.line_plot
        if new:
            plot.plot(('frequency', 'fit'), style='line', color='red', name='fit')
            self.line_label.visible = True
        else:
            plot.delplot('fit')
            self.line_label.visible = False
        plot.request_redraw()

    def _update_line_data_index(self):
        self.line_data.set_data('frequency', self.frequency * 1e-6)
        self.counts_matrix = self._counts_matrix_default()

    def _update_line_data_value(self):
        self.line_data.set_data('counts', self.counts)

    def _update_line_data_fit(self):
        if not np.isnan(self.fit_parameters[0]):
            self.line_data.set_data('fit', n_lorentzians(*self.fit_parameters)(self.frequency))
            p = self.fit_parameters
            f = p[1::3]
            w = p[2::3]
            N = len(p) // 3
            contrast = np.empty(N)
            c = p[0]
            pp = p[1:].reshape((N, 3))
            for i, pi in enumerate(pp):
                a = pi[2]
                g = pi[1]
                A = np.abs(a / (np.pi * g))
                if a > 0:
                    contrast[i] = 100 * A / (A + c)
                else:
                    contrast[i] = 100 * A / c
            s = ''
            for i, fi in enumerate(f):
                s += 'f %i: %.6e Hz, HWHM %.3e Hz, contrast %.1f%%\n' % (i + 1, fi, w[i], contrast[i])
            self.line_label.text = s

    def _update_matrix_data_value(self):
        self.matrix_data.set_data('image', self.counts_matrix)

    def _update_matrix_data_index(self):
        if self.n_lines > self.counts_matrix.shape[0]:
            self.counts_matrix = np.vstack((self.counts_matrix, np.zeros(
                (self.n_lines - self.counts_matrix.shape[0], self.counts_matrix.shape[1]))))
        else:
            self.counts_matrix = self.counts_matrix[:self.n_lines]
        self.matrix_plot.components[0].index.set_data((self.frequency.min() * 1e-6, self.frequency.max() * 1e-6),
                                                      (0.0, float(self.n_lines)))

    # react to GUI events

    def submit(self):
        """Submit the job to the JobManager."""
        self.keep_data = False
        ManagedJob.submit(self)

    def resubmit(self):
        """Submit the job to the JobManager."""
        self.keep_data = True
        ManagedJob.submit(self)

    def _resubmit_button_fired(self):
        """React to start button. Submit the Job."""
        self.resubmit()

    get_set_items = ['frequency', 'counts', 'mw_frequency', 'mw_power', 'mw_t_pi2', 'mw_t_pi',
                     'rf_power', 'rf_begin', 'rf_end', 'rf_delta', 'rf_t_pi', 'rf_delay',
                     'laser', 'wait', 'seconds_per_point']

    traits_view = View(VGroup(HGroup(Item('submit_button', show_label=False),
                                     Item('remove_button', show_label=False),
                                     Item('resubmit_button', show_label=False),
                                     Item('priority', enabled_when='state != "run"'),
                                     Item('state', style='readonly'),
                                     Item('run_time', style='readonly', format_str='%.f'),
                                     Item('stop_time'),
                                     ),
                              HGroup(Item('filename', springy=True),
                                     Item('save_button', show_label=False),
                                     Item('load_button', show_label=False)
                                     ),
                              Tabbed(VGroup(HGroup(Item('mw_power', width=-40),
                                                   Item('mw_frequency', width=-80,
                                                        editor=TextEditor(auto_set=False, enter_set=True,
                                                                          evaluate=float,
                                                                          format_func=lambda x: '%e' % x)),
                                                   Item('mw_t_pi2', width=-80),
                                                   Item('mw_t_pi', width=-80),
                                                   Item('mw_tau', width=-80),
                                                   ),
                                            HGroup(Item('rf_power', width=-40),
                                                   Item('rf_begin', width=-80,
                                                        editor=TextEditor(auto_set=False, enter_set=True,
                                                                          evaluate=float,
                                                                          format_func=lambda x: '%e' % x)),
                                                   Item('rf_end', width=-80,
                                                        editor=TextEditor(auto_set=False, enter_set=True,
                                                                          evaluate=float,
                                                                          format_func=lambda x: '%e' % x)),
                                                   Item('rf_delta', width=-80,
                                                        editor=TextEditor(auto_set=False, enter_set=True,
                                                                          evaluate=float,
                                                                          format_func=lambda x: '%e' % x)),
                                                   Item('rf_t_pi', width=-80),
                                                   Item('rf_delay', width=-80),
                                                   ),
                                            HGroup(Item('perform_fit'),
                                                   Item('number_of_resonances', width=-60),
                                                   Item('threshold', width=-60),
                                                   Item('n_lines', width=-60),
                                                   ),
                                            VSplit(Item('matrix_plot', show_label=False, resizable=True),
                                                   Item('line_plot', show_label=False, resizable=True),
                                                   ),
                                            label='parameter'),
                                     VGroup(HGroup(Item('laser', width=-80),
                                                   Item('wait', width=-80),
                                                   Item('rf_pulse_delay', width=-80),
                                                   ),
                                            HGroup(
                                                Item('seconds_per_point', width=-120, enabled_when='state == "idle"'),
                                            ),
                                            label='settings'
                                            ),
                                     ),
                              ),
                       title='DEER - frequency scan', resizable=True
                       )
