"""
This code is currently broken

small changes are required to adapt it to the new pulsed measurements (without hardware API).

See rabi.py as example.
"""

# import numpy as np

from traits.api import Range, Int, Float
from traitsui.api import View, Item, Tabbed, HGroup, VGroup

from .pulsed import Pulsed, sequence_remove_zeros, sequence_simplify
from .rabi import Rabi


class PulseCal(Rabi):
    """Pulse Calibration by just chaining pulses."""

    mw_pulse = Float(1000., desc='Length of the Pulse that is Calibrated', label='pulse [ns]',
                     mode='text', auto_set=False, enter_set=True)
    delay = Float(100., desc='Delay between two pulses', label='delay [ns]', mode='text',
                  auto_set=False, enter_set=True)

    N = Int(6, desc='Maximum Number of pulses', label='N', mode='text', auto_set=False,
            enter_set=True)

    def generate_sequence(self):
        mw = self.switch
        N = self.N
        sequence = []
        for i in range(N):
            # if i == N-1:
            #    sequence += [(['trigger'],100)]
            sequence += i * [([mw], self.mw_pulse), ([], self.delay)] + [
                (['detect', 'aom'], self.laser), ([], self.decay_init)]
        sequence += [(['sequence'], 100)]
        sequence = sequence_remove_zeros(sequence)
        return sequence

    get_set_items = Pulsed.get_set_items + ['mw_frequency', 'mw_power', 'laser', 'decay_init',
                                            'mw_pulse', 'delay', 'N', 'switch']

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
                              Tabbed(VGroup(HGroup(
                                  Item('mw_frequency', width=-80, enabled_when='state != "run"'),
                                  Item('mw_power', width=-80, enabled_when='state != "run"'),
                                  Item('switch', style='custom', )
                              ),
                                  HGroup(Item('laser', width=-80,
                                              enabled_when='state != "run"'),
                                         Item('mw_pulse', width=-80,
                                              enabled_when='state != "run"'),
                                         Item('delay', width=-80,
                                              enabled_when='state != "run"'),
                                         Item('N', width=-80,
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
                              ),
                       title='Pulse Calibration',
                       )


class Pi2PiCal(Pulsed):
    """Pulse Calibration with initial and final pi/2_x pulses, pi_x and pi_y pulse sequences and bright / dark reference."""

    frequency = Range(low=1, high=20e9, value=2.8705e9, desc='microwave frequency',
                      label='frequency [Hz]', mode='text', auto_set=False, enter_set=True)
    power = Range(low=-100., high=25., value=-20, desc='microwave power', label='power [dBm]',
                  mode='text', auto_set=False, enter_set=True)

    t_pi2_x = Range(low=0., high=100000., value=1000., desc='pi/2 pulse length (x)',
                    label='pi/2 x [ns]', mode='text', auto_set=False, enter_set=True)
    t_pi_y = Range(low=1., high=100000., value=1000., desc='pi pulse length (y)', label='pi y [ns]',
                   mode='text', auto_set=False, enter_set=True)
    t_pi_x = Range(low=1., high=100000., value=1000., desc='pi pulse length (x)', label='pi x [ns]',
                   mode='text', auto_set=False, enter_set=True)
    delay = Range(low=1., high=100000., value=100., desc='Delay between two pulses',
                  label='delay [ns]', mode='text', auto_set=False, enter_set=True)

    n_pi = Range(low=0, high=100, value=10, desc='number of pi pulses', label='n pi', mode='text',
                 auto_set=False, enter_set=True)

    laser = Float(default_value=3000., desc='laser [ns]', label='laser [ns]', mode='text',
                  auto_set=False, enter_set=True)
    decay_init = Float(default_value=1000.,
                       desc='time to let the system decay after laser pulse [ns]',
                       label='decay init [ns]', mode='text', auto_set=False, enter_set=True)
    decay_read = Float(default_value=0.,
                       desc='time to let the system decay before laser pulse [ns]',
                       label='decay read [ns]', mode='text', auto_set=False, enter_set=True)

    aom_delay = Float(default_value=0.,
                      desc='If set to a value other than 0.0, the aom triggers are applied\nearlier by the specified value. Use with care!',
                      label='aom delay [ns]', mode='text', auto_set=False, enter_set=True)

    def __init__(self, pulse_generator, time_tagger, microwave, **kwargs):
        super(Pi2PiCal, self).__init__(pulse_generator, time_tagger, **kwargs)
        self.microwave = microwave

    def start_up(self):
        self.pulse_generator.Night()
        self.microwave.setOutput(self.power, self.frequency)

    def shut_down(self):
        self.pulse_generator.Light()
        self.microwave.setOutput(None, self.frequency)

    def generate_sequence(self):
        # parameters
        laser = self.laser
        decay_init = self.decay_init
        t_pi2_x = self.t_pi2_x
        t_pi_y = self.t_pi_y
        t_pi_x = self.t_pi_x
        n_pi = self.n_pi
        t = self.delay
        sequence = []

        # first sequence
        # sequence +=     [ (['detect','aom'],laser),  ([],decay_init) ]
        # for n in range(n_pi+1):
        #    sequence +=     [ (['mw_x'],t_pi2_x),       ([],t)    ]
        #    sequence += n * [ (['mw_x'],t_pi_x),        ([],2*t)  ] 
        #    sequence +=     [ (['detect','aom'],laser),  ([],decay_init) ]
        # sequence +=     [ (['mw_x'],t_pi2_x),       ([],t)    ]
        # sequence += n * [ (['mw_x'],t_pi_x),        ([],2*t)  ]
        # sequence +=     [ (['mw_x'],t_pi2_x),       ([],t)    ]
        # sequence +=     [ (['detect','aom'],laser),  ([],decay_init) ]

        # second sequence
        sequence += [(['detect', 'aom'], laser), ([], decay_init)]
        for n in range(n_pi + 1):
            sequence += [(['mw_x'], t_pi2_x), ([], t)]
            sequence += n * [(['mw_y'], t_pi_y), ([], 2 * t)]
            sequence += [(['detect', 'aom'], laser), ([], decay_init)]
        sequence += [(['mw_x'], t_pi2_x), ([], t)]
        sequence += n * [(['mw_y'], t_pi_y), ([], 2 * t)]
        sequence += [(['mw_x'], t_pi2_x), ([], t)]
        sequence += [(['detect', 'aom'], laser), ([], decay_init)]

        # start trigger
        sequence += [(['sequence'], 100)]

        return sequence

    get_set_items = Pulsed.get_set_items + ['frequency', 'power', 'laser', 'decay_init',
                                            'decay_read', 'aom_delay', 't_pi2_x', 't_pi_x',
                                            't_pi_y', 'delay', 'n_pi']

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
                              Tabbed(VGroup(HGroup(
                                  Item('frequency', width=-80, enabled_when='state != "run"'),
                                  Item('power', width=-80, enabled_when='state != "run"'),
                                  Item('aom_delay', width=-80, enabled_when='state != "run"'),
                              ),
                                  HGroup(Item('laser', width=-80,
                                              enabled_when='state != "run"'),
                                         Item('decay_init', width=-80,
                                              enabled_when='state != "run"'),
                                         Item('decay_read', width=-80,
                                              enabled_when='state != "run"'),
                                         ),
                                  HGroup(Item('t_pi2_x', width=-80,
                                              enabled_when='state != "run"'),
                                         Item('t_pi_y', width=-80,
                                              enabled_when='state != "run"'),
                                         Item('t_pi_x', width=-80,
                                              enabled_when='state != "run"'),
                                         ),
                                  HGroup(Item('delay', width=-80,
                                              enabled_when='state != "run"'),
                                         Item('n_pi', width=-80,
                                              enabled_when='state != "run"'),
                                         ),
                                  label='stimulation'
                              ),
                                  VGroup(HGroup(Item('record_length', width=-80,
                                                     enabled_when='state != "run"'),
                                                Item('bin_width', width=-80,
                                                     enabled_when='state != "run"'),
                                                ),
                                         label='acquisition'
                                         ),
                                  VGroup(HGroup(Item('integration_width'),
                                                Item('position_signal'),
                                                Item('position_normalize'),
                                                ),
                                         label='analysis'
                                         ),
                              ),
                              ),
                       title='Pi/2 Pi Calibration',
                       )


