import time

from traits.api import Range, Int, Float
from traitsui.api import View, Item, Tabbed, HGroup, VGroup, TextEditor

from measurements.pulsed import Pulsed, sequence_remove_zeros


class DEER(Pulsed):
    debug = True

    """Values, that define a DEER - measurement"""

    """Values that define the XY-8 Part of the DEER Sequence. Pulse Calibration with initial and
    final pi/2_x pulses, pi_x and pi_y pulse sequences and bright / dark reference.
    """
    mw_frequency = Range(low=1e9, high=10e9, value=2.8705e9, desc='microwave frequency',
                         label='Microwave frequency [Hz]', mode='text', auto_set=False,
                         enter_set=True, editor=TextEditor(auto_set=False, enter_set=True,
                                                           evaluate=float, format_str='%e')
                         )
    mw_power = Range(low=-100., high=25., value=-20, desc='microwave power', label='power [dBm]',
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
    t_3pi2_x = Range(low=0., high=100000., value=100., desc='3pi/2 pulse length (x)',
                     label='3pi/2 x [ns]', mode='text', auto_set=False, enter_set=True)
    t_pi_y = Range(low=1., high=100000., value=100., desc='pi pulse length (y)', label='pi y [ns]',
                   mode='text', auto_set=False, enter_set=True)
    t_pi_x = Range(low=1., high=100000., value=150., desc='pi pulse length (x)', label='pi x [ns]',
                   mode='text', auto_set=False, enter_set=True)
    power_imbalance = Range(low=-1., high=1., value=0., desc='microwave power imbalance',
                            label='power imbalance [dBm]', mode='text', auto_set=False,
                            enter_set=True)
    n_sequences = Int(default_value=0, desc='number of XY_8-Sequences', label='n_seq', mode='text',
                      auto_set=False, enter_set=True)
    tau = Float(default_value=2000, desc='time between pi pulses[ns]', label='tau [ns]',
                mode='text', auto_set=False, enter_set=True)

    # laser      = Float(default_value=3000., desc='laser [ns]',      label='laser [ns]',       mode='text', auto_set=False, enter_set=True)
    # decay_init = Float(default_value=1000., desc='time to let the system decay after laser pulse [ns]',       label='decay init [ns]',        mode='text', auto_set=False, enter_set=True)
    # decay_read = Float(default_value=0.,    desc='time to let the system decay before laser pulse [ns]',       label='decay read [ns]',        mode='text', auto_set=False, enter_set=True)

    # aom_delay  = Float(default_value=0.,    desc='If set to a value other than 0.0, the aom triggers are applied\nearlier by the specified value. Use with care!', label='aom delay [ns]', mode='text', auto_set=False, enter_set=True)

    """"Values that define the RF e-Spin excitation in the DEER sequence."""
    rf_frequency = Range(low=70.e6, high=450.e6, value=220.e6, desc='RF frequency',
                         label='RF frequency [Hz]', mode='text', auto_set=False, enter_set=True,
                         editor=TextEditor(auto_set=False, enter_set=True, evaluate=float,
                                           format_str='%e')
                         )
    rf_power = Range(low=-40., high=-3., value=-30., desc='rf power',
                     label='RF Power [dBm]', mode='text', auto_set=False, enter_set=True)
    t_rf_pi = Float(default_value=100., desc='length of pi pulse of RF[ns]', label='RF pi [ns]',
                    mode='text', auto_set=False, enter_set=True)
    t_rf_wait = Float(default_value=15., desc='wait between mw and rf pulse[ns]',
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
        tau = self.tau
        laser = self.laser
        n = self.n_sequences
        decay_init = self.decay_init

        t_pi2_x = self.t_pi2_x
        t_3pi2_x = self.t_3pi2_x
        t_pi_y = self.t_pi_y
        t_pi_x = self.t_pi_x

        t_rf_wait = self.t_rf_wait
        t_rf_pi = self.t_rf_pi

        if n == 0:
            """In this case we just do a simple hahn echo with an rf in between
            tau corresponds twice the time between the pi2 and pi pulse of the mw.
            """
            sequence_pi2 = [(['mw_x'], t_pi2_x), ([], t_rf_wait), (['rf'], t_rf_pi),
                            ([], (0.5 * tau) - t_rf_wait - t_rf_pi), (['mw_x'], t_pi_x), ([], t_rf_wait),
                            (['rf'], t_rf_pi), ([], (0.5 * tau) - t_rf_wait - t_rf_pi), (['mw_x'], t_pi2_x),
                            (['detect', 'aom'], laser), ([], decay_init)]
            sequence_3pi2 = [(['mw_x'], t_pi2_x), ([], t_rf_wait), (['rf'], t_rf_pi),
                             ([], (0.5 * tau) - t_rf_wait - t_rf_pi), (['mw_x'], t_pi_x), ([], t_rf_wait),
                             (['rf'], t_rf_pi), ([], (0.5 * tau) - t_rf_wait - t_rf_pi), (['mw_x'], t_3pi2_x),
                             (['detect', 'aom'], laser), ([], decay_init)]
            sequence = sequence_pi2 + sequence_3pi2
        else:
            """In this case we just do xy8_n-DD, with an rf pulse in between each tau
            tau corresponds to the time/8*n the sequence takes. This time is used in NMR analysis
            and since our xy8 measurements are using this time we use it here as well.
            """
            # t is the time between the infinitely short xy8 pulses
            t = tau / (8. * n)
            # This lambda function gives correct tau for the approximation of infinetly short pulses
            t_bar = lambda t, p1, p2=0., p3=0., p4=0.: t - (p1 / 2.) - (p2 / 2.) - p3 - p4
            # check, if the start time is long enough to fit at least the mw pulses in it.
            if t_bar(t, t_pi_y, t_pi_y, t_rf_wait, t_rf_pi) < 0 or t_bar(t, t_pi_x, t_pi_x, t_rf_wait, t_rf_pi) < 0:
                raise IOError('The delay between pulses is too short. It has to be larger than the pulse_duration')

            sequence = []

            """
            Build the signal sequence, i.e. the spin state with applied rf at a specific tau with xy8
            decoupling.
            """

            xy_8_rf_part = []
            init = [(['detect', 'aom'], laser), ([], decay_init)]

            xy_8_rf_part += [(['mw_x'], t_pi_x), ([], t_rf_wait), (['rf'], t_rf_pi),
                             ([], t_bar(t, t_pi_x, t_pi_y, t_rf_wait, t_rf_pi))]
            xy_8_rf_part += [(['mw_y'], t_pi_y), ([], t_rf_wait), (['rf'], t_rf_pi),
                             ([], t_bar(t, t_pi_x, t_pi_y, t_rf_wait, t_rf_pi))]
            xy_8_rf_part += [(['mw_x'], t_pi_x), ([], t_rf_wait), (['rf'], t_rf_pi),
                             ([], t_bar(t, t_pi_x, t_pi_y, t_rf_wait, t_rf_pi))]
            xy_8_rf_part += [(['mw_y'], t_pi_y), ([], t_rf_wait), (['rf'], t_rf_pi),
                             ([], t_bar(t, t_pi_y, t_pi_y, t_rf_wait, t_rf_pi))]
            xy_8_rf_part += [(['mw_y'], t_pi_y), ([], t_rf_wait), (['rf'], t_rf_pi),
                             ([], t_bar(t, t_pi_x, t_pi_y, t_rf_wait, t_rf_pi))]
            xy_8_rf_part += [(['mw_x'], t_pi_x), ([], t_rf_wait), (['rf'], t_rf_pi),
                             ([], t_bar(t, t_pi_x, t_pi_y, t_rf_wait, t_rf_pi))]
            xy_8_rf_part += [(['mw_y'], t_pi_y), ([], t_rf_wait), (['rf'], t_rf_pi),
                             ([], t_bar(t, t_pi_x, t_pi_y, t_rf_wait, t_rf_pi))]
            xy_8_rf_part += [(['mw_x'], t_pi_x)]

            start = [(['mw_x'], t_pi2_x), ([], t_rf_wait), (['rf'], t_rf_pi),
                     ([], t_bar(t / 2., t_pi_x, p3=t_rf_wait, p4=t_rf_pi))]
            end_pi2 = [([], t_bar(t, t_pi_x) / 2. - t_rf_wait - t_rf_pi), (['mw_x'], t_pi2_x)]
            end_3pi2 = [([], t_bar(t, t_pi_x) / 2. - t_rf_wait - t_rf_pi), (['mw_x'], t_3pi2_x)]

            # build the sequences
            sequence_pi2 = start + (
                    (n - 1) * (xy_8_rf_part + [([], t_bar(t, t_pi_x, t_pi_y))])) + xy_8_rf_part + end_pi2 + init
            sequence_3pi2 = start + (
                    (n - 1) * (xy_8_rf_part + [([], t_bar(t, t_pi_x, t_pi_y))])) + xy_8_rf_part + end_3pi2 + init
            # join the two sequences
            sequence = sequence_pi2 + sequence_3pi2
        # tail of the sequence
        sequence += [(['sequence'], 100)]
        sequence = sequence_remove_zeros(sequence)

        return sequence

    def _run(self):
        pass

    get_set_items = Pulsed.get_set_items + ['t_pi2_x', 't_pi_y', 'n_sequences', 't_pi_x', 'power_imbalance', 't_3pi2_x',
                                            'rf_frequency', 'rf_power', 't_rf_pi', 't_rf_wait']

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
                                            HGroup(Item('t_pi2_x', width=-80, enabled_when='state != "run"'),
                                                   Item('t_pi_x', width=-80, enabled_when='state != "run"'),
                                                   Item('t_pi_y', width=-80, enabled_when='state != "run"'),
                                                   Item('t_3pi2_x', width=-80, enabled_when='state != "run"'),
                                                   Item('n_sequences', width=-80, enabled_when='state != "run"'),
                                                   Item('tau', width=-80, enabled_when='state != "run"'), ),
                                            HGroup(Item('rf_frequency', width=-120, enabled_when='state != "run"'),
                                                   Item('rf_power', width=-80, enabled_when='state != "run"'),
                                                   Item('t_rf_pi', width=-80, enabled_when='state != "run"'),
                                                   Item('t_rf_wait', width=-80, enabled_when='state != "run"'),
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
