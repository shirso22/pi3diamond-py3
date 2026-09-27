import logging

import numpy as np
from chaco.api import ArrayPlotData
from traits.api import Range, Int, Float
from traitsui.api import View, Item, Tabbed, HGroup, VGroup, TextEditor, VSplit

from measurements.rabi import Rabi
from .pulsed import sequence_remove_zeros
from tools.chaco_addons import SavePlot as Plot, SaveTool


class DEER(Rabi):
    """Class for DEER Measurement.

    This class provides the variables and sequences to perform a DEER Measurement. Namely, we either
    perform Hahn-Echo or dynamical decoupling on the NV center while we vary the magnetic
    environment with a freely tunable, pulsed rf-excitation.
    """
    double_sequence = True

    power_imbalance = Range(low=-1., high=1., value=0., desc='microwave power imbalance',
                            label='power imbalance [dBm]', mode='text', auto_set=False,
                            enter_set=True)
    decoupling_order = Int(default_value=0, desc='number of XY_8-Sequences', label='n_seq',
                           mode='text', auto_set=False, enter_set=True)
    mw_tau = Float(default_value=2000, desc='time between pi pulses[ns]', label='mw_tau [ns]',
                   mode='text', auto_set=False, enter_set=True)

    # Values that define the RF e-Spin excitation in the DEER sequence.
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
        super(DEER, self).__init__(pulse_generator, time_tagger, microwave, **kwargs)
        self.rf = rf

    def start_up(self):
        self.pulse_generator.Night()
        self.microwave.setOutput(self.mw_power, self.mw_frequency)
        self.rf.setFrequency(self.rf_frequency)
        self.rf.setPower(self.rf_power)

    def shut_down(self):
        self.pulse_generator.Light()
        self.microwave.setOutput(-40, self.mw_frequency)
        self.rf.setPower(-40)

    def generate_sequence(self):
        mw_tau = self.mw_tau
        laser = self.laser
        n = self.decoupling_order
        decay_init = self.decay_init

        mw_x_t_pi2 = self.mw_x_t_pi2
        mw_x_t_3pi2 = self.mw_x_t_3pi2
        mw_y_t_pi = self.mw_y_t_pi
        mw_x_t_pi = self.mw_x_t_pi

        rf_pulse_delay = self.rf_pulse_delay
        rf_t_pi = self.rf_t_pi

        if n == 0:
            """
            In this case we just do a simple hahn echo with an rf in between
            mw_tau corresponds twice the time between the pi2 and pi pulse of the mw.
            The rf_pulse_delay can also be negative.
            """
            sequence1_reference = [(['mw_x'], mw_x_t_pi2), ([], 0.5 * mw_tau),
                                   (['mw_x'], mw_x_t_pi),
                                   ([], 0.5 * mw_tau), (['mw_x'], mw_x_t_pi2),
                                   (['detect', 'aom'], laser),
                                   ([], decay_init)]
            sequence2_reference = [(['mw_x'], mw_x_t_pi2), ([], 0.5 * mw_tau),
                                   (['mw_x'], mw_x_t_pi),
                                   ([], 0.5 * mw_tau), (['mw_x'], mw_x_t_3pi2),
                                   (['detect', 'aom'], laser),
                                   ([], decay_init)]
            if rf_pulse_delay >= 0.0:
                sequence1_signal = [(['mw_x'], mw_x_t_pi2), ([], (0.5 * mw_tau)),
                                    (['mw_x'], mw_x_t_pi),
                                    ([], rf_pulse_delay), (['rf'], rf_t_pi),
                                    ([], (0.5 * mw_tau) - rf_pulse_delay - rf_t_pi),
                                    (['mw_x'], mw_x_t_pi2),
                                    (['detect', 'aom'], laser), ([], decay_init)]
                sequence2_signal = [(['mw_x'], mw_x_t_pi2), ([], (0.5 * mw_tau)),
                                    (['mw_x'], mw_x_t_pi),
                                    ([], rf_pulse_delay), (['rf'], rf_t_pi),
                                    ([], (0.5 * mw_tau) - rf_pulse_delay - rf_t_pi),
                                    (['mw_x'], mw_x_t_3pi2),
                                    (['detect', 'aom'], laser), ([], decay_init)]
            if rf_pulse_delay < 0.0:
                rf_pulse_delay = abs(rf_pulse_delay)
                sequence1_signal = [(['mw_x'], mw_x_t_pi2),
                                    ([], (0.5 * mw_tau) - rf_pulse_delay - rf_t_pi),
                                    (['rf'], rf_t_pi), ([], rf_pulse_delay), (['mw_x'], mw_x_t_pi),
                                    ([], (0.5 * mw_tau)), (['mw_x'], mw_x_t_pi2),
                                    (['detect', 'aom'], laser), ([], decay_init)]
                sequence2_signal = [(['mw_x'], mw_x_t_pi2),
                                    ([], (0.5 * mw_tau) - rf_pulse_delay - rf_t_pi),
                                    (['rf'], rf_t_pi), ([], rf_pulse_delay), (['mw_x'], mw_x_t_pi),
                                    ([], (0.5 * mw_tau)), (['mw_x'], mw_x_t_3pi2),
                                    (['detect', 'aom'], laser), ([], decay_init)]
            sequence_reference = sequence1_reference + sequence2_reference
            sequence_signal = sequence1_signal + sequence2_signal
        else:
            """In this case we just do xy8_n-DD, with an rf pulse in between each mw_tau
            mw_tau corresponds to the time/8*n the sequence takes. This time is used in NMR analysis
            and since our xy8 measurements are using this time we use it here as well.
            """
            # t is the time between the infinitely short xy8 pulses
            t = mw_tau / (8. * n)
            # This lambda function gives correct mw_tau for approximation of infinitely short pulses
            t_bar = lambda t, p1, p2=0., p3=0., p4=0.: t - (p1 / 2.) - (p2 / 2.) - p3 - p4
            # check, if the start time is long enough to fit at least the mw pulses in it.
            if t_bar(t, mw_y_t_pi, mw_y_t_pi, rf_pulse_delay, rf_t_pi) < 0 or t_bar(t, mw_x_t_pi,
                                                                                    mw_x_t_pi,
                                                                                    rf_pulse_delay,
                                                                                    rf_t_pi) < 0:
                raise IOError('The delay between pulses is too short. It has to be larger than the'
                              'pulse_duration')
            # Here, a negative rf pulse delay makes no sense.
            if rf_pulse_delay < 0.0:
                rf_pulse_delay = abs(rf_pulse_delay)
            """
            Build the reference sequence, i.e. the spin state at a specific mw_tau with xy8
            decoupling.
            """
            sequence1_reference = []
            sequence2_reference = []

            xy_8_part = []
            init = [(['detect', 'aom'], laser), ([], decay_init)]

            xy_8_part += [(['mw_x'], mw_x_t_pi), ([], t_bar(t, mw_x_t_pi, mw_y_t_pi))]
            xy_8_part += [(['mw_y'], mw_y_t_pi), ([], t_bar(t, mw_x_t_pi, mw_y_t_pi))]
            xy_8_part += [(['mw_x'], mw_x_t_pi), ([], t_bar(t, mw_x_t_pi, mw_y_t_pi))]
            xy_8_part += [(['mw_y'], mw_y_t_pi), ([], t_bar(t, mw_y_t_pi, mw_y_t_pi))]
            xy_8_part += [(['mw_y'], mw_y_t_pi), ([], t_bar(t, mw_x_t_pi, mw_y_t_pi))]
            xy_8_part += [(['mw_x'], mw_x_t_pi), ([], t_bar(t, mw_x_t_pi, mw_y_t_pi))]
            xy_8_part += [(['mw_y'], mw_y_t_pi), ([], t_bar(t, mw_x_t_pi, mw_y_t_pi))]
            xy_8_part += [(['mw_x'], mw_x_t_pi)]

            start = [(['mw_x'], mw_x_t_pi2), ([], t_bar(t, mw_x_t_pi) / 2.)]
            end_pi2 = [([], t_bar(t, mw_x_t_pi) / 2.), (['mw_x'], mw_x_t_pi2)]
            end_3pi2 = [([], t_bar(t, mw_x_t_pi) / 2.), (['mw_x'], mw_x_t_3pi2)]

            # build the sequences
            sequence1_reference += start + (
                    (n - 1) * (
                    xy_8_part + [
                ([], t_bar(t, mw_x_t_pi, mw_y_t_pi))])) + xy_8_part + end_pi2 + init
            sequence2_reference += start + (
                    (n - 1) * (
                    xy_8_part + [
                ([], t_bar(t, mw_x_t_pi, mw_y_t_pi))])) + xy_8_part + end_3pi2 + init

            # join the two sequences
            sequence_reference = sequence1_reference + sequence2_reference

            """
            Build the signal sequence, i.e. the spin state with applied rf at a specific mw_tau with
            xy8 decoupling.
            """
            sequence1_signal = []
            sequence2_signal = []

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
            sequence1_signal += start + (
                    (n - 1) * (xy_8_rf_part + [
                ([], t_bar(t, mw_x_t_pi, mw_y_t_pi))])) + xy_8_rf_part + end_pi2 + init
            sequence2_signal += start + (
                    (n - 1) * (xy_8_rf_part + [
                ([], t_bar(t, mw_x_t_pi, mw_y_t_pi))])) + xy_8_rf_part + end_3pi2 + init
            # join the two sequences
            sequence_signal = sequence1_signal + sequence2_signal
        # now, join reference and signal sequence
        sequence = sequence_reference + sequence_signal
        # tail of the sequence
        sequence += [(['sequence'], 100)]
        sequence = sequence_remove_zeros(sequence)

        return sequence

    get_set_items = Rabi.get_set_items + ['mw_tau', 'mw_x_t_pi2', 'mw_x_t_pi', 'mw_x_t_3pi2',
                                          'mw_y_t_pi', 'decoupling_order', 'power_imbalance',
                                          'rf_frequency', 'rf_power', 'rf_t_pi', 'rf_pulse_delay']

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
                                     Item('load_button', show_label=False)
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
                                  HGroup(Item('mw_x_t_pi2', width=-80,
                                              enabled_when='state != "run"'),
                                         Item('mw_x_t_pi', width=-80,
                                              enabled_when='state != "run"'),
                                         Item('mw_y_t_pi', width=-80,
                                              enabled_when='state != "run"'),
                                         Item('mw_x_t_3pi2', width=-80,
                                              enabled_when='state != "run"'),
                                         Item('decoupling_order', width=-80,
                                              enabled_when='state != "run"'),
                                         Item('mw_tau', width=-80,
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
                                  label='acquisition'),
                                  VGroup(HGroup(Item('integration_width'),
                                                Item('position_signal'),
                                                Item('position_normalize'),
                                                ),
                                         label='analysis'),
                              ),
                              ),
                       title='DEER Measurement',
                       buttons=[],
                       resizable=True,
                       )


