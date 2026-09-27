# PY3-PORT: threading camelCase aliases (currentThread, isSet,
# setDaemon, ...) were deprecated in Python 3.10 and REMOVED in 3.13.
# Rewritten to the snake_case names, which have worked since 2.6.
__version__ = '12.12.04'

import logging

from traits.api import Instance, Property, Range, Float, Int, Bool, Array, Button, \
    cached_property
from traitsui.api import View, Item, HGroup, VGroup, TextEditor
from hardware.api import FastComtec
from hardware.api import Microwave
from hardware.api import PulseGenerator
from hardware.waveform import *

from hardware.awg import *
from tools.emod import ManagedJob
from tools.utility import GetSetItemsMixin

PG = PulseGenerator()
MW = Microwave()
# MW = Microwave_HMC()
FC = FastComtec()
AWG = AWG()


# awg_device = AWG(('192.168.0.44', 4000))
# import SMIQ_2 as RF
def find_laser_pulses(sequence):
    n = 0
    prev = []
    for channels, t in sequence:
        if 'laser' in channels and not 'laser' in prev:
            n += 1
        prev = channels
        if 'sequence' in channels:
            break
    return n


class Pulsed(ManagedJob, GetSetItemsMixin):
    """Defines a pulsed measurement."""
    keep_data = Bool(False)  # helper variable to decide whether to keep existing data

    resubmit_button = Button(label='resubmit',
                             desc='Submits the measurement to the job manager. Tries to keep previously acquired data. Behaves like a normal submit if sequence or time bins have changed since previous run.')

    sequence = Instance(list, factory=list)

    record_length = Range(low=100, high=100000., value=3000, desc='length of acquisition record [ns]',
                          label='record length [ns]', mode='text', auto_set=False, enter_set=True)
    bin_width = Range(low=0.1, high=1000., value=3.2, desc='data bin width [ns]', label='bin width [ns]', mode='text',
                      auto_set=False, enter_set=True)

    n_laser = Int(2)
    n_bins = Int(2)
    time_bins = Array(value=np.array((0, 1)))

    count_data = Array(value=np.zeros((2, 2)))

    run_time = Float(value=0.0, label='run time [ns]', format_str='%.f')
    stop_time = Range(low=1., value=np.inf, desc='Time after which the experiment stops by itself [s]',
                      label='Stop time [s]', mode='text', auto_set=False, enter_set=True)

    tau_begin = Range(low=0., high=1e8, value=300., desc='tau begin [ns]', label='tau begin [ns]', mode='text',
                      auto_set=False, enter_set=True)
    tau_end = Range(low=1., high=1e8, value=4000., desc='tau end [ns]', label='tau end [ns]', mode='text',
                    auto_set=False, enter_set=True)
    tau_delta = Range(low=1., high=1e8, value=50., desc='delta tau [ns]', label='delta tau [ns]', mode='text',
                      auto_set=False, enter_set=True)

    tau = Array(value=np.array((0., 1.)))

    laser = Range(low=1., high=5e6, value=3000., desc='laser [ns]', label='laser [ns]', mode='text', auto_set=False,
                  enter_set=True)
    wait = Range(low=1., high=5e6, value=5000., desc='wait [ns]', label='wait [ns]', mode='text', auto_set=False,
                 enter_set=True)

    freq_center = Range(low=1, high=20e9, value=2.71e9, desc='frequency [Hz]', label='MW frequency [Hz]', mode='text',
                        auto_set=False, enter_set=True)
    power = Range(low=-100., high=25., value=-26, desc='power [dBm]', label='power [dBm]', mode='text', auto_set=False,
                  enter_set=True)

    sweeps = Range(low=1., high=1e10, value=1e6, desc='number of sweeps', label='sweeps', mode='text', auto_set=False,
                   enter_set=True)
    expected_duration = Property(trait=Float, depends_on='sweeps,sequence',
                                 desc='expected duration of the measurement [s]', label='expected duration [s]')
    elapsed_sweeps = Float(value=0, desc='Elapsed Sweeps ', label='Elapsed Sweeps ', mode='text')
    elapsed_time = Float(value=0, desc='Elapsed Time [ns]', label='Elapsed Time [ns]', mode='text')
    progress = Int(value=0, desc='Progress [%]', label='Progress [%]', mode='text')

    load_button = Button(desc='compile and upload waveforms to AWG', label='load')
    reload = True

    def submit(self):
        """Submit the job to the JobManager."""
        self.keep_data = False
        ManagedJob.submit(self)

    def resubmit(self):
        """Submit the job to the JobManager."""
        self.keep_data = True
        ManagedJob.submit(self)

    def _resubmit_button_fired(self):
        """React to start button. Submit the Job."""
        self.resubmit()

    def generate_sequence(self):
        return []

    def prepare_awg(self):
        """ override this """
        AWG.reset()

    def _load_button_changed(self):
        self.load()

    def load(self):
        self.reload = True
        # make sure tau is updated
        self.tau = np.arange(self.tau_begin, self.tau_end, self.tau_delta)
        self.prepare_awg()
        self.reload = False

    @cached_property
    def _get_expected_duration(self):
        sequence_length = 0
        for step in self.sequence:
            sequence_length += step[1]
        return self.sweeps * sequence_length * 1e-9

    def _get_sequence_points(self):
        return len(self.tau)

    def apply_parameters(self):
        """Apply the current parameters and decide whether to keep previous data."""
        n_bins = int(self.record_length / self.bin_width)
        time_bins = self.bin_width * np.arange(n_bins)
        sequence = self.generate_sequence()
        """if load button is not used, make sure tau is generated"""
        if (self.tau.shape[0] == 2):
            tau = np.arange(self.tau_begin, self.tau_end, self.tau_delta)
            self.tau = tau
            # sequence_points = len(tau)
        n_laser = find_laser_pulses(sequence)

        self.sequence_points = self._get_sequence_points()
        self.time_bins = time_bins
        self.n_bins = n_bins
        self.n_laser = n_laser

        if self.keep_data and sequence == self.sequence and np.all(
                time_bins == self.time_bins):  # if the sequence and time_bins are the same as previous, keep existing data
            # print(1)
            self.old_count_data = self.count_data.copy()
            self.previous_sweeps = self.elapsed_sweeps
            self.previous_elapsed_time = self.elapsed_time
            self.keep_data = True  # when job manager stops and starts the job, data should be kept. Only new submission should clear data.
        else:

            # self.old_count_data = np.zeros((n_laser, n_bins))
            FC.Configure(self.laser, self.bin_width, self.sequence_points)
            # self.check = True
            self.old_count_data = np.zeros(FC.GetData().shape)
            self.count_data = np.zeros(FC.GetData().shape)
            self.previous_sweeps = 0
            self.previous_elapsed_time = 0.0
            self.run_time = 0.0
            self.keep_data = True  # when job manager stops and starts the job, data should be kept. Only new submission should clear data.

        self.sequence = sequence

    def _run(self):
        """Acquire data."""

        try:  # try to run the acquisition from start_up to shut_down
            self.state = 'run'
            self.apply_parameters()

            PG.High([])
            FC.SetCycles(np.inf)
            FC.SetTime(np.inf)
            FC.SetDelay(0)
            FC.SetLevel(0.6, 0.6)
            FC.Configure(self.laser, self.bin_width, self.sequence_points)
            # self.previous_time = 0
            # self.previous_count_data = FC.GetData()
            self.prepare_awg()
            MW.setFrequency(self.freq_center)
            MW.setPower(self.power)
            AWG.run()
            time.sleep(4.0)
            FC.Start()
            time.sleep(0.1)
            PG.Sequence(self.sequence, loop=True)

            start_time = time.time()

            while True:
                self.thread.stop_request.wait(5.0)
                if self.thread.stop_request.is_set():
                    logging.getLogger().debug('Caught stop signal. Exiting.')
                    break
                self.elapsed_time = self.previous_elapsed_time + time.time() - start_time
                self.run_time += self.elapsed_time
                runtime, cycles = FC.GetState()
                sweeps = cycles / FC.GetData().shape[0]
                self.elapsed_sweeps = self.previous_sweeps + sweeps
                self.progress = int(100 * self.elapsed_sweeps / self.sweeps)
                self.count_data = self.old_count_data + FC.GetData()
                # print(FC.GetData()[0:20])
                if self.elapsed_sweeps > self.sweeps:
                    break

            FC.Halt()
            MW.Off()
            PG.High(['laser', 'mw'])
            AWG.stop()
            if self.elapsed_sweeps < self.sweeps:
                self.state = 'idle'
            else:
                self.state = 'done'

        except:  # if anything fails, log the exception and set the state
            logging.getLogger().exception('Something went wrong in pulsed loop.')
            self.state = 'error'

    get_set_items = ['__doc__', 'record_length', 'laser', 'wait', 'bin_width', 'n_bins', 'time_bins', 'n_laser',
                     'sequence', 'count_data', 'run_time', 'tau_begin', 'tau_end', 'tau_delta', 'tau', 'freq_center',
                     'power']

    traits_view = View(VGroup(HGroup(Item('load_button', show_label=False),
                                     Item('submit_button', show_label=False),
                                     Item('remove_button', show_label=False),
                                     Item('resubmit_button', show_label=False),
                                     Item('priority'),
                                     ),
                              HGroup(Item('freq', width=30),
                                     Item('power', width=20),
                                     ),
                              HGroup(Item('laser', width=20),
                                     Item('wait', width=20),
                                     Item('bin_width', width=20, enabled_when='state != "run"'),
                                     Item('record_length', width=20, enabled_when='state != "run"'),
                                     ),

                              HGroup(Item('tau_begin', width=40),
                                     Item('tau_end', width=40),
                                     Item('tau_delta', width=40),
                                     ),

                              HGroup(Item('state', style='readonly'),
                                     Item('run_time', style='readonly', format_str='%.f'),
                                     Item('sweeps', editor=TextEditor(auto_set=False, enter_set=True, evaluate=float,
                                                                      format_func=lambda x: '%.3e' % x), width=30),
                                     Item('expected_duration', style='readonly',
                                          editor=TextEditor(evaluate=float, format_func=lambda x: '%.f' % x), width=30),
                                     Item('progress', style='readonly'),
                                     Item('elapsed_time', style='readonly',
                                          editor=TextEditor(auto_set=False, enter_set=True, evaluate=float,
                                                            format_func=lambda x: ' %.f' % x), width=30),
                                     ),

                              ),
                       title='Pulsed AWG Measurement',
                       )


