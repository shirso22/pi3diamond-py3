__author__ = 'Lukas Schlipf'
"""
Module to do DEER correlation spectroscopy.
TODO: Various methods are implied, i.e. dark spin T1, dark spin Rabi etc. measurements.
"""

import time

import numpy as np
from chaco.api import ArrayPlotData
from traits.api import Range, Int, Float
from traitsui.api import View, Item, Tabbed, HGroup, VGroup, TextEditor

from measurements.rabi import Rabi
from .pulsed import sequence_remove_zeros
from tools.chaco_addons import SavePlot as Plot, SaveTool


class DEER_correlation(Rabi):
    """Class for correlation measurements on an electron spin.

    """
    double_sequence = True

    power_imbalance = Range(low=-1., high=1., value=0., desc='microwave power imbalance',
                            label='power imbalance [dBm]', mode='text', auto_set=False,
                            enter_set=True)
    n_sequences = Int(default_value=0, desc='number of XY_8-Sequences', label='n_seq', mode='text',
                      auto_set=False, enter_set=True)
    mw_tau = Float(default_value=2000, desc='time between pi pulses[ns]', label='mw_tau [ns]',
                   mode='text', auto_set=False, enter_set=True)

    """"Values that define the RF e-Spin excitation in the DEER sequence."""
    rf_frequency = Range(low=10.e6, high=3000.e6, value=220.e6, desc='RF frequency',
                         label='RF frequency [Hz]', mode='text', auto_set=False, enter_set=True,
                         editor=TextEditor(auto_set=False, enter_set=True, evaluate=float,
                                           format_str='%e')
                         )
    rf_power = Range(low=-40., high=12., value=-4., desc='rf power',
                     label='RF Power [dBm]', mode='text', auto_set=False, enter_set=True)
    rf_t_pi = Float(default_value=100., desc='length of pi pulse of RF[ns]', label='RF pi [ns]',
                    mode='text', auto_set=False, enter_set=True)
    rf_pulse_delay = Float(default_value=15., desc='wait between mw and rf pulse[ns]',
                           label='RF wait [ns]', mode='text', auto_set=False, enter_set=True)

    def __init__(self, pulse_generator, time_tagger, microwave, rf, **kwargs):
        super(DEER_correlation, self).__init__(pulse_generator, time_tagger, microwave, **kwargs)
        self.rf = rf

    def start_up(self):
        self.pulse_generator.Night()
        self.microwave.setOutput(self.mw_power, self.mw_frequency)
        time.sleep(0.1)
        self.rf.setFrequency(self.rf_frequency)
        time.sleep(0.1)
        self.rf.setPower(self.rf_power)

    def shut_down(self):
        self.pulse_generator.Light()
        self.microwave.setOutput(-40, self.mw_frequency)
        time.sleep(0.1)
        self.rf.setPower(-40)

    def generate_sequence(self):
        mw_tau = self.mw_tau
        laser = self.laser
        n = self.n_sequences
        decay_init = self.decay_init

        mw_x_t_pi2 = self.mw_x_t_pi2
        mw_x_t_pi = self.mw_x_t_pi
        mw_x_t_3pi2 = self.mw_x_t_3pi2
        mw_y_t_pi2 = self.mw_y_t_pi2
        mw_y_t_pi = self.mw_y_t_pi
        mw_y_t_3pi2 = self.mw_y_t_3pi2

        rf_pulse_delay = self.rf_pulse_delay
        rf_t_pi = self.rf_t_pi

        if n == 0:
            """
            In this case use hahn echo with an rf in between.
            mw_tau corresponds twice the time between the pi2 and pi pulse of the mw.
            For the Correlation Spectroscopy we use a variable time PulsedTau.tau to vary the time
            between two DEER sequences. (See Sushkov et al., PRL 113 (2014))
            """
            if rf_pulse_delay >= 0.0:
                sequence1_deer = [(['mw_x'], mw_x_t_pi2), ([], (0.5 * mw_tau)),
                                  (['mw_y'], mw_y_t_pi),
                                  ([], rf_pulse_delay), (['rf'], rf_t_pi),
                                  ([], (0.5 * mw_tau) - rf_pulse_delay - rf_t_pi),
                                  (['mw_y'], mw_y_t_pi2)]
                sequence2_deer = [(['mw_x'], mw_x_t_pi2), ([], (0.5 * mw_tau)),
                                  (['mw_y'], mw_y_t_pi),
                                  ([], rf_pulse_delay), (['rf'], rf_t_pi),
                                  ([], (0.5 * mw_tau) - rf_pulse_delay - rf_t_pi),
                                  (['mw_y'], mw_y_t_3pi2)]
            if rf_pulse_delay < 0.0:
                rf_pulse_delay = abs(rf_pulse_delay)
                sequence1_deer = [(['mw_x'], mw_x_t_pi2),
                                  ([], (0.5 * mw_tau) - rf_pulse_delay - rf_t_pi),
                                  (['rf'], rf_t_pi), ([], rf_pulse_delay),
                                  (['mw_y'], mw_y_t_pi), ([], (0.5 * mw_tau)),
                                  (['mw_y'], mw_y_t_pi2)]
                sequence2_deer = [(['mw_x'], mw_x_t_pi2),
                                  ([], (0.5 * mw_tau) - rf_pulse_delay - rf_t_pi),
                                  (['rf'], rf_t_pi), ([], rf_pulse_delay),
                                  (['mw_y'], mw_y_t_pi), ([], (0.5 * mw_tau)),
                                  (['mw_y'], mw_y_t_3pi2)]
            sequence = []
            for t in self.tau:
                sequence += sequence1_deer + \
                            [([], t)] + \
                            sequence1_deer + \
                            [(['detect', 'aom'], laser), ([], decay_init)]
            for t in self.tau:
                sequence += sequence1_deer + \
                            [([], t)] + \
                            sequence2_deer + \
                            [(['detect', 'aom'], laser), ([], decay_init)]
        else:
            """In this case we do xy8_n-DD, with an rf pulse in between each mw_tau
            mw_tau corresponds to the time/8*n the sequence takes. This time is used in NMR analysis
            and since our xy8 measurements are using this time we use it here as well.
            """
            # t is the time between the infinitely short xy8 pulses
            t = mw_tau / (8. * n)
            # This lambda function gives correct mw_tau for the approximation of infinetly short pulses
            t_bar = lambda t, p1, p2=0., p3=0., p4=0.: t - (p1 / 2.) - (p2 / 2.) - p3 - p4
            # check, if the start time is long enough to fit at least the mw pulses in it.
            if t_bar(t, mw_y_t_pi, mw_y_t_pi, rf_pulse_delay, rf_t_pi) < 0 or t_bar(t, mw_x_t_pi,
                                                                                    mw_x_t_pi,
                                                                                    rf_pulse_delay,
                                                                                    rf_t_pi) < 0:
                raise IOError(
                    'The delay between pulses is too short.'
                    'It has to be larger than the pulse_duration')
            # Here, a negative rf pulse delay makes no sense.
            if rf_pulse_delay < 0.0:
                rf_pulse_delay = abs(rf_pulse_delay)

            """
            Build the signal sequence, i.e. the spin state with applied rf at a specific mw_tau with
            xy8 decoupling.
            """
            sequence1_deer = []
            sequence2_deer = []

            xy_8_rf_part = []
            start = []
            end_pi2 = []
            end_3pi2 = []
            init = [(['detect', 'aom'], laser), ([], decay_init)]

            xy_8_rf_part += [(['mw_x'], mw_x_t_pi), ([], rf_pulse_delay), (['rf'], rf_t_pi),
                             ([], t_bar(t, mw_x_t_pi, mw_y_t_pi, rf_pulse_delay, rf_t_pi))]
            xy_8_rf_part += [(['mw_y'], mw_y_t_pi), ([], rf_pulse_delay), (['rf'], rf_t_pi),
                             ([], t_bar(t, mw_x_t_pi, mw_y_t_pi, rf_pulse_delay, rf_t_pi))]
            xy_8_rf_part += [(['mw_x'], mw_x_t_pi), ([], rf_pulse_delay), (['rf'], rf_t_pi),
                             ([], t_bar(t, mw_x_t_pi, mw_y_t_pi, rf_pulse_delay, rf_t_pi))]
            xy_8_rf_part += [(['mw_y'], mw_y_t_pi), ([], rf_pulse_delay), (['rf'], rf_t_pi),
                             ([], t_bar(t, mw_y_t_pi, mw_y_t_pi, rf_pulse_delay, rf_t_pi))]
            xy_8_rf_part += [(['mw_y'], mw_y_t_pi), ([], rf_pulse_delay), (['rf'], rf_t_pi),
                             ([], t_bar(t, mw_x_t_pi, mw_y_t_pi, rf_pulse_delay, rf_t_pi))]
            xy_8_rf_part += [(['mw_x'], mw_x_t_pi), ([], rf_pulse_delay), (['rf'], rf_t_pi),
                             ([], t_bar(t, mw_x_t_pi, mw_y_t_pi, rf_pulse_delay, rf_t_pi))]
            xy_8_rf_part += [(['mw_y'], mw_y_t_pi), ([], rf_pulse_delay), (['rf'], rf_t_pi),
                             ([], t_bar(t, mw_x_t_pi, mw_y_t_pi, rf_pulse_delay, rf_t_pi))]
            xy_8_rf_part += [(['mw_x'], mw_x_t_pi)]

            start = [(['mw_x'], mw_x_t_pi2), ([], rf_pulse_delay), (['rf'], rf_t_pi),
                     ([], t_bar(t / 2., mw_x_t_pi, p3=rf_pulse_delay, p4=rf_t_pi))]
            end_pi2 = [([], t_bar(t, mw_x_t_pi) / 2. - rf_pulse_delay - rf_t_pi),
                       (['mw_x'], mw_x_t_pi2)]
            end_3pi2 = [([], t_bar(t, mw_x_t_pi) / 2. - rf_pulse_delay - rf_t_pi),
                        (['mw_x'], mw_x_t_3pi2)]

            # build the sequences
            sequence1_deer += start + (
                    (n - 1) * (xy_8_rf_part + [
                ([], t_bar(t, mw_x_t_pi, mw_y_t_pi))])) + xy_8_rf_part + end_pi2
            sequence2_deer += start + (
                    (n - 1) * (xy_8_rf_part + [
                ([], t_bar(t, mw_x_t_pi, mw_y_t_pi))])) + xy_8_rf_part + end_3pi2

            # join the two sequences
            sequence = []
            for t in self.tau:
                sequence += sequence1_deer + \
                            [([], t)] + \
                            sequence1_deer + init
            for t in self.tau:
                sequence += sequence2_deer + \
                            [([], t)] + \
                            sequence2_deer + init

        # tail of the sequence
        sequence = sequence + [(['sequence'], 100)]
        sequence = sequence_remove_zeros(sequence)

        return sequence

    get_set_items = Rabi.get_set_items + ['mw_tau', 'n_sequences', 'power_imbalance',
                                          'mw_x_t_pi2', 'mw_x_t_pi', 'mw_x_t_3pi2',
                                          'mw_y_t_pi2', 'mw_y_t_pi', 'mw_y_t_3pi2',
                                          'rf_frequency', 'rf_power', 'rf_t_pi', 'rf_pulse_delay']

    traits_view = View(VGroup(HGroup(Item('submit_button', show_label=False),
                                     Item('remove_button', show_label=False),
                                     Item('resubmit_button', show_label=False),
                                     Item('get_global_vars_button', show_label=False),
                                     Item('priority'),
                                     Item('state', style='readonly'),
                                     Item('run_time', style='readonly', format_str='%.f',
                                          width=-60),
                                     Item('stop_time', format_str='%.f', width=-60),
                                     Item('stop_counts', width=-60),
                                     ),
                              HGroup(Item('filename', springy=True),
                                     Item('save_button', show_label=False),
                                     Item('load_button', show_label=False),
                                     Item('periodic_save'),
                                     Item('save_interval', enabled_when='not periodic_save'),
                                     ),
                              Tabbed(VGroup(HGroup(
                                  Item('mw_frequency', width=-120, enabled_when='state != "run"'),
                                  Item('mw_power', width=-60, enabled_when='state != "run"'),
                              ),
                                  HGroup(Item('laser', width=-80,
                                              enabled_when='state != "run"'),
                                         Item('decay_init', width=-80,
                                              enabled_when='state != "run"'),
                                         ),
                                  HGroup(Item('n_sequences', width=-80,
                                              enabled_when='state != "run"'),
                                         Item('mw_tau', width=-80,
                                              enabled_when='state != "run"'), ),
                                  HGroup(Item('mw_x_t_pi2', width=-80,
                                              enabled_when='state != "run"'),
                                         Item('mw_x_t_pi', width=-80,
                                              enabled_when='state != "run"'),
                                         Item('mw_x_t_3pi2', width=-80,
                                              enabled_when='state != "run"'), ),
                                  HGroup(Item('mw_y_t_pi2', width=-80,
                                              enabled_when='state != "run"'),
                                         Item('mw_y_t_pi', width=-80,
                                              enabled_when='state != "run"'),
                                         Item('mw_y_t_3pi2', width=-80,
                                              enabled_when='state != "run"'), ),
                                  HGroup(Item('rf_frequency', width=-120,
                                              enabled_when='state != "run"'),
                                         Item('rf_power', width=-80,
                                              enabled_when='state != "run"'),
                                         Item('rf_t_pi', width=-80,
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
                                  label='acquisition'),
                                  VGroup(HGroup(Item('integration_width'),
                                                Item('position_signal'),
                                                Item('position_normalize'),
                                                ),
                                         label='analysis'),
                              ),
                              Tabbed(Item('line_plot', show_label=False, width=500, height=-300,
                                          resizable=True),
                                     Item('matrix_plot', show_label=False, width=500, height=-300,
                                          resizable=True),
                                     Item('pulse_plot', show_label=False, width=500, height=-300,
                                          resizable=True),
                                     ),
                              ),
                       title='Pi3diamond: DEER Correlation',
                       buttons=[],
                       resizable=True,
                       )


class DarkSpin_Rabi(DEER_correlation):
    """
    Use DEER correlation to perform a Rabi Measurement on the external Dark Spin.
    """
    tau_evo = Float(default_value=1000., desc='tau for free evolution',
                    label='evolution tau [ns]', mode='text', auto_set=False, enter_set=True)
    pi_offset_evo = Float(default_value=12., desc='evolution pi offset',
                          label='evolution pi offset [ns]', mode='text', auto_set=False,
                          enter_set=True)

    def generate_sequence(self):
        mw_tau = self.mw_tau
        laser = self.laser
        n = self.n_sequences
        decay_init = self.decay_init

        mw_x_t_pi2 = self.mw_x_t_pi2
        mw_x_t_pi = self.mw_x_t_pi
        mw_x_t_3pi2 = self.mw_x_t_3pi2
        mw_y_t_pi2 = self.mw_y_t_pi2
        mw_y_t_pi = self.mw_y_t_pi
        mw_y_t_3pi2 = self.mw_y_t_3pi2

        rf_pulse_delay = self.rf_pulse_delay
        rf_t_pi = self.rf_t_pi

        tau_evo = self.tau_evo
        pi_offset_evo = self.pi_offset_evo

        if n == 0:
            """
            In this case use hahn echo with an rf in between.
            mw_tau corresponds twice the time between the pi2 and pi pulse of the mw.
            For the Correlation Spectroscopy we use a dark spin pi-RF pulse and a variable time
            PulsedTau.tau to vary the time when it is applied in between the DEER sequences. The
            total dark spin free evolution time stays fixed (See Sushkov et al., PRL 113 (2014))
            """
            if rf_pulse_delay >= 0.0:
                sequence1_deer = [(['mw_x'], mw_x_t_pi2), ([], (0.5 * mw_tau)),
                                  (['mw_y'], mw_y_t_pi),
                                  ([], rf_pulse_delay), (['rf'], rf_t_pi),
                                  ([], (0.5 * mw_tau) - rf_pulse_delay - rf_t_pi),
                                  (['mw_y'], mw_y_t_pi2)]
                sequence2_deer = [(['mw_x'], mw_x_t_pi2), ([], (0.5 * mw_tau)),
                                  (['mw_y'], mw_y_t_pi),
                                  ([], rf_pulse_delay), (['rf'], rf_t_pi),
                                  ([], (0.5 * mw_tau) - rf_pulse_delay - rf_t_pi),
                                  (['mw_y'], mw_y_t_3pi2)]
            if rf_pulse_delay < 0.0:
                rf_pulse_delay = abs(rf_pulse_delay)
                sequence1_deer = [(['mw_x'], mw_x_t_pi2),
                                  ([], (0.5 * mw_tau) - rf_pulse_delay - rf_t_pi),
                                  (['rf'], rf_t_pi), ([], rf_pulse_delay),
                                  (['mw_y'], mw_y_t_pi), ([], (0.5 * mw_tau)),
                                  (['mw_y'], mw_y_t_pi2)]
                sequence2_deer = [(['mw_x'], mw_x_t_pi2),
                                  ([], (0.5 * mw_tau) - rf_pulse_delay - rf_t_pi),
                                  (['rf'], rf_t_pi), ([], rf_pulse_delay),
                                  (['mw_y'], mw_y_t_pi), ([], (0.5 * mw_tau)),
                                  (['mw_y'], mw_y_t_3pi2)]
            sequence = []
            for t in self.tau:
                sequence += sequence1_deer + \
                            [([], pi_offset_evo)] + \
                            [(['rf'], t)] + \
                            [([], tau_evo - pi_offset_evo - t)] + \
                            sequence1_deer + \
                            [(['detect', 'aom'], laser), ([], decay_init)]
            for t in self.tau:
                sequence += sequence1_deer + \
                            [([], pi_offset_evo)] + \
                            [(['rf'], t)] + \
                            [([], tau_evo - pi_offset_evo - t)] + \
                            sequence2_deer + \
                            [(['detect', 'aom'], laser), ([], decay_init)]
        else:
            """In this case we do xy8_n-DD, with an rf pulse in between each mw_tau
            mw_tau corresponds to the time/8*n the sequence takes. This time is used in NMR analysis
            and since our xy8 measurements are using this time we use it here as well.
            """
            # t is the time between the infinitely short xy8 pulses
            t = mw_tau / (8. * n)
            # This lambda function gives correct mw_tau for the approximation of infinitely short
            # pulses
            t_bar = lambda t, p1, p2=0., p3=0., p4=0.: t - (p1 / 2.) - (p2 / 2.) - p3 - p4
            # check, if the start time is long enough to fit at least the mw pulses in it.
            if t_bar(t, mw_y_t_pi, mw_y_t_pi, rf_pulse_delay, rf_t_pi) < 0 or t_bar(t, mw_x_t_pi,
                                                                                    mw_x_t_pi,
                                                                                    rf_pulse_delay,
                                                                                    rf_t_pi) < 0:
                raise IOError(
                    'The delay between pulses is too short.'
                    'It has to be larger than the pulse_duration')
            # Here, a negative rf pulse delay makes no sense.
            if rf_pulse_delay < 0.0:
                rf_pulse_delay = abs(rf_pulse_delay)

            """
            Build the signal sequence, i.e. the spin state with applied rf at a specific mw_tau with
            xy8 decoupling.
            """
            sequence1_deer = []
            sequence2_deer = []

            xy_8_rf_part = []
            start = []
            end_pi2 = []
            end_3pi2 = []
            init = [(['detect', 'aom'], laser), ([], decay_init)]

            xy_8_rf_part += [(['mw_x'], mw_x_t_pi), ([], rf_pulse_delay), (['rf'], rf_t_pi),
                             ([], t_bar(t, mw_x_t_pi, mw_y_t_pi, rf_pulse_delay, rf_t_pi))]
            xy_8_rf_part += [(['mw_y'], mw_y_t_pi), ([], rf_pulse_delay), (['rf'], rf_t_pi),
                             ([], t_bar(t, mw_x_t_pi, mw_y_t_pi, rf_pulse_delay, rf_t_pi))]
            xy_8_rf_part += [(['mw_x'], mw_x_t_pi), ([], rf_pulse_delay), (['rf'], rf_t_pi),
                             ([], t_bar(t, mw_x_t_pi, mw_y_t_pi, rf_pulse_delay, rf_t_pi))]
            xy_8_rf_part += [(['mw_y'], mw_y_t_pi), ([], rf_pulse_delay), (['rf'], rf_t_pi),
                             ([], t_bar(t, mw_y_t_pi, mw_y_t_pi, rf_pulse_delay, rf_t_pi))]
            xy_8_rf_part += [(['mw_y'], mw_y_t_pi), ([], rf_pulse_delay), (['rf'], rf_t_pi),
                             ([], t_bar(t, mw_x_t_pi, mw_y_t_pi, rf_pulse_delay, rf_t_pi))]
            xy_8_rf_part += [(['mw_x'], mw_x_t_pi), ([], rf_pulse_delay), (['rf'], rf_t_pi),
                             ([], t_bar(t, mw_x_t_pi, mw_y_t_pi, rf_pulse_delay, rf_t_pi))]
            xy_8_rf_part += [(['mw_y'], mw_y_t_pi), ([], rf_pulse_delay), (['rf'], rf_t_pi),
                             ([], t_bar(t, mw_x_t_pi, mw_y_t_pi, rf_pulse_delay, rf_t_pi))]
            xy_8_rf_part += [(['mw_x'], mw_x_t_pi)]

            start = [(['mw_x'], mw_x_t_pi2), ([], rf_pulse_delay), (['rf'], rf_t_pi),
                     ([], t_bar(t / 2., mw_x_t_pi, p3=rf_pulse_delay, p4=rf_t_pi))]
            end_pi2 = [([], t_bar(t, mw_x_t_pi) / 2. - rf_pulse_delay - rf_t_pi),
                       (['mw_x'], mw_x_t_pi2)]
            end_3pi2 = [([], t_bar(t, mw_x_t_pi) / 2. - rf_pulse_delay - rf_t_pi),
                        (['mw_x'], mw_x_t_3pi2)]

            # build the sequences
            sequence1_deer += start + (
                    (n - 1) * (xy_8_rf_part + [
                ([], t_bar(t, mw_x_t_pi, mw_y_t_pi))])) + xy_8_rf_part + end_pi2
            sequence2_deer += start + (
                    (n - 1) * (xy_8_rf_part + [
                ([], t_bar(t, mw_x_t_pi, mw_y_t_pi))])) + xy_8_rf_part + end_3pi2

            # join the two sequences
            sequence = []
            for t in self.tau:
                sequence += sequence1_deer + \
                            [([], tau_evo - pi_offset_evo - t)] + \
                            [(['rf'], t)] + \
                            [([], pi_offset_evo)] + \
                            sequence1_deer + init
            for t in self.tau:
                sequence += sequence1_deer + \
                            [([], tau_evo - pi_offset_evo - t)] + \
                            [(['rf'], t)] + \
                            [([], pi_offset_evo)] + \
                            sequence2_deer + init

        # tail of the sequence
        sequence = sequence + [(['sequence'], 100)]
        sequence = sequence_remove_zeros(sequence)

        return sequence

    get_set_items = DEER_correlation.get_set_items + ['tau_evo', 'pi_offset_evo']

    traits_view = View(VGroup(HGroup(Item('submit_button', show_label=False),
                                     Item('remove_button', show_label=False),
                                     Item('resubmit_button', show_label=False),
                                     Item('get_global_vars_button', show_label=False),
                                     Item('priority'),
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
                              Tabbed(VGroup(HGroup(
                                  Item('mw_frequency', width=-120, enabled_when='state != "run"'),
                                  Item('mw_power', width=-60, enabled_when='state != "run"'),
                              ),
                                  HGroup(Item('laser', width=-80,
                                              enabled_when='state != "run"'),
                                         Item('decay_init', width=-80,
                                              enabled_when='state != "run"'),
                                         ),
                                  HGroup(Item('n_sequences', width=-80,
                                              enabled_when='state != "run"'),
                                         Item('mw_tau', width=-80,
                                              enabled_when='state != "run"'), ),
                                  HGroup(Item('mw_x_t_pi2', width=-80,
                                              enabled_when='state != "run"'),
                                         Item('mw_x_t_pi', width=-80,
                                              enabled_when='state != "run"'),
                                         Item('mw_x_t_3pi2', width=-80,
                                              enabled_when='state != "run"'), ),
                                  HGroup(Item('mw_y_t_pi2', width=-80,
                                              enabled_when='state != "run"'),
                                         Item('mw_y_t_pi', width=-80,
                                              enabled_when='state != "run"'),
                                         Item('mw_y_t_3pi2', width=-80,
                                              enabled_when='state != "run"'), ),
                                  HGroup(Item('rf_frequency', width=-120,
                                              enabled_when='state != "run"'),
                                         Item('rf_power', width=-80,
                                              enabled_when='state != "run"'),
                                         Item('rf_t_pi', width=-80,
                                              enabled_when='state != "run"'),
                                         Item('rf_pulse_delay', width=-80,
                                              enabled_when='state != "run"'),
                                         ),
                                  HGroup(Item('tau_evo', width=-80,
                                              enabled_when='state != "run"'),
                                         Item('pi_offset_evo', width=-80,
                                              enabled_when='state != "run"'),
                                         ),
                                  HGroup(Item('tau_begin', width=-80,
                                              enabled_when='state != "run"'),
                                         Item('tau_end', width=-80,
                                              enabled_when='state != "run"'),
                                         Item('tau_delta', width=-80,
                                              enabled_when='state != "run"'),
                                         ),
                                  label='acquisition'),
                                  VGroup(HGroup(Item('integration_width'),
                                                Item('position_signal'),
                                                Item('position_normalize'),
                                                ),
                                         label='analysis'),
                              ),
                              Tabbed(Item('line_plot', show_label=False, width=500, height=-300,
                                          resizable=True),
                                     Item('matrix_plot', show_label=False, width=500, height=-300,
                                          resizable=True),
                                     Item('pulse_plot', show_label=False, width=500, height=-300,
                                          resizable=True),
                                     ),
                              ),
                       title='Pi3diamond: DEER Correlation Rabi',
                       )


class DarkSpin_T1(DEER_correlation):
    """
    Use DEER correlation measurements to determine the Dark Spin T1
    """
    # Values that define the sequence applied during dark spin free evolution
    rf_evo_delay = Float(default_value=15., desc='rf delay in free evolution',
                         label='tau rf offset [ns]', mode='text', auto_set=False, enter_set=True)
    rf_evo_t_pi = Float(default_value=100., desc='length of RF pi pulse during free evolution [ns]',
                        label='RF pi evolution [ns]', mode='text', auto_set=False, enter_set=True)

    def generate_sequence(self):
        """Generate the sequence to measure a T1 decay of an external spin.

        As regular for such lengthy measurements, we use a logarithmic tau array, saving greatly in
        measurement time, yet loosing a bit of information (phase oscillations).
        :return: np.array containing sequence for pulse_generator
        """
        # overwrite tau with logarithmic spacing
        self.tau = np.logspace(np.log10(self.tau_begin), np.log10(self.tau_end + self.tau_delta),
                               self.tau_delta)

        mw_tau = self.mw_tau
        laser = self.laser
        n = self.n_sequences
        decay_init = self.decay_init

        mw_x_t_pi2 = self.mw_x_t_pi2
        mw_x_t_pi = self.mw_x_t_pi
        mw_x_t_3pi2 = self.mw_x_t_3pi2
        mw_y_t_pi2 = self.mw_y_t_pi2
        mw_y_t_pi = self.mw_y_t_pi

        rf_pulse_delay = self.rf_pulse_delay
        rf_t_pi = self.rf_t_pi

        rf_evo_delay = self.rf_evo_delay
        rf_evo_t_pi = self.rf_evo_t_pi

        if n == 0:
            """
            In this case use hahn echo with an rf in between.
            mw_tau corresponds twice the time between the pi2 and pi pulse of the mw.
            For the Correlation Spectroscopy we use a dark spin pi-RF pulse and a variable time
            PulsedTau.tau to vary the time between the DEER sequences, while appying a rf pi pulse
            in the end of the sequence to generate contrast. (See Sushkov et al., PRL 113 (2014))
            """
            if rf_pulse_delay >= 0.0:
                sequence1_deer = [(['mw_x'], mw_x_t_pi2), ([], (0.5 * mw_tau)),
                                  (['mw_y'], mw_y_t_pi),
                                  ([], rf_pulse_delay), (['rf'], rf_t_pi),
                                  ([], (0.5 * mw_tau) - rf_pulse_delay - rf_t_pi),
                                  (['mw_y'], mw_y_t_pi2)]
            if rf_pulse_delay < 0.0:
                rf_pulse_delay = abs(rf_pulse_delay)
                sequence1_deer = [(['mw_x'], mw_x_t_pi2),
                                  ([], (0.5 * mw_tau) - rf_pulse_delay - rf_t_pi),
                                  (['rf'], rf_t_pi), ([], rf_pulse_delay),
                                  (['mw_y'], mw_y_t_pi), ([], (0.5 * mw_tau)),
                                  (['mw_y'], mw_y_t_pi2)]
            sequence = []
            for t in self.tau:
                sequence += sequence1_deer + \
                            [([], t)] + \
                            sequence1_deer + \
                            [(['detect', 'aom'], laser), ([], decay_init)]
            for t in self.tau:
                sequence += sequence1_deer + \
                            [([], rf_evo_delay)] + \
                            [(['rf'], rf_evo_t_pi)] + \
                            [([], t - rf_evo_t_pi - rf_evo_delay)] + \
                            sequence1_deer + \
                            [(['detect', 'aom'], laser), ([], decay_init)]
        else:
            """In this case we do xy8_n-DD, with an rf pulse in between each mw_tau
            mw_tau corresponds to the time/8*n the sequence takes. This time is used in NMR analysis
            and since our xy8 measurements are using this time we use it here as well.
            """
            # t is the time between the infinitely short xy8 pulses
            t = mw_tau / (8. * n)
            # This lambda function gives correct mw_tau for the approximation of infinetly short pulses
            t_bar = lambda t, p1, p2=0., p3=0., p4=0.: t - (p1 / 2.) - (p2 / 2.) - p3 - p4
            # check, if the start time is long enough to fit at least the mw pulses in it.
            if t_bar(t, mw_y_t_pi, mw_y_t_pi, rf_pulse_delay, rf_t_pi) < 0 or t_bar(t, mw_x_t_pi,
                                                                                    mw_x_t_pi,
                                                                                    rf_pulse_delay,
                                                                                    rf_t_pi) < 0:
                raise IOError(
                    'The delay between pulses is too short.'
                    'It has to be larger than the pulse_duration')
            # Here, a negative rf pulse delay makes no sense.
            if rf_pulse_delay < 0.0:
                rf_pulse_delay = abs(rf_pulse_delay)

            """
            Build the signal sequence, i.e. the spin state with applied rf at a specific mw_tau with
            xy8 decoupling.
            """
            sequence1_deer = []
            sequence2_deer = []

            xy_8_rf_part = []
            start = []
            end_pi2 = []
            end_3pi2 = []
            init = [(['detect', 'aom'], laser), ([], decay_init)]

            xy_8_rf_part += [(['mw_x'], mw_x_t_pi), ([], rf_pulse_delay), (['rf'], rf_t_pi),
                             ([], t_bar(t, mw_x_t_pi, mw_y_t_pi, rf_pulse_delay, rf_t_pi))]
            xy_8_rf_part += [(['mw_y'], mw_y_t_pi), ([], rf_pulse_delay), (['rf'], rf_t_pi),
                             ([], t_bar(t, mw_x_t_pi, mw_y_t_pi, rf_pulse_delay, rf_t_pi))]
            xy_8_rf_part += [(['mw_x'], mw_x_t_pi), ([], rf_pulse_delay), (['rf'], rf_t_pi),
                             ([], t_bar(t, mw_x_t_pi, mw_y_t_pi, rf_pulse_delay, rf_t_pi))]
            xy_8_rf_part += [(['mw_y'], mw_y_t_pi), ([], rf_pulse_delay), (['rf'], rf_t_pi),
                             ([], t_bar(t, mw_y_t_pi, mw_y_t_pi, rf_pulse_delay, rf_t_pi))]
            xy_8_rf_part += [(['mw_y'], mw_y_t_pi), ([], rf_pulse_delay), (['rf'], rf_t_pi),
                             ([], t_bar(t, mw_x_t_pi, mw_y_t_pi, rf_pulse_delay, rf_t_pi))]
            xy_8_rf_part += [(['mw_x'], mw_x_t_pi), ([], rf_pulse_delay), (['rf'], rf_t_pi),
                             ([], t_bar(t, mw_x_t_pi, mw_y_t_pi, rf_pulse_delay, rf_t_pi))]
            xy_8_rf_part += [(['mw_y'], mw_y_t_pi), ([], rf_pulse_delay), (['rf'], rf_t_pi),
                             ([], t_bar(t, mw_x_t_pi, mw_y_t_pi, rf_pulse_delay, rf_t_pi))]
            xy_8_rf_part += [(['mw_x'], mw_x_t_pi)]

            start = [(['mw_x'], mw_x_t_pi2), ([], rf_pulse_delay), (['rf'], rf_t_pi),
                     ([], t_bar(t / 2., mw_x_t_pi, p3=rf_pulse_delay, p4=rf_t_pi))]
            end_pi2 = [([], t_bar(t, mw_x_t_pi) / 2. - rf_pulse_delay - rf_t_pi),
                       (['mw_x'], mw_x_t_pi2)]
            end_3pi2 = [([], t_bar(t, mw_x_t_pi) / 2. - rf_pulse_delay - rf_t_pi),
                        (['mw_x'], mw_x_t_3pi2)]

            # build the sequences
            sequence1_deer += start + (
                    (n - 1) * (xy_8_rf_part + [
                ([], t_bar(t, mw_x_t_pi, mw_y_t_pi))])) + xy_8_rf_part + end_pi2
            sequence2_deer += start + (
                    (n - 1) * (xy_8_rf_part + [
                ([], t_bar(t, mw_x_t_pi, mw_y_t_pi))])) + xy_8_rf_part + end_3pi2

            # join the two sequences
            sequence = []
            for t in self.tau:
                sequence += sequence1_deer + \
                            [([], t)] + \
                            sequence1_deer + init
            for t in self.tau:
                sequence += sequence1_deer + \
                            [([], t - rf_evo_t_pi - rf_evo_delay)] + \
                            [(['rf'], rf_evo_t_pi)] + \
                            [([], rf_evo_delay)] + \
                            sequence1_deer + init

        # tail of the sequence
        sequence = sequence + [(['sequence'], 100)]
        sequence = sequence_remove_zeros(sequence)

        return sequence

    def _create_line_plot(self):
        line_data = ArrayPlotData(index=np.array((0, 1)),
                                  first=np.array((0, 0)),
                                  second=np.array((0, 0)),
                                  )
        plot = Plot(line_data, padding=8, padding_left=64, padding_bottom=36)
        plot.plot(('index', 'first'), color='blue', name='first', index_scale='log')
        plot.plot(('index', 'second'), color='green', name='second', index_scale='log')
        plot.index_axis.title = 'time [micro s]'
        plot.value_axis.title = 'spin state'
        plot.tools.append(SaveTool(plot))
        self.line_data = line_data
        self.line_plot = plot

    get_set_items = DEER_correlation.get_set_items + ['rf_evo_delay', 'rf_evo_t_pi']

    traits_view = View(VGroup(HGroup(Item('submit_button', show_label=False),
                                     Item('remove_button', show_label=False),
                                     Item('resubmit_button', show_label=False),
                                     Item('get_global_vars_button', show_label=False),
                                     Item('priority'),
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
                              Tabbed(VGroup(HGroup(
                                  Item('mw_frequency', width=-120, enabled_when='state != "run"'),
                                  Item('mw_power', width=-60, enabled_when='state != "run"'),
                              ),
                                  HGroup(Item('laser', width=-80,
                                              enabled_when='state != "run"'),
                                         Item('decay_init', width=-80,
                                              enabled_when='state != "run"'),
                                         ),
                                  HGroup(Item('n_sequences', width=-80,
                                              enabled_when='state != "run"'),
                                         Item('mw_tau', width=-80,
                                              enabled_when='state != "run"'), ),
                                  HGroup(Item('mw_x_t_pi2', width=-80,
                                              enabled_when='state != "run"'),
                                         Item('mw_x_t_pi', width=-80,
                                              enabled_when='state != "run"'),
                                         Item('mw_x_t_3pi2', width=-80,
                                              enabled_when='state != "run"'), ),
                                  HGroup(Item('mw_y_t_pi2', width=-80,
                                              enabled_when='state != "run"'),
                                         Item('mw_y_t_pi', width=-80,
                                              enabled_when='state != "run"'),
                                         Item('mw_y_t_3pi2', width=-80,
                                              enabled_when='state != "run"'), ),
                                  HGroup(Item('rf_frequency', width=-120,
                                              enabled_when='state != "run"'),
                                         Item('rf_power', width=-80,
                                              enabled_when='state != "run"'),
                                         Item('rf_t_pi', width=-80,
                                              enabled_when='state != "run"'),
                                         Item('rf_pulse_delay', width=-80,
                                              enabled_when='state != "run"'),
                                         ),
                                  HGroup(Item('rf_evo_delay', width=-80,
                                              enabled_when='state != "run"'),
                                         Item('rf_evo_t_pi', width=-80,
                                              enabled_when='state != "run"'),
                                         ),
                                  HGroup(Item('tau_begin', width=-80,
                                              enabled_when='state != "run"'),
                                         Item('tau_end', width=-80,
                                              enabled_when='state != "run"'),
                                         Item('tau_delta', width=-80,
                                              enabled_when='state != "run"'),
                                         ),
                                  label='acquisition'),
                                  VGroup(HGroup(Item('integration_width'),
                                                Item('position_signal'),
                                                Item('position_normalize'),
                                                ),
                                         label='analysis'),
                              ),
                              Tabbed(Item('line_plot', show_label=False, width=500, height=-300,
                                          resizable=True),
                                     Item('matrix_plot', show_label=False, width=500, height=-300,
                                          resizable=True),
                                     Item('pulse_plot', show_label=False, width=500, height=-300,
                                          resizable=True),
                                     ),
                              ),
                       title='Pi3diamond: DEER Correlation T1',
                       buttons=[],
                       resizable=True,
                       )


class DarkSpin_Hahn(DEER_correlation):
    """
    Use DEER correlation measurements to perform a Hahn Echo measurement on the Dark Spin
    """
    # Values that define the sequence applied during dark spin free evolution
    tau_evo = Float(default_value=15., desc='tau for free evolution',
                    label='tau evolution [ns]', mode='text', auto_set=False, enter_set=True)
    seq_offset_evo = Float(default_value=12., desc='evolution pi offset',
                           label='Sequence offset evolution [ns]', mode='text', auto_set=False,
                           enter_set=True)
    rf_evo_t_pi2 = Float(default_value=50.,
                         desc='length of RF pi2 pulse during free evolution [ns]',
                         label='RF pi2 evolution [ns]', mode='text', auto_set=False, enter_set=True)
    rf_evo_t_pi = Float(default_value=100., desc='length of RF pi pulse during free evolution [ns]',
                        label='RF pi evolution [ns]', mode='text', auto_set=False, enter_set=True)

    def generate_sequence(self):
        mw_tau = self.mw_tau
        laser = self.laser
        n = self.n_sequences
        decay_init = self.decay_init

        mw_x_t_pi2 = self.mw_x_t_pi2
        mw_x_t_pi = self.mw_x_t_pi
        mw_x_t_3pi2 = self.mw_x_t_3pi2
        mw_y_t_pi2 = self.mw_y_t_pi2
        mw_y_t_pi = self.mw_y_t_pi
        mw_y_t_3pi2 = self.mw_y_t_3pi2

        rf_pulse_delay = self.rf_pulse_delay
        rf_t_pi = self.rf_t_pi

        tau_evo = self.tau_evo
        seq_offset_evo = self.seq_offset_evo
        rf_evo_t_pi2 = self.rf_evo_t_pi2
        rf_evo_t_pi = self.rf_evo_t_pi

        if n == 0:
            """
            In this case use hahn echo with an rf in between.
            mw_tau corresponds twice the time between the pi2 and pi pulse of the mw.
            For the Correlation Spectroscopy we use a dark spin pi-RF pulse and a variable time
            PulsedTau.tau to vary the time when it is applied in between the DEER sequences. The
            total dark spin free evolution time stays fixed (See Sushkov et al., PRL 113 (2014))
            """
            if rf_pulse_delay >= 0.0:
                sequence1_deer = [(['mw_x'], mw_x_t_pi2), ([], (0.5 * mw_tau)),
                                  (['mw_y'], mw_y_t_pi),
                                  ([], rf_pulse_delay), (['rf'], rf_t_pi),
                                  ([], (0.5 * mw_tau) - rf_pulse_delay - rf_t_pi),
                                  (['mw_y'], mw_y_t_pi2)]
                sequence2_deer = [(['mw_x'], mw_x_t_pi2), ([], (0.5 * mw_tau)),
                                  (['mw_y'], mw_y_t_pi),
                                  ([], rf_pulse_delay), (['rf'], rf_t_pi),
                                  ([], (0.5 * mw_tau) - rf_pulse_delay - rf_t_pi),
                                  (['mw_y'], mw_y_t_3pi2)]
            if rf_pulse_delay < 0.0:
                rf_pulse_delay = abs(rf_pulse_delay)
                sequence1_deer = [(['mw_x'], mw_x_t_pi2),
                                  ([], (0.5 * mw_tau) - rf_pulse_delay - rf_t_pi),
                                  (['rf'], rf_t_pi), ([], rf_pulse_delay),
                                  (['mw_y'], mw_y_t_pi), ([], (0.5 * mw_tau)),
                                  (['mw_y'], mw_y_t_pi2)]
                sequence2_deer = [(['mw_x'], mw_x_t_pi2),
                                  ([], (0.5 * mw_tau) - rf_pulse_delay - rf_t_pi),
                                  (['rf'], rf_t_pi), ([], rf_pulse_delay),
                                  (['mw_y'], mw_y_t_pi), ([], (0.5 * mw_tau)),
                                  (['mw_y'], mw_y_t_3pi2)]
            sequence = []
            for t in self.tau:
                sequence += sequence1_deer + \
                            [([], seq_offset_evo)] + \
                            [(['rf'], rf_evo_t_pi2)] + [([], t / 2.)] + [(['rf'], rf_evo_t_pi)] + \
                            [([], t / 2.)] + [(['rf'], rf_evo_t_pi2)] + \
                            [([], tau_evo - 2 * rf_evo_t_pi - t - seq_offset_evo)] + \
                            sequence1_deer + \
                            [(['detect', 'aom'], laser), ([], decay_init)]
            for t in self.tau:
                sequence += sequence1_deer + \
                            [([], seq_offset_evo)] + \
                            [(['rf'], rf_evo_t_pi2)] + [([], t / 2.)] + [(['rf'], rf_evo_t_pi)] + \
                            [([], t / 2.)] + [(['rf'], rf_evo_t_pi2)] + \
                            [([], tau_evo - 2 * rf_evo_t_pi - t - seq_offset_evo)] + \
                            sequence2_deer + \
                            [(['detect', 'aom'], laser), ([], decay_init)]
        else:
            """In this case we do xy8_n-DD, with an rf pulse in between each mw_tau
            mw_tau corresponds to the time/8*n the sequence takes. This time is used in NMR analysis
            and since our xy8 measurements are using this time we use it here as well.
            """
            # t is the time between the infinitely short xy8 pulses
            t = mw_tau / (8. * n)
            # This lambda function gives correct mw_tau for the approximation of infinetly short pulses
            t_bar = lambda t, p1, p2=0., p3=0., p4=0.: t - (p1 / 2.) - (p2 / 2.) - p3 - p4
            # check, if the start time is long enough to fit at least the mw pulses in it.
            if t_bar(t, mw_y_t_pi, mw_y_t_pi, rf_pulse_delay, rf_t_pi) < 0 or t_bar(t, mw_x_t_pi,
                                                                                    mw_x_t_pi,
                                                                                    rf_pulse_delay,
                                                                                    rf_t_pi) < 0:
                raise IOError(
                    'The delay between pulses is too short.'
                    'It has to be larger than the pulse_duration')
            # Here, a negative rf pulse delay makes no sense.
            if rf_pulse_delay < 0.0:
                rf_pulse_delay = abs(rf_pulse_delay)

            """
            Build the signal sequence, i.e. the spin state with applied rf at a specific mw_tau with
            xy8 decoupling.
            """
            sequence1_deer = []
            sequence2_deer = []

            xy_8_rf_part = []
            start = []
            end_pi2 = []
            end_3pi2 = []
            init = [(['detect', 'aom'], laser), ([], decay_init)]

            xy_8_rf_part += [(['mw_x'], mw_x_t_pi), ([], rf_pulse_delay), (['rf'], rf_t_pi),
                             ([], t_bar(t, mw_x_t_pi, mw_y_t_pi, rf_pulse_delay, rf_t_pi))]
            xy_8_rf_part += [(['mw_y'], mw_y_t_pi), ([], rf_pulse_delay), (['rf'], rf_t_pi),
                             ([], t_bar(t, mw_x_t_pi, mw_y_t_pi, rf_pulse_delay, rf_t_pi))]
            xy_8_rf_part += [(['mw_x'], mw_x_t_pi), ([], rf_pulse_delay), (['rf'], rf_t_pi),
                             ([], t_bar(t, mw_x_t_pi, mw_y_t_pi, rf_pulse_delay, rf_t_pi))]
            xy_8_rf_part += [(['mw_y'], mw_y_t_pi), ([], rf_pulse_delay), (['rf'], rf_t_pi),
                             ([], t_bar(t, mw_y_t_pi, mw_y_t_pi, rf_pulse_delay, rf_t_pi))]
            xy_8_rf_part += [(['mw_y'], mw_y_t_pi), ([], rf_pulse_delay), (['rf'], rf_t_pi),
                             ([], t_bar(t, mw_x_t_pi, mw_y_t_pi, rf_pulse_delay, rf_t_pi))]
            xy_8_rf_part += [(['mw_x'], mw_x_t_pi), ([], rf_pulse_delay), (['rf'], rf_t_pi),
                             ([], t_bar(t, mw_x_t_pi, mw_y_t_pi, rf_pulse_delay, rf_t_pi))]
            xy_8_rf_part += [(['mw_y'], mw_y_t_pi), ([], rf_pulse_delay), (['rf'], rf_t_pi),
                             ([], t_bar(t, mw_x_t_pi, mw_y_t_pi, rf_pulse_delay, rf_t_pi))]
            xy_8_rf_part += [(['mw_x'], mw_x_t_pi)]

            start = [(['mw_x'], mw_x_t_pi2), ([], rf_pulse_delay), (['rf'], rf_t_pi),
                     ([], t_bar(t / 2., mw_x_t_pi, p3=rf_pulse_delay, p4=rf_t_pi))]
            end_pi2 = [([], t_bar(t, mw_x_t_pi) / 2. - rf_pulse_delay - rf_t_pi),
                       (['mw_x'], mw_x_t_pi2)]
            end_3pi2 = [([], t_bar(t, mw_x_t_pi) / 2. - rf_pulse_delay - rf_t_pi),
                        (['mw_x'], mw_x_t_3pi2)]

            # build the sequences
            sequence1_deer += start + (
                    (n - 1) * (xy_8_rf_part + [
                ([], t_bar(t, mw_x_t_pi, mw_y_t_pi))])) + xy_8_rf_part + end_pi2
            sequence2_deer += start + (
                    (n - 1) * (xy_8_rf_part + [
                ([], t_bar(t, mw_x_t_pi, mw_y_t_pi))])) + xy_8_rf_part + end_3pi2

            # join the two sequences
            sequence = []
            for t in self.tau:
                sequence += sequence1_deer + \
                            [([], tau_evo - t - rf_evo_t_pi)] + \
                            [(['rf'], rf_evo_t_pi)] + \
                            [([], t)] + \
                            sequence1_deer + init
            for t in self.tau:
                sequence += sequence1_deer + \
                            [([], tau_evo - t - rf_evo_t_pi)] + \
                            [(['rf'], rf_evo_t_pi)] + \
                            [([], t)] + \
                            sequence2_deer + init

        # tail of the sequence
        sequence = sequence + [(['sequence'], 100)]
        sequence = sequence_remove_zeros(sequence)

        return sequence

    get_set_items = DEER_correlation.get_set_items + ['tau_evo', 'seq_offset_evo', 'rf_evo_t_pi2',
                                                      'rf_evo_t_pi']

    traits_view = View(VGroup(HGroup(Item('submit_button', show_label=False),
                                     Item('remove_button', show_label=False),
                                     Item('resubmit_button', show_label=False),
                                     Item('get_global_vars_button', show_label=False),
                                     Item('priority'),
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
                              Tabbed(VGroup(HGroup(
                                  Item('mw_frequency', width=-120, enabled_when='state != "run"'),
                                  Item('mw_power', width=-60, enabled_when='state != "run"'),
                              ),
                                  HGroup(Item('laser', width=-80,
                                              enabled_when='state != "run"'),
                                         Item('decay_init', width=-80,
                                              enabled_when='state != "run"'),
                                         ),
                                  HGroup(Item('n_sequences', width=-80,
                                              enabled_when='state != "run"'),
                                         Item('mw_tau', width=-80,
                                              enabled_when='state != "run"'), ),
                                  HGroup(Item('mw_x_t_pi2', width=-80,
                                              enabled_when='state != "run"'),
                                         Item('mw_x_t_pi', width=-80,
                                              enabled_when='state != "run"'),
                                         Item('mw_x_t_3pi2', width=-80,
                                              enabled_when='state != "run"'), ),
                                  HGroup(Item('mw_y_t_pi2', width=-80,
                                              enabled_when='state != "run"'),
                                         Item('mw_y_t_pi', width=-80,
                                              enabled_when='state != "run"'),
                                         Item('mw_y_t_3pi2', width=-80,
                                              enabled_when='state != "run"'), ),
                                  HGroup(Item('rf_frequency', width=-120,
                                              enabled_when='state != "run"'),
                                         Item('rf_power', width=-80,
                                              enabled_when='state != "run"'),
                                         Item('rf_t_pi', width=-80,
                                              enabled_when='state != "run"'),
                                         Item('rf_pulse_delay', width=-80,
                                              enabled_when='state != "run"'),
                                         ),
                                  HGroup(Item('tau_evo', width=-80,
                                              enabled_when='state != "run"'),
                                         Item('seq_offset_evo', width=-80,
                                              enabled_when='state != "run"'),
                                         Item('rf_evo_t_pi2', width=-80,
                                              enabled_when='state != "run"'),
                                         Item('rf_evo_t_pi', width=-80,
                                              enabled_when='state != "run"'),
                                         ),
                                  HGroup(Item('tau_begin', width=-80,
                                              enabled_when='state != "run"'),
                                         Item('tau_end', width=-80,
                                              enabled_when='state != "run"'),
                                         Item('tau_delta', width=-80,
                                              enabled_when='state != "run"'),
                                         ),
                                  label='acquisition'),
                                  VGroup(HGroup(Item('integration_width'),
                                                Item('position_signal'),
                                                Item('position_normalize'),
                                                ),
                                         label='analysis'),
                              ),
                              Tabbed(Item('line_plot', show_label=False, width=500, height=-300,
                                          resizable=True),
                                     Item('matrix_plot', show_label=False, width=500, height=-300,
                                          resizable=True),
                                     Item('pulse_plot', show_label=False, width=500, height=-300,
                                          resizable=True),
                                     ),
                              ),
                       title='Pi3diamond: DEER Correlation Hahn',
                       buttons=[],
                       resizable=True,
                       )


if __name__ == '__main__':
    pass
