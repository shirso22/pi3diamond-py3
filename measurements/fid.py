"""
Perform FID Measurements.
See rabi.py for some details about inheritance and naming conventions that are used here.
"""
from traits.api import Range
from traitsui.api import View, Item, Tabbed, HGroup, VGroup

from .rabi import Rabi


class FID3pi2(Rabi):
    """Defines a FID measurement with both pi/2 and 3pi/2 readout pulse."""

    def generate_sequence(self):
        tau = self.tau
        laser = self.laser
        decay_init = self.decay_init
        mw_x_t_pi2 = self.mw_x_t_pi2
        mw_x_t_3pi2 = self.mw_x_t_3pi2
        sequence = []
        for t in tau:
            sequence.append((['mw'], mw_x_t_pi2))
            sequence.append(([], t))
            sequence.append((['mw'], mw_x_t_pi2))
            sequence.append((['detect', 'aom'], laser))
            sequence.append(([], decay_init))
        for t in tau:
            sequence.append((['mw'], mw_x_t_pi2))
            sequence.append(([], t))
            sequence.append((['mw'], mw_x_t_3pi2))
            sequence.append((['detect', 'aom'], laser))
            sequence.append(([], decay_init))
        sequence.append((['sequence'], 100))
        return sequence

    # items to be saved
    get_set_items = Rabi.get_set_items + ['mw_x_t_pi2', 'mw_x_t_3pi2']

    # gui elements
    traits_view = View(VGroup(HGroup(Item('submit_button', show_label=False),
                                     Item('remove_button', show_label=False),
                                     Item('resubmit_button', show_label=False),
                                     Item('get_global_vars_button', show_label=False),
                                     Item('priority'),
                                     Item('state', style='readonly'),
                                     Item('run_time', style='readonly', format_str='%.f'),
                                     Item('stop_time', format_str='%.f'),
                                     ),
                              HGroup(Item('filename', springy=True),
                                     Item('save_button', show_label=False),
                                     Item('load_button', show_label=False)
                                     ),
                              Tabbed(VGroup(HGroup(
                                  Item('mw_frequency', width=-70, enabled_when='state != "run"'),
                                  Item('mw_power', width=-60, enabled_when='state != "run"'),
                                  Item('mw_x_t_pi2', width=-60, enabled_when='state != "run"'),
                                  Item('mw_x_t_3pi2', width=-60, enabled_when='state != "run"'), ),
                                  HGroup(Item('tau_begin', width=-60,
                                              enabled_when='state != "run"'),
                                         Item('tau_end', width=-60,
                                              enabled_when='state != "run"'),
                                         Item('tau_delta', width=-60,
                                              enabled_when='state != "run"'),
                                         ),
                                  label='parameter'),
                                  VGroup(HGroup(
                                      Item('laser', width=-80, enabled_when='state != "run"'),
                                      Item('decay_init', width=-80, enabled_when='state != "run"'),
                                      Item('record_length', width=-80,
                                           enabled_when='state != "run"'),
                                      Item('bin_width', width=-80,
                                           enabled_when='state != "run"'), ),
                                      label='settings'),
                              ),
                              ),
                       title='FID3pi2',
                       )


class HardDQTFID(Rabi):
    """Defines a Double Quantum Transition FID Measurement with pi-tau-pi."""

    t_pi = Range(low=1., high=100000., value=1000., desc='pi pulse length', label='pi [ns]',
                 mode='text', auto_set=False, enter_set=True)

    def generate_sequence(self):
        tau = self.tau
        laser = self.laser
        wait = self.wait
        t_pi = self.t_pi
        sequence = []
        for t in tau:
            sequence.append((['mw'], t_pi))
            sequence.append(([], t))
            sequence.append((['mw'], t_pi))
            sequence.append((['detect', 'aom'], laser))
            sequence.append(([], wait))
        sequence.append((['sequence'], 100))
        return sequence

    get_set_items = Rabi.get_set_items + ['t_pi']

    traits_view = View(VGroup(HGroup(Item('submit_button', show_label=False),
                                     Item('remove_button', show_label=False),
                                     Item('resubmit_button', show_label=False),
                                     Item('priority'),
                                     Item('state', style='readonly'),
                                     Item('run_time', style='readonly', format_str='%.f'),
                                     Item('stop_time'),
                                     ),
                              Tabbed(VGroup(HGroup(
                                  Item('frequency', width=-80, enabled_when='state != "run"'),
                                  Item('power', width=-80, enabled_when='state != "run"'),
                                  Item('t_pi', width=-80, enabled_when='state != "run"'), ),
                                  HGroup(Item('tau_begin', width=-80,
                                              enabled_when='state != "run"'),
                                         Item('tau_end', width=-80,
                                              enabled_when='state != "run"'),
                                         Item('tau_delta', width=-80,
                                              enabled_when='state != "run"'),
                                         ),
                                  label='parameter'),
                                  VGroup(HGroup(
                                      Item('laser', width=-80, enabled_when='state != "run"'),
                                      Item('wait', width=-80, enabled_when='state != "run"'),
                                      Item('record_length', width=-80,
                                           enabled_when='state != "run"'),
                                      Item('bin_width', width=-80,
                                           enabled_when='state != "run"'), ),
                                      label='settings'),
                              ),
                              ),
                       title='HardDQTFID',
                       )