class ODMR(Pulsed):
    """Rabi measurement.
    """
    # def _init_(self):
    # super(Rabi, self).__init__()

    reload = True

    tau_begin = Range(low=0., high=20e9, value=1.9e9, desc='freq begin [Hz]', label='freq begin [Hz]', mode='text',
                      auto_set=False, enter_set=True)
    tau_end = Range(low=1., high=20e9, value=2.0e9, desc='freq end [Hz]', label='freq end [Hz]', mode='text',
                    auto_set=False, enter_set=True)
    tau_delta = Range(low=1., high=1e9, value=1e6, desc='delt freq [Hz]', label='delta freq [Hz]', mode='text',
                      auto_set=False, enter_set=True)

    amp = Range(low=0., high=1.0, value=1.0, desc='Normalized amplitude of waveform', label='WFM amp', mode='text',
                auto_set=False, enter_set=True)
    vpp = Range(low=0., high=4.5, value=0.6, desc='Amplitude of AWG [Vpp]', label='AWG vpp', mode='text',
                auto_set=False, enter_set=True)

    pi = Range(low=0., high=5e4, value=2e3, desc='pi pulse length', label='pi [ns]', mode='text', auto_set=False,
               enter_set=True)

    def prepare_awg(self):
        sampling = 1.2e9
        pi = int(self.pi * sampling / 1.0e9)

        if self.reload:
            AWG.stop()
            AWG.set_output(0b0000)
            AWG.delete_all()

            zero = Idle(1)
            self.waves = []
            self.main_seq = Sequence('ODMR.SEQ')
            for i, t in enumerate(self.tau):
                drive_x = Sin(pi, (t - self.freq_center) / sampling, 0, self.amp)
                drive_y = Sin(pi, (t - self.freq_center) / sampling, np.pi / 2, self.amp)

                x_name = 'X_RA_%03i.WFM' % i
                y_name = 'Y_RA_%03i.WFM' % i
                self.waves.append(Waveform(x_name, [zero, drive_x, zero]))
                self.waves.append(Waveform(y_name, [zero, drive_y, zero]))
                self.main_seq.append(*self.waves[-2:], wait=True)
            for w in self.waves:
                w.join()
            AWG.upload(self.waves)
            AWG.upload(self.main_seq)
            AWG.tell('*WAI')
            AWG.load('ODMR.SEQ')
        AWG.set_vpp(self.vpp)
        AWG.set_sample(sampling / 1.0e9)
        AWG.set_mode('S')
        AWG.set_output(0b0011)

    def generate_sequence(self):
        tau = self.tau
        laser = self.laser
        wait = self.wait
        pi = self.pi
        sequence = []
        for t in tau:
            sequence.append((['awgTrigger'], 100))
            sequence.append(([], pi + 100))
            sequence.append((['laser', 'trigger'], laser))
            sequence.append(([], wait))
        # sequence.append(  ([                   ] , 12.5  )  )
        return sequence

    get_set_items = Pulsed.get_set_items + ['amp', 'vpp', 'pi']

    traits_view = View(VGroup(HGroup(Item('load_button', show_label=False),
                                     Item('submit_button', show_label=False),
                                     Item('remove_button', show_label=False),
                                     Item('resubmit_button', show_label=False),
                                     Item('priority'),
                                     ),
                              HGroup(Item('amp', width=-30),
                                     Item('vpp', width=-30),
                                     Item('freq_center', width=20),
                                     Item('power', width=-30),
                                     Item('pi', width=20),
                                     ),
                              HGroup(Item('laser', width=30),
                                     Item('wait', width=30),
                                     Item('bin_width', width=30, enabled_when='state != "run"'),
                                     Item('record_length', width=30, enabled_when='state != "run"'),
                                     ),

                              HGroup(Item('tau_begin', width=30),
                                     Item('tau_end', width=30),
                                     Item('tau_delta', width=30),
                                     ),

                              HGroup(Item('state', style='readonly'),
                                     Item('run_time', style='readonly', format_str='%.f', width=50),
                                     Item('sweeps', editor=TextEditor(auto_set=False, enter_set=True, evaluate=float,
                                                                      format_func=lambda x: '%.3e' % x), width=30),
                                     Item('expected_duration', style='readonly',
                                          editor=TextEditor(evaluate=float, format_func=lambda x: '%.f' % x), width=30),
                                     Item('progress', style='readonly'),
                                     Item('elapsed_time', style='readonly',
                                          editor=TextEditor(auto_set=False, enter_set=True, evaluate=float,
                                                            format_func=lambda x: ' %.f' % x), width=30),
                                     ),

                              ),
                       title='ODMR Measurement',
                       )


