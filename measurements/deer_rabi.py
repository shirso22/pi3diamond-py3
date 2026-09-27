import logging

import numpy as np
from chaco.api import ArrayPlotData
from traitsui.api import View, Item, Tabbed, HGroup, VGroup

from analysis import fitting
from measurements.deer import DEER, DEERDQT
from measurements.rabi import Rabi
from .pulsed import sequence_remove_zeros
from tools.chaco_addons import SavePlot as Plot, SaveTool


class DEERRabi(DEER):
    """Defines a DEER Rabi measurement.
    
    Here we drive the external electron spin with a source RF, whose pulses are applied during the
    Hahn Echo or an XY8 Sequence, while we measure the coherence of the NV. This measurement varies
    the pulse length of a fixed rf Frequency pulse, to determine if we can coherently drive the
    external spin.
    """

    def __init__(self, pulse_generator, time_tagger, microwave, rf, **kwargs):
        super(DEERRabi, self).__init__(pulse_generator, time_tagger, microwave, rf, **kwargs)

    def generate_sequence(self):
        tau = self.tau
        laser = self.laser
        n = self.decoupling_order
        decay_init = self.decay_init

        mw_tau = self.mw_tau
        mw_x_t_pi2 = self.mw_x_t_pi2
        mw_x_t_3pi2 = self.mw_x_t_3pi2
        mw_y_t_pi = self.mw_y_t_pi
        mw_x_t_pi = self.mw_x_t_pi

        rf_pulse_delay = self.rf_pulse_delay

        # This lambda function gives correct mw_tau for the approximation of infinetly short pulses
        t_bar = lambda mw_t, p1, p2=0., p3=0., p4=0.: mw_t - (p1 / 2.) - (p2 / 2.) - p3 - p4
        if n == 0:
            """In this case we just do a simple hahn echo with an rf in between.
            mw_tau corresponds to half the time between the pi2 and pi pulse of the mw.
            """
            # check, if the start time is long enough to fit at least the mw+rf pulses in it.
            t_max = tau.max()
            if mw_tau * 0.5 - rf_pulse_delay - t_max < 0:
                raise IOError('The delay between pulses is too short. It has to be larger than the'
                              'combined pulse duration')
            sequence_pi2 = []
            sequence_3pi2 = []
            for t in tau:
                sequence_pi2 += [(['mw_x'], mw_x_t_pi2), ([], (0.5 * mw_tau)),
                                 (['mw_x'], mw_x_t_pi),
                                 ([], rf_pulse_delay), (['rf'], t),
                                 ([], (0.5 * mw_tau) - rf_pulse_delay - t),
                                 (['mw_x'], mw_x_t_pi2), (['detect', 'aom'], laser),
                                 ([], decay_init)]
                sequence_3pi2 += [(['mw_x'], mw_x_t_pi2), ([], (0.5 * mw_tau)),
                                  (['mw_x'], mw_x_t_pi),
                                  ([], rf_pulse_delay), (['rf'], t),
                                  ([], (0.5 * mw_tau) - rf_pulse_delay - t),
                                  (['mw_x'], mw_x_t_3pi2), (['detect', 'aom'], laser),
                                  ([], decay_init)]
            sequence = sequence_pi2 + sequence_3pi2
        else:
            """In this case we just do xy8_n-DD, with an rf pulse in between each mw_tau
            mw_tau corresponds to the time/8*n the sequence takes. This time is used in NMR analysis
            and since our xy8 measurements are using this time we use it here as well.
            """
            # mw_t is the time between the infinitely short xy8 pulses
            mw_t = mw_tau / (8. * n)
            # check, if the start time is long enough to fit at least the mw+rf pulses in it.
            t_max = tau.max()
            if t_bar(mw_t, mw_y_t_pi, mw_y_t_pi, rf_pulse_delay, t_max) < 0 or t_bar(mw_t,
                                                                                     mw_x_t_pi,
                                                                                     mw_x_t_pi,
                                                                                     rf_pulse_delay,
                                                                                     t_max) < 0:
                raise IOError('The delay between pulses is too short. It has to be larger than the '
                              'combined pulse duration')

            """
            Build the signal sequence, i.e. the spin state with applied rf at a specific mw_tau with
            xy8 decoupling.
            """
            sequence1_signal = []
            sequence2_signal = []

            for t in tau:
                xy_8_rf_part = []
                init = [(['detect', 'aom'], laser), ([], decay_init)]

                xy_8_rf_part += [(['mw_x'], mw_x_t_pi), ([], rf_pulse_delay), (['rf'], t),
                                 ([], t_bar(mw_t, mw_x_t_pi, mw_y_t_pi, rf_pulse_delay, t))]
                xy_8_rf_part += [(['mw_y'], mw_y_t_pi), ([], rf_pulse_delay), (['rf'], t),
                                 ([], t_bar(mw_t, mw_x_t_pi, mw_y_t_pi, rf_pulse_delay, t))]
                xy_8_rf_part += [(['mw_x'], mw_x_t_pi), ([], rf_pulse_delay), (['rf'], t),
                                 ([], t_bar(mw_t, mw_x_t_pi, mw_y_t_pi, rf_pulse_delay, t))]
                xy_8_rf_part += [(['mw_y'], mw_y_t_pi), ([], rf_pulse_delay), (['rf'], t),
                                 ([], t_bar(mw_t, mw_y_t_pi, mw_y_t_pi, rf_pulse_delay, t))]
                xy_8_rf_part += [(['mw_y'], mw_y_t_pi), ([], rf_pulse_delay), (['rf'], t),
                                 ([], t_bar(mw_t, mw_x_t_pi, mw_y_t_pi, rf_pulse_delay, t))]
                xy_8_rf_part += [(['mw_x'], mw_x_t_pi), ([], rf_pulse_delay), (['rf'], t),
                                 ([], t_bar(mw_t, mw_x_t_pi, mw_y_t_pi, rf_pulse_delay, t))]
                xy_8_rf_part += [(['mw_y'], mw_y_t_pi), ([], rf_pulse_delay), (['rf'], t),
                                 ([], t_bar(mw_t, mw_x_t_pi, mw_y_t_pi, rf_pulse_delay, t))]
                xy_8_rf_part += [(['mw_x'], mw_x_t_pi)]

                start = [(['mw_x'], mw_x_t_pi2), ([], t_bar(mw_t, mw_x_t_pi) / 2.)]
                end_pi2 = [([], t_bar(mw_t, mw_x_t_pi) / 2.), (['mw_x'], mw_x_t_pi2)]
                end_3pi2 = [([], t_bar(mw_t, mw_x_t_pi) / 2.), (['mw_x'], mw_x_t_3pi2)]

                # build the sequences
                sequence1_signal += start + (
                        (n - 1) * (xy_8_rf_part + [
                    ([], t_bar(mw_t, mw_x_t_pi, mw_y_t_pi))])) + xy_8_rf_part + end_pi2 + init
                sequence2_signal += start + (
                        (n - 1) * (xy_8_rf_part + [
                    ([], t_bar(mw_t, mw_x_t_pi, mw_y_t_pi))])) + xy_8_rf_part + end_3pi2 + init

            # join the two sequences
            sequence = sequence1_signal + sequence2_signal
        # tail of the sequence
        sequence += [(['sequence'], 100)]
        sequence = sequence_remove_zeros(sequence)

        return sequence

    def _create_line_plot(self):
        line_data = ArrayPlotData(index=np.array((0, 1)),
                                  state_first_seq=np.array((0, 0)),
                                  state_second_seq=np.array((0, 0)),
                                  state_difference=np.array((0, 0)),
                                  fit=np.array((0, 0))
                                  )
        plot = Plot(line_data, padding=8, padding_left=64, padding_bottom=36)
        plot.plot(('index', 'state_first_seq'), color='blue', name='state_first_seq')
        plot.plot(('index', 'state_second_seq'), color='green', name='state_second_seq')
        plot.plot(('index', 'state_difference'), color='black', name='state_difference',
                  line_width=2)
        plot.plot(('index', 'fit'), color='red', name='state_difference', line_width=2)
        plot.index_axis.title = 'time [micro s]'
        plot.value_axis.title = 'spin state'
        plot.tools.append(SaveTool(plot))
        self.line_data = line_data
        self.line_plot = plot

    def _update_line_plot_value(self):
        y = self.spin_state
        n = len(self.tau)
        first = y[:n]
        second = y[n:2 * n]
        spin_state_difference = (first - second) + (first.max() + second.min()) / 2.
        try:
            self.line_data.set_data('state_first_seq', first)
            self.line_data.set_data('state_second_seq', second)
            self.line_data.set_data('state_difference', spin_state_difference)
        except:
            logging.getLogger().debug('Could not set data for spin_state plots.')

    def _update_fit(self):
        n = len(self.tau)
        first = self.spin_state[:n]
        second = self.spin_state[n:2 * n]
        y = (first - second) + (first.max() + second.min()) / 2.
        try:
            fit_result = fitting.fit_rabi(self.tau, y, y ** 0.5)
        except:
            fit_result = (np.nan * np.zeros(3), np.nan * np.zeros((3, 3)), np.nan, np.nan)

        p, v, q, chisqr = fit_result
        a, T, x0, c = p
        a_var, T_var, x0_var, c_var = v.diagonal()

        # compute some relevant parameters from fit result
        contrast = 200 * a / (c + a)
        contrast_delta = 200. / c ** 2 * (a_var * c ** 2 + c_var * a ** 2) ** 0.5
        T_delta = abs(T_var) ** 0.5
        pi2 = 0.25 * T + x0
        pi = 0.5 * T + x0
        threepi2 = 0.75 * T + x0
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

    get_set_items = Rabi.get_set_items + ['mw_tau', 'mw_x_t_pi2', 'mw_x_t_pi', 'mw_x_t_3pi2',
                                          'mw_y_t_pi', 'decoupling_order', 'power_imbalance',
                                          'rf_frequency', 'rf_power', 'rf_pulse_delay']

    traits_view = View(VGroup(HGroup(Item('submit_button', width=-60, show_label=False),
                                     Item('remove_button', width=-60, show_label=False),
                                     Item('resubmit_button', width=-60, show_label=False),
                                     Item('get_global_vars_button', show_label=False),
                                     Item('priority', width=-30),
                                     Item('state', style='readonly'),
                                     Item('run_time', style='readonly', format_str='%.f'),
                                     Item('stop_time', format_str='%.f'),
                                     Item('stop_counts'),
                                     ),
                              HGroup(Item('filename', springy=True),
                                     Item('save_button', show_label=False),
                                     Item('load_button', show_label=False),
                                     Item('periodic_save'),
                                     Item('save_interval', enabled_when='not periodic_save'),
                                     ),
                              Tabbed(VGroup(HGroup(Item('laser', width=-80,
                                                        enabled_when='state != "run"'),
                                                   Item('decay_init', width=-80,
                                                        enabled_when='state != "run"'),
                                                   Item('decay_read', width=-80,
                                                        enabled_when='state != "run"'),
                                                   ),
                                            HGroup(Item('mw_frequency', width=-120,
                                                        enabled_when='state != "run"'),
                                                   Item('mw_power', width=-60,
                                                        enabled_when='state != "run"'),
                                                   ),
                                            HGroup(Item('mw_x_t_pi2', width=-80,
                                                        enabled_when='state != "run"'),
                                                   Item('mw_x_t_pi', width=-80,
                                                        enabled_when='state != "run"'),
                                                   Item('mw_y_t_pi', width=-80,
                                                        enabled_when='state != "run"'),
                                                   Item('mw_x_t_3pi2', width=-80,
                                                        enabled_when='state != "run"'),
                                                   ),
                                            HGroup(Item('decoupling_order', width=-80,
                                                        enabled_when='state != "run"'),
                                                   Item('mw_tau', width=-80,
                                                        enabled_when='state != "run"'),
                                                   ),
                                            HGroup(Item('rf_frequency', width=-120,
                                                        enabled_when='state != "run"'),
                                                   Item('rf_power', width=-80,
                                                        enabled_when='state != "run"'),
                                                   Item('rf_pulse_delay', width=-80,
                                                        enabled_when='state != "run"'),
                                                   ),
                                            HGroup(Item('tau_begin', width=-80,
                                                        enabled_when='state != "run"'),
                                                   Item('tau_end', width=-80,
                                                        enabled_when='state != "run"'),
                                                   Item('tau_delta', width=-80,
                                                        enabled_when='state != "run"'),
                                                   ),
                                            label='stimulation'),
                                     VGroup(HGroup(Item('record_length', width=-80,
                                                        enabled_when='state != "run"'),
                                                   Item('bin_width', width=-80,
                                                        enabled_when='state != "run"'),
                                                   ),
                                            label='acquisition'),
                                     VGroup(HGroup(Item('integration_width'),
                                                   Item('position_signal'),
                                                   Item('position_normalize'),
                                                   ),
                                            label='analysis'),
                                     ),
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
                              Tabbed(Item('line_plot', show_label=False, width=500, height=-300,
                                          resizable=True),
                                     Item('matrix_plot', show_label=False, width=500, height=-300,
                                          resizable=True),
                                     Item('pulse_plot', show_label=False, width=500, height=-300,
                                          resizable=True),
                                     ),
                              ),
                       title='Pi3diamond: DEER Rabi',
                       resizable=True,
                       buttons=[],
                       )


