import time

from traits.api import Range, Int, Float
from traitsui.api import View, Item, Tabbed, HGroup, VGroup, TextEditor

from measurements.pulsed import Pulsed, sequence_remove_zeros


class DEER(Pulsed):
    debug = True

    """Values, that define a DEER - measurement
    First, values that define the XY-8 Part of the DEER Sequence. Pulse Calibration with initial and
    final pi/2_x pulses, pi_x and pi_y pulse sequences.
    """
    mw_frequency = Range(low=1e9, high=10e9, value=2.8705e9, desc='microwave frequency',
                         label='Microwave frequency [Hz]', mode='text', auto_set=False,
                         enter_set=True, editor=TextEditor(auto_set=False, enter_set=True,
                                                           evaluate=float, format_str='%e'))
    mw_power = Range(low=-100., high=25., value=-10, desc='microwave power', label='power [dBm]',
                     mode='text', auto_set=False, enter_set=True)
    laser = Float(default_value=3000., desc='laser [ns]', label='laser [ns]', mode='text', auto_set=False,
                  enter_set=True)
    decay_init = Float(default_value=250., desc='time to let the system decay after laser pulse [ns]',
                       label='decay init [ns]', mode='text', auto_set=False, enter_set=True)
    decay_read = Float(default_value=0., desc='time to let the system decay before laser pulse [ns]',
                       label='decay read [ns]', mode='text', auto_set=False, enter_set=True)
    aom_delay = Float(default_value=0., desc='If set to a value other than 0.0, the aom triggers are applied\n'
                                             'earlier by the specified value. Use with care!', label='aom delay [ns]',
                      mode='text', auto_set=False, enter_set=True)
    mx_x_t_pi2 = Range(low=0., high=100000., value=50., desc='pi/2 pulse length (x)',
                       label='pi/2 x [ns]', mode='text', auto_set=False, enter_set=True)
    mx_x_t_3pi2 = Range(low=0., high=100000., value=150., desc='3pi/2 pulse length (x)',
                        label='3pi/2 x [ns]', mode='text', auto_set=False, enter_set=True)
    mx_y_t_pi = Range(low=1., high=100000., value=100., desc='pi pulse length (y)', label='pi y [ns]',
                      mode='text', auto_set=False, enter_set=True)
    mx_x_t_pi = Range(low=1., high=100000., value=100., desc='pi pulse length (x)', label='pi x [ns]',
                      mode='text', auto_set=False, enter_set=True)
    power_imbalance = Range(low=-1., high=1., value=0., desc='microwave power imbalance',
                            label='power imbalance [dBm]', mode='text', auto_set=False,
                            enter_set=True)
    n_sequences = Int(default_value=0, desc='number of XY_8-Sequences', label='n_seq', mode='text',
                      auto_set=False, enter_set=True)
    mw_tau = Float(default_value=2000, desc='time between pi pulses[ns]', label='mw_tau [ns]',
                   mode='text', auto_set=False, enter_set=True)
    # laser      = Float(default_value=3000., desc='laser [ns]',      label='laser [ns]',       mode='text', auto_set=False, enter_set=True)
    # decay_init = Float(default_value=1000., desc='time to let the system decay after laser pulse [ns]',       label='decay init [ns]',        mode='text', auto_set=False, enter_set=True)
    # decay_read = Float(default_value=0.,    desc='time to let the system decay before laser pulse [ns]',       label='decay read [ns]',        mode='text', auto_set=False, enter_set=True)
    # aom_delay  = Float(default_value=0.,    desc='If set to a value other than 0.0, the aom triggers are applied\nearlier by the specified value. Use with care!', label='aom delay [ns]', mode='text', auto_set=False, enter_set=True)
    """Values that define the RF e-Spin excitation in the DEER sequence."""
    rf_frequency = Range(low=70.e6, high=450.e6, value=70.e6, desc='RF frequency',
                         label='RF frequency [Hz]', mode='text', auto_set=False, enter_set=True,
                         editor=TextEditor(auto_set=False, enter_set=True, evaluate=float,
                                           format_str='%e')
                         )
    rf_power = Range(low=-60., high=0., value=-35., desc='rf power',
                     label='RF Power [dBm]', mode='text', auto_set=False, enter_set=True)
    rf_t_pi = Float(default_value=200., desc='length of pi pulse of RF[ns]', label='RF pi [ns]',
                    mode='text', auto_set=False, enter_set=True)
    rf_pulse_delay = Float(default_value=15., desc='wait between mw and rf pulse[ns]',
                           label='RF wait [ns]', mode='text', auto_set=False, enter_set=True)

    def __init__(self, pulse_generator, time_tagger, microwave, rf, **kwargs):
        super(DEER, self).__init__(pulse_generator, time_tagger, **kwargs)
        self.microwave = microwave
        self.rf = rf

    def start_up(self):
        self.pulse_generator.Night()
        self.microwave.setOutput(self.mw_power, self.mw_frequency)
        time.sleep(0.1)
        self.rf.setFrequency(self.rf_frequency)
        time.sleep(0.1)
        self.rf.setPower(self.rf_power)

        # if self.power_imbalance != 0:
        # self.microwave.set_stat_ImpairmentIQ('ON')
        # self.microwave.set_Gain_Imbalance_IQ(self.power_imbalance)

    def shut_down(self):
        self.pulse_generator.Light()
        self.microwave.setOutput(-40, self.mw_frequency)
        time.sleep(0.1)
        self.rf.setPower(-40)
        # self.microwave.set_Gain_Imbalance_IQ(0.)
        # self.microwave.set_stat_ImpairmentIQ('OFF')

    def generate_sequence(self):
        mw_tau = self.mw_tau
        laser = self.laser
        n = self.n_sequences
        decay_init = self.decay_init

        mx_x_t_pi2 = self.mx_x_t_pi2
        mx_x_t_3pi2 = self.mx_x_t_3pi2
        mx_y_t_pi = self.mx_y_t_pi
        mx_x_t_pi = self.mx_x_t_pi

        rf_pulse_delay = self.rf_pulse_delay
        rf_t_pi = self.rf_t_pi

        sequence = []
        if n == 0:
            """In this case we just do a simple hahn echo with an rf in between
            mw_tau corresponds to twice the time between the pi2 and pi pulse of the mw.
            """
            sequence1_signal = [(['mw_x'], mx_x_t_pi2), ([], rf_pulse_delay), (['rf'], rf_t_pi),
                                ([], (0.5 * mw_tau) - rf_pulse_delay - rf_t_pi), (['mw_x'], mx_x_t_pi),
                                ([], rf_pulse_delay),
                                (['rf'], rf_t_pi), ([], (0.5 * mw_tau) - rf_pulse_delay - rf_t_pi),
                                (['mw_x'], mx_x_t_pi2),
                                (['detect', 'aom'], laser), ([], decay_init)]
            sequence2_signal = [(['mw_x'], mx_x_t_pi2), ([], rf_pulse_delay), (['rf'], rf_t_pi),
                                ([], (0.5 * mw_tau) - rf_pulse_delay - rf_t_pi), (['mw_x'], mx_x_t_pi),
                                ([], rf_pulse_delay),
                                (['rf'], rf_t_pi), ([], (0.5 * mw_tau) - rf_pulse_delay - rf_t_pi),
                                (['mw_x'], mx_x_t_3pi2),
                                (['detect', 'aom'], laser), ([], decay_init)]
            sequence = sequence1_signal + sequence2_signal
        else:
            """In this case we just do xy8_n-DD, with an rf pulse in between each mw_tau
            mw_tau corresponds to the time/8*n the sequence takes. This time is used in NMR analysis
            and since our xy8 measurements are using this time we use it here as well.
            """
            # t is the time between the infinitely short xy8 pulses
            t = mw_tau / (8. * n)
            # This lambda function gives correct mw_tau for the approximation of infinetly short pulses
            t_bar = lambda t, p1, p2=0., p3=0., p4=0.: t - (p1 / 2.) - (p2 / 2.) - p3 - p4
            # check, if the start time is long enough to fit at least the mw pulses in it.
            if t_bar(t, mx_y_t_pi, mx_y_t_pi, rf_pulse_delay, rf_t_pi) < 0 or t_bar(t, mx_x_t_pi, mx_x_t_pi,
                                                                                    rf_pulse_delay, rf_t_pi) < 0:
                raise IOError('The delay between pulses is too short. It has to be larger than the pulse_duration')
            """
            Build the signal sequence, i.e. the spin state with applied rf at a specific mw_tau with xy8
            decoupling.
            """
            sequence1_signal = []
            sequence2_signal = []

            xy_8_rf_part = []
            init = [(['detect', 'aom'], laser), ([], decay_init)]

            xy_8_rf_part += [(['mw_x'], mx_x_t_pi), ([], rf_pulse_delay), (['rf'], rf_t_pi),
                             ([], t_bar(t, mx_x_t_pi, mx_y_t_pi, rf_pulse_delay, rf_t_pi))]
            xy_8_rf_part += [(['mw_y'], mx_y_t_pi), ([], rf_pulse_delay), (['rf'], rf_t_pi),
                             ([], t_bar(t, mx_x_t_pi, mx_y_t_pi, rf_pulse_delay, rf_t_pi))]
            xy_8_rf_part += [(['mw_x'], mx_x_t_pi), ([], rf_pulse_delay), (['rf'], rf_t_pi),
                             ([], t_bar(t, mx_x_t_pi, mx_y_t_pi, rf_pulse_delay, rf_t_pi))]
            xy_8_rf_part += [(['mw_y'], mx_y_t_pi), ([], rf_pulse_delay), (['rf'], rf_t_pi),
                             ([], t_bar(t, mx_y_t_pi, mx_y_t_pi, rf_pulse_delay, rf_t_pi))]
            xy_8_rf_part += [(['mw_y'], mx_y_t_pi), ([], rf_pulse_delay), (['rf'], rf_t_pi),
                             ([], t_bar(t, mx_x_t_pi, mx_y_t_pi, rf_pulse_delay, rf_t_pi))]
            xy_8_rf_part += [(['mw_x'], mx_x_t_pi), ([], rf_pulse_delay), (['rf'], rf_t_pi),
                             ([], t_bar(t, mx_x_t_pi, mx_y_t_pi, rf_pulse_delay, rf_t_pi))]
            xy_8_rf_part += [(['mw_y'], mx_y_t_pi), ([], rf_pulse_delay), (['rf'], rf_t_pi),
                             ([], t_bar(t, mx_x_t_pi, mx_y_t_pi, rf_pulse_delay, rf_t_pi))]
            xy_8_rf_part += [(['mw_x'], mx_x_t_pi)]

            start = [(['mw_x'], mx_x_t_pi2), ([], t_bar(t, mx_x_t_pi) / 2.)]
            end_pi2 = [([], t_bar(t, mx_x_t_pi) / 2.), (['mw_x'], mx_x_t_pi2)]
            end_3pi2 = [([], t_bar(t, mx_x_t_pi) / 2.), (['mw_x'], mx_x_t_3pi2)]

            # build the sequences
            sequence1_signal += start + (
                    (n - 1) * (xy_8_rf_part + [([], rf_pulse_delay), (['rf'], rf_t_pi), (
                [], t_bar(t, mx_x_t_pi, mx_x_t_pi, rf_pulse_delay, rf_t_pi))])) + xy_8_rf_part + end_pi2 + init
            sequence2_signal += start + (
                    (n - 1) * (xy_8_rf_part + [([], rf_pulse_delay), (['rf'], rf_t_pi), (
                [], t_bar(t, mx_x_t_pi, mx_x_t_pi, rf_pulse_delay, rf_t_pi))])) + xy_8_rf_part + end_3pi2 + init
            # join the two sequences
            sequence = sequence1_signal + sequence2_signal

        # tail of the sequence
        sequence += [(['sequence'], 100)]
        sequence = sequence_remove_zeros(sequence)

        return sequence

    get_set_items = Pulsed.get_set_items + ['mx_x_t_pi2', 'mx_y_t_pi', 'n_sequences', 'mx_x_t_pi', 'mx_x_t_3pi2',
                                            'mw_tau',
                                            'rf_frequency', 'rf_power', 'rf', 'rf_t_pi', 'rf_pulse_delay']

    traits_view = View(VGroup(HGroup(Item('submit_button', show_label=False),
                                     Item('remove_button', show_label=False),
                                     Item('resubmit_button', show_label=False),
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
                              Tabbed(VGroup(HGroup(Item('mw_frequency', width=-120, enabled_when='state != "run"'),
                                                   Item('mw_power', width=-60, enabled_when='state != "run"'),
                                                   ),
                                            HGroup(Item('laser', width=-80, enabled_when='state != "run"'),
                                                   Item('decay_init', width=-80, enabled_when='state != "run"'),
                                                   # Item('decay_read',    width=-80, enabled_when='state != "run"'),
                                                   ),
                                            HGroup(Item('mx_x_t_pi2', width=-80, enabled_when='state != "run"'),
                                                   Item('mx_x_t_pi', width=-80, enabled_when='state != "run"'),
                                                   Item('mx_y_t_pi', width=-80, enabled_when='state != "run"'),
                                                   Item('mx_x_t_3pi2', width=-80, enabled_when='state != "run"'),
                                                   Item('n_sequences', width=-80, enabled_when='state != "run"'),
                                                   Item('mw_tau', width=-80, enabled_when='state != "run"'), ),
                                            HGroup(Item('rf_frequency', width=-120, enabled_when='state != "run"'),
                                                   Item('rf_power', width=-80, enabled_when='state != "run"'),
                                                   Item('rf_t_pi', width=-80, enabled_when='state != "run"'),
                                                   Item('rf_pulse_delay', width=-80, enabled_when='state != "run"'),
                                                   ),
                                            #       label='stimulation'),
                                            # VGroup(HGroup(Item('record_length', width=-80, enabled_when='state != "run"'),
                                            #              Item('bin_width',     width=-80, enabled_when='state != "run"'),
                                            #             ),
                                            label='acquisition'),
                                     VGroup(HGroup(Item('integration_width'),
                                                   Item('position_signal'),
                                                   Item('position_normalize'),
                                                   ),
                                            label='analysis'),
                                     ),
                              ),
                       title='DEER Measurement',
                       )


if __name__ == '__main__':
    pass