# class Test( Pulsed ):
#    
#    """Test sequence."""
#
#   frequency   = Range(low=1,      high=20e9,  value=2.8705e9, desc='microwave frequency', label='frequency [Hz]', mode='text', auto_set=False, enter_set=True)
#  power       = Range(low=-100.,  high=25.,   value=-20,      desc='microwave power',     label='power [dBm]',    mode='text', auto_set=False, enter_set=True)
#
#    laser       = Range(low=1., high=100000.,   value=3000.,    desc='laser [ns]',      label='laser [ns]',       mode='text', auto_set=False, enter_set=True)
#    wait        = Range(low=1., high=100000.,   value=1000.,    desc='wait [ns]',       label='wait [ns]',        mode='text', auto_set=False, enter_set=True)#
#
#    t_pi2_x     = Range(low=1., high=100000.,   value=1000.,    desc='pi/2 pulse length (x)',   label='pi/2 x [ns]',    mode='text', auto_set=False, enter_set=True)
#    t_pi_x      = Range(low=1., high=100000.,   value=1000.,    desc='pi pulse length (x)',     label='pi x [ns]',   mode='text', auto_set=False, enter_set=True)#
#
#   n           = Range(low=0,  high=100,       value=10,       desc='number of pulses',   label='n',           mode='text', auto_set=False, enter_set=True)#
#   def start_up(self):
#        PulseGenerator().Night()
#        Microwave().setOutput(self.power, self.frequency)
#
#    def shut_down(self):
#        PulseGenerator().Light()
#        Microwave().setOutput(None, self.frequency)
#
#    def generate_sequence(self):
#
#       # parameters        
#        laser = self.laser
#        wait  = self.wait
#        t_pi2_x  = self.t_pi2_x
#        t_pi_x   = self.t_pi_x
#        n        = self.n
#        
#        # start trigger
#        sequence = [ (['sequence'],100)  ]
#
#        # three sequence
#        sequence += n * [ (['detect','aom'],laser),  ([],wait) ]
#        sequence += n * [ (['mw_x'],t_pi_x),  (['detect','aom'],laser),  ([],wait)  ]
#        sequence += n * [ (['mw_x'],t_pi2_x), (['detect','aom'],laser),  ([],wait)  ]
#        
#       return sequence
#
#    get_set_items = Pulsed.get_set_items + ['frequency','power','laser','wait','t_pi2_x','t_pi_x','n']
#
#    traits_view = View(VGroup(HGroup(Item('submit_button',   show_label=False),
#                                     Item('remove_button',   show_label=False),
#                                     Item('resubmit_button', show_label=False),
#                                     Item('priority'),
#                                     Item('state', style='readonly'),
#                                     Item('run_time', style='readonly',format_str='%.f'),
#                                     ),
#                              Tabbed(VGroup(HGroup(Item('frequency',     width=-80, enabled_when='state != "run"'),
#                                                   Item('power',         width=-80, enabled_when='state != "run"'),),
#                                            HGroup(Item('t_pi2_x',       width=-80, enabled_when='state != "run"'),
#                                                   Item('t_pi_x',        width=-80, enabled_when='state != "run"'),
#                                                   Item('n',             width=-80, enabled_when='state != "run"'),),
#                                            label='manipulation'),
#                                     VGroup(HGroup(Item('laser',         width=-80, enabled_when='state != "run"'),
#                                                   Item('wait',          width=-80, enabled_when='state != "run"'),
#                                                   Item('record_length', width=-80, enabled_when='state != "run"'),
#                                                   Item('bin_width',     width=-80, enabled_when='state != "run"'),),
#                                            label='detection'
#                                            ),
#                                     ),
#                              ),
#                              title='Test bright, dark and pi/2 reproducability',
#                              )
#
# class TestBright( Pulsed ):
#    
#   """Test sequence."""
#
#    laser       = Range(low=1., high=100000.,   value=3000.,    desc='laser [ns]',      label='laser [ns]',       mode='text', auto_set=False, enter_set=True)
#    wait        = Range(low=1., high=100000.,   value=1000.,    desc='wait [ns]',       label='wait [ns]',        mode='text', auto_set=False, enter_set=True)
#
#    n           = Range(low=0,  high=100,       value=10,       desc='number of pulses',   label='n',           mode='text', auto_set=False, enter_set=True)
#
#    def start_up(self):
#        PulseGenerator().Night()
#
#    def shut_down(self):
#        PulseGenerator().Light()
#
#    def generate_sequence(self):
#
#        # parameters        
#        laser = self.laser
#        wait  = self.wait
#        n        = self.n
#        
#        sequence = [ (['sequence'],100)  ] + n * [ (['detect','aom'],laser),  ([],wait) ]
#
#        return sequence
#
#    get_set_items = Pulsed.get_set_items + ['laser','wait','n']
#
#    traits_view = View(VGroup(HGroup(Item('submit_button',   show_label=False),
#                                     Item('remove_button',   show_label=False),
#                                     Item('resubmit_button', show_label=False),
#                                     Item('priority'),
#                                     Item('state', style='readonly'),
#                                     Item('run_time', style='readonly',format_str='%.f'),
#                                     ),
#                              Tabbed(VGroup(HGroup(Item('laser',         width=-80, enabled_when='state != "run"'),
#                                                   Item('wait',          width=-80, enabled_when='state != "run"'),
#                                                   Item('n',             width=-80, enabled_when='state != "run"'),),
#                                            label='manipulation'),
#                                     VGroup(HGroup(Item('record_length', width=-80, enabled_when='state != "run"'),
#                                                   Item('bin_width',     width=-80, enabled_when='state != "run"'),),
#                                            label='detection'
#                                            ),
#                                     ),
#                              ),
#                              title='Bright state detection',
#                              )

