# -*- coding: utf-8 -*-
"""
Created on Wed Sep 07 15:17:09 2016

@author: kbxu
"""

"""
Classes to conduct a DEER_rabi measurement using the AWG as a source of rf in between the NV-
decoupling.
As all advanced NV-ESR measurements we inherit from Rabi and already have the Rabi-variables at hand
Alongside to recieve them from global_vars.py
See rabi.py as example.
TODO: On the fly evaluation, i.e. subtracting the two pulse sequences and evaluation of the latter.
"""

from traits.api import Range
from traitsui.api import View, Item, Tabbed, HGroup, VGroup, VSplit

from analysis.pulsed import PulsedTool
from measurements.awg.hahn_echo_awg import Hahn3pi2_awg
from measurements.awg.rabi_awg import Rabi_awg
from .waveform import *


class DEER_Rabi_awg(Rabi_awg):
    """Defines a DEER_Rabi measurement with both pi/2 and 3pi/2 readout pulse."""
    sequence_delay = Range(low=0., high=1200., value=400.)
    rf_power = Range(low=-100., high=25., value=-20, desc='microwave power', label='rf power [dBm]',
                     mode='text', auto_set=False, enter_set=True)
    RF_t_pi2 = Range(low=1., high=1e6, value=25., desc='pi/2 pulse length', label='RF pi/2 [ns]',
                     mode='text', auto_set=False, enter_set=True)
    RF_t_pi = Range(low=1., high=1e6, value=50., desc='pi pulse length', label='RF pi [ns]',
                    mode='text', auto_set=False, enter_set=True)
    RF_t_3pi2 = Range(low=1., high=1e6, value=100., desc='3pi/2 pulse length',
                      label='RF 3pi/2 [ns]',
                      mode='text', auto_set=False, enter_set=True)
    NV_tau = Range(low=1, high=20e9, value=1000, desc='time [ns]', label='NV Tau [ns]', mode='text',
                   auto_set=False, enter_set=True)

    def start_up(self):
        self.pulse_generator.Night()
        self.microwave.setOutput(self.mw_power, self.mw_frequency)
        self.rf.setOutput(self.rf_power, self.freq_center)
        self.rf._write('SOUR:DM:IQ:STAT ON')
        self.prepare_awg()

    def prepare_awg(self):
        sampling = 1.0e9
        tau_begin = self.tau_begin
        tau_end = self.tau_end
        tau_delta = self.tau_delta
        half_pi = self.RF_t_pi2
        half_3pi = self.RF_t_3pi2
        pi = self.RF_t_pi

        tau_begin = int(tau_begin * sampling / 1.0e9)
        tau_delta = int(tau_delta * sampling / 1.0e9)
        half_pi = int(half_pi * sampling / 1.0e9)
        half_3pi = int(half_3pi * sampling / 1.0e9)
        pi = int(pi * sampling / 1.0e9)

        if self.reload:
            self.AWG.stop()
            self.AWG.set_output(0b0000)
            self.AWG.delete_all()
            self.AWG.tell('*WAI')
            if self.phase:
                phase_1 = self.phase_1
            else:
                phase_1 = 0
            drive_x = Sin(0, (self.freq_center - self.freq) / sampling, 0, self.amp)
            drive_y = Sin(0, (self.freq_center - self.freq) / sampling, np.pi / 2 + phase_1,
                          self.amp)
            zero = Idle(1)
            zeros = Idle(250)
            t_blank = self.laser + self.NV_tau / 2. + self.mw_x_t_pi2 + self.sequence_delay
            self.waves = []
            self.main_seq = Sequence('DEER_Rabi.SEQ')
            # pi pulses for the NV-|0> state measurement
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
            # upload
            self.AWG.upload(self.waves)
            self.AWG.upload(self.main_seq)
            self.AWG.tell('*WAI')
            self.AWG.load('DEER_Rabi.SEQ')
            self.AWG.tell('*WAI')
        self.AWG.set_vpp(self.vpp)
        self.AWG.set_sample(sampling / 1.0e9)
        self.AWG.set_mode('S')
        self.AWG.set_output(0b0011)
        self.AWG.run()

    def generate_sequence(self):
        tau = self.tau
        laser = self.laser
        trigger_delay = self.trigger_delay

        mw_x_t_pi2 = self.mw_x_t_pi2
        mw_x_t_pi = self.mw_x_t_pi
        NV_tau = self.NV_tau

        decay_init = self.decay_init
        wavegenerator = self.wavegenerator
        if wavegenerator == 'AWG':
            sequence = []
            for i in range(len(tau)):
                sequence.append(([], decay_init))
                sequence.append((['microwave'], mw_x_t_pi2))
                sequence.append(([], 0.5 * NV_tau - trigger_delay - 100))
                sequence.append((['awgTrigger', 'rf'], 100))
                sequence.append((['rf'], trigger_delay))
                sequence.append((['microwave', 'rf'], mw_x_t_pi))
                sequence.append((['rf'], 0.5 * NV_tau))
                sequence.append((['microwave'], mw_x_t_pi2))
                sequence.append((['detect', 'aom'], laser))
            return sequence
        else:
            sequence = []
            # ADD SEQUENCE HERE
            return sequence

    get_set_items = Hahn3pi2_awg.get_set_items + ['NV_tau', 'RF_t_pi2', 'RF_t_pi', 'RF_t_3pi2',
                                                  'rf_power']

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
                                     Item('load_button', show_label=False)
                                     ),
                              Tabbed(VGroup(HGroup(Item('wavegenerator', style='custom',
                                                        enabled_when='state != "run"'),
                                                   Item('reload', width=20),
                                                   ),
                                            HGroup(Item('mw_frequency', width=-120,
                                                        enabled_when='state != "run"'),
                                                   Item('mw_power', width=-80,
                                                        enabled_when='state != "run"'),
                                                   Item('mw_x_t_pi2', width=-80,
                                                        enabled_when='state != "run"'),
                                                   Item('mw_x_t_pi', width=-80,
                                                        enabled_when='state != "run"'),
                                                   Item('mw_x_t_3pi2', width=-80,
                                                        enabled_when='state != "run"'),
                                                   Item('NV_tau', width=-80,
                                                        enabled_when='state != "run"'),
                                                   ),
                                            HGroup(Item('rf_power', width=-80,
                                                        enabled_when='state != "run"'),
                                                   Item('tau_begin', width=-80,
                                                        enabled_when='state != "run"'),
                                                   Item('tau_end', width=-80,
                                                        enabled_when='state != "run"'),
                                                   Item('tau_delta', width=-80,
                                                        enabled_when='state != "run"'),
                                                   ),
                                            HGroup(Item('freq_center', width=20,
                                                        enabled_when='state != "run"'),
                                                   Item('freq', width=20,
                                                        enabled_when='state != "run"'),
                                                   Item('trigger_delay', width=-80,
                                                        enabled_when='state != "run"'),
                                                   Item('amp', width=20,
                                                        enabled_when='state != "run"'),
                                                   Item('vpp', width=20,
                                                        enabled_when='state != "run"'),
                                                   ),
                                            label='stimulation'
                                            ),
                                     VGroup(HGroup(Item('record_length', width=-80,
                                                        enabled_when='state != "run"'),
                                                   Item('bin_width', width=-80,
                                                        enabled_when='state != "run"'),
                                                   ),
                                            HGroup(Item('laser', width=-80,
                                                        enabled_when='state != "run"'),
                                                   Item('decay_init', width=-80,
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
                       title='DEER Rabi AWG Measurement',
                       )


class DEER_Rabi_awg_view(PulsedTool):
    """
    Analysis of a DEER Rabi AWG measurement with a 'tau' as index-data.
    """

    # overwrite this to change the window title and sizes
    traits_view = View(VGroup(Item(name='measurement', style='custom', show_label=False),
                              VSplit(Item('line_plot', show_label=False, width=500, height=200,
                                          resizable=True),
                                     Item('pulse_plot', show_label=False, width=500, height=100,
                                          resizable=True),
                                     Item('matrix_plot', show_label=False, width=500, height=100,
                                          resizable=True),
                                     ),
                              ),
                       title='DEER Rabi AWG Measurement',
                       buttons=[], resizable=True
                       )
