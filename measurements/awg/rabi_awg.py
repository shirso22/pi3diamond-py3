from traits.api import Range, Float, Enum, Button, Bool
from traitsui.api import View, Item, Tabbed, HGroup, VGroup, EnumEditor, TextEditor

import global_vars
from measurements.pulsed import PulsedTau, sequence_remove_zeros, sequence_union
from .waveform import *


# ==============================================================================
# log: 
# 24/06/2016 changed the freq_center to be 0
# 24/06/2016 changed the sampling rate to be 1GHz    
#
# ==============================================================================


class Rabi_awg(PulsedTau):
    """Defines a Rabi measurement.

    This measurement class also serves as a base class for more complex measurements that build up
    on it. All the measurements that use the NV-specific spin variable, i.e. the Rabi period, will
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
    mw_frequency = Range(low=1, high=20e9, value=2.6379e9, desc='microwave frequency',
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

    rf_power = Range(low=-100., high=25., value=-20, desc='rf power', label='RF power [dBm]',
                     mode='text', auto_set=False, enter_set=True)
    vpp = Range(low=0., high=4.5, value=0.6, desc='Amplitude of AWG [Vpp]', label='AWG vpp',
                mode='text', auto_set=False, enter_set=True)
    phase = Bool(False, label='phase', desc='true, Y pulse, false, X pulse')
    phase_1 = Range(low=0., high=3.1415, value=0.0, desc='Amplitude of AWG [Vpp]', label='AWG vpp',
                    mode='text', auto_set=False, enter_set=True)
    amp = Range(low=0., high=1.0, value=1.0, desc='Normalized amplitude of waveform',
                label='WFM amp', mode='text', auto_set=False, enter_set=True)
    reload = Bool(True, label='reload', desc='true, reload, false, not reload')
    # measurement variables
    wavegenerator = Enum('AWG', 'Others',
                         desc='Choose the wave generator from AWG and others, say SMIQ',
                         label='Wave Generator',
                         editor=EnumEditor(cols=3, values={'AWG': '1:Awg', 'Others': '2:Ohters'}))
    laser = Float(default_value=3000., desc='laser [ns]', label='laser [ns]', mode='text',
                  auto_set=False,
                  enter_set=True)
    decay_init = Float(default_value=250.,
                       desc='time to let the system decay after laser pulse [ns]',
                       label='decay init [ns]', mode='text', auto_set=False, enter_set=True)
    decay_read = Float(default_value=0.,
                       desc='time to let the system decay before laser pulse [ns]',
                       label='decay read [ns]', mode='text', auto_set=False, enter_set=True)

    aom_delay = Float(default_value=1000.,
                      desc='If set to a value other than 0.0, the aom triggers are applied\n'
                           'earlier by the specified value. Use with care!',
                      label='aom delay [ns]', mode='text', auto_set=False, enter_set=True)
    trigger_delay = Float(default_value=320.,
                          desc='',
                          label='trigger delay [ns]', mode='text', auto_set=False, enter_set=True)
    freq_center = Range(low=1, high=20e9, value=2.6e8, desc='carrier frequency',
                        label='carrier frequency [Hz]', mode='text', auto_set=False, enter_set=True,
                        editor=TextEditor(auto_set=False, enter_set=True, evaluate=float,
                                          format_str='%.5e'))
    # freq_center = Range(low=1, high=20e9, value=2.6379e9, desc='frequency [Hz]',
    #                   label='center frequency [Hz]', mode='text', auto_set=False, enter_set=True)
    freq = Range(low=1, high=20e9, value=2.5e8, desc='resonance frequency [Hz]',
                 label='Reson freq [Hz]',
                 mode='text', auto_set=False, enter_set=True,
                 editor=TextEditor(auto_set=False, enter_set=True, evaluate=float,
                                   format_str='%.5e'))
    sequence_delay = Range(low=0., high=1200., value=400.)

    def __init__(self, pulse_generator, time_tagger, microwave, rf, awg, **kwargs):
        super(Rabi_awg, self).__init__(pulse_generator, time_tagger, **kwargs)
        self.microwave = microwave
        self.AWG = awg
        self.rf = rf

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
            print('Something went wrong while getting of global variables.')
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
            print('Something went wrong while setting of global variables.')
            print(e)

    def _set_global_vars_button_fired(self):
        """
        React to get_global_vars_button event.
        """
        self.set_global_vars()

    def start_up(self):
        self.pulse_generator.Night()
        self.microwave.setOutput(self.mw_power, self.mw_frequency)
        self.rf.setOutput(self.rf_power, self.freq_center)
        if self.wavegenerator == 'AWG':
            # SET SMIQ TO VECTOR MODE
            self.rf._write('SOUR:DM:IQ:STAT ON')
            self.prepare_awg()

    def shut_down(self):
        self.pulse_generator.Light()
        self.rf.setOutput(None, self.mw_frequency)
        if self.wavegenerator == 'AWG':
            # SET SMIQ TO NORMAL MODE
            self.rf._write('SOUR:DM:IQ:STAT OFF')
            self.AWG.stop()

    def prepare_awg(self):
        sampling = 1.0e9
        if self.reload:
            self.AWG.stop()
            self.AWG.set_output(0b0000)
            self.AWG.delete_all()
            if self.phase:
                phase_1 = self.phase_1
            else:
                phase_1 = 0
            drive_x = Sin(0, (self.freq_center - self.freq) / sampling, 0, self.amp)
            drive_y = Sin(0, (self.freq_center - self.freq) / sampling, np.pi / 2 + phase_1,
                          self.amp)
            zero = Idle(1)
            zeros = Idle(250)
            t_blank = self.laser + self.sequence_delay
            self.waves = []
            self.main_seq = Sequence('RABI.SEQ')
            for i, t in enumerate(self.tau):
                t = int(t * sampling / 1.0e9)

                drive_x.duration = t
                drive_y.duration = t
                x_name = 'X_RA_%03i.WFM' % i
                y_name = 'Y_RA_%03i.WFM' % i
                self.waves.append(Waveform(x_name, [zero, drive_x, zeros]))
                self.waves.append(Waveform(y_name, [zero, drive_y, zeros]))
                self.main_seq.append(*self.waves[-2:], wait=True)

            add_marker(self.waves, self.main_seq, t_blank)
            self.AWG.upload(self.waves)
            self.AWG.upload(self.main_seq)
            self.AWG.tell('*WAI')
            self.AWG.load('RABI.SEQ')
            self.AWG.tell('*WAI')
        self.AWG.set_vpp(self.vpp)
        self.AWG.set_sample(sampling / 1.0e9)
        self.AWG.set_mode('S')
        self.AWG.set_output(0b0011)
        self.AWG.run()

    def generate_sequence(self):
        tau = self.tau
        laser = self.laser
        decay_init = self.decay_init
        decay_read = self.decay_read
        aom_delay = self.aom_delay
        wavegenerator = self.wavegenerator
        if wavegenerator == 'AWG':
            sequence = []
            for t in tau:
                sequence.append(([], decay_init))
                sequence.append((['awgTrigger', 'rf'], 100))
                sequence.append((['rf'], aom_delay))
                sequence.append((['detect', 'aom'], laser))
            sequence += [(['sequence'], 100)]
            return sequence
        else:
            if aom_delay == 0.0:
                sequence = [(['aom'], laser)]
                for t in tau:
                    sequence += [([], decay_init), (['rf'], t), ([], decay_read),
                                 (['detect', 'aom'], laser)]
                sequence += [(['sequence'], 100)]
                sequence = sequence_remove_zeros(sequence)
            else:
                s1 = [(['aom'], laser)]
                s2 = [([], aom_delay + laser)]
                for t in tau:
                    s1 += [([], decay_init + t + decay_read), (['aom'], laser)]
                    s2 += [([], decay_init), (['microwave'], t), ([], decay_read),
                           (['detect'], laser)]
                s2 += [(['sequence'], 100)]
                s1 = sequence_remove_zeros(s1)
                s2 = sequence_remove_zeros(s2)
                sequence = sequence_union(s1, s2)
            return sequence

    get_set_items = PulsedTau.get_set_items + ['mw_frequency', 'mw_power', 'laser', 'decay_init',
                                               'decay_read', 'aom_delay', 'trigger_delay',
                                               'wavegenerator', 'amp', 'freq', 'vpp',
                                               'phase_1', 'rf_power', 'freq_center']

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
                              Tabbed(VGroup(HGroup(
                                  Item('freq_center', width=-120, enabled_when='state != "run"'),
                                  Item('rf_power', width=-60, enabled_when='state != "run"'),
                                  Item('wavegenerator', style='custom',
                                       enabled_when='state != "run"'),
                              ),
                                  HGroup(
                                      Item('aom_delay', width=-80, enabled_when='state != "run"'),
                                      Item('amp', width=20, enabled_when='state != "run"'),
                                      Item('vpp', width=20, enabled_when='state != "run"'),
                                  ),
                                  HGroup(
                                      Item('reload', width=20, enabled_when='state != "run"'),
                                      Item('freq', width=20, enabled_when='state != "run"'),
                                  ),
                                  HGroup(Item('laser', width=-80,
                                              enabled_when='state != "run"'),
                                         Item('decay_init', width=-80,
                                              enabled_when='state != "run"'),
                                         Item('decay_read', width=-80,
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
                              )
                       , title='Rabi_awg'
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