class CPMG3pi2(Rabi):
    """
    Defines a CPMG measurement with both pi/2 and 3pi/2 readout pulse,
    using a second microwave switch for 90 degree phase shifted pi pulses.
    """

    t_pi2_x = Range(low=1., high=100000., value=1000., desc='pi/2 pulse length (x)',
                    label='pi/2 x [ns]', mode='text', auto_set=False, enter_set=True)
    t_pi_y = Range(low=1., high=100000., value=1000., desc='pi pulse length (y)', label='pi y [ns]',
                   mode='text', auto_set=False, enter_set=True)
    t_3pi2_x = Range(low=1., high=100000., value=1000., desc='3pi/2 pulse length (x)',
                     label='3pi/2 x [ns]', mode='text', auto_set=False, enter_set=True)
    n_pi = Range(low=1, high=100, value=5, desc='number of pi pulses', label='n pi', mode='text',
                 auto_set=False, enter_set=True)

    # n_ref       = Range(low=1,  high=100,       value=10,       desc='number of reference pulses',   label='n ref',   mode='text', auto_set=False, enter_set=True)

    def generate_sequence(self):
        tau = self.tau
        laser = self.laser

        t_pi2_x = self.t_pi2_x
        t_pi_y = self.t_pi_y
        t_3pi2_x = self.t_3pi2_x
        n_pi = self.n_pi

        decay_init = self.decay_init
        # decay_read = self.decay_read
        # aom_delay = self.aom_delay

        sequence = []
        for t in tau:
            sequence += [(['mw_x'], t_pi2_x)]
            sequence += n_pi * [([], t / float(2 * n_pi)), (['mw_y'], t_pi_y),
                                ([], t / float(2 * n_pi))]
            sequence += [(['mw_x'], t_pi2_x)]
            sequence += [(['detect', 'aom'], laser), ([], decay_init)]
        for t in tau:
            sequence += [(['mw_x'], t_pi2_x)]
            sequence += n_pi * [([], t / float(2 * n_pi)), (['mw_y'], t_pi_y),
                                ([], t / float(2 * n_pi))]
            sequence += [(['mw_x'], t_3pi2_x)]
            sequence += [(['detect', 'aom'], laser), ([], decay_init)]
        sequence += [(['sequence'], 100)]
        sequence = sequence_simplify(sequence)
        #        sequence = []
        #        for t in tau:
        #            sequence +=            [ (['mw_x'],t_pi2_x),       ([],t/float(2*n_pi))  ]
        #            sequence += (n_pi-1) * [ (['mw_y'],t_pi_y),        ([],t/float(n_pi))    ]
        #            sequence +=            [ (['mw_y'],t_pi_y),        ([],t/float(2*n_pi))  ]
        #            sequence +=            [ (['mw_x'],t_pi2_x)                              ]
        #            sequence +=            [ (['detect','aom'],laser),  ([],decay_init)             ]
        #        for t in tau:
        #            sequence +=             [ (['mw_x'],t_pi2_x),       ([],t/float(2*n_pi))  ]
        #            sequence += (n_pi-1) *  [ (['mw_y'],t_pi_y),        ([],t/float(n_pi))    ]
        #            sequence +=             [ (['mw_y'],t_pi_y),        ([],t/float(2*n_pi))  ]
        #            sequence +=             [ (['mw_x'],t_3pi2_x)                             ]
        #            sequence +=             [ (['detect','aom'],laser),  ([],decay_init)      ]
        #        sequence +=            [ (['sequence'],100)                        ]
        return sequence

    get_set_items = Rabi.get_set_items + ['t_pi2_x', 't_pi_y', 't_3pi2_x', 'n_pi']

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
                              Tabbed(VGroup(HGroup(
                                  Item('frequency', width=-120, enabled_when='state != "run"'),
                                  Item('power', width=-60, enabled_when='state != "run"'),
                                  # Item('aom_delay',     width=-80, enabled_when='state != "run"'),
                              ),
                                  HGroup(Item('laser', width=-80,
                                              enabled_when='state != "run"'),
                                         Item('decay_init', width=-80,
                                              enabled_when='state != "run"'),
                                         # Item('decay_read',    width=-80, enabled_when='state != "run"'),
                                         ),
                                  HGroup(Item('t_pi2_x', width=-80,
                                              enabled_when='state != "run"'),
                                         Item('t_pi_y', width=-80,
                                              enabled_when='state != "run"'),
                                         Item('t_3pi2_x', width=-80,
                                              enabled_when='state != "run"'),
                                         Item('n_pi', width=-80,
                                              enabled_when='state != "run"'), ),
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
                              ),
                       title='CPMG Measurement with both pi/2 and 3pi/2 readout pulse',
                       )

