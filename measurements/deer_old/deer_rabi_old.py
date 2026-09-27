import logging

import numpy as np
# PY3-PORT: implicit relative import across packages; 2to3 only rewrites siblings.
from ..pulsed import PulsedTau, sequence_remove_zeros
from traits.api import Range, Tuple, Int, Float, Instance
from traitsui.api import View, Item, Tabbed, HGroup, VGroup, TextEditor


class DEERRabi(PulsedTau):
    """Defines a DEER Rabi measurement.
    
    Here we drive the external electron spin with a source RF, whose pulses are applied during the
    Hahn Echo or an XY8 Sequence, while we measure the coherence of the NV. This measurement varies
    the pulse length of a fixed rf Frequency pulse, to determine if we can coherently drive the
    external spin.
    """

    """values that .save wants to have... we need to change that!"""
    switch = 'X'

    frequency = Range(low=1e9, high=10e9, value=2.8705e9, desc='microwave frequency',
                      label='Microwave frequency [Hz]', mode='text', auto_set=False,
                      enter_set=True, editor=TextEditor(auto_set=False, enter_set=True,
                                                        evaluate=float, format_str='%e'))
    power = Range(low=-100., high=25., value=-20, desc='microwave power', label='power [dBm]',
                  mode='text', auto_set=False, enter_set=True)

    laser = Float(default_value=3000., desc='laser [ns]', label='laser [ns]', mode='text',
                  auto_set=False, enter_set=True)
    decay_init = Float(default_value=1000., desc='time to let the system decay after laser pulse [ns]',
                       label='decay init [ns]', mode='text', auto_set=False, enter_set=True)
    decay_read = Float(default_value=0., desc='time to let the system decay before laser pulse [ns]',
                       label='decay read [ns]', mode='text', auto_set=False, enter_set=True)

    aom_delay = Float(default_value=0.,
                      desc='If set to a value other than 0.0, the aom triggers are applied\nearlier by the specified value. Use with care!',
                      label='aom delay [ns]', mode='text', auto_set=False, enter_set=True)

    t_pi2_x = Range(low=0., high=100000., value=50., desc='pi/2 pulse length (x)',
                    label='pi/2 x [ns]', mode='text', auto_set=False, enter_set=True)
    t_3pi2_x = Range(low=0., high=100000., value=150., desc='3pi/2 pulse length (x)',
                     label='3pi/2 x [ns]', mode='text', auto_set=False, enter_set=True)
    t_pi_y = Range(low=1., high=100000., value=100., desc='pi pulse length (y)', label='pi y [ns]',
                   mode='text', auto_set=False, enter_set=True)
    t_pi_x = Range(low=1., high=100000., value=100., desc='pi pulse length (x)', label='pi x [ns]',
                   mode='text', auto_set=False, enter_set=True)
    power_imbalance = Range(low=-1., high=1., value=0., desc='microwave power imbalance',
                            label='power imbalance [dBm]', mode='text', auto_set=False,
                            enter_set=True)
    n_sequences = Int(default_value=1, desc='number of XY_8-Sequences', label='n_seq', mode='text',
                      auto_set=False, enter_set=True)
    mw_tau = Float(default_value=2000, desc='time between mw pi pulses[ns]', label='mw_tau [ns]',
                   mode='text', auto_set=False, enter_set=True)
    """"Values that define the RF e-Spin excitation in the DEER sequence."""
    rf_frequency = Range(low=10.e6, high=3200.e6, value=200.e6, desc='RF frequency',
                         label='RF frequency [Hz]', mode='text', auto_set=False, enter_set=True,
                         editor=TextEditor(auto_set=False, enter_set=True, evaluate=float,
                                           format_str='%e'))
    rf_power = Range(low=-60., high=4., value=-20., desc='rf power', label='RF Power [dBm]',
                     mode='text', auto_set=False, enter_set=True)
    t_rf_wait = Float(default_value=15., desc='wait between mw and rf pulse[ns]',
                      label='RF wait [ns]', mode='text', auto_set=False, enter_set=True)

    def __init__(self, pulse_generator, time_tagger, microwave, rf, **kwargs):
        super(DEERRabi, self).__init__(pulse_generator, time_tagger, **kwargs)
        self.microwave = microwave
        self.rf = rf

    def start_up(self):
        self.pulse_generator.Night()
        self.microwave.setOutput(self.power, self.frequency)
        self.rf.setFrequency(self.rf_frequency)
        self.rf.setPower(self.rf_power)

    def shut_down(self):
        self.pulse_generator.Light()
        self.microwave.setOutput(None, self.frequency)
        self.rf.setPower(-40)

    def generate_sequence(self):
        tau = self.tau
        laser = self.laser
        n = self.n_sequences
        decay_init = self.decay_init

        mw_tau = self.mw_tau
        t_pi2_x = self.t_pi2_x
        t_3pi2_x = self.t_3pi2_x
        t_pi_y = self.t_pi_y
        t_pi_x = self.t_pi_x

        t_rf_wait = self.t_rf_wait

        sequence = []
        sequence_reference = []
        sequence_signal = []
        if n == 0:
            """In this case we just do a simple hahn echo with an rf in between.
            mw_tau corresponds to half the time between the pi2 and pi pulse of the mw.
            """
            sequence1_signal = []
            sequence2_signal = []
            for t in tau:
                sequence1_signal += [(['mw_x'], t_pi2_x), ([], t_rf_wait), (['rf'], t),
                                     ([], (0.5 * mw_tau) - t_rf_wait - t), (['mw_x'], t_pi_x),
                                     ([], t_rf_wait), (['rf'], t), ([], (0.5 * mw_tau) - t_rf_wait - t),
                                     (['mw_x'], t_pi2_x), (['detect', 'aom'], laser), ([], decay_init)]
                sequence2_signal += [(['mw_x'], t_pi2_x), ([], t_rf_wait), (['rf'], t),
                                     ([], (0.5 * mw_tau) - t_rf_wait - t), (['mw_x'], t_pi_x),
                                     ([], t_rf_wait), (['rf'], t), ([], (0.5 * mw_tau) - t_rf_wait - t),
                                     (['mw_x'], t_3pi2_x), (['detect', 'aom'], laser), ([], decay_init)]
            sequence_signal = sequence1_signal + sequence2_signal
        else:
            """In this case we just do xy8_n-DD, with an rf pulse in between each mw_tau
            mw_tau corresponds to the time/8*n the sequence takes. This time is used in NMR analysis
            and since our xy8 measurements are using this time we use it here as well.
            """
            # mw_t is the time between the infinitely short xy8 pulses
            mw_t = mw_tau / (8. * n)
            # This lambda function gives correct mw_tau for the approximation of infinetly short pulses
            t_bar = lambda mw_t, p1, p2=0., p3=0., p4=0.: mw_t - (p1 / 2.) - (p2 / 2.) - p3 - p4
            # check, if the start time is long enough to fit at least the mw+rf pulses in it.
            t_max = tau.max()
            if t_bar(mw_t, t_pi_y, t_pi_y, t_rf_wait, t_max) < 0 or t_bar(mw_t, t_pi_x, t_pi_x, t_rf_wait, t_max) < 0:
                raise IOError(
                    'The delay between pulses is too short. It has to be larger than the combined pulse duration')

            sequence = []
            """
            Build the signal sequence, i.e. the spin state with applied rf at a specific mw_tau with xy8
            decoupling.
            """
            sequence1_signal = []
            sequence2_signal = []

            for t in tau:
                xy_8_rf_part = []
                start = []
                end_pi2 = []
                end_3pi2 = []
                init = [(['detect', 'aom'], laser), ([], decay_init)]

                xy_8_rf_part += [(['mw_x'], t_pi_x), ([], t_rf_wait), (['rf'], t),
                                 ([], t_bar(mw_t, t_pi_x, t_pi_y, t_rf_wait, t))]
                xy_8_rf_part += [(['mw_y'], t_pi_y), ([], t_rf_wait), (['rf'], t),
                                 ([], t_bar(mw_t, t_pi_x, t_pi_y, t_rf_wait, t))]
                xy_8_rf_part += [(['mw_x'], t_pi_x), ([], t_rf_wait), (['rf'], t),
                                 ([], t_bar(mw_t, t_pi_x, t_pi_y, t_rf_wait, t))]
                xy_8_rf_part += [(['mw_y'], t_pi_y), ([], t_rf_wait), (['rf'], t),
                                 ([], t_bar(mw_t, t_pi_y, t_pi_y, t_rf_wait, t))]
                xy_8_rf_part += [(['mw_y'], t_pi_y), ([], t_rf_wait), (['rf'], t),
                                 ([], t_bar(mw_t, t_pi_x, t_pi_y, t_rf_wait, t))]
                xy_8_rf_part += [(['mw_x'], t_pi_x), ([], t_rf_wait), (['rf'], t),
                                 ([], t_bar(mw_t, t_pi_x, t_pi_y, t_rf_wait, t))]
                xy_8_rf_part += [(['mw_y'], t_pi_y), ([], t_rf_wait), (['rf'], t),
                                 ([], t_bar(mw_t, t_pi_x, t_pi_y, t_rf_wait, t))]
                xy_8_rf_part += [(['mw_x'], t_pi_x)]

                start = [(['mw_x'], t_pi2_x), ([], t_bar(mw_t, t_pi_x) / 2.)]
                end_pi2 = [([], t_bar(mw_t, t_pi_x) / 2.), (['mw_x'], t_pi2_x)]
                end_3pi2 = [([], t_bar(mw_t, t_pi_x) / 2.), (['mw_x'], t_3pi2_x)]

                # build the sequences
                sequence1_signal += start + (
                        (n - 1) * (xy_8_rf_part + [([], t_bar(mw_t, t_pi_x, t_pi_y))])) + xy_8_rf_part + end_pi2 + init
                sequence2_signal += start + (
                        (n - 1) * (xy_8_rf_part + [([], t_bar(mw_t, t_pi_x, t_pi_y))])) + xy_8_rf_part + end_3pi2 + init

            # join the two sequences
            sequence_signal = sequence1_signal + sequence2_signal
        # now, join reference and signal sequence
        sequence = sequence_reference + sequence_signal
        # tail of the sequence
        sequence += [(['sequence'], 100)]
        sequence = sequence_remove_zeros(sequence)

        return sequence

    get_set_items = PulsedTau.get_set_items + ['frequency', 'power', 'laser', 'decay_init', 'decay_read', 'aom_delay',
                                               'switch']

    traits_view = View(VGroup(HGroup(Item('submit_button', width=-60, show_label=False),
                                     Item('remove_button', width=-60, show_label=False),
                                     Item('resubmit_button', width=-60, show_label=False),
                                     Item('priority', width=-30),
                                     Item('state', style='readonly'),
                                     Item('run_time', style='readonly', format_str='%.f'),
                                     Item('stop_time', format_str='%.f'),
                                     Item('stop_counts'),
                                     ),
                              HGroup(Item('filename', springy=True),
                                     Item('save_button', show_label=False),
                                     Item('load_button', show_label=False)
                                     ),
                              Tabbed(VGroup(HGroup(Item('frequency', width=-120, enabled_when='state != "run"'),
                                                   Item('power', width=-60, enabled_when='state != "run"'),
                                                   ),
                                            HGroup(Item('laser', width=-80, enabled_when='state != "run"'),
                                                   Item('decay_init', width=-80, enabled_when='state != "run"'),
                                                   Item('decay_read', width=-80, enabled_when='state != "run"'),
                                                   ),
                                            HGroup(Item('t_pi2_x', width=-80, enabled_when='state != "run"'),
                                                   Item('t_pi_x', width=-80, enabled_when='state != "run"'),
                                                   Item('t_pi_y', width=-80, enabled_when='state != "run"'),
                                                   Item('t_3pi2_x', width=-80, enabled_when='state != "run"'),
                                                   Item('n_sequences', width=-80, enabled_when='state != "run"'),
                                                   Item('mw_tau', width=-80, enabled_when='state != "run"'),
                                                   ),
                                            HGroup(Item('rf_frequency', width=-120, enabled_when='state != "run"'),
                                                   Item('rf_power', width=-80, enabled_when='state != "run"'),
                                                   Item('t_rf_wait', width=-80, enabled_when='state != "run"'),
                                                   ),
                                            HGroup(Item('tau_begin', width=-80, enabled_when='state != "run"'),
                                                   Item('tau_end', width=-80, enabled_when='state != "run"'),
                                                   Item('tau_delta', width=-80, enabled_when='state != "run"'),
                                                   ),
                                            label='stimulation'),
                                     VGroup(HGroup(Item('record_length', width=-80, enabled_when='state != "run"'),
                                                   Item('bin_width', width=-80, enabled_when='state != "run"'),
                                                   ),
                                            label='acquisition'),
                                     VGroup(HGroup(Item('integration_width'),
                                                   Item('position_signal'),
                                                   Item('position_normalize'),
                                                   ),
                                            label='analysis'),
                                     ),
                              ),
                       title='DEER Rabi',
                       )