class DEERRabiDQT(DEERDQT):
    """Defines a DEER Rabi Measurement utilizing the Double Quantum Transition.

    So far we will only use a 'simple' DQT Hahn sequence to measure DEER Signals. Furthermore we
    will use a successive sequences, that do single pulses on both transitions to generate the mixed
    state between |-1> and |1>.
    """

    def generate_sequence(self):
        """Generate the sequence for a DQ-DEER Rabi measurement

        :return: sequence string.
        """
        tau = self.tau
        decay_init = self.decay_init
        laser = self.laser

        # Values for the NV center DQT:
        mw_tau = self.mw_tau
        mw_x_t_pi2 = self.mw_x_t_pi2
        mw_x_t_pi = self.mw_x_t_pi
        mw_x_t_3pi2 = self.mw_x_t_3pi2
        mw2_x_t_pi = self.mw2_x_t_pi
        ip_delay = self.interpulse_delay

        # Defining the RF sequence:
        rf_pulse_delay = float(self.rf_pulse_delay)

        # check, if the start time is long enough to fit at least the mw+rf pulses in it.
        t_max = tau.max()
        if mw_tau * 0.5 - rf_pulse_delay - t_max < 0:
            raise IOError('The delay between pulses is too short. It has to be larger than the'
                          'combined pulse duration')

        sequence = []
        for t in tau:
            sequence += [(['microwave'], mw_x_t_pi2), ([], ip_delay),
                         (['microwave2'], mw2_x_t_pi),
                         ([], 0.5 * mw_tau),
                         (['microwave2'], mw2_x_t_pi), ([], ip_delay), (['microwave'], mw_x_t_pi),
                         ([], ip_delay), (['microwave2'], mw2_x_t_pi),
                         ([], rf_pulse_delay), (['rf'], t),
                         ([], 0.5 * mw_tau - t - rf_pulse_delay),
                         (['microwave2'], mw2_x_t_pi), ([], ip_delay), (['microwave'], mw_x_t_pi2),
                         (['detect', 'aom'], laser), ([], decay_init)]
        for t in tau:
            sequence += [(['microwave'], mw_x_t_pi2), ([], ip_delay),
                         (['microwave2'], mw2_x_t_pi),
                         ([], 0.5 * mw_tau),
                         (['microwave2'], mw2_x_t_pi), ([], ip_delay), (['microwave'], mw_x_t_pi),
                         ([], ip_delay), (['microwave2'], mw2_x_t_pi),
                         ([], rf_pulse_delay), (['rf'], t),
                         ([], 0.5 * mw_tau - t - rf_pulse_delay),
                         (['microwave2'], mw2_x_t_pi), ([], ip_delay), (['microwave'], mw_x_t_3pi2),
                         (['detect', 'aom'], laser), ([], decay_init)]
        sequence += [(['sequence'], 100)]

        # Removing zeros from sequences:
        sequence = sequence_remove_zeros(sequence)

        sequence *= 100
        return sequence

    def _create_line_plot(self):
        line_data = ArrayPlotData(index=np.array((0, 1)),
                                  state_first_seq=np.array((0, 0)),
                                  state_second_seq=np.array((0, 0)),
                                  state_difference=np.array((0, 0)),
                                  fit=np.array((0, 0))
                                  )
        plot = Plot(line_data, padding=8, padding_left=64, padding_bottom=36)
        plot.plot(('index', 'state_first_seq'), color='blue', name='state_first_seq')
        plot.plot(('index', 'state_second_seq'), color='green', name='state_second_seq')
        plot.plot(('index', 'state_difference'), color='black', name='state_difference',
                  line_width=2)
        plot.plot(('index', 'fit'), color='red', name='state_difference', line_width=2)
        plot.index_axis.title = 'time [micro s]'
        plot.value_axis.title = 'spin state'
        plot.tools.append(SaveTool(plot))
        self.line_data = line_data
        self.line_plot = plot

    def _update_line_plot_value(self):
        y = self.spin_state
        n = len(self.tau)
        first = y[:n]
        second = y[n:2 * n]
        spin_state_difference = (first - second) + (first.max() + second.min()) / 2.
        try:
            self.line_data.set_data('state_first_seq', first)
            self.line_data.set_data('state_second_seq', second)
            self.line_data.set_data('state_difference', spin_state_difference)
        except:
            logging.getLogger().debug('Could not set data for spin_state plots.')

    def _update_fit(self):
        n = len(self.tau)
        first = self.spin_state[:n]
        second = self.spin_state[n:2 * n]
        y = (first - second) + (first.max() + second.min()) / 2.
        try:
            fit_result = fitting.fit_rabi(self.tau, y, y ** 0.5)
        except:
            fit_result = (np.nan * np.zeros(3), np.nan * np.zeros((3, 3)), np.nan, np.nan)

        p, v, q, chisqr = fit_result
        a, T, x0, c = p
        a_var, T_var, x0_var, c_var = v.diagonal()

        # compute some relevant parameters from fit result
        contrast = 200 * a / (c + a)
        contrast_delta = 200. / c ** 2 * (a_var * c ** 2 + c_var * a ** 2) ** 0.5
        T_delta = abs(T_var) ** 0.5
        pi2 = 0.25 * T + x0
        pi = 0.5 * T + x0
        threepi2 = 0.75 * T + x0
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

    traits_view = View(VGroup(HGroup(Item('submit_button', width=-60, show_label=False),
                                     Item('remove_button', width=-60, show_label=False),
                                     Item('resubmit_button', width=-60, show_label=False),
                                     Item('get_global_vars_button', show_label=False),
                                     Item('priority', width=-30),
                                     Item('state', style='readonly'),
                                     Item('run_time', style='readonly', format_str='%.f'),
                                     Item('stop_time', format_str='%.f'),
                                     Item('stop_counts'),
                                     ),
                              HGroup(Item('filename', springy=True),
                                     Item('save_button', show_label=False),
                                     Item('load_button', show_label=False),
                                     Item('periodic_save'),
                                     Item('save_interval', enabled_when='not periodic_save'),
                                     ),
                              Tabbed(VGroup(HGroup(Item('laser', width=-80,
                                                        enabled_when='state != "run"'),
                                                   Item('decay_init', width=-80,
                                                        enabled_when='state != "run"'),
                                                   Item('decay_read', width=-80,
                                                        enabled_when='state != "run"'),
                                                   ),
                                            HGroup(Item('mw_frequency', width=-120,
                                                        enabled_when='state != "run"'),
                                                   Item('mw_power', width=-60,
                                                        enabled_when='state != "run"'),
                                                   Item('mw_x_t_pi2', width=-80,
                                                        enabled_when='state != "run"'),
                                                   Item('mw_x_t_pi', width=-80,
                                                        enabled_when='state != "run"'),
                                                   Item('mw_y_t_pi', width=-80,
                                                        enabled_when='state != "run"'),
                                                   Item('mw_x_t_3pi2', width=-80,
                                                        enabled_when='state != "run"'),
                                                   Item('mw_tau', width=-80,
                                                        enabled_when='state != "run"'),
                                                   ),
                                            HGroup(Item('mw2_power', width=-40,
                                                        enabled_when='state != "run"'),
                                                   Item('mw2_frequency', width=-80,
                                                        enabled_when='state != "run"'),
                                                   Item('mw2_x_t_pi', width=-40,
                                                        enabled_when='state != "run"'),
                                                   ),
                                            HGroup(Item('rf_frequency', width=-120,
                                                        enabled_when='state != "run"'),
                                                   Item('rf_power', width=-80,
                                                        enabled_when='state != "run"'),
                                                   Item('rf_pulse_delay', width=-80,
                                                        enabled_when='state != "run"'),
                                                   ),
                                            HGroup(Item('tau_begin', width=-80,
                                                        enabled_when='state != "run"'),
                                                   Item('tau_end', width=-80,
                                                        enabled_when='state != "run"'),
                                                   Item('tau_delta', width=-80,
                                                        enabled_when='state != "run"'),
                                                   ),
                                            label='stimulation'),
                                     VGroup(HGroup(Item('record_length', width=-80,
                                                        enabled_when='state != "run"'),
                                                   Item('bin_width', width=-80,
                                                        enabled_when='state != "run"'),
                                                   ),
                                            label='acquisition'),
                                     VGroup(HGroup(Item('integration_width'),
                                                   Item('position_signal'),
                                                   Item('position_normalize'),
                                                   ),
                                            label='analysis'),
                                     ),
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
                              Tabbed(Item('line_plot', show_label=False, width=500, height=-300,
                                          resizable=True),
                                     Item('matrix_plot', show_label=False, width=500, height=-300,
                                          resizable=True),
                                     Item('pulse_plot', show_label=False, width=500, height=-300,
                                          resizable=True),
                                     ),
                              ),
                       title='Pi3diamond: DEER-DQT Rabi',
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