# class CPMG( Rabi ):
#    
#    """Defines a basic CPMG measurement with a single sequence and bright / dark reference points."""
#
#    t_pi2_x     = Range(low=1., high=100000.,   value=1000.,    desc='pi/2 x pulse length',   label='pi/2 x [ns]',    mode='text', auto_set=False, enter_set=True)
#    t_pi_y      = Range(low=1., high=100000.,   value=1000.,    desc='pi y pulse length',     label='pi y [ns]',      mode='text', auto_set=False, enter_set=True)
#    n_pi        = Range(low=1,  high=100,       value=5,        desc='number of pi pulses',   label='n pi',           mode='text', auto_set=False, enter_set=True)
#    n_ref       = Range(low=1,  high=100,       value=10,       desc='number of reference pulses',   label='n ref',   mode='text', auto_set=False, enter_set=True)
#
#    def generate_sequence(self):
#        tau = self.tau
#        laser = self.laser
#        wait  = self.wait
#        t_pi2_x = self.t_pi2_x
#        t_pi_y  = self.t_pi_y
#        n_pi    = self.n_pi
#        n_ref   = self.n_ref
#        sequence = []
#        for t in tau:
#            sequence +=            [ (['mw_x'],t_pi2_x),       ([],t/float(2*n_pi)) ]
#            sequence += (n_pi-1) * [ (['mw_y'],t_pi_y),        ([],t/float(n_pi))   ] 
#            sequence +=            [ (['mw_y'],t_pi_y),        ([],t/float(2*n_pi)) ]
#            sequence +=            [ (['mw_x'],t_pi2_x)                             ]
#            sequence +=            [ (['detect','aom'],laser),  ([],wait)            ]
#        sequence +=    n_ref * [ (['detect','aom'],laser),  ([],wait)       ]
#        sequence +=    n_ref * [ (['mw_y'],t_pi_y),  (['detect','aom'],laser),  ([],wait)      ]
#        sequence +=            [ (['sequence'],100)                        ]
#        return sequence
#
#    traits_view = View(VGroup(HGroup(Item('submit_button',   show_label=False),
#                                     Item('remove_button',   show_label=False),
#                                     Item('resubmit_button', show_label=False),
#                                     Item('priority'),
#                                     Item('state', style='readonly'),
#                                     Item('run_time', style='readonly',format_str='%.f'),
#                                     Item('stop_time',format_str='%.f'),
#                                     Item('stop_counts'),
#                                     ),
#                              HGroup(Item('filename',springy=True),
#                                     Item('save_button', show_label=False),
#                                     Item('load_button', show_label=False)
#                                     ),
#                              Tabbed(VGroup(HGroup(Item('frequency',     width=-80, enabled_when='state != "run"'),
#                                                   Item('power',         width=-80, enabled_when='state != "run"'),),       
#                                            HGroup(Item('t_pi2_x',       width=-80, enabled_when='state != "run"'),
#                                                   Item('t_pi_y',        width=-80, enabled_when='state != "run"'),
#                                                   Item('n_pi',          width=-80, enabled_when='state != "run"'),
#                                                   #Item('n_ref',         width=-80, enabled_when='state != "run"'),
#                                                   ),
#                                            HGroup(Item('tau_begin',     width=-80, enabled_when='state != "run"'),
#                                                   Item('tau_end',       width=-80, enabled_when='state != "run"'),
#                                                   Item('tau_delta',     width=-80, enabled_when='state != "run"'),
#                                                   ),
#                                            label='parameter'),
#                                     VGroup(HGroup(Item('laser',         width=-80, enabled_when='state != "run"'),
#                                                   Item('wait',          width=-80, enabled_when='state != "run"'),
#                                                   Item('record_length', width=-80, enabled_when='state != "run"'),
#                                                   Item('bin_width',     width=-80, enabled_when='state != "run"'),),
#                                            label='settings'),
#                                     ),
#                              ),
#                       title='Basic CPMG Measurement with pi/2 pulse on B and pi pulses on A',
#                       )
#    
#    get_set_items = Rabi.get_set_items + ['t_pi2_x','t_pi_y','n_pi','n_ref']
#
#
# class CPMGxy( Rabi ):
#    
#    """
#    Defines a CPMG measurement with both pi_x and pi_y pulses.
#
#    Includes also bright (no pulse) and dark (pi_y pulse) reference points.
#    """
#
#    t_pi2_x     = Range(low=1., high=100000.,   value=1000.,    desc='pi/2 pulse length (x)',   label='pi/2 x [ns]',    mode='text', auto_set=False, enter_set=True)
#    t_pi_x      = Range(low=1., high=100000.,   value=1000.,    desc='pi pulse length (x)',     label='pi x [ns]',      mode='text', auto_set=False, enter_set=True)
#    t_pi_y      = Range(low=1., high=100000.,   value=1000.,    desc='pi pulse length (y, 90 degree)',  label='pi y [ns]',   mode='text', auto_set=False, enter_set=True)
#    n_pi        = Range(low=1,  high=100,       value=5,        desc='number of pi pulses',   label='n pi',           mode='text', auto_set=False, enter_set=True)
#    n_ref       = Range(low=1,  high=100,       value=10,       desc='number of reference pulses',   label='n ref',   mode='text', auto_set=False, enter_set=True)
#
#    def generate_sequence(self):
#        tau = self.tau
#        laser = self.laser
#        wait  = self.wait
#        t_pi2_x  = self.t_pi2_x
#        t_pi_x   = self.t_pi_x
#        t_pi_y = self.t_pi_y
#        n_pi   = self.n_pi
#        n_ref    = self.n_ref
#        sequence = []
#        for t in tau:
#            sequence +=             [ (['mw_x'],t_pi2_x),       ([],t/float(2*n_pi))  ]
#            sequence += (n_pi-1) *  [ (['mw_x'],t_pi_x),        ([],t/float(n_pi))    ] 
#            sequence +=             [ (['mw_x'],t_pi_x),        ([],t/float(2*n_pi))  ]
#            sequence +=             [ (['mw_x'],t_pi2_x)                              ]
#            sequence +=             [ (['detect','aom'],laser),  ([],wait)             ]
#        for t in tau:
#            sequence +=             [ (['mw_x'],t_pi2_x),       ([],t/float(2*n_pi))  ]
#            sequence += (n_pi-1) *  [ (['mw_y'],t_pi_y),        ([],t/float(n_pi))    ] 
#            sequence +=             [ (['mw_y'],t_pi_y),        ([],t/float(2*n_pi))  ]
#            sequence +=             [ (['mw_x'],t_pi2_x)                              ]
#            sequence +=             [ (['detect','aom'],laser),  ([],wait)             ]            
#        sequence +=    n_ref * [ (['detect','aom'],laser),  ([],wait)        ]
#        sequence +=    n_ref * [ (['mw_y'],t_pi_y),  (['detect','aom'],laser),  ([],wait)      ]
#        sequence +=            [ (['sequence'],100)                         ]
#        return sequence
#
#    traits_view = View(VGroup(HGroup(Item('submit_button',   show_label=False),
#                                     Item('remove_button',   show_label=False),
#                                     Item('resubmit_button', show_label=False),
#                                     Item('priority'),
#                                     Item('state', style='readonly'),
#                                     Item('run_time', style='readonly',format_str='%.f'),
#                                     Item('stop_time',format_str='%.f'),
#                                     Item('stop_counts'),
#                                     ),
#                              HGroup(Item('filename',springy=True),
#                                     Item('save_button', show_label=False),
#                                     Item('load_button', show_label=False)
#                                     ),
#                              Tabbed(VGroup(HGroup(Item('frequency',     width=-80, enabled_when='state != "run"'),
#                                                   Item('power',         width=-80, enabled_when='state != "run"'),),
#                                            HGroup(Item('t_pi2_x',       width=-80, enabled_when='state != "run"'),
#                                                   Item('t_pi_x',        width=-80, enabled_when='state != "run"'),
#                                                   Item('t_pi_y',        width=-80, enabled_when='state != "run"'),
#                                                   Item('n_pi',          width=-80, enabled_when='state != "run"'),
#                                                   Item('n_ref',         width=-80, enabled_when='state != "run"'),),
#                                            HGroup(Item('tau_begin',     width=-80, enabled_when='state != "run"'),
#                                                   Item('tau_end',       width=-80, enabled_when='state != "run"'),
#                                                   Item('tau_delta',     width=-80, enabled_when='state != "run"'),
#                                                   ),
#                                            label='parameter'),
#                                     VGroup(HGroup(Item('laser',         width=-80, enabled_when='state != "run"'),
#                                                   Item('wait',          width=-80, enabled_when='state != "run"'),
#                                                   Item('record_length', width=-80, enabled_when='state != "run"'),
#                                                   Item('bin_width',     width=-80, enabled_when='state != "run"'),),
#                                            label='settings'),
#                                     ),
#                              ),
#                       title='CPMG Measurement with both pix and piys pulses',
#                       )
#    
#    get_set_items = Rabi.get_set_items + ['t_pi2_x','t_pi_x','t_pi_y','n_pi','n_ref']
#


