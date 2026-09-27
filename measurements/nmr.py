# PY3-PORT: threading camelCase aliases (currentThread, isSet,
# setDaemon, ...) were deprecated in Python 3.10 and REMOVED in 3.13.
# Rewritten to the snake_case names, which have worked since 2.6.
"""
Provides NMR measurement based on pulsed measurement and step by step RF sweep.
"""

import logging
import time

import numpy as np
from traits.api import Range, Float, Int, Array
from traitsui.api import View, Item, HGroup, VGroup, Tabbed, TextEditor

from .pulsed import Pulsed, sequence_remove_zeros, sequence_union


class NMR(Pulsed):
    mw_power = Range(low=-100., high=25., value=-100, desc='microwave power', label='MW power [dBm]', mode='text',
                     auto_set=False, enter_set=True)
    mw_frequency = Float(default_value=2.883450e9, desc='microwave frequency', label='MW frequency [Hz]', mode='text',
                         auto_set=False, enter_set=True)
    mw_t_pi = Float(default_value=800., desc='length of pi pulse of MW[ns]', label='MW pi [ns]', mode='text',
                    auto_set=False, enter_set=True)

    rf_power = Range(low=-100., high=17., value=-60, desc='RF power', label='RF power [dBm]', mode='text',
                     auto_set=False, enter_set=True)
    rf_begin = Float(default_value=2.4e6, desc='Start Frequency [Hz]', label='RF Begin [Hz]', mode='text',
                     auto_set=False, enter_set=True)
    rf_end = Float(default_value=2.7e6, desc='Stop Frequency [Hz]', label='RF End [Hz]', mode='text', auto_set=False,
                   enter_set=True)
    rf_delta = Float(default_value=2.0e3, desc='frequency step [Hz]', label='Delta [Hz]', mode='text', auto_set=False,
                     enter_set=True)
    rf_t_pi = Float(default_value=1.e6, desc='length of pi pulse of RF[ns]', label='RF pi [ns]', mode='text',
                    auto_set=False, enter_set=True)

    laser = Float(default_value=3000., desc='laser [ns]', label='laser [ns]', mode='text', auto_set=False,
                  enter_set=True)
    decay = Float(default_value=2.0e6, desc='decay [ns]', label='decay [ns]', mode='text', auto_set=False,
                  enter_set=True)
    aom_delay = Float(default_value=0.0,
                      desc='If set to a value other than 0.0, the aom triggers are applied\nearlier by the specified value. Use with care!',
                      label='aom delay [ns]', mode='text', auto_set=False, enter_set=True)

    seconds_per_point = Float(default_value=0.5, desc='Seconds per point', label='Seconds per point', mode='text',
                              auto_set=False, enter_set=True)
    sweeps_per_point = Int()

    frequencies = Array(value=np.array((0., 1.)))

    def __init__(self, pulse_generator, time_tagger, mw_source, rf_source, **kwargs):
        super(NMR, self).__init__(pulse_generator, time_tagger, **kwargs)
        self.mw_source = mw_source
        self.rf_source = rf_source

    def generate_sequence(self):
        # ESR:
        # return 100*[ (['aom','detect','microwave'], self.laser), (['sequence'], 18) ]
        # decay - rf_pi-pulse - readout / polarize
        aom_delay = self.aom_delay
        laser = self.laser
        decay = self.decay
        rf_t_pi = self.rf_t_pi
        s_aom = 100 * [([], decay + rf_t_pi), (['aom'], laser), ([], 18)]
        s_other = [([], aom_delay)] + 100 * [([], decay), (['rf'], rf_t_pi), (['detect'], laser), (['sequence'], 18)]
        s_aom = sequence_remove_zeros(s_aom)
        s_other = sequence_remove_zeros(s_other)
        sequence = sequence_union(s_aom, s_other)
        return sequence

    def apply_parameters(self):
        """Apply the current parameters and decide whether to keep previous data."""

        frequencies = np.arange(self.rf_begin, self.rf_end + self.rf_delta, self.rf_delta)
        n_bins = int(self.record_length / self.bin_width)
        time_bins = self.bin_width * np.arange(n_bins)
        sequence = self.generate_sequence()

        if not (self.keep_data and sequence == self.sequence and np.all(time_bins == self.time_bins) and np.all(
                frequencies == self.frequencies)):  # if the sequence and time_bins are the same as previous, keep existing data
            self.count_data = np.zeros((len(frequencies), n_bins))
            self.run_time = 0.0

        self.frequencies = frequencies
        self.sequence = sequence
        self.time_bins = time_bins
        self.n_bins = n_bins
        # ESR:
        # self.sweeps_per_point = int(self.seconds_per_point * 1e9 / (self.laser))
        self.sweeps_per_point = int(
            np.max((1, int(self.seconds_per_point * 1e9 / (self.laser + self.decay + self.rf_t_pi)))))
        self.keep_data = True  # when job manager stops and starts the job, data should be kept. Only new submission should clear data.

    def _run(self):
        """Acquire data."""

        try:  # try to run the acquisition from beginning to end
            self.state = 'run'
            self.apply_parameters()

            if self.run_time >= self.stop_time:
                logging.getLogger().debug('Runtime larger than stop_time. Returning')
                self.state = 'done'
                return

            self.pulse_generator.Night()
            self.mw_source.setOutput(self.mw_power, self.mw_frequency)
            if self.channel_apd_0 > -1:
                pulsed_0 = self.time_tagger.Pulsed(self.n_bins, int(np.round(self.bin_width * 1000)), 1,
                                                   self.channel_apd_0, self.channel_detect, self.channel_sequence)
                pulsed_0.setMaxCounts(self.sweeps_per_point)
            if self.channel_apd_1 > -1:
                pulsed_1 = self.time_tagger.Pulsed(self.n_bins, int(np.round(self.bin_width * 1000)), 1,
                                                   self.channel_apd_1, self.channel_detect, self.channel_sequence)
                pulsed_1.setMaxCounts(self.sweeps_per_point)

            self.pulse_generator.Sequence(self.sequence)
            if self.pulse_generator.checkUnderflow():
                raise RuntimeError('Underflow in pulse generator.')

            while self.run_time < self.stop_time:

                new_counts = np.zeros_like(self.count_data)

                start_time = time.time()

                for i, fi in enumerate(self.frequencies):

                    if self.thread.stop_request.is_set():
                        break

                    self.rf_source.setOutput(self.rf_power, fi)

                    if self.channel_apd_0 > -1:
                        pulsed_0.clear()
                    if self.channel_apd_1 > -1:
                        pulsed_1.clear()

                    if self.channel_apd_0 > -1:
                        while not pulsed_0.ready():
                            time.sleep(1.1 * self.seconds_per_point)
                    if self.channel_apd_1 > -1:
                        while not pulsed_1.ready():
                            time.sleep(1.1 * self.seconds_per_point)

                    if self.pulse_generator.checkUnderflow():
                        raise RuntimeError('Underflow in pulse generator.')

                    if self.channel_apd_0 > -1:
                        new_counts[i, :] = pulsed_0.getData()[0]
                    if self.channel_apd_1 > -1:
                        new_counts[i, :] = pulsed_1.getData()[0]
                else:
                    self.run_time += time.time() - start_time
                    self.count_data += new_counts
                    self.trait_property_changed('count_data', self.count_data)

                if self.thread.stop_request.is_set():
                    break

            if self.run_time < self.stop_time:
                self.state = 'idle'
            else:
                try:
                    self.save(self.filename)
                except:
                    logging.getLogger().exception('Failed to save the data to file.')
                self.state = 'done'
            if self.channel_apd_0 > -1:
                del pulsed_0
            if self.channel_apd_1 > -1:
                del pulsed_1
            self.pulse_generator.Light()
            self.mw_source.setOutput(None, self.mw_frequency)
            self.rf_source.setOutput(None, self.rf_begin)

        except:  # if anything fails, log the exception and set the state
            logging.getLogger().exception('Something went wrong in pulsed loop.')
            self.state = 'error'

    get_set_items = Pulsed.get_set_items + ['mw_frequency', 'mw_power', 'mw_t_pi',
                                            'rf_power', 'rf_begin', 'rf_end', 'rf_delta', 'rf_t_pi',
                                            'laser', 'decay', 'aom_delay', 'seconds_per_point', 'frequencies',
                                            'count_data', 'sequence']

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
                              Tabbed(VGroup(HGroup(Item('mw_power', width=-40),
                                                   Item('mw_frequency', width=-80,
                                                        editor=TextEditor(auto_set=False, enter_set=True,
                                                                          evaluate=float,
                                                                          format_func=lambda x: '%e' % x)),
                                                   Item('mw_t_pi', width=-80),
                                                   ),
                                            HGroup(Item('rf_power', width=-40),
                                                   Item('rf_begin', width=-80,
                                                        editor=TextEditor(auto_set=False, enter_set=True,
                                                                          evaluate=float,
                                                                          format_func=lambda x: '%e' % x)),
                                                   Item('rf_end', width=-80,
                                                        editor=TextEditor(auto_set=False, enter_set=True,
                                                                          evaluate=float,
                                                                          format_func=lambda x: '%e' % x)),
                                                   Item('rf_delta', width=-80,
                                                        editor=TextEditor(auto_set=False, enter_set=True,
                                                                          evaluate=float,
                                                                          format_func=lambda x: '%e' % x)),
                                                   Item('rf_t_pi', width=-80),
                                                   ),
                                            HGroup(Item('laser', width=-80, enabled_when='state != "run"'),
                                                   Item('decay', width=-80, enabled_when='state != "run"'),
                                                   Item('aom_delay', width=-80, enabled_when='state != "run"'),
                                                   ),
                                            label='stimulation'),
                                     VGroup(HGroup(Item('record_length', width=-80, enabled_when='state != "run"'),
                                                   Item('bin_width', width=-80, enabled_when='state != "run"'),
                                                   ),
                                            HGroup(
                                                Item('seconds_per_point', width=-120, enabled_when='state == "idle"'),
                                                Item('sweeps_per_point', width=-120, style='readonly'),
                                            ),
                                            label='acquisition'),
                                     VGroup(HGroup(Item('integration_width'),
                                                   Item('position_signal'),
                                                   Item('position_normalize'),
                                                   ),
                                            label='analysis'),
                                     ),
                              ),
                       title='NMR',
                       )


if __name__ == '__main__':
    """
    Test code using dummy hardware
    """
    # from hardware.dummy import PulseGenerator, TimeTagger, Microwave

    # pulse_generator = PulseGenerator()
    # time_tagger = TimeTagger()
    # microwave = Microwave()

    # from tools.emod import JobManager
    # JobManager().start()

    # nmr = NMR(pulse_generator,time_tagger,microwave,microwave)
    nmr = NMR(pulse_generator, time_tagger, microwave, rf_source)
    nmr.edit_traits()
