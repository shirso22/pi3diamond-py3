# PY3-PORT: threading camelCase aliases (currentThread, isSet,
# setDaemon, ...) were deprecated in Python 3.10 and REMOVED in 3.13.
# Rewritten to the snake_case names, which have worked since 2.6.
import logging
import threading
import time

import numpy as np
from chaco.api import ArrayPlotData, PlotLabel
from chaco.tools.api import PanTool, ZoomTool
from enable.api import ComponentEditor
from traits.api import Trait, Instance, String, Range, Float, Int, Bool, Array, Button, Enum, List, on_trait_change, Property
from traitsui.api import View, Item, HGroup, VGroup, TextEditor, Group

from analysis.odmr_analysis import fit_odmr, n_lorentzians, n_gaussians, n_n15
from tools.chaco_addons import SavePlot as Plot, SaveTool, ClickTool
from tools.colormaps import viridis, navia
from tools.emod import ManagedJob
from tools.utility import GetSetItemsMixin


class ODMR(ManagedJob, GetSetItemsMixin):
    """Provides ODMR measurements."""

    # starting and stopping
    keep_data = Bool(False)  # helper variable to decide whether to keep existing data
    resubmit_button = Button(label='resubmit',
                             desc='Submits the measurement to the job manager. Tries to keep '
                                  'previously acquired data. Behaves like a normal submit if '
                                  'sequence or time bins have changed since previous run.')
    perform_fit_button = Button(label="Fit")

    # measurement parameters
    power = Range(low=-100., high=25., value=-20, desc='Power [dBm]', label='Power [dBm]',
                  mode='text', auto_set=False, enter_set=True)
    frequency_begin = Float(default_value=2.8e9, desc='Start Frequency [Hz]', label='Begin [Hz]',
                            editor=TextEditor(auto_set=False, enter_set=True, evaluate=float,
                                              format_str='%e'))
    frequency_end = Float(default_value=2.95e9, desc='Stop Frequency [Hz]', label='End [Hz]',
                          editor=TextEditor(auto_set=False, enter_set=True, evaluate=float,
                                            format_str='%e'))
    frequency_delta = Float(default_value=5e6, desc='frequency step [Hz]', label='Delta [Hz]',
                            editor=TextEditor(auto_set=False, enter_set=True, evaluate=float,
                                              format_str='%e'))
    t_pi = Range(low=1., high=100000., value=150., desc='length of pi pulse [ns]', label='pi [ns]',
                 mode='text', auto_set=False, enter_set=True)
    laser = Range(low=1., high=10000., value=300., desc='laser [ns]', label='laser [ns]',
                  mode='text', auto_set=False, enter_set=True)
    wait = Range(low=1., high=10000., value=1000., desc='wait [ns]', label='wait [ns]', mode='text',
                 auto_set=False, enter_set=True)
    pulsed = Bool(True, label='pulsed')
    seconds_per_point = Range(low=20e-3, high=1, value=20e-3, desc='Seconds per point',
                              label='Seconds per point', mode='text', auto_set=False,
                              enter_set=True)
    stop_time = Range(low=1., value=np.inf,
                      desc='Time after which the experiment stops by itself [s]',
                      label='Stop time [s]', mode='text', auto_set=False, enter_set=True)
    n_lines = Range(low=1, high=10000, value=50, desc='Number of lines in Matrix',
                    label='Matrix lines', mode='text', auto_set=False, enter_set=True)

    # control data fitting
    perform_fit = Bool(False, label='perform fit') #fix attempt
    calculate_center = Bool(False, label='calculate center')
    number_of_resonances = Trait('auto', String('auto', auto_set=False, enter_set=True),
                                 Int(10000., desc='Number of Lorentzians used in fit', label='N',
                                     auto_set=False, enter_set=True))
    threshold = Float(low=-99, high=99., value=-5.,
                      desc='Threshold for detection of resonances [%]. '
                           'The sign of the threshold specifies whether the resonances are negative'
                           ' or positive.',
                      label='threshold [%]', mode='text', auto_set=False, enter_set=True)
    peakshape_list = List(['lorentzian', 'gaussian', 'n15'])
    peakshape = Enum(values='peakshape_list')

    # fit result
    fit_parameters = Array(value=np.array((np.nan, np.nan, np.nan, np.nan)))
    fit_frequencies = Array(value=np.array((np.nan,)), label='Frequency [Hz]')
    fit_frequencies_display = Property(String, depends_on='fit_frequencies')

    def _get_fit_frequencies_display(self):
        if self.fit_frequencies is None or len(self.fit_frequencies) == 0:
            return ''
        return ', '.join(['%.3f' % (f * 1e-9) for f in self.fit_frequencies])

    fit_line_width = Array(value=np.array((np.nan,)), label='Line width [MHz]')
    fit_line_width_display = Property(String, depends_on='fit_line_width')

    def _get_fit_line_width_display(self):
        if self.fit_line_width is None or len(self.fit_line_width) == 0:
            return ''
        # convert to MHz and format
        return ', '.join(['%.3f' % (w) for w in self.fit_line_width])

    fit_contrast = Array(value=np.array((np.nan,)), label='Contrast [%]')
    # new property for display
    fit_contrast_display = Property(String, depends_on='fit_contrast')

    def _get_fit_contrast_display(self):
        if self.fit_contrast is None or len(self.fit_contrast) == 0:
            return ''
        # Format each value to 2 decimals, join with commas
        return ', '.join(['%.3f' % fc for fc in self.fit_contrast])
    center = Float(value=np.nan)

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
    click_tool = Instance(ClickTool)
    click_coords = Array(value=np.array((np.nan,)), label='[x, y]')

    def __init__(self, microwave, counter, pulse_generator=None, **kwargs):
        super(ODMR, self).__init__(**kwargs)
        self.microwave = microwave
        self.counter = counter
        self.pulse_generator = pulse_generator
        self._create_line_plot()
        self._create_matrix_plot()
        self.on_trait_change(self._update_line_data_index, 'frequency', dispatch='ui')
        self.on_trait_change(self._update_line_data_value, 'counts', dispatch='ui')
        self.on_trait_change(self._update_line_data_fit, 'fit_parameters', dispatch='ui')
        self.on_trait_change(self._update_matrix_data_value, 'counts_matrix', dispatch='ui')
        self.on_trait_change(self._update_matrix_data_index, 'n_lines,frequency', dispatch='ui')
        self.on_trait_change(self._update_fit, 'counts,perform_fit,number_of_resonances,threshold',
                             dispatch='ui')
        #fix attempt starts here
        self.on_trait_change(self._update_fit, 'perform_fit', dispatch='ui')
        #fix attempt ends here
    def _counts_matrix_default(self):
        return np.zeros((self.n_lines, len(self.frequency)))

    def _frequency_default(self):
        return np.arange(self.frequency_begin, self.frequency_end + self.frequency_delta,
                         self.frequency_delta)

    def _counts_default(self):
        return np.zeros(self.frequency.shape)

    # data acquisition

    def apply_parameters(self):
        """Apply the current parameters and decide whether to keep previous data."""
        frequency = np.arange(self.frequency_begin, self.frequency_end, self.frequency_delta)

        if not self.keep_data or np.any(frequency != self.frequency):
            self.frequency = frequency
            self.counts = np.zeros(frequency.shape)
            self.run_time = 0.0
            self.line_data.set_data('fit', np.zeros_like(self.frequency))
        self.keep_data = True  # when job manager stops and starts the job, data should be kept. Only new submission should clear data.

    def _run(self):
        try:
            self.state = 'run'
            self.apply_parameters()

            if self.run_time >= self.stop_time:
                self.state = 'done'
                return

            # if pulsed, turn on sequence
            if self.pulse_generator:
                if self.pulsed:
                    self.pulse_generator.setSequence(
                        100 * [(['detect', 'aom'], self.laser), ([], self.wait),
                               (['mw'], self.t_pi)])
                else:
                    self.pulse_generator.Open()
            else:
                if self.pulsed:
                    raise ValueError("pulse_generator not defined while running measurement"
                                     "in pulsed mode.")

            n = len(self.frequency)

            self.microwave.setPower(self.power)
            time.sleep(0.5)

            while self.run_time < self.stop_time:
                if threading.current_thread().stop_request.is_set():
                    break
                self.counter.configure(n + 2, self.seconds_per_point)
                self.counter.start()
                start_time = time.time()
                self.microwave.Sweep(self.frequency_begin,
                                     self.frequency_end + self.frequency_delta,
                                     self.frequency_delta, int(self.seconds_per_point * 1e3))
                counts, self.ai = self.counter.read()
                # here, implement something to free the resources of the channel, so that another measurement can use it! (i.e. Autofocus, Scanner)
                self.counter.stop()
                time_diff = time.time() - start_time
                self.run_time += time_diff
                counts = counts[2:]
                self.counts += counts
                self.counts_matrix = np.vstack((counts, self.counts_matrix[:-1, :]))
                self.trait_property_changed('counts', self.counts)

            self.microwave.setOutput(None, self.frequency_begin)
            if self.pulse_generator:
                self.pulse_generator.Light()
            self.counter.clear()
        except:
            logging.getLogger().exception('Error in odmr.')
            # HW-FIX: release the DAQ counter before anything else. Without
            # this, a failure here left the CI/CO tasks started, and every
            # later scan died on -50103 (resource reserved), -200479 (task
            # already running) or -200557 (cannot set property while running).
            # One crash poisoned the whole session and produced a cascade of
            # errors that looked unrelated to the original fault.
            for _cleanup in ('stop', 'clear'):
                try:
                    getattr(self.counter, _cleanup)()
                except Exception:
                    logging.getLogger().debug('odmr cleanup: counter.%s() failed',
                                              _cleanup, exc_info=True)
            try:
                self.microwave.setOutput(None, self.frequency_begin)
            except Exception:
                logging.getLogger().exception('odmr cleanup: microwave reset failed')
            self.state = 'error'
        else:
            if self.run_time < self.stop_time:
                self.state = 'idle'
            else:
                #                try:
                #                    self.save(self.filename)
                #                except:
                #                    logging.getLogger().exception('Failed to save the data to file.')
                self.state = 'done'

    # fitting
    def fit(self):

        N = self.number_of_resonances

        if N < 0 or N > 4:
            return

        p, dp = fit_odmr(self.frequency, self.counts, threshold=self.threshold * 0.01,
                         number_of_peaks=N, peakshape=self.peakshape)

        self.fit_parameters = p
        self.fit_frequencies = p[1::3]
        self.fit_line_width = p[2::3]

        plot = self.line_plot

        if not np.isnan(self.fit_parameters[0]):
            if self.peakshape == 'lorentzian':
                self.line_data.set_data('fit', n_lorentzians(*self.fit_parameters)(self.frequency))
            if self.peakshape == 'gaussian':
                self.line_data.set_data('fit', n_gaussians(*self.fit_parameters)(self.frequency))
            if self.peakshape == 'n15': #fix from 15N
                self.line_data.set_data('fit', n_n15(*self.fit_parameters)(self.frequency))
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
                s += 'f %i: %.6e Hz, HWHM %.3e Hz, contrast %.1f%%\n' % (i + 1, fi, w[i],
                                                                         contrast[i])
            if self.calculate_center:
                s += 'Center Frequency: %.6e Hz' % self.center
            self.line_label.text = s

        plot.plot(('frequency', 'fit'), style='line', color='red', name='fit')
        self.line_label.visible = True

    def _update_fit(self):
        #print("Performing fit")

        # --- DEBUG: check n15 output length ---

        from analysis.odmr_analysis import n_n15
        p_test = np.array([self.counts.max(), 1e6, -5000, 1e6, -5000, 1e6])  # example params
        y_test = n_n15(*p_test)(self.frequency)
        #print("n_n15 output length:", len(y_test))
        # --------------------------------------


        #N = self.number_of_resonances
        #if N != 'auto':
            #N = int(N)
        N = self.number_of_resonances
        if N == 'auto':
            N = 1  # fallback or a better heuristic could be used
        else:
            try:
                N = int(N)
            except ValueError:
                print("Warning: number_of_resonances could not be converted, using 1")
                N = 1
        #print("Number of resonances (int for fit):", N)

        #fix attempt starts here
        threshold = self.threshold
        if threshold == 0.0:
            threshold = 0.01
        #fix attempt ends here
        try:
            p, dp = fit_odmr(self.frequency, self.counts, threshold=threshold * 0.01, #fix from threshold=self.threshold * 0.01
                             number_of_peaks=N, peakshape=self.peakshape)
            #print("Fit returned p:", p)
            # --- BEGIN PATCH: fix length mismatch ---
            expected_len = 1 + 3 * int(N)  # 1 baseline + 3 params per peak
            if len(p) != expected_len:
                print("Fixing fit length mismatch! Original length:", len(p))
                new_p = np.ones(expected_len) * np.nan
                for i in range(min(len(p), expected_len)):
                    new_p[i] = p[i]
                p = new_p
            # --- END PATCH ---

            #fixing attempt begins here
            if not np.all(np.isfinite(p)):
                raise ValueError("Fit returned invalid parameters")
            #fixing attempt ends here
        except Exception as e:
            print ("ODMR fit failed", e)
            logging.getLogger().debug('ODMR fit failed.', exc_info=True)
            p = np.nan * np.empty(1 + N*3)
            self.line_data.set_data('fit', np.zeros_like(self.frequency))
            self.line_plot.request_redraw()
        #else: #fix attempt
            #p = np.nan * np.empty(4) #fix attempt
        self.fit_parameters = p
        self.fit_frequencies = p[1::3]
        self.fit_line_width = p[2::3] * 1e-6
        N = len(p) // 3
        contrast = np.empty(N)
        c = p[0]
        pp = p[1:].reshape((N, 3))
        for i, pi in enumerate(pp):
            a = pi[2]
            g = pi[1]
            #fixing attempt starts here
            if not np.isfinite(g) or g == 0 or not np.isfinite(a):
                contrast[i] = np.nan
                continue
            #fixing attempt ends here
            A = np.abs(a / (np.pi * g))
            if a > 0:
                contrast[i] = 100 * A / (A + c)
            else:
                contrast[i] = 100 * A / c
        self.fit_contrast = contrast
        if len(self.fit_frequencies) == 2 and self.calculate_center:
            self.center = abs(self.fit_frequencies[0] + self.fit_frequencies[1]) / 2.
        else:
            self.center = np.nan

    # plotting
    def _create_line_plot(self):
        line_data = ArrayPlotData(frequency=np.array((0., 1.)), counts=np.array((0., 0.)),
                                  fit=np.array((0., 0.)))
        line_plot = Plot(line_data, padding=8, padding_left=64, padding_bottom=32)
        line_plot.plot(('frequency', 'counts'), style='line', color='blue')
        line_plot.plot(('frequency', 'counts'), type='scatter', marker="circle", marker_size=3, color='blue')
        line_plot.index_axis.title = 'Frequency [MHz]'
        line_plot.value_axis.title = 'Fluorescence counts'
        line_label = PlotLabel(text='', hjustify='left', vjustify='bottom', position=[64, 128])
        line_plot.overlays.append(line_label)
        line_plot.tools.append(SaveTool(line_plot))
        line_plot.tools.append(PanTool(line_plot))
        line_plot.tools.append(ZoomTool(line_plot))
        self.click_tool = ClickTool(line_plot)
        line_plot.tools.append(self.click_tool)

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
                             colormap=navia)
        matrix_plot.tools.append(SaveTool(matrix_plot))
        self.matrix_data = matrix_data
        self.matrix_plot = matrix_plot

    #def _perform_fit_changed(self, new):
        #plot = self.line_plot
        #if new:
           # plot.plot(('frequency', 'fit'), style='line', color='red', name='fit')
            #self.line_label.visible = True
        #else:
           # plot.delplot('fit')
            #self.line_label.visible = False
        #plot.request_redraw()

    def _update_line_data_index(self):
        self.line_data.set_data('frequency', self.frequency * 1e-6)
        self.counts_matrix = self._counts_matrix_default()

    def _update_line_data_value(self):
        self.line_data.set_data('counts', self.counts)
        if len(self.counts) > 0:
            ymin = np.min(self.counts)
            ymax = np.max(self.counts)

            margin = 0.05 * (ymax - ymin)

            self.line_plot.value_range.low = ymin - margin
            self.line_plot.value_range.high = ymax + margin

    def _update_line_data_fit(self):
        ("fit_parameters =", self.fit_parameters) #fix attempt
        if not np.isnan(self.fit_parameters[0]):
            #fix attempt starts here
            if not np.all(np.isfinite(self.fit_parameters)):
                return
            #fix attempt ends here
            fit_curve = None
            if self.peakshape == 'lorentzian':
                fit_curve = n_lorentzians(*self.fit_parameters)(self.frequency)
            if self.peakshape == 'gaussian':
                fit_curve = n_gaussians(*self.fit_parameters)(self.frequency)
            if self.peakshape == 'n15':
                fit_curve = n_n15(*self.fit_parameters)(self.frequency)


            #print("fit_curve.shape:", fit_curve.shape, "frequency.shape:", self.frequency.shape)

            # Only set the data if the shapes match
            if fit_curve is not None and len(fit_curve) == len(self.frequency):
                self.line_data.set_data('fit', fit_curve)
                if 'fit' not in [p.name for p in self.line_plot.plots.values()]:
                    self.line_plot.plot(('frequency', 'fit'), style='line', color='red', name='fit')
                self.line_label.visible = True
                self.line_plot.request_redraw()
            else:
                print("Fit curve length mismatch! Skipping plot.")
            '''
            if self.peakshape == 'lorentzian':
                self.line_data.set_data('fit', n_lorentzians(*self.fit_parameters)(self.frequency))
            if self.peakshape == 'gaussian':
                self.line_data.set_data('fit', n_gaussians(*self.fit_parameters)(self.frequency))
            if self.peakshape == 'n15': #fix from 15N
                self.line_data.set_data('fit', n_n15(*self.fit_parameters)(self.frequency))
            '''


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
                #fix attempt starts here
                if not np.isfinite(g) or g == 0 or not np.isfinite(a):
                    contrast[i] = np.nan
                    continue

                A = np.abs(a / (np.pi * g)) #original

                if not np.isfinite(A) or not np.isfinite(c):
                    contrast[i] = np.nan
                    continue
                #fix attempt ends here
                if a > 0:
                    contrast[i] = 100 * A / (A + c)
                else:
                    contrast[i] = 100 * A / c
            s = ''
            for i, fi in enumerate(f):
                freq_mhz = fi * 1e-6  # Convert frequency from Hz  MHz if you want
                width_mhz = w[i] * 1e-6  # Convert HWHM from Hz  MHz
                s += 'f %i: %.1f MHz, HWHM %.3f MHz, contrast %.1f%%\n' % (
                    i + 1, freq_mhz, width_mhz, contrast[i])
            if self.calculate_center:
                s += 'Center Frequency: %.6e Hz' % self.center
            self.line_label.text = s

    def _update_matrix_data_value(self):
        self.matrix_data.set_data('image', self.counts_matrix)

    def _update_matrix_data_index(self):
        if self.n_lines > self.counts_matrix.shape[0]:
            self.counts_matrix = np.vstack((self.counts_matrix, np.zeros(
                (self.n_lines - self.counts_matrix.shape[0], self.counts_matrix.shape[1]))))
        else:
            self.counts_matrix = self.counts_matrix[:self.n_lines]
        self.matrix_plot.components[0].index.set_data((self.frequency.min() * 1e-6,
                                                       self.frequency.max() * 1e-6),
                                                      (0.0, float(self.n_lines)))

    @on_trait_change("click_tool:click_coords")
    def _change_click_coords(self):
        self.click_coords = self.click_tool.click_coords

    # saving data

    def save_all(self, filename):
        self.line_plot.save(filename + '_ODMR.png')
        # self.matrix_plot.save(filename+'_ODMR_Matrix_Plot.png')
        self.save(filename + '_ODMR.pys')

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

    def _perform_fit_button_fired(self): #fixing the button
        print("Fit button pressed!")
        self._update_fit()

    traits_view = View(
        VGroup(
            HGroup(
                Item('submit_button', show_label=False),
                Item('remove_button', show_label=False),
                Item('resubmit_button', show_label=False),
                Item('priority', enabled_when='state != "run"'),
                Item('state', style='readonly'),
                Item('run_time', style='readonly', format_str='%.f'),
                Item('stop_time'),
            ),
            HGroup(
                Item('filename', springy=True),
                Item('save_button', show_label=False),
                Item('load_button', show_label=False)
            ),
            HGroup(
                Group(
                    Item('power', width=-40, enabled_when='state != "run"'),
                    Item('frequency_begin', width=-80,
                         enabled_when='state != "run"'),
                    Item('frequency_end', width=-80,
                         enabled_when='state != "run"'),
                    Item('frequency_delta', width=-80,
                         enabled_when='state != "run"'),
                    Item('pulsed', enabled_when='state != "run"'),
                    Item('t_pi', width=-50, enabled_when='state != "run"'),

                    show_border=True,
                    label="Timing"
                ),
                Group(
                    Item('seconds_per_point', width=-40,
                         enabled_when='state != "run"'),
                    Item('laser', width=-50, enabled_when='state != "run"'),
                    Item('wait', width=-50, enabled_when='state != "run"'),
                    show_border=True,
                    label="Timing"
                ),
                Group(
                    Group(
                        Item('calculate_center'),
                        Item('number_of_resonances', width=-60),
                        Item('threshold', width=-60),
                        Item('peakshape'),
                        Item('n_lines', width=-60),
                        label="Plot and Fit",
                        show_border=True,
                    ),
                    Item('perform_fit_button', show_label=False), #fix from fitting button
                )

            ),
            HGroup(
                Item('fit_contrast_display', style='readonly', label='Contrast [%]'),
                Item('fit_line_width_display', style='readonly', label='Fit line width [MHz]'),
                Item('fit_frequencies_display', style='readonly', label='Frequency [GHz]'),
                show_border=True

            ),
            VGroup(
                Item('matrix_plot', show_label=False, resizable=True),
                show_border=True
            ),
            VGroup(
                Item('line_plot', show_label=False, resizable=True),
                show_border=True
            ),
            Item('click_coords', style='readonly'),
            layout='normal', show_border=True
        ),
        title='ODMR', width=740, height=800, buttons=[], resizable=True,
    )

    get_set_items = ['frequency', 'counts', 'counts_matrix',
                     'fit_parameters', 'fit_contrast', 'fit_line_width', 'fit_frequencies',
                     'perform_fit', 'run_time',
                     'power', 'frequency_begin', 'frequency_end', 'frequency_delta',
                     'laser', 'wait', 'pulsed', 't_pi',
                     'seconds_per_point', 'stop_time', 'n_lines',
                     'number_of_resonances', 'threshold',
                     '__doc__']


if __name__ == '__main__':
    # logging.getLogger().addHandler(logging.StreamHandler())
    # logging.getLogger().setLevel(logging.DEBUG)
    # logging.getLogger().info('Starting logger.')

    from hardware.dummy import Counter, Microwave, PulseGenerator

    microwave = Microwave()
    counter = Counter()
    pulse_generator = PulseGenerator()

    # from tools.emod import JobManager
    # JobManager().start()

    odmr = ODMR(microwave, counter, pulse_generator)
    odmr.edit_traits()
