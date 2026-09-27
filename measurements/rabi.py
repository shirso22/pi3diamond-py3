import logging

import numpy as np
from chaco.api import ArrayPlotData, Plot
from traits.api import Range, Tuple, Float, Array, Enum, Button
from traitsui.api import View, Item, Group, Tabbed, HGroup, VGroup, VSplit, EnumEditor, TextEditor

import global_vars
from analysis import fitting
from analysis.pulsed import PulsedToolTau, PlotTool
from .pulsed import PulsedTau, sequence_remove_zeros, sequence_union


class Rabi(PulsedTau, PlotTool):
    """Defines a Rabi measurement.

    This measurement class also serves as a base class for more complex measurements require a Rabi
    oscillation as a prerequisite.
    All the measurements that use the NV-specific spin variable, i.e. the Rabi period, will
    inherit from this class and thus use global variables for the microwave frequency, power and
    Rabi period, that are set by an instance of this class via measurement and usage of the
    global_vars.py module.
    """

    # this button is used for getting the global variables in global_vars.py
    get_global_vars_button = Button(label='get globals',
                                    desc='get previously saved global Rabi periods.')

    # this button is used for setting the global variables in global_vars.py
    set_global_vars_button = Button(label='set globals',
                                    desc='set global Rabi periods.')

    # NV- and B-specific variables, mainly for inheritance and not necessarily needed here.
    mw_frequency = Range(low=1, high=20e9, value=2.8705e9, desc='microwave frequency',
                         label='frequency [Hz]', mode='text', auto_set=False, enter_set=True,
                         editor=TextEditor(auto_set=False, enter_set=True, evaluate=float,
                                           format_str='%.5e'))
    mw_power = Range(low=-100., high=25., value=-20, desc='microwave power', label='power [dBm]',
                     mode='text',
                     auto_set=False, enter_set=True)
    mw_x_t_pi2 = Range(low=1., high=1e6, value=25., desc='pi/2 pulse length', label='pi/2 [ns]',
                       mode='text', auto_set=False, enter_set=True)
    mw_x_t_pi = Range(low=1., high=1e6, value=50., desc='pi pulse length', label='pi [ns]',
                      mode='text', auto_set=False, enter_set=True)
    mw_x_t_3pi2 = Range(low=1., high=1e6, value=100., desc='3pi/2 pulse length', label='3pi/2 [ns]',
                        mode='text', auto_set=False, enter_set=True)
    mw_y_t_pi2 = Range(low=0., high=100000., value=50., desc='pi/2 pulse length (y)',
                       label='pi/2 y [ns]', mode='text', auto_set=False, enter_set=True)
    mw_y_t_pi = Range(low=1., high=100000., value=100., desc='pi pulse length (y)',
                      label='pi y [ns]', mode='text', auto_set=False, enter_set=True)
    mw_y_t_3pi2 = Range(low=0., high=100000., value=100., desc='3pi/2 pulse length (y)',
                        label='3pi/2 y [ns]', mode='text', auto_set=False, enter_set=True)

    # measurement variables
    switch = Enum('mw_x', 'mw_y', 'mw2', 'rf', desc='switch to use for microwave pulses',
                  label='MW switch', editor=EnumEditor(cols=3, values={'mw_x': '1:MW 1 X',
                                                                       'mw_y': '2:MW 1 Y',
                                                                       'mw2': '3:MW 2',
                                                                       'rf': '4:SMIQ', }))
    laser = Float(default_value=3000., desc='laser [ns]', label='laser [ns]', mode='text',
                  auto_set=False, enter_set=True)
    decay_init = Float(default_value=250.,
                       desc='time to let the system decay after laser pulse [ns]',
                       label='decay init [ns]', mode='text', auto_set=False, enter_set=True)
    decay_read = Float(default_value=0.,
                       desc='time to let the system decay before laser pulse [ns]',
                       label='decay read [ns]', mode='text', auto_set=False, enter_set=True)
    aom_delay = Float(default_value=0.,
                      desc='If set to a value other than 0.0, the aom triggers are applied\n'
                           'earlier by the specified value. Use with care!',
                      label='aom delay [ns]', mode='text', auto_set=False, enter_set=True)

    # fit results
    contrast = Tuple((np.nan, np.nan),
                     editor=TextEditor(auto_set=False, enter_set=True, evaluate=float,
                                       format_str=' %.1f+-%.1f %%'))
    period = Tuple((np.nan, np.nan),
                   editor=TextEditor(auto_set=False, enter_set=True, evaluate=float,
                                     format_str=' %.2f+-%.2f'))
    q = Float(np.nan, editor=TextEditor(auto_set=False, enter_set=True, evaluate=float,
                                        format_func=lambda x: (' %.3f' if x >= 0.001 else ' %.2e')
                                                              % x))
    x0 = Tuple((np.nan, np.nan),
               editor=TextEditor(auto_set=False, enter_set=True, evaluate=float,
                                 format_str=' %.1f+-%.1f'))
    t_pi2 = Tuple((np.nan, np.nan),
                  editor=TextEditor(auto_set=False, enter_set=True, evaluate=float,
                                    format_str=' %.2f+-%.2f'))
    t_pi = Tuple((np.nan, np.nan),
                 editor=TextEditor(auto_set=False, enter_set=True, evaluate=float,
                                   format_str=' %.2f+-%.2f'))
    t_3pi2 = Tuple((np.nan, np.nan),
                   editor=TextEditor(auto_set=False, enter_set=True, evaluate=float,
                                     format_str=' %.2f+-%.2f'))

    # Make a single line plot
    double_sequence = False

    # add fit results to the get_set_items
    get_set_items = PlotTool.get_set_items + ['contrast', 'period', 't_pi2', 't_pi', 't_3pi2'] + \
                    PulsedTau.get_set_items + ['mw_frequency', 'mw_power', 'laser', 'decay_init',
                                               'decay_read', 'aom_delay',
                                               'switch']

    def __init__(self, pulse_generator, time_tagger, microwave, **kwargs):
        super(Rabi, self).__init__(pulse_generator, time_tagger, **kwargs)
        self.microwave = microwave
        self._create_line_plot()
        self._create_matrix_plot()

        # if we give another mw source at start
        if 'rf' in kwargs:
            self.rf = kwargs['rf']
        else:
            self.rf = None
        if 'microwave2' in kwargs:
            self.microwave2 = kwargs['microwave2']

    def get_global_vars(self):
        """
        Fetch global variables from global_vars.py
        """
        try:
            self.mw_frequency = global_vars.mw_frequency
            self.mw_power = global_vars.mw_power
            self.mw_x_t_pi2 = global_vars.mw_x_t_pi2
            self.mw_x_t_pi = global_vars.mw_x_t_pi
            self.mw_x_t_3pi2 = global_vars.mw_x_t_3pi2
            self.mw_y_t_pi2 = global_vars.mw_y_t_pi2
            self.mw_y_t_pi = global_vars.mw_y_t_pi
            self.mw_y_t_3pi2 = global_vars.mw_y_t_3pi2
        except:
            print('Something went wrong while setting of global variables.')
            pass

    def _get_global_vars_button_fired(self):
        """
        React to get_global_vars_button event.
        """
        self.get_global_vars()

    def set_global_vars(self):
        """
        Fetch global variables from global_vars.py
        """
        try:
            global_vars.mw_frequency = self.mw_frequency
            global_vars.mw_power = self.mw_power
            global_vars.mw_x_t_pi2 = self.mw_x_t_pi2
            global_vars.mw_x_t_pi = self.mw_x_t_pi
            global_vars.mw_x_t_3pi2 = self.mw_x_t_3pi2
            global_vars.mw_y_t_pi2 = self.mw_y_t_pi2
            global_vars.mw_y_t_pi = self.mw_y_t_pi2
            global_vars.mw_y_t_3pi2 = self.mw_y_t_3pi2
        except Exception as e:
            print('Something went wrong while setting global variables.')
            print(e)

    def _set_global_vars_button_fired(self):
        """
        React to get_global_vars_button event.
        """
        self.set_global_vars()

    def start_up(self):
        self.pulse_generator.Night()
        if self.switch == 'rf':
            self.rf.setOutput(self.mw_power, self.mw_frequency)
        else:
            if self.switch == 'mw2':
                self.microwave2.setOutput(self.mw_power, self.mw_frequency)
            else:
                self.microwave.setOutput(self.mw_power, self.mw_frequency)

    def shut_down(self):
        self.pulse_generator.Light()
        if self.switch == 'rf':
            self.rf.setOutput(None, self.mw_frequency)
        else:
            if self.switch == 'mw2':
                self.microwave2.setOutput(None, self.mw_frequency)
            else:
                self.microwave.setOutput(None, self.mw_frequency)

    def generate_sequence(self):
        tau = self.tau
        laser = self.laser
        MW = self.switch
        decay_init = self.decay_init
        decay_read = self.decay_read
        aom_delay = self.aom_delay
        if aom_delay == 0.0:
            sequence = []
            # sequence = [(['aom'], laser)]
            for t in tau:
                sequence += [([], decay_init), ([MW], t), ([], decay_read),
                             (['detect', 'aom'], laser)]
            sequence += [(['sequence'], 100)]
            sequence = sequence_remove_zeros(sequence)
        else:
            s1 = [(['aom'], laser)]
            s2 = [([], aom_delay + laser)]
            for t in tau:
                s1 += [([], decay_init + t + decay_read), (['aom'], laser)]
                s2 += [([], decay_init), (['microwave'], t), ([], decay_read), (['detect'], laser)]
            s2 += [(['sequence'], 100)]
            s1 = sequence_remove_zeros(s1)
            s2 = sequence_remove_zeros(s2)
            sequence = sequence_union(s1, s2)
        return sequence

    def _update_fit(self):
        y = self.spin_state
        try:
            fit_result = fitting.fit_rabi(self.tau, y, y ** 0.5)
        except:
            fit_result = ((np.nan, np.nan, np.nan, np.nan, np.nan), np.nan * np.zeros((5, 5)),
                          np.nan, np.nan)

        p, v, q, chisqr = fit_result
        a, T, c, x0, tau = p
        a_var, T_var, c_var, x0_var, tau_var = v.diagonal()

        # compute some relevant parameters from fit result
        contrast = 200 * a / (c + a)
        contrast_delta = 200. / c ** 2 * (a_var * c ** 2 + c_var * a ** 2) ** 0.5
        T_delta = abs(T_var) ** 0.5
        x0_delta = abs(x0_var) ** 0.5
        pi2 = 0.25 * T + x0
        pi = 0.5 * T + x0
        threepi2 = 0.75 * T + x0
        pi2_delta = 0.25 * T_delta
        pi_delta = 0.5 * T_delta
        threepi2_delta = 0.75 * T_delta

        # set respective attributes
        self.q = q
        self.period = T, T_delta
        self.x0 = x0, x0_delta
        self.contrast = contrast, contrast_delta
        self.t_pi2 = pi2, pi2_delta
        self.t_pi = pi, pi_delta
        self.t_3pi2 = threepi2, threepi2_delta

        # create a summary of fit result as a text string
        s = 'q: %.2e\n' % q
        s += 'contrast: %.1f+-%.1f%%\n' % (contrast, contrast_delta)
        s += 'period: %.2f+-%.2f ns\n' % (T, T_delta)
        # s += 'pi/2: %.2f+-%.2f ns\n'%(pi2, pi2_delta)
        # s += 'pi: %.2f+-%.2f ns\n'%(pi, pi_delta)
        # s += '3pi/2: %.2f+-%.2f ns\n'%(threepi2, threepi2_delta)

        self.fit_result = fit_result
        self.text = s

    def _on_fit_result_change(self, new):
        if len(new) > 0 and new[0][0] is not np.nan:
            self.line_data.set_data('fit', fitting.CosinusDecay(*new[0])(self.tau))

    traits_view = View(
        VGroup(
            HGroup(
                Item('submit_button', width=-60, show_label=False),
                Item('remove_button', width=-60, show_label=False),
                Item('resubmit_button', width=-60, show_label=False),
                Item('priority', width=-30),
                Item('state', style='readonly'),
                Item('run_time', style='readonly', format_str='%.f'),
                Item('stop_time', format_str='%.f'),
                Item('stop_counts'),
            ),
            HGroup(
                Item('filename', springy=True),
                Item('save_button', show_label=False),
                Item('load_button', show_label=False),
                Item('periodic_save'),
                Item('save_interval', enabled_when='not periodic_save'),
            ),
            Tabbed(
                VGroup(
                    HGroup(
                        Item('mw_frequency', width=-120, enabled_when='state != "run"'),
                        Item('mw_power', width=-60, enabled_when='state != "run"'),
                        Item('switch', style='custom', enabled_when='state != "run"'),
                        Item('aom_delay', width=-80, enabled_when='state != "run"'),
                    ),
                    HGroup(
                        Item('laser', width=-80, enabled_when='state != "run"'),
                        Item('decay_init', width=-80, enabled_when='state != "run"'),
                        Item('decay_read', width=-80, enabled_when='state != "run"'),
                    ),
                    HGroup(
                        Item('tau_begin', width=-80, enabled_when='state != "run"'),
                        Item('tau_end', width=-80, enabled_when='state != "run"'),
                        Item('tau_delta', width=-80, enabled_when='state != "run"'),
                    ),
                    label='Stimulation'
                ),
                VGroup(
                    HGroup(
                        Item('record_length', width=-80, enabled_when='state != "run"'),
                        Item('bin_width', width=-80, enabled_when='state != "run"'),
                    ),
                    label='Acquisition'
                ),
                VGroup(
                    HGroup(
                        Item('integration_width'),
                        Item('position_signal'),
                        Item('position_normalize'),
                    ),
                    label='Analysis'
                ),
            ),
            VGroup(
                VGroup(
                    HGroup(
                        Item('contrast', style='readonly', width=-100),
                        Item('period', style='readonly', width=-100),
                        Item('x0', style='readonly', width=-100),
                        Item('q', style='readonly', width=-100),
                    ),
                    HGroup(
                        Item('t_pi2', style='readonly', width=-100),
                        Item('t_pi', style='readonly', width=-100),
                        Item('t_3pi2', style='readonly', width=-100),
                    ),
                    # label='fit_result',
                ),
            ),
            Tabbed(
                Item('line_plot', show_label=False, width=500, height=-300, resizable=True),
                Item('matrix_plot', show_label=False, width=500, height=-300, resizable=True),
                Item('pulse_plot', show_label=False, width=500, height=-300, resizable=True),
            ),
        ),
        title='Pi3diamond: Rabi',
        buttons=[],
        resizable=True,
        height=-640
    )