"""
class HardDQTFIDTauMod( HardDQTFID ):
    tau_gen = Code("tg = np.arange(self.tau_begin, self.tau_end, self.tau_delta)\ntf = np.arange(0., 500., 50.)\ntau = np.array(())\nfor t0 in tg:\n   tau=np.append(tau,tf+t0)\nself.tau=tau")
    def start_up(self):
        # this needs to come first, because Pulsed.start_up() will
        # generate the sequence and thereby call the generate_sequence method of RabiMeasurement
        # and this method needs the correct tau 
        exec self.tau_gen
        Pulsed.start_up(self)
        PulseGenerator().Night()
        Microwave().setOutput(self.power, self.frequency)
        
    traits_view = View( VGroup( HGroup(Item('state', show_label=False, style='custom',
                                            editor=EnumEditor(values={'idle':'1:idle','run':'2:run',},cols=2),),),
                                Tabbed( VGroup(HGroup(Item('frequency',     width=-80, enabled_when='state != "run"'),
                                                      Item('power',         width=-80, enabled_when='state != "run"'),
                                                      Item('t_pi',          width=-80, enabled_when='state != "run"'),),
                                               HGroup(Item('tau_begin',     width=-80, enabled_when='state != "run"'),
                                                      Item('tau_end',       width=-80, enabled_when='state != "run"'),
                                                      Item('tau_delta',     width=-80, enabled_when='state != "run"'),),
                                               label='parameter'),
                                        VGroup(HGroup(Item('laser',         width=-80, enabled_when='state != "run"'),
                                                      Item('wait',          width=-80, enabled_when='state != "run"'),
                                                      Item('record_length', width=-80, enabled_when='state != "run"'),
                                                      Item('bin_width',     width=-80, enabled_when='state != "run"'),),
                                               label='settings'),
                                        VGroup(HGroup(Item('tau_begin',     width=-80, enabled_when='state != "run"'),
                                                      Item('tau_end',       width=-80, enabled_when='state != "run"'),
                                                      Item('tau_delta',     width=-80, enabled_when='state != "run"'),),
                                                Item('tau_gen',   width=-200, height=-200, enabled_when='state != "run"'),
                                               label='taumod'),
                                            
                                ),
                        ),
                        title='HardDQTFIDTauMod',
                  )
"""