# class PulsedToolTauRef( PulsedToolTau ):
#
#    """
#    Analysis of a pulsed measurement with a 'tau' as index-data.
#    and bright / dark reference points at the end of the sequence.
#    """
#    
#    # overwrite the line_plot such that the bright and dark state reference lines are plotted 
#    def _create_line_plot(self):
#        line_data   = ArrayPlotData(index=np.array((0,1)),
#                                    spin_state=np.array((0,0)),
#                                    bright=np.array((1,1)),
#                                    dark=np.array((0,0)))
#        plot = Plot(line_data, padding=8, padding_left=64, padding_bottom=36)
#        plot.plot(('index','spin_state'), color='blue',  name='pulsed')
#        plot.plot(('index','bright'),     color='red',   name='bright')
#        plot.plot(('index','dark'),       color='black', name='dark')
#        plot.index_axis.title = 'time [micro s]'
#        plot.value_axis.title = 'spin state'
#        self.line_data = line_data
#        self.line_plot = plot
#    
#    # overwrite this one to provide splitting up of spin_state array and setting of bright and dark state data 
#    def _update_line_plot_value(self):
#        y = self.spin_state
#        n_ref = self.measurement.n_ref
#        n = len(y)-2*n_ref
#        self.line_data.set_data('spin_state',y[:n])
#        self.line_data.set_data('bright',np.mean(y[n:n+n_ref])*np.ones(n))
#        self.line_data.set_data('dark',np.mean(y[n+n_ref:n+2*n_ref])*np.ones(n))