class PulseExtractTool(PulsedToolTau):
    """
    Provides extraction of pulses from a Rabi measurement.
    """

    period = Float()
    contrast = Float()
    t_pi2 = Array()
    t_pi = Array()
    t_3pi2 = Array()
    t_2pi = Array()

    # add fit results to the get_set_items
    get_set_items = PulsedToolTau.get_set_items + ['contrast', 'period', 't_pi2', 't_pi', 't_3pi2',
                                                   't_2pi']

    traits_view = View(VGroup(VGroup(Item(name='measurement', style='custom', show_label=False),
                                     Group(VGroup(HGroup(
                                         Item('contrast', style='readonly', format_str='%.1f'),
                                         Item('period', style='readonly'),
                                     ),
                                         HGroup(Item('t_pi2', style='readonly'),
                                                Item('t_pi', style='readonly'),
                                                Item('t_3pi2', style='readonly'),
                                                Item('t_2pi', style='readonly'),
                                                ),
                                         label='fit_result',
                                     ),
                                         VGroup(HGroup(Item('integration_width'),
                                                       Item('position_signal'),
                                                       Item('position_normalize'),
                                                       ),
                                                label='fit_parameter',
                                                ),
                                         orientation='horizontal', layout='tabbed', springy=False,
                                     ),
                                     ),
                              VSplit(Item('matrix_plot', show_label=False, width=500, height=300,
                                          resizable=True),
                                     Item('line_plot', show_label=False, width=500, height=300,
                                          resizable=True),
                                     Item('pulse_plot', show_label=False, width=500, height=300,
                                          resizable=True),
                                     ),
                              ),
                       title='Pulse Extraction',
                       buttons=[], resizable=True)

    # overwrite __init__ to trigger update events
    def __init__(self, **kwargs):
        super(PulseExtractTool, self).__init__(**kwargs)
        self.on_trait_change(self._update_fit, 'spin_state', dispatch='ui')

    def _update_fit(self, y):
        # try to extract pulses from spin_state and tau.
        tau = self.measurement.tau
        try:
            f, r, p, tp = fitting.extract_pulses(y)
        except:
            logging.getLogger().debug('Failed to compute fit.')
            f = [0]
            r = [0]
            p = [0]
            tp = [0]

        pi2 = tau[f]
        pi = tau[p]
        three_pi2 = tau[r]
        two_pi = tau[tp]

        # compute some relevant parameters from the result
        mi = y.min()
        ma = y.max()
        contrast = 100 * (ma - mi) / ma
        # simple rough estimate of the period to avoid index out of range Error
        T = 4 * (pi[0] - pi2[0])

        # set respective attributes
        self.period = T
        self.contrast = contrast
        self.t_pi2 = pi2
        self.t_pi = pi
        self.t_3pi2 = three_pi2
        self.t_2pi = two_pi

        # create a summary of the result as a text string
        s = 'contrast: %.1f\n' % contrast
        s += 'period: %.2f ns\n' % T

        # markers in the plot that show the result of the pulse extraction
        self.line_data.set_data('pulse_indices', np.hstack((pi2, pi, three_pi2, two_pi)) * 1e-3)
        self.line_data.set_data('pulse_values', np.hstack((y[f], y[p], y[r], y[tp])))
        self.line_plot.overlays[0].text = s

    # overwrite the line_plot to include fit and text label 
    def _create_line_plot(self):
        line_data = ArrayPlotData(index=np.array((0, 1)),
                                  spin_state=np.array((0, 0)),
                                  pulse_indices=np.array((0, 0)),
                                  pulse_values=np.array((0, 0)))
        plot = Plot(line_data, padding=8, padding_left=64, padding_bottom=36)
        plot.plot(('index', 'spin_state'), color='blue', name='spin_state')
        plot.plot(('pulse_indices', 'pulse_values'),
                  type='scatter',
                  marker='circle',
                  color='none',
                  outline_color='red',
                  line_width=1.0,
                  name='pulses')
        plot.index_axis.title = 'time [micro s]'
        plot.value_axis.title = 'spin state'
        # plot.overlays.insert(0, PlotLabel(text=self.label_text, hjustify='left', vjustify='bottom', position=[64,32]) )
        self.line_data = line_data
        self.line_plot = plot


if __name__ == '__main__':
    # import logging

    # logging.getLogger().addHandler(logging.StreamHandler())
    # logging.getLogger().setLevel(logging.DEBUG)
    # logging.getLogger().info('Starting logger.')

    # from tools.emod import JobManager

    # JobManager().start()

    # from hardware.dummy import PulseGenerator, TimeTagger, Microwave

    pass