class Rabi(Pulsed):
    """Rabi measurement.
    """
    # def _init_(self):
    # super(Rabi, self).__init__()

    reload = True

    freq = Range(low=1, high=20e9, value=2.71e9, desc='frequency [Hz]', label='freq1 [Hz]', mode='text', auto_set=False,
                 enter_set=True)
    freq_2 = Range(low=1, high=20e9, value=2.71e9, desc='frequency [Hz]', label='freq2 [Hz]', mode='text',
                   auto_set=False, enter_set=True)
    freq_3 = Range(low=1, high=20e9, value=2.71e9, desc='frequency [Hz]', label='freq3 [Hz]', mode='text',
                   auto_set=False, enter_set=True)
    amp = Range(low=0., high=1.0, value=1.0, desc='Normalized amplitude of waveform', label='WFM amp', mode='text',
                auto_set=False, enter_set=True)
    vpp = Range(low=0., high=4.5, value=0.6, desc='Amplitude of AWG [Vpp]', label='AWG vpp', mode='text',
                auto_set=False, enter_set=True)
    phase = Bool(False, label='phase', desc='true, Y pulse, false, X pulse')
    phase_1 = Range(low=0., high=3.1415, value=0.0, desc='Amplitude of AWG [Vpp]', label='AWG vpp', mode='text',
                    auto_set=False, enter_set=True)

    def prepare_awg(self):
        sampling = 1.2e9
        if self.reload:
            AWG.stop()
            AWG.set_output(0b0000)
            AWG.delete_all()
            if self.phase:
                phase_1 = self.phase_1
            else:
                phase_1 = 0
            drive_x = Sin(0, (self.freq - self.freq_center) / sampling, 0, self.amp)
            drive_y = Sin(0, (self.freq - self.freq_center) / sampling, np.pi / 2 + phase_1, self.amp)
            zero = Idle(1)

            self.waves = []
            self.main_seq = Sequence('RABI.SEQ')
            for i, t in enumerate(self.tau):
                t = int(t * sampling / 1.0e9)

                drive_x.duration = t
                drive_y.duration = t
                x_name = 'X_RA_%03i.WFM' % i
                y_name = 'Y_RA_%03i.WFM' % i
                self.waves.append(Waveform(x_name, [zero, drive_x, zero]))
                self.waves.append(Waveform(y_name, [zero, drive_y, zero]))
                self.main_seq.append(*self.waves[-2:], wait=True)
            for w in self.waves:
                w.join()
            AWG.upload(self.waves)
            AWG.upload(self.main_seq)
            AWG.tell('*WAI')
            AWG.load('RABI.SEQ')
        AWG.set_vpp(self.vpp)
        AWG.set_sample(sampling / 1.0e9)
        AWG.set_mode('S')
        AWG.set_output(0b0011)

    def generate_sequence(self):
        tau = self.tau
        laser = self.laser
        wait = self.wait
        sequence = []
        for t in tau:
            sequence.append((['awgTrigger'], 100))
            sequence.append(([], t + 200))

            # sequence.append( (['laser'], laser) )
            # sequence.append( (['trigger'], 100) )
            sequence.append((['laser', 'trigger'], laser))
            sequence.append(([], wait))
        # sequence.append(  ([                   ] , 12.5  )  )
        return sequence

    get_set_items = Pulsed.get_set_items + ['freq', 'amp', 'vpp', 'phase_1']

    traits_view = View(VGroup(HGroup(Item('load_button', show_label=False),
                                     Item('submit_button', show_label=False),
                                     Item('remove_button', show_label=False),
                                     Item('resubmit_button', show_label=False),
                                     Item('priority'),
                                     ),
                              HGroup(Item('freq', width=20),
                                     Item('freq_2', width=20),
                                     Item('freq_3', width=20),
                                     Item('phase', width=20),
                                     Item('phase_1', width=20),

                                     ),
                              HGroup(Item('amp', width=20),
                                     Item('vpp', width=20),
                                     Item('freq_center', width=20),
                                     Item('power', width=20),
                                     ),
                              HGroup(Item('laser', width=30),
                                     Item('wait', width=30),
                                     Item('bin_width', width=30, enabled_when='state != "run"'),
                                     Item('record_length', width=30, enabled_when='state != "run"'),
                                     ),

                              HGroup(Item('tau_begin', width=30),
                                     Item('tau_end', width=30),
                                     Item('tau_delta', width=30),
                                     ),

                              HGroup(Item('state', style='readonly'),
                                     Item('run_time', style='readonly', format_str='%.f', width=50),
                                     Item('sweeps', editor=TextEditor(auto_set=False, enter_set=True, evaluate=float,
                                                                      format_func=lambda x: '%.3e' % x), width=30),
                                     Item('expected_duration', style='readonly',
                                          editor=TextEditor(evaluate=float, format_func=lambda x: '%.f' % x), width=30),
                                     Item('progress', style='readonly'),
                                     Item('elapsed_time', style='readonly',
                                          editor=TextEditor(auto_set=False, enter_set=True, evaluate=float,
                                                            format_func=lambda x: ' %.f' % x), width=30),
                                     ),

                              ),
                       title='Rabi Measurement',
                       )