class DEEREvolutionTau(DEER):
    """Perform a measurement of DEER contrast with respect to tau of a hahn measurement.

    In principle we just perform a DEER measurement, yet the extension of this class is that we
    do an additional regular hahn and all in dependence of the free evolution time spacing tau.
    """

    def generate_sequence(self):
        laser = self.laser
        n = self.decoupling_order
        decay_init = self.decay_init

        mw_x_t_pi2 = self.mw_x_t_pi2
        mw_x_t_3pi2 = self.mw_x_t_3pi2
        mw_y_t_pi = self.mw_y_t_pi
        mw_x_t_pi = self.mw_x_t_pi

        rf_pulse_delay = self.rf_pulse_delay
        rf_t_pi = self.rf_t_pi

        if n == 0:
            """
            In this case we just do a simple hahn echo with an rf in between
            mw_tau corresponds twice the time between the pi2 and pi pulse of the mw.
            The rf_pulse_delay can also be negative.
            """
            sequence1_reference = []
            sequence2_reference = []
            sequence1_signal = []
            sequence2_signal = []
            for t in self.tau:
                sequence1_reference += [(['mw_x'], mw_x_t_pi2), ([], 0.5 * t),
                                        (['mw_x'], mw_x_t_pi),
                                        ([], 0.5 * t), (['mw_x'], mw_x_t_pi2),
                                        (['detect', 'aom'], laser),
                                        ([], decay_init)]
                sequence2_reference += [(['mw_x'], mw_x_t_pi2), ([], 0.5 * t),
                                        (['mw_x'], mw_x_t_pi),
                                        ([], 0.5 * t), (['mw_x'], mw_x_t_3pi2),
                                        (['detect', 'aom'], laser),
                                        ([], decay_init)]
                if rf_pulse_delay >= 0.0:
                    sequence1_signal += [(['mw_x'], mw_x_t_pi2), ([], (0.5 * t)),
                                         (['mw_x'], mw_x_t_pi),
                                         ([], rf_pulse_delay), (['rf'], rf_t_pi),
                                         ([], (0.5 * t) - rf_pulse_delay - rf_t_pi),
                                         (['mw_x'], mw_x_t_pi2),
                                         (['detect', 'aom'], laser), ([], decay_init)]
                    sequence2_signal += [(['mw_x'], mw_x_t_pi2), ([], (0.5 * t)),
                                         (['mw_x'], mw_x_t_pi),
                                         ([], rf_pulse_delay), (['rf'], rf_t_pi),
                                         ([], (0.5 * t) - rf_pulse_delay - rf_t_pi),
                                         (['mw_x'], mw_x_t_3pi2),
                                         (['detect', 'aom'], laser), ([], decay_init)]
                if rf_pulse_delay < 0.0:
                    rf_pulse_delay = abs(rf_pulse_delay)
                    sequence1_signal += [(['mw_x'], mw_x_t_pi2),
                                         ([], (0.5 * t) - rf_pulse_delay - rf_t_pi),
                                         (['rf'], rf_t_pi), ([], rf_pulse_delay),
                                         (['mw_x'], mw_x_t_pi),
                                         ([], (0.5 * t)), (['mw_x'], mw_x_t_pi2),
                                         (['detect', 'aom'], laser), ([], decay_init)]
                    sequence2_signal += [(['mw_x'], mw_x_t_pi2),
                                         ([], (0.5 * t) - rf_pulse_delay - rf_t_pi),
                                         (['rf'], rf_t_pi), ([], rf_pulse_delay),
                                         (['mw_x'], mw_x_t_pi),
                                         ([], (0.5 * t)), (['mw_x'], mw_x_t_3pi2),
                                         (['detect', 'aom'], laser), ([], decay_init)]
            sequence_reference = sequence1_reference + sequence2_reference
            sequence_signal = sequence1_signal + sequence2_signal
        else:
            """In this case we just do xy8_n-DD, with an rf pulse in between each t
            t corresponds to the time/8*n the sequence takes. This time is used in NMR analysis
            and since our xy8 measurements are using this time we use it here as well.
            """
            # This lambda function gives correct time for approximation of infinitely short pulses
            t_bar = lambda t, p1, p2=0., p3=0., p4=0.: t - (p1 / 2.) - (p2 / 2.) - p3 - p4
            # Here, a negative rf pulse delay makes no sense.
            if rf_pulse_delay < 0.0:
                rf_pulse_delay = abs(rf_pulse_delay)
            """
            Build the reference sequence, i.e. the spin state with xy8 decoupling in dependence of
            interpulse spacing.
            """
            sequence1_reference = []
            sequence2_reference = []

            init = [(['detect', 'aom'], laser), ([], decay_init)]
            for mw_tau in self.tau:
                # t is the time between the infinitely short xy8 pulses
                t = mw_tau / (8. * n)
                # check, if the start time is long enough to fit at least the mw pulses in it.
                if t_bar(t, mw_y_t_pi, mw_y_t_pi, rf_pulse_delay, rf_t_pi) < 0 or \
                        t_bar(t, mw_x_t_pi, mw_x_t_pi, rf_pulse_delay, rf_t_pi) < 0:
                    raise IOError('The delay between pulses is too short. It has to be larger than'
                                  'the pulse_duration')
                xy_8_part = []
                xy_8_part += [(['mw_x'], mw_x_t_pi), ([], t_bar(t, mw_x_t_pi, mw_y_t_pi))]
                xy_8_part += [(['mw_y'], mw_y_t_pi), ([], t_bar(t, mw_x_t_pi, mw_y_t_pi))]
                xy_8_part += [(['mw_x'], mw_x_t_pi), ([], t_bar(t, mw_x_t_pi, mw_y_t_pi))]
                xy_8_part += [(['mw_y'], mw_y_t_pi), ([], t_bar(t, mw_y_t_pi, mw_y_t_pi))]
                xy_8_part += [(['mw_y'], mw_y_t_pi), ([], t_bar(t, mw_x_t_pi, mw_y_t_pi))]
                xy_8_part += [(['mw_x'], mw_x_t_pi), ([], t_bar(t, mw_x_t_pi, mw_y_t_pi))]
                xy_8_part += [(['mw_y'], mw_y_t_pi), ([], t_bar(t, mw_x_t_pi, mw_y_t_pi))]
                xy_8_part += [(['mw_x'], mw_x_t_pi)]

                start = [(['mw_x'], mw_x_t_pi2), ([], t_bar(t, mw_x_t_pi) / 2.)]
                end_pi2 = [([], t_bar(t, mw_x_t_pi) / 2.), (['mw_x'], mw_x_t_pi2)]
                end_3pi2 = [([], t_bar(t, mw_x_t_pi) / 2.), (['mw_x'], mw_x_t_3pi2)]

                # build the sequences
                sequence1_reference += start + (
                        (n - 1) * (
                        xy_8_part + [
                    ([], t_bar(t, mw_x_t_pi, mw_y_t_pi))])) + xy_8_part + end_pi2 + init
                sequence2_reference += start + (
                        (n - 1) * (
                        xy_8_part + [
                    ([], t_bar(t, mw_x_t_pi, mw_y_t_pi))])) + xy_8_part + end_3pi2 + init

            # join the two sequences
            sequence_reference = sequence1_reference + sequence2_reference

            """
            Build the reference sequence, i.e. the spin state with xy8 decoupling and rf pulses in
            dependence of interpulse spacing.
            """
            sequence1_signal = []
            sequence2_signal = []

            for mw_tau in self.tau:
                t = mw_tau / (8. * n)
                xy_8_rf_part = []
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
                sequence1_signal += start + (
                        (n - 1) * (xy_8_rf_part + [
                    ([], t_bar(t, mw_x_t_pi, mw_y_t_pi))])) + xy_8_rf_part + end_pi2 + init
                sequence2_signal += start + (
                        (n - 1) * (xy_8_rf_part + [
                    ([], t_bar(t, mw_x_t_pi, mw_y_t_pi))])) + xy_8_rf_part + end_3pi2 + init
            # join the two sequences
            sequence_signal = sequence1_signal + sequence2_signal
        # now, join reference and signal sequence
        sequence = sequence_reference + sequence_signal
        # tail of the sequence
        sequence += [(['sequence'], 100)]
        sequence = sequence_remove_zeros(sequence)

        return sequence

    def _create_line_plot(self):
        line_data = ArrayPlotData(index=np.array((0, 1)),
                                  first=np.array((0, 0)),
                                  second=np.array((0, 0)),
                                  third=np.array((0, 0)),
                                  fourth=np.array((0, 0)),
                                  )
        plot = Plot(line_data, padding=8, padding_left=80, padding_bottom=48)
        plot.plot(('index', 'first'), color='blue', name='first')
        plot.plot(('index', 'second'), color='green', name='second')
        plot.plot(('index', 'third'), color='red', name='third')
        plot.plot(('index', 'fourth'), color='black', name='fourth')
        plot.index_axis.title = 'time [micro s]'
        plot.value_axis.title = 'spin state'
        plot.tools.append(SaveTool(plot))
        self.line_data = line_data
        self.line_plot = plot

    def _update_line_plot_value(self):
        y = self.spin_state
        n = len(y) // 4
        first = y[:n]
        second = y[n:2 * n]
        third = y[2 * n:3 * n]
        fourth = y[3 * n:4 * n]
        try:
            self.line_data.set_data('first', first)
            self.line_data.set_data('second', second)
            self.line_data.set_data('third', third)
            self.line_data.set_data('fourth', fourth)
        except:
            logging.getLogger().debug('Could not set data for spin_state plots.')

    def _create_contrast_plot(self):
        contrast_data = ArrayPlotData(index=np.array((0, 1)), contrast=np.array((0, 0)))
        plot = Plot(contrast_data, padding=8, padding_left=80, padding_bottom=48)
        plot.plot(('index', 'contrast'), color='blue', name='contrast')
        plot.index_axis.title = 'time [micro s]'
        plot.value_axis.title = 'contrast'
        plot.tools.append(SaveTool(plot))
        self.contrast_data = contrast_data
        self.contrast_plot = plot

    def _update_contrast_plot_value(self):
        y = self.spin_state
        n = len(y) // 4
        first = y[:n]
        second = y[n:2 * n]
        third = y[2 * n:3 * n]
        fourth = y[3 * n:4 * n]
        contrast = (first - second) - (third - fourth)
        try:
            self.contrast_data.set_data('contrast', contrast)
        except:
            logging.getLogger().debug('Could not set data for spin_state plots.')

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
                                  Item('mw_frequency', width=-80, enabled_when='state != "run"'),
                                  Item('mw_power', width=-60, enabled_when='state != "run"'),
                              ),
                                  HGroup(Item('laser', width=-80,
                                              enabled_when='state != "run"'),
                                         Item('decay_init', width=-80,
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
                                         Item('decoupling_order', width=-80,
                                              enabled_when='state != "run"'),
                                         ),
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
                                     Item('contrast_plot', show_label=False, width=500, height=-300,
                                          resizable=True),
                                     ),
                              ),
                       title='Pi3diamond: DEER Signal Evolution Tau',
                       buttons=[],
                       resizable=True,
                       )


