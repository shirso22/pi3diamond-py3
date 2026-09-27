from traits.api import Range, Int, Float, Instance
from traitsui.api import View, Item, Tabbed, HGroup, VGroup, TextEditor

from measurements.pulsed import PulsedTau, sequence_remove_zeros
from measurements.rabi import RabiTool


class DEERRabi(PulsedTau):
    """Defines a DEER Rabi measurement.
    
    Here we drive the external electron spin with a source RF, whose pulses are applied during the
    Hahn Echo or an XY8 Sequence, while we measure the coherence of the NV. This measurement varies
    the pulse length of a fixed rf Frequency pulse, to determine if we can coherently drive the
    external spin.
    """

    frequency = Range(low=1e9, high=10e9, value=2.8705e9, desc='microwave frequency',
                      label='Microwave frequency [Hz]', mode='text', auto_set=False,
                      enter_set=True, editor=TextEditor(auto_set=False, enter_set=True,
                                                        evaluate=float, format_str='%e'))
    power = Range(low=-100., high=25., value=-20, desc='microwave power', label='power [dBm]',
                  mode='text', auto_set=False, enter_set=True)

    laser = Float(default_value=3000., desc='laser [ns]', label='laser [ns]', mode='text',
                  auto_set=False, enter_set=True)
    decay_init = Float(default_value=250., desc='time to let the system decay after laser pulse [ns]',
                       label='decay init [ns]', mode='text', auto_set=False, enter_set=True)
    decay_read = Float(default_value=0., desc='time to let the system decay before laser pulse [ns]',
                       label='decay read [ns]', mode='text', auto_set=False, enter_set=True)

    aom_delay = Float(default_value=0.,
                      desc='If set to a value other than 0.0, the aom triggers are applied\nearlier by the specified value. Use with care!',
                      label='aom delay [ns]', mode='text', auto_set=False, enter_set=True)

    mw_t_pi2 = Range(low=0., high=100000., value=50., desc='pi/2 pulse length (x)',
                     label='pi/2 x [ns]', mode='text', auto_set=False, enter_set=True)
    mw_t_3pi2 = Range(low=0., high=100000., value=150., desc='3pi/2 pulse length (x)',
                      label='3pi/2 x [ns]', mode='text', auto_set=False, enter_set=True)
    mw_y_t_pi = Range(low=1., high=100000., value=100., desc='pi pulse length (y)', label='pi y [ns]',
                      mode='text', auto_set=False, enter_set=True)
    mw_x_t_pi = Range(low=1., high=100000., value=100., desc='pi pulse length (x)', label='pi x [ns]',
                      mode='text', auto_set=False, enter_set=True)
    power_imbalance = Range(low=-1., high=1., value=0., desc='microwave power imbalance',
                            label='power imbalance [dBm]', mode='text', auto_set=False,
                            enter_set=True)
    decoupling_order = Int(default_value=1, desc='number of XY_8-Sequences', label='n_seq', mode='text',
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
    rf_pulse_delay = Float(default_value=15., desc='wait between mw and rf pulse[ns]',
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
        n = self.decoupling_order
        decay_init = self.decay_init

        mw_tau = self.mw_tau
        mw_t_pi2 = self.mw_t_pi2
        mw_t_3pi2 = self.mw_t_3pi2
        mw_y_t_pi = self.mw_y_t_pi
        mw_x_t_pi = self.mw_x_t_pi

        rf_pulse_delay = self.rf_pulse_delay

        sequence = []
        if n == 0:
            """In this case we just do a simple hahn echo with an rf in between.
            mw_tau corresponds to half the time between the pi2 and pi pulse of the mw.
            """
            if (0.5 * mw_tau) < self.tau_end + rf_pulse_delay:
                raise IOError('The delay between pulses is too short.'
                              ' It has to be larger than the pulse_duration')
            for t in tau:
                sequence += [(['mw_x'], mw_t_pi2), ([], 0.5 * mw_tau), (['mw_x'], mw_x_t_pi),
                             ([], rf_pulse_delay), (['rf'], t), ([], (0.5 * mw_tau) - rf_pulse_delay - t),
                             (['mw_x'], mw_t_pi2), (['detect', 'aom'], laser), ([], decay_init)]
        else:
            """In this case we just do xy8_n-DD, with an rf pulse in between each mw_tau
            mw_tau corresponds to the time/8*n the sequence takes. This time is used in NMR analysis
            and since our xy8 measurements are using this time we use it here as well.
            """
            # mw_t is the time between the infinitely short xy8 pulses
            mw_t = mw_tau / (8. * n)
            # This lambda function gives correct mw_tau for the approximation of infinitely short pulses
            t_bar = lambda time, p1, p2=0., p3=0., p4=0.: time - (p1 / 2.) - (p2 / 2.) - p3 - p4
            # check, if the start time is long enough to fit at least the mw+rf pulses in it.
            t_max = tau.max()
            if t_bar(mw_t, mw_y_t_pi, mw_y_t_pi, rf_pulse_delay, t_max) < 0 or t_bar(mw_t, mw_x_t_pi, mw_x_t_pi,
                                                                                     rf_pulse_delay, t_max) < 0:
                raise IOError(
                    'The delay between pulses is too short. It has to be larger than the combined pulse duration')
            """Build the signal sequence, i.e. the spin state with applied rf at a specific mw_tau with xy8
            decoupling.
            """
            for t in tau:
                xy_8_rf_part = []
                start = []
                end_pi2 = []
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
                xy_8_rf_part += [(['mw_x'], mw_x_t_pi), ([], rf_pulse_delay), (['rf'], t)]

                start = [(['mw_x'], mw_t_pi2), ([], t_bar(mw_t / 2., mw_t_pi2, mw_x_t_pi))]
                end_pi2 = [([], t_bar(mw_t / 2., mw_x_t_pi, mw_t_pi2, t, rf_pulse_delay)), (['mw_x'], mw_t_pi2)]

                # build the sequences
                sequence += start + (
                        (n - 1) * (
                        xy_8_rf_part + [([], t_bar(mw_t, mw_x_t_pi, mw_y_t_pi))])) + xy_8_rf_part + end_pi2 + init

        # tail of the sequence
        sequence += [(['sequence'], 100)]
        sequence = sequence_remove_zeros(sequence)

        return sequence

    get_set_items = PulsedTau.get_set_items + ['frequency', 'power', 'laser', 'decay_init', 'decay_read', 'aom_delay',
                                               'mw_t_pi2', 'mw_t_3pi2', 'mw_x_t_pi', 'mw_y_t_pi',
                                               'decoupling_order', 'mw_tau', 'rf_frequency', 'rf_power',
                                               'rf_pulse_delay']

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
                                            HGroup(Item('mw_t_pi2', width=-80, enabled_when='state != "run"'),
                                                   Item('mw_x_t_pi', width=-80, enabled_when='state != "run"'),
                                                   Item('mw_y_t_pi', width=-80, enabled_when='state != "run"'),
                                                   Item('mw_t_3pi2', width=-80, enabled_when='state != "run"'),
                                                   Item('decoupling_order', width=-80, enabled_when='state != "run"'),
                                                   Item('mw_tau', width=-80, enabled_when='state != "run"'),
                                                   ),
                                            HGroup(Item('rf_frequency', width=-120, enabled_when='state != "run"'),
                                                   Item('rf_power', width=-80, enabled_when='state != "run"'),
                                                   Item('rf_pulse_delay', width=-80, enabled_when='state != "run"'),
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


class DEERRabiTool(RabiTool):
    """Provides visualization and fit of a DEERRabi measurement.

    Here we use the exact same class for a usual Rabi measurement and just overwrite some attributes
    to fit the DEERRabi class.
    """
    measurement = Instance(DEERRabi)

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
                              Tabbed(Item('line_plot', show_label=False, width=500, height=-300,
                                          resizable=True),
                                     Item('matrix_plot', show_label=False, width=500, height=-300,
                                          resizable=True),
                                     Item('pulse_plot', show_label=False, width=500, height=-300,
                                          resizable=True),
                                     ),
                              ),
                       title='DEER - Rabi tool',
                       buttons=[],
                       resizable=True,
                       height=-640
                       )