# class PulsedToolDoubleRef( PulsedTool ):
#
#    """
#    Analysis of a pulsed measurement with two
#    sequences and bright / dark reference
#    measurement at the end of the sequence.
#    """
#
#    measurement = Instance( mp.Pulsed, factory=mp.Pi2PiCal )
#    
#    # overwrite the line_plot such that the bright and dark state reference lines are plotted 
#    def _create_line_plot(self):
#        line_data   = ArrayPlotData(index=np.array((0,1)),
#                                    first=np.array((0,0)),
#                                    second=np.array((0,0)),
#                                    bright=np.array((1,1)),
#                                    dark=np.array((0,0)))
#        plot = Plot(line_data, padding=8, padding_left=64, padding_bottom=36)
#        plot.plot(('index','first'),  color='blue',  name='first')
#        plot.plot(('index','second'), color='green', name='second')
#        plot.plot(('index','bright'), color='red',   name='bright')
#        plot.plot(('index','dark'),   color='black', name='dark')
#        plot.index_axis.title = 'pulse #'
#        plot.value_axis.title = 'spin state'
#        self.line_data = line_data
#        self.line_plot = plot
#
#    # overwrite this one to provide splitting up of spin_state array and setting of bright and dark state data 
#    def _update_line_plot_value(self):
#        y = self.spin_state
#        n_ref = self.measurement.n_ref
#        n = len(y)/2-n_ref
#        old_index = self.line_data.get_data('index')
#        if old_index is not None and len(old_index) != n:
#            self.line_data.set_data('index',np.arange(n))
#        self.line_data.set_data('first',y[:n])
#        self.line_data.set_data('second',y[n:2*n])
#        self.line_data.set_data('bright',np.mean(y[2*n:2*n+n_ref])*np.ones(n))
#        self.line_data.set_data('dark',np.mean(y[2*n+n_ref:])*np.ones(n))