# class DQTFID3pi2( Pulsed ):
#
#     """Defines a pulsed measurement with two microwave transitions and FID sequence including 3pi2 readout pulses.TODO: untested"""
#     frequency_a = Range(low=1,      high=20e9,  value=2.8705e9, desc='microwave frequency A',   label='frequency A [Hz]', mode='text', auto_set=False, enter_set=True)
#     frequency_b = Range(low=1,      high=20e9,  value=2.8705e9, desc='microwave frequency B',   label='frequency B [Hz]', mode='text', auto_set=False, enter_set=True)
#     power_a     = Range(low=-100.,  high=25.,   value=-20,      desc='microwave power A',       label='power A [dBm]',    mode='text', auto_set=False, enter_set=True)
#     power_b     = Range(low=-100.,  high=25.,   value=-20,      desc='microwave power B',       label='power B [dBm]',    mode='text', auto_set=False, enter_set=True)
#
#     tau_begin   = Range(low=1., high=1e8,       value=10.0,     desc='tau begin [ns]',  label='tau begin [ns]',   mode='text', auto_set=False, enter_set=True)
#     tau_end     = Range(low=1., high=1e8,       value=500.,     desc='tau end [ns]',    label='tau end [ns]',     mode='text', auto_set=False, enter_set=True)
#     tau_delta   = Range(low=1., high=1e6,       value=50.,      desc='delta tau [ns]',  label='delta tau [ns]',   mode='text', auto_set=False, enter_set=True)
#     laser       = Range(low=1., high=100000.,   value=3000.,    desc='laser [ns]',      label='laser [ns]',       mode='text', auto_set=False, enter_set=True)
#     wait        = Range(low=1., high=100000.,   value=1000.,    desc='wait [ns]',       label='wait [ns]',        mode='text', auto_set=False, enter_set=True)
#
#     t_pi2_a     = Range(low=1., high=100000.,   value=1000.,    desc='pi/2 pulse length A',     label='pi/2 A [ns]',    mode='text', auto_set=False, enter_set=True)
#     t_pi_a      = Range(low=1., high=100000.,   value=1000.,    desc='pi pulse length A',       label='pi A [ns]',      mode='text', auto_set=False, enter_set=True)
#     t_3pi2_a    = Range(low=1., high=100000.,   value=1000.,    desc='3pi/2 pulse length A',    label='3pi/2 A [ns]',   mode='text', auto_set=False, enter_set=True)
#     t_pi2_b     = Range(low=1., high=100000.,   value=1000.,    desc='pi/2 pulse length B',     label='pi/2 B [ns]',    mode='text', auto_set=False, enter_set=True)
#     t_pi_b      = Range(low=1., high=100000.,   value=1000.,    desc='pi pulse length B',       label='pi B [ns]',      mode='text', auto_set=False, enter_set=True)
#     t_3pi2_b    = Range(low=1., high=100000.,   value=1000.,    desc='3pi/2 pulse length B',    label='3pi/2 B [ns]',   mode='text', auto_set=False, enter_set=True)
#
#     tau = Array( value=np.array((0.,1.)) )
#
#     def start_up(self):
#         self.tau = np.arange(self.tau_begin, self.tau_end, self.tau_delta)
#         PulseGenerator().Night()
#         MicrowaveA().setOutput(self.power_a, self.frequency_a)
#         MicrowaveB().setOutput(self.power_b, self.frequency_b)
#
#     def shut_down(self):
#         PulseGenerator().Light()
#         MicrowaveA().setOutput(None, self.frequency_a)
#         MicrowaveB().setOutput(None, self.frequency_b)
#
#     def generate_sequence(self):
#         tau = self.tau
#         laser = self.laser
#         wait  = self.wait
#         t_pi2_a  = self.t_pi2_a
#         t_pi_a   = self.t_pi_a
#         t_3pi2_a = self.t_3pi2_a
#         t_pi2_b  = self.t_pi2_b
#         t_pi_b   = self.t_pi_b
#         t_3pi2_b = self.t_3pi2_b
#         sequence = []
#         for t in tau:
#             sequence.append(  (['mw_a'   ],  t_pi2_a  )  )
#             sequence.append(  (['mw_b'   ],  t_pi_b   )  )
#             sequence.append(  ([         ],  t        )  )
#             sequence.append(  (['mw_b'   ],  t_pi_b   )  )
#             sequence.append(  (['mw_a'   ],  t_pi2_a  )  )
#             sequence.append(  (['detect','aom'],  laser    )  )
#             sequence.append(  ([         ],  wait     )  )
#         for t in tau:
#             sequence.append(  (['mw_a'   ],  t_pi2_a  )  )
#             sequence.append(  (['mw_b'   ],  t_pi_b   )  )
#             sequence.append(  ([         ],  t        )  )
#             sequence.append(  (['mw_b'   ],  t_pi_b   )  )
#             sequence.append(  (['mw_a'   ], t_3pi2_a  )  )
#             sequence.append(  (['detect','aom'],  laser    )  )
#             sequence.append(  ([         ],  wait     )  )
#         sequence.append(  (['sequence'], 100  )  )
#         return sequence
#
#     get_set_items = Pulsed.get_set_items + ['frequency_a','frequency_b','power_a','power_b',
#                                                        't_pi2_a', 't_pi_a', 't_3pi2_a', 't_pi2_b', 't_pi_b', 't_3pi2_b',
#                                                        'tau_begin','tau_end','tau_delta','laser','wait','tau']
#
#     traits_view = View(VGroup(HGroup(Item('submit_button',   show_label=False),
#                                      Item('remove_button',   show_label=False),
#                                      Item('resubmit_button', show_label=False),
#                                      Item('priority'),
#                                      Item('state', style='readonly'),
#                                      Item('run_time', style='readonly',format_str='%.f'),
#                                      ),
#                               Tabbed(VGroup(HGroup(Item('frequency_a',   width=-80, enabled_when='state != "run"'),
#                                                    Item('power_a',       width=-80, enabled_when='state != "run"'),
#                                                    Item('t_pi2_a',       width=-80, enabled_when='state != "run"'),
#                                                    Item('t_pi_a',        width=-80, enabled_when='state != "run"'),
#                                                    Item('t_3pi2_a',      width=-80, enabled_when='state != "run"'),
#                                             ),
#                                             HGroup(Item('frequency_b',   width=-80, enabled_when='state != "run"'),
#                                                    Item('power_b',       width=-80, enabled_when='state != "run"'),
#                                                    Item('t_pi2_b',       width=-80, enabled_when='state != "run"'),
#                                                    Item('t_pi_b',        width=-80, enabled_when='state != "run"'),
#                                                    Item('t_3pi2_b',      width=-80, enabled_when='state != "run"'),
#                                             ),
#                                             HGroup(Item('tau_begin',     width=-80, enabled_when='state != "run"'),
#                                                    Item('tau_end',       width=-80, enabled_when='state != "run"'),
#                                                    Item('tau_delta',     width=-80, enabled_when='state != "run"'),
#                                                    Item('stop_time'),),
#                                             label='parameter'),
#                                      VGroup(HGroup(Item('laser',         width=-80, enabled_when='state != "run"'),
#                                                    Item('wait',          width=-80, enabled_when='state != "run"'),
#                                                    Item('record_length', width=-80, enabled_when='state != "run"'),
#                                                    Item('bin_width',     width=-80, enabled_when='state != "run"'),),
#                                                    label='settings'),
#                                      ),
#                               ),
#                        title='DQTFID3pi2 Measurement',
#                        )