class DEEREvolutionRf(DEER):
    """Perform a measurement of DEER contrast with respect to the rf pulse delay.

    In principle we just perform a DEER measurement, yet the extension of this class is that we
    do an additional regular hahn and all in dependence of the rf pulse delay within the free
    evolution time of the decoupling sequence.
    """

    def generate_sequence(self):
        laser = self.laser
        n = self.decoupling_order
        decay_init = self.decay_init

        mw_x_t_pi2 = self.mw_x_t_pi2
        mw_x_t_3pi2 = self.mw_x_t_3pi2
        mw_y_t_pi = self.mw_y_t_pi
        mw_x_t_pi = self.mw_x_t_pi
        mw_tau = self.mw_tau

        rf_t_pi = self.rf_t_pi

        if n == 0:
            """
            In this case we just do a simple hahn echo with an rf in between
            mw_tau corresponds twice the time between the pi2 and pi pulse of the mw.
            The rf_pulse_delay can also be negative.
            """
            sequence1_reference = []
            sequence2_reference = []
            sequence1_signal = []
            sequence2_signal = []
            neg_tau = -1. * self.tau
            pos_tau = self.tau
            self.tau = np.append(neg_tau[::-1], pos_tau)
            for t in self.tau:
                rf_pulse_delay = t
                sequence1_reference += [(['mw_x'], mw_x_t_pi2), ([], 0.5 * mw_tau),
                                        (['mw_x'], mw_x_t_pi),
                                        ([], 0.5 * mw_tau), (['mw_x'], mw_x_t_pi2),
                                        (['detect', 'aom'], laser),
                                        ([], decay_init)]
                sequence2_reference += [(['mw_x'], mw_x_t_pi2), ([], 0.5 * mw_tau),
                                        (['mw_x'], mw_x_t_pi),
                                        ([], 0.5 * mw_tau), (['mw_x'], mw_x_t_3pi2),
                                        (['detect', 'aom'], laser),
                                        ([], decay_init)]
                if rf_pulse_delay >= 0.0:
                    sequence1_signal += [(['mw_x'], mw_x_t_pi2), ([], (0.5 * mw_tau)),
                                         (['mw_x'], mw_x_t_pi),
                                         ([], rf_pulse_delay), (['rf'], rf_t_pi),
                                         ([], (0.5 * mw_tau) - rf_pulse_delay - rf_t_pi),
                                         (['mw_x'], mw_x_t_pi2),
                                         (['detect', 'aom'], laser), ([], decay_init)]
                    sequence2_signal += [(['mw_x'], mw_x_t_pi2), ([], (0.5 * mw_tau)),
                                         (['mw_x'], mw_x_t_pi),
                                         ([], rf_pulse_delay), (['rf'], rf_t_pi),
                                         ([], (0.5 * mw_tau) - rf_pulse_delay - rf_t_pi),
                                         (['mw_x'], mw_x_t_3pi2),
                                         (['detect', 'aom'], laser), ([], decay_init)]
                if rf_pulse_delay < 0.0:
                    rf_pulse_delay = abs(rf_pulse_delay)
                    sequence1_signal += [(['mw_x'], mw_x_t_pi2),
                                         ([], (0.5 * mw_tau) - rf_pulse_delay - rf_t_pi),
                                         (['rf'], rf_t_pi), ([], rf_pulse_delay),
                                         (['mw_x'], mw_x_t_pi),
                                         ([], (0.5 * mw_tau)), (['mw_x'], mw_x_t_pi2),
                                         (['detect', 'aom'], laser), ([], decay_init)]
                    sequence2_signal += [(['mw_x'], mw_x_t_pi2),
                                         ([], (0.5 * mw_tau) - rf_pulse_delay - rf_t_pi),
                                         (['rf'], rf_t_pi), ([], rf_pulse_delay),
                                         (['mw_x'], mw_x_t_pi),
                                         ([], (0.5 * mw_tau)), (['mw_x'], mw_x_t_3pi2),
                                         (['detect', 'aom'], laser), ([], decay_init)]
            sequence_reference = sequence1_reference + sequence2_reference
            sequence_signal = sequence1_signal + sequence2_signal
        else:
            """In this case we just do xy8_n-DD, with an rf pulse in between. We use the tau array
            to shift around the rf pulse within each free evolution time, since a negative
            rf_pulse_delay makes no sense here.
            t corresponds to the time/8*n the sequence takes. This time is used in NMR analysis
            and since our xy8 measurements are using this time we use it here as well.
            """
            # This lambda function gives correct time for approximation of infinitely short pulses
            t_bar = lambda t, p1, p2=0., p3=0., p4=0.: t - (p1 / 2.) - (p2 / 2.) - p3 - p4
            """
            Build the reference sequence, i.e. the spin state with xy8 decoupling in dependence of
            interpulse spacing.
            """
            sequence1_reference = []
            sequence2_reference = []

            init = [(['detect', 'aom'], laser), ([], decay_init)]
            for rf_pulse_delay in self.tau:
                # t is the time between the infinitely short xy8 pulses
                t = mw_tau / (8. * n)
                # check, if the start time is long enough to fit at least the mw pulses in it.
                if t_bar(t, mw_y_t_pi, mw_y_t_pi, rf_pulse_delay, rf_t_pi) < 0 or \
                        t_bar(t, mw_x_t_pi, mw_x_t_pi, rf_pulse_delay, rf_t_pi) < 0:
                    raise IOError('The delay between pulses is too short. It has to be larger than'
                                  'the pulse_duration')
                xy_8_part = []
                xy_8_part += [(['mw_x'], mw_x_t_pi), ([], t_bar(t, mw_x_t_pi, mw_y_t_pi))]
                xy_8_part += [(['mw_y'], mw_y_t_pi), ([], t_bar(t, mw_x_t_pi, mw_y_t_pi))]
                xy_8_part += [(['mw_x'], mw_x_t_pi), ([], t_bar(t, mw_x_t_pi, mw_y_t_pi))]
                xy_8_part += [(['mw_y'], mw_y_t_pi), ([], t_bar(t, mw_y_t_pi, mw_y_t_pi))]
                xy_8_part += [(['mw_y'], mw_y_t_pi), ([], t_bar(t, mw_x_t_pi, mw_y_t_pi))]
                xy_8_part += [(['mw_x'], mw_x_t_pi), ([], t_bar(t, mw_x_t_pi, mw_y_t_pi))]
                xy_8_part += [(['mw_y'], mw_y_t_pi), ([], t_bar(t, mw_x_t_pi, mw_y_t_pi))]
                xy_8_part += [(['mw_x'], mw_x_t_pi)]

                start = [(['mw_x'], mw_x_t_pi2), ([], t_bar(t, mw_x_t_pi) / 2.)]
                end_pi2 = [([], t_bar(t, mw_x_t_pi) / 2.), (['mw_x'], mw_x_t_pi2)]
                end_3pi2 = [([], t_bar(t, mw_x_t_pi) / 2.), (['mw_x'], mw_x_t_3pi2)]

                # build the sequences
                sequence1_reference += start + (
                        (n - 1) * (
                        xy_8_part + [
                    ([], t_bar(t, mw_x_t_pi, mw_y_t_pi))])) + xy_8_part + end_pi2 + init
                sequence2_reference += start + (
                        (n - 1) * (
                        xy_8_part + [
                    ([], t_bar(t, mw_x_t_pi, mw_y_t_pi))])) + xy_8_part + end_3pi2 + init

            # join the two sequences
            sequence_reference = sequence1_reference + sequence2_reference

            """
            Build the reference sequence, i.e. the spin state with xy8 decoupling and rf pulses in
            dependence of interpulse spacing.
            """
            sequence1_signal = []
            sequence2_signal = []

            for rf_pulse_delay in self.tau:
                t = mw_tau / (8. * n)
                xy_8_rf_part = []
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
                sequence1_signal += start + (
                        (n - 1) * (xy_8_rf_part + [
                    ([], t_bar(t, mw_x_t_pi, mw_y_t_pi))])) + xy_8_rf_part + end_pi2 + init
                sequence2_signal += start + (
                        (n - 1) * (xy_8_rf_part + [
                    ([], t_bar(t, mw_x_t_pi, mw_y_t_pi))])) + xy_8_rf_part + end_3pi2 + init
            # join the two sequences
            sequence_signal = sequence1_signal + sequence2_signal
        # now, join reference and signal sequence
        sequence = sequence_reference + sequence_signal
        # tail of the sequence
        sequence += [(['sequence'], 100)]
        sequence = sequence_remove_zeros(sequence)

        return sequence

    def _create_line_plot(self):
        line_data = ArrayPlotData(index=np.array((0, 1)),
                                  first=np.array((0, 0)),
                                  second=np.array((0, 0)),
                                  third=np.array((0, 0)),
                                  fourth=np.array((0, 0)),
                                  )
        plot = Plot(line_data, padding=8, padding_left=80, padding_bottom=48)
        plot.plot(('index', 'first'), color='blue', name='first')
        plot.plot(('index', 'second'), color='green', name='second')
        plot.plot(('index', 'third'), color='red', name='third')
        plot.plot(('index', 'fourth'), color='black', name='fourth')
        plot.index_axis.title = 'time [micro s]'
        plot.value_axis.title = 'spin state'
        plot.tools.append(SaveTool(plot))
        self.line_data = line_data
        self.line_plot = plot

    def _update_line_plot_value(self):
        y = self.spin_state
        n = len(y) // 4
        first = y[:n]
        second = y[n:2 * n]
        third = y[2 * n:3 * n]
        fourth = y[3 * n:4 * n]
        try:
            self.line_data.set_data('first', first)
            self.line_data.set_data('second', second)
            self.line_data.set_data('third', third)
            self.line_data.set_data('fourth', fourth)
        except:
            logging.getLogger().debug('Could not set data for spin_state plots.')

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
                                  Item('mw_frequency', width=-80, enabled_when='state != "run"'),
                                  Item('mw_power', width=-60, enabled_when='state != "run"'),
                              ),
                                  HGroup(Item('laser', width=-80,
                                              enabled_when='state != "run"'),
                                         Item('decay_init', width=-80,
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
                                         Item('decoupling_order', width=-80,
                                              enabled_when='state != "run"'),
                                         Item('mw_tau', width=-80,
                                              enabled_when='state != "run"'),
                                         ),
                                  HGroup(Item('rf_frequency', width=-120,
                                              enabled_when='state != "run"'),
                                         Item('rf_power', width=-80,
                                              enabled_when='state != "run"'),
                                         Item('rf_t_pi', width=-80,
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
                       title='Pi3diamond: DEER Signal Evolution RF',
                       buttons=[],
                       resizable=True,
                       )


class DEERDQT(DEER):
    """This class performs a DEER measurement utilizing the double quantum transition.

    Requirements are that we have a second microwave source (in our case that is a second LabBrick),
    so we are able to drive the |0> - |-1> and |0> - |1> transitions in quick succession!
    The class inherits everything from regular DEER and we just need to change the sequence
    to operate on the double quantum transition.
    """

    mw2_frequency = Range(low=1, high=20e9, value=2.8705e9, desc='microwave 2 frequency',
                          label='MW2 frequency [Hz]', mode='text', auto_set=False, enter_set=True,
                          editor=TextEditor(auto_set=False, enter_set=True, evaluate=float,
                                            format_str='%.5e'))
    mw2_power = Range(low=-100., high=25., value=-20, desc='microwave power',
                      label='MW2 power [dBm]', mode='text', auto_set=False, enter_set=True)
    mw2_x_t_pi2 = Range(low=1., high=1e6, value=25., desc='pi/2 pulse length',
                        label='MW2 pi/2 [ns]', mode='text', auto_set=False, enter_set=True)
    mw2_x_t_pi = Range(low=1., high=1e6, value=50., desc='pi pulse length', label='MW2 pi [ns]',
                       mode='text', auto_set=False, enter_set=True)
    mw2_x_t_3pi2 = Range(low=1., high=1e6, value=100., desc='3pi/2 pulse length',
                         label='MW2 3pi/2 [ns]', mode='text', auto_set=False, enter_set=True)
    interpulse_delay = Range(low=0., high=10000., value=15.0, desc='interpulse delay',
                             label='MW interpulse delay [dBm]', mode='text', auto_set=False,
                             enter_set=True)

    def __init__(self, pulse_generator, time_tagger, microwave, microwave2, rf, **kwargs):
        super(DEERDQT, self).__init__(pulse_generator, time_tagger, microwave, rf, **kwargs)
        self.microwave2 = microwave2

    def start_up(self):
        self.pulse_generator.Night()
        self.microwave.setOutput(self.mw_power, self.mw_frequency)
        self.microwave2.setOutput(self.mw2_power, self.mw2_frequency)
        self.rf.setPower(self.rf_power)

    def shut_down(self):
        self.pulse_generator.Light()
        self.microwave.setOutput(None, self.mw_frequency)
        self.microwave2.setOutput(None, self.mw_frequency)
        self.rf.setOutput(None, self.rf_begin)

    def generate_sequence(self):
        """ We generate a Deer frequency sequence conditional on the user input.
        Here we use two microwave sources to sense with the double quantum transition.
        CHANGE IN OTHER CLASSES.
        :return: Sequence string
        """
        # Values for the NV center DQT:
        mw_tau = self.mw_tau
        decay_init = self.decay_init
        laser = self.laser
        mw_x_t_pi2 = self.mw_x_t_pi2
        mw_x_t_pi = self.mw_x_t_pi
        mw2_x_t_pi = self.mw2_x_t_pi
        ip_delay = self.interpulse_delay

        # Defining the RF sequence:
        rf_t_pi = self.rf_t_pi
        rf_pulse_delay = float(self.rf_pulse_delay)

        sequence = []

        if rf_pulse_delay != 0.0:
            sequence += [(['microwave'], mw_x_t_pi2), ([], ip_delay),
                         (['microwave2'], mw2_x_t_pi),
                         ([], 0.5 * mw_tau),
                         (['microwave2'], mw2_x_t_pi), ([], ip_delay), (['microwave'], mw_x_t_pi),
                         ([], ip_delay), (['microwave2'], mw2_x_t_pi),
                         ([], rf_pulse_delay), (['rf'], rf_t_pi),
                         ([], 0.5 * mw_tau - rf_t_pi - rf_pulse_delay),
                         (['microwave2'], mw2_x_t_pi), ([], ip_delay), (['microwave'], mw_x_t_pi2),
                         (['detect', 'aom'], laser), ([], decay_init)]
        else:
            sequence += [(['microwave'], mw_x_t_pi2), ([], ip_delay),
                         (['microwave2'], mw2_x_t_pi),
                         ([], 0.5 * mw_tau),
                         (['microwave2'], mw2_x_t_pi), ([], ip_delay), (['microwave'], mw_x_t_pi),
                         ([], ip_delay), (['microwave2'], mw2_x_t_pi),
                         (['rf'], rf_t_pi), ([], 0.5 * mw_tau - rf_t_pi),
                         (['microwave2'], mw2_x_t_pi), ([], ip_delay), (['microwave'], mw_x_t_pi2),
                         (['detect', 'aom'], laser), ([], decay_init)]
        sequence += [(['sequence'], 100)]

        # Removing zeros from sequences:
        sequence = sequence_remove_zeros(sequence)

        sequence *= 100
        return sequence

    get_set_items = DEER.get_set_items + ['mw2_frequency', 'mw2_power', 'mw2_x_t_pi',
                                          'interpulse_delay']

    traits_view = View(VGroup(HGroup(Item('submit_button', show_label=False),
                                     Item('remove_button', show_label=False),
                                     Item('resubmit_button', show_label=False),
                                     Item('get_global_vars_button', show_label=False),
                                     Item('priority', enabled_when='state != "run"'),
                                     Item('state', style='readonly'),
                                     Item('run_time', style='readonly', format_str='%.f'),
                                     Item('stop_time'),
                                     Item('stop_counts'),
                                     ),
                              HGroup(Item('filename', springy=True),
                                     Item('save_button', show_label=False),
                                     Item('load_button', show_label=False),
                                     ),
                              Tabbed(VGroup(HGroup(Item('laser', width=-80,
                                                        enabled_when='state != "run"'),
                                                   Item('decay_init', width=-80,
                                                        enabled_when='state != "run"'),
                                                   Item('integration_width', width=-40),
                                                   Item('position_signal', width=-40),
                                                   Item('position_normalize', width=-40),
                                                   Item('seconds_per_point', width=-40,
                                                        enabled_when='state != "run"'),
                                                   ),
                                            HGroup(Item('mw_power', width=-40,
                                                        enabled_when='state != "run"'),
                                                   Item('mw_frequency', width=-80,
                                                        enabled_when='state != "run"'),
                                                   Item('mw_x_t_pi2', width=-40,
                                                        enabled_when='state != "run"'),
                                                   Item('mw_x_t_pi', width=-40,
                                                        enabled_when='state != "run"'),
                                                   Item('mw_tau', width=-40,
                                                        enabled_when='state != "run"'),
                                                   ),
                                            HGroup(Item('mw2_power', width=-40,
                                                        enabled_when='state != "run"'),
                                                   Item('mw2_frequency', width=-80,
                                                        enabled_when='state != "run"'),
                                                   Item('mw2_x_t_pi', width=-40,
                                                        enabled_when='state != "run"'),
                                                   ),
                                            HGroup(Item('rf_t_pi', width=-80,
                                                        enabled_when='state != "run"'),
                                                   Item('rf_pulse_delay', width=-80,
                                                        enabled_when='state != "run"'),
                                                   ),
                                            HGroup(Item('perform_fit'),
                                                   Item('calculate_center'),
                                                   Item('number_of_resonances', width=-60),
                                                   Item('threshold', width=-60),
                                                   ),
                                            HGroup(Item('fit_contrast', style='readonly'),
                                                   Item('fit_line_width', style='readonly'),
                                                   Item('fit_frequencies', style='readonly'),
                                                   ),
                                            label='measurement parameters'
                                            ),
                                     VGroup(HGroup(Item('record_length', width=-80,
                                                        enabled_when='state != "run"'),
                                                   Item('bin_width', width=-80,
                                                        enabled_when='state != "run"'),
                                                   ),
                                            label='acquisition'
                                            ),
                                     ),
                              VSplit(Item('matrix_plot', show_label=False, resizable=True),
                                     Item('line_plot', show_label=False, resizable=True),
                                     ),
                              ),
                       title='Pi3diamond: DEER Spectroscopy DQT', width=940, height=400, buttons=[],
                       resizable=True, x=800, y=220
                       )


if __name__ == '__main__':
    pass