from analysis.pulsed import FitToolTau, PulsedToolDoubleTau
from analysis import fitting


class DEERRabiTool(PulsedToolDoubleTau):
    """Plotting of a DEER Rabi measurement.
    
    For now we inherit everything from PulsedToolDoubleTau and just change the evaluation.
    """

    """
    The Sequence we assume is [echo+pi2, echo+3pi2, echo_rf+pi2, echo_rf+3pi2]. Accordingly we take
    the difference between the sequences with and without rf pulse and display two signals to
    distinguish between pi2 and 3pi2 mw pluses at the end.
    """

    def _update_line_plot_value(self):
        y = self.measurement.spin_state
        n = len(self.measurement.tau)
        first = y[0:n]
        second = y[n:2 * n]
        try:
            self.line_data.set_data('first', first)
            self.line_data.set_data('second', second)
        except:
            logging.getLogger().debug('Could not set data for spin_state plots.')


class DEERRabiFitTool(FitToolTau):
    """Plotting and Analysis of a DEER Rabi measurement.
    
    For now we inherit everyhting from 
    """

    measurement = Instance(DEERRabi)

    # fit results
    contrast = Tuple((np.nan, np.nan),
                     editor=TextEditor(auto_set=False, enter_set=True, evaluate=float, format_str=' %.1f+-%.1f %%'))
    period = Tuple((np.nan, np.nan),
                   editor=TextEditor(auto_set=False, enter_set=True, evaluate=float, format_str=' %.2f+-%.2f'))
    q = Float(np.nan, editor=TextEditor(auto_set=False, enter_set=True, evaluate=float,
                                        format_func=lambda x: (' %.3f' if x >= 0.001 else ' %.2e') % x))
    t_pi2 = Tuple((np.nan, np.nan),
                  editor=TextEditor(auto_set=False, enter_set=True, evaluate=float, format_str=' %.2f+-%.2f'))
    t_pi = Tuple((np.nan, np.nan),
                 editor=TextEditor(auto_set=False, enter_set=True, evaluate=float, format_str=' %.2f+-%.2f'))
    t_3pi2 = Tuple((np.nan, np.nan),
                   editor=TextEditor(auto_set=False, enter_set=True, evaluate=float, format_str=' %.2f+-%.2f'))

    # add fit results to the get_set_items
    get_set_items = FitToolTau.get_set_items + ['contrast', 'period', 't_pi2', 't_pi', 't_3pi2']

    def _update_fit(self):
        y = self.measurement.spin_state
        try:
            fit_result = fitting.fit_rabi(self.measurement.tau, y, y ** 0.5)
        except:
            fit_result = (np.nan * np.zeros(3), np.nan * np.zeros((3, 3)), np.nan, np.nan)

        p, v, q, chisqr = fit_result
        a, T, c = p
        a_var, T_var, c_var = v.diagonal()

        # compute some relevant parameters from fit result
        contrast = 200 * a / (c + a)
        contrast_delta = 200. / c ** 2 * (a_var * c ** 2 + c_var * a ** 2) ** 0.5
        T_delta = abs(T_var) ** 0.5
        pi2 = 0.25 * T
        pi = 0.5 * T
        threepi2 = 0.75 * T
        pi2_delta = 0.25 * T_delta
        pi_delta = 0.5 * T_delta
        threepi2_delta = 0.75 * T_delta

        # set respective attributes
        self.q = q
        self.period = T, T_delta
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
            self.line_data.set_data('fit', fitting.Cosinus(*new[0])(self.measurement.tau))

    traits_view = View(VGroup(VGroup(Item(name='measurement', style='custom', show_label=False),
                                     VGroup(HGroup(Item('contrast', style='readonly', width=-100),
                                                   Item('period', style='readonly', width=-100),
                                                   Item('q', style='readonly', width=-100),
                                                   ),
                                            HGroup(Item('t_pi2', style='readonly', width=-100),
                                                   Item('t_pi', style='readonly', width=-100),
                                                   Item('t_3pi2', style='readonly', width=-100),
                                                   ),
                                            label='fit_result',
                                            ),
                                     ),
                              Tabbed(Item('line_plot', show_label=False, width=500, height=-300, resizable=True),
                                     Item('matrix_plot', show_label=False, width=500, height=-300, resizable=True),
                                     Item('pulse_plot', show_label=False, width=500, height=-300, resizable=True),
                                     ),
                              ),
                       title='DEER Rabi Tool',
                       buttons=[],
                       resizable=True,
                       height=-640
                       )


if __name__ == '__main__':
    # import logging

    # logging.getLogger().addHandler(logging.StreamHandler())
    # logging.getLogger().setLevel(logging.DEBUG)
    # logging.getLogger().info('Starting logger.')

    # from tools.emod import JobManager

    # JobManager().start()

    # from hardware.dummy import PulseGenerator, TimeTagger, Microwave
    pass