# from analysis import fitting

# class PulseCalTool( PulsedTool ):
#
#    """Provides calculation of RMS from PulseCal  measurement."""
#    
#    measurement = Instance( PulseCal, factory=PulseCal )
#    
#    rms  = Float()
#    
#    get_set_items = PulsedTool.get_set_items + ['rms']
#
#    traits_view = View(VGroup(Item(name='measurement', style='custom', show_label=False),
#                              HGroup(Item('integration_width'),
#                                     Item('position_signal'),
#                                     Item('position_normalize'),
#                                     Item('run_sum'),
#                                     Item('rms', style='readonly', format_str='%.1f'),
#                                     ),
#                              VSplit(Item('matrix_plot', show_label=False, width=500, height=300, resizable=True),
#                                     Item('line_plot', show_label=False, width=500, height=300, resizable=True),
#                                     Item('pulse_plot', show_label=False, width=500, height=300, resizable=True),
#                                     ),
#                              ),
#                       title='Pulse Calibration Analysis',
#                       menubar = menubar,
#                       buttons=[], resizable=True)
#
#    def __init__(self, **kwargs):
#        super(PulseCalTool, self).__init__(**kwargs)
#        self.on_trait_change(self._update_fit, 'spin_state', dispatch='ui')
#
#    def _update_fit(self, s):
#        """compute relative rms"""
#        m = s.mean()
#        rms = 2*(np.sum((s-m)**2)/len(s))**0.5/float(s.max()-s.min())
#        
#        self.rms = rms
#        self.line_plot.overlays[0].text = 'rms: %.2f'%rms
#
#    # overwrite the line_plot such that the x-axis label is time 
#    def _create_line_plot(self):
#        line_data   = ArrayPlotData(index=np.array((0,1)), spin_state=np.array((0,0)),)
#        plot = Plot(line_data, padding=8, padding_left=64, padding_bottom=36)
#        plot.plot(('index','spin_state'), color='blue',   name='spin_state')
#        plot.plot(('index','spin_state'), type='scatter', name='pulses')
#        plot.index_axis.title = 'pulse #'
#        plot.value_axis.title = 'spin state'
#        plot.overlays.insert(0, PlotLabel(text='', hjustify='left', vjustify='bottom', position=[70,40]) )
#        self.line_data = line_data
#        self.line_plot = plot
