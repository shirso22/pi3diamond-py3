# PY3-PORT: threading camelCase aliases (currentThread, isSet,
# setDaemon, ...) were deprecated in Python 3.10 and REMOVED in 3.13.
# Rewritten to the snake_case names, which have worked since 2.6.
"""
Provides basis for a pulsed measurement based on pulse_generator and time_tagger.
"""

import logging
import time

import numpy as np
from traits.api import Range, Int, Float, Bool, Array, Instance, on_trait_change, Button
from traitsui.api import View, Item, HGroup, VGroup

from tools.emod import ManagedJob
from tools.utility import GetSetItemsMixin

"""
Several options to decide when to start  and when to restart a job, i.e. when to clear data, etc.

1. set a 'new' flag on every submit button

pro: simple, need not to think about anything in subclass

con: continue of measurement only possible by hack (manual submit to JobManager without submit button)
     submit button does not do what it says
     
2. check at start time whether this is a new measurement.

pro: 

con: complicated checking needed
     checking has to be reimplemented on sub classes
     no explicit way to restart the same measurement

3. provide user settable clear / keep flag

pro: explicit

con: user can forget

4. provide two different submit buttons: submit, resubmit

pro: explicit

con: two buttons that user may not understand
     user may use wrong button
     wrong button can result in errors

"""

from analysis.fitting import find_edge


# utility functions
def find_detection_pulses(sequence):
    """
    Find the number of detection triggers in a pulse sequence.
    """
    n = 0
    prev = []
    for channels, t in sequence:
        if 'detect' in channels and not 'detect' in prev:
            n += 1
        prev = channels
        if 'sequence' in channels:
            break
    return n


def sequence_length(sequence):
    """
    Return the total length of a pulse sequence.
    """
    t = 0
    for c, ti in sequence:
        t += ti
    return t


def sequence_union(s1, s2):
    """
    Return the union of two pulse sequences s1 and s2.
    """
    # make sure that s1 is the longer sequence and s2 is merged into it
    if sequence_length(s1) < sequence_length(s2):
        sp = s2
        s2 = s1
        s1 = sp
    s = []
    c1, dt1 = s1.pop(0)
    c2, dt2 = s2.pop(0)
    while True:
        if dt1 < dt2:
            s.append((set(c1) | set(c2), dt1))
            dt2 -= dt1
            try:
                c1, dt1 = s1.pop(0)
            except:
                break
        elif dt2 < dt1:
            s.append((set(c1) | set(c2), dt2))
            dt1 -= dt2
            try:
                c2, dt2 = s2.pop(0)
            except:
                c2 = []
                dt2 = np.inf
        else:
            s.append((set(c1) | set(c2), dt1))
            try:
                c1, dt1 = s1.pop(0)
            except:
                break
            try:
                c2, dt2 = s2.pop(0)
            except:
                c2 = []
                dt2 = np.inf
    return s


def sequence_simplify(sequence):
    """Merge adjacent pulses that have equal channels"""
    i = 0
    end = len(sequence)
    current = sequence[i]
    while i + 1 < end:
        next = sequence[i + 1]
        if current[0] == next[0]:  # merge next into the current one, pop next, and decrease length
            sequence[i] = (current[0], current[1] + next[1])
            sequence.pop(i + 1)
            end -= 1
        else:  # move one to the right
            i += 1
            current = next
    return sequence


def sequence_remove_zeros(sequence):
    """remove all pulses with zero length from a sequence"""
    return [x for x in sequence if x[1] != 0.0]


def spin_state(c, dt, T, t0=0.0, t1=-1.):
    """
    Compute the spin state from a 2D array of count data.
    
    Parameters:
    
        c    = count data
        dt   = time step
        t0   = beginning of integration window relative to the edge
        t1   = None or beginning of integration window for normalization relative to edge
        T    = width of integration window
        
    Returns:
    
        y       = 1D array that contains the spin state
        profile = 1D array that contains the pulse profile
        edge    = position of the edge that was found from the pulse profile
        
    If t1<0, no normalization is performed. If t1>=0, each data point is divided by
    the value from the second integration window and multiplied with the mean of
    all normalization windows.
    """

    profile = c.sum(0)
    edge = find_edge(profile)

    I = int(round(T / float(dt)))
    i0 = edge + int(round(t0 / float(dt)))
    y = np.empty((c.shape[0],))
    for i, slot in enumerate(c):
        y[i] = slot[i0:i0 + I].sum()
    if t1 >= 0:
        i1 = edge + int(round(t1 / float(dt)))
        y1 = np.empty((c.shape[0],))
        for i, slot in enumerate(c):
            y1[i] = slot[i1:i1 + I].sum()
        y = y / y1 * y1.mean()
    return y, profile, edge


class Pulsed(ManagedJob, GetSetItemsMixin):
    """Defines a pulsed measurement."""

    run_time = Float(value=0.0, label='run time [s]', format_str='%.f')
    stop_time = Float(default_value=np.inf, desc='Time after which the experiment stops by itself [s]',
                      label='Stop time [s]', mode='text', auto_set=False, enter_set=True)
    stop_counts = Float(default_value=np.inf,
                        desc='Stop the measurement when all data points of the extracted spin state have at least this many counts.',
                        label='Stop counts', mode='text', auto_set=False, enter_set=True)

    keep_data = Bool(False)  # helper variable to decide whether to keep existing data

    resubmit_button = Button(label='resubmit',
                             desc='Submits the measurement to the job manager. Tries to keep previously acquired data. Behaves like a normal submit if sequence or time bins have changed since previous run.')

    # acquisition parameters    
    record_length = Float(default_value=3000, desc='length of acquisition record [ns]', label='record length [ns]',
                          mode='text', auto_set=False, enter_set=True)
    bin_width = Range(low=0.1, high=1000., value=1.0, desc='bin width [ns]', label='bin width [ns]', mode='text',
                      auto_set=False, enter_set=True)

    n_laser = Int(2)
    n_bins = Int(2)
    time_bins = Array(value=np.array((0, 1)))

    sequence = Instance(list, factory=list)

    # measured data
    count_data = Array(value=np.zeros((2, 2)))

    # parameters for calculating spin state
    integration_width = Float(default_value=400., desc='width of integration window [ns]', label='integr. width [ns]',
                              mode='text', auto_set=False, enter_set=True)
    position_signal = Float(default_value=0., desc='position of signal window relative to edge [ns]',
                            label='pos. signal [ns]', mode='text', auto_set=False, enter_set=True)
    position_normalize = Float(default_value=2500.,
                               desc='position of normalization window relative to edge [ns]. If negative, no normalization is performed',
                               label='pos. norm. [ns]', mode='text', auto_set=False, enter_set=True)

    # analyzed data
    pulse = Array(value=np.array((0., 0.)))
    edge = Float(value=0.0)
    spin_state = Array(value=np.array((0., 0.)))

    channel_apd_0 = Int(0)
    channel_apd_1 = Int(1)
    channel_detect = Int(2)
    channel_sequence = Int(3)

    def __init__(self, pulse_generator, time_tagger, **kwargs):
        super(Pulsed, self).__init__(**kwargs)
        self.pulse_generator = pulse_generator
        self.time_tagger = time_tagger

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

    def apply_parameters(self):
        """Apply the current parameters and decide whether to keep previous data."""
        n_bins = int(self.record_length / self.bin_width)
        time_bins = self.bin_width * np.arange(n_bins)
        sequence = self.generate_sequence()
        n_laser = find_detection_pulses(sequence)

        if self.keep_data and sequence == self.sequence and np.all(
                time_bins == self.time_bins):  # if the sequence and time_bins are the same as previous, keep existing data
            self.old_count_data = self.count_data.copy()
        else:
            self.old_count_data = np.zeros((n_laser, n_bins))
            self.count_data = np.zeros((n_laser, n_bins))
            self.run_time = 0.0

        self.sequence = sequence
        self.time_bins = time_bins
        self.n_bins = n_bins
        self.n_laser = n_laser
        self.keep_data = True  # when job manager stops and starts the job, data should be kept. Only new submission should clear data.

    def start_up(self):
        """Put here additional stuff to be executed at startup."""
        pass

    def shut_down(self):
        """Put here additional stuff to be executed at shut_down."""
        pass

    def _run(self):
        """Acquire data."""

        try:  # try to run the acquisition from start_up to shut_down
            self.state = 'run'
            self.apply_parameters()

            if not (self.run_time < self.stop_time and any(self.spin_state < self.stop_counts)):
                logging.getLogger().debug('Runtime larger than stop_time. Returning')
                self.state = 'done'
                return

            self.start_up()
            self.pulse_generator.Night()
            if self.channel_apd_0 > -1:
                pulsed_0 = self.time_tagger.Pulsed(self.n_bins, int(np.round(self.bin_width * 1000)), self.n_laser,
                                                   self.channel_apd_0, self.channel_detect, self.channel_sequence)
            if self.channel_apd_1 > -1:
                pulsed_1 = self.time_tagger.Pulsed(self.n_bins, int(np.round(self.bin_width * 1000)), self.n_laser,
                                                   self.channel_apd_1, self.channel_detect, self.channel_sequence)
            self.pulse_generator.Sequence(self.sequence)
            self.pulse_generator.checkUnderflow()

            while self.run_time < self.stop_time and any(self.spin_state < self.stop_counts):
                start_time = time.time()
                self.thread.stop_request.wait(1.0)
                if self.thread.stop_request.is_set():
                    logging.getLogger().debug('Caught stop signal. Exiting.')
                    break
                if self.pulse_generator.checkUnderflow():
                    raise RuntimeError('Underflow in pulse generator.')
                if self.channel_apd_0 > -1 and self.channel_apd_1 > -1:
                    self.count_data = self.old_count_data + pulsed_0.getData() + pulsed_1.getData()
                elif self.channel_apd_0 > -1:
                    self.count_data = self.old_count_data + pulsed_0.getData()
                elif self.channel_apd_1 > -1:
                    self.count_data = self.old_count_data + pulsed_1.getData()
                self.run_time += time.time() - start_time

            if self.run_time < self.stop_time and any(self.spin_state < self.stop_counts):
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
            self.shut_down()
            self.pulse_generator.Light()

        except:  # if anything fails, log the exception and set the state
            logging.getLogger().exception('Something went wrong in pulsed loop.')
            self.state = 'error'

    @on_trait_change('count_data,integration_width,position_signal,position_normalize')
    def _compute_spin_state(self):
        y, profile, edge = spin_state(c=self.count_data,
                                      dt=self.bin_width,
                                      T=self.integration_width,
                                      t0=self.position_signal,
                                      t1=self.position_normalize,
                                      )
        self.spin_state = y
        self.pulse = profile
        self.edge = self.time_bins[edge]

    traits_view = View(VGroup(HGroup(Item('submit_button', show_label=False),
                                     Item('remove_button', show_label=False),
                                     Item('resubmit_button', show_label=False),
                                     Item('priority', width=-40),
                                     Item('state', style='readonly'),
                                     Item('run_time', style='readonly', format_str='%.f'),
                                     Item('stop_time', format_str='%.f'),
                                     Item('stop_counts'),
                                     ),
                              HGroup(Item('filename', springy=True),
                                     Item('save_button', show_label=False),
                                     Item('load_button', show_label=False)
                                     ),
                              HGroup(Item('bin_width', width=-80, enabled_when='state != "run"'),
                                     Item('record_length', width=-80, enabled_when='state != "run"'),
                                     ),
                              ),
                       title='Pulsed Measurement',
                       )

    get_set_items = ['__doc__', 'record_length', 'bin_width', 'n_bins', 'time_bins', 'n_laser', 'sequence',
                     'count_data', 'run_time',
                     'integration_width', 'position_signal', 'position_normalize',
                     'pulse', 'edge', 'spin_state']


class PulsedTau(Pulsed):
    """Defines a Pulsed measurement with tau mesh."""

    tau_begin = Float(default_value=0., desc='tau begin [ns]', label='tau begin [ns]', mode='text', auto_set=False,
                      enter_set=True)
    tau_end = Float(default_value=300., desc='tau end [ns]', label='tau end [ns]', mode='text', auto_set=False,
                    enter_set=True)
    tau_delta = Float(default_value=3., desc='delta tau [ns]', label='delta tau [ns]', mode='text', auto_set=False,
                      enter_set=True)

    tau = Array(value=np.array((0., 1.)))

    def apply_parameters(self):
        """Overwrites apply_parameters() from pulsed. Prior to generating sequence, etc., generate the tau mesh."""
        self.tau = np.arange(self.tau_begin, self.tau_end + self.tau_delta, self.tau_delta)
        Pulsed.apply_parameters(self)

    get_set_items = Pulsed.get_set_items + ['tau_begin', 'tau_end', 'tau_delta', 'tau']

    traits_view = View(VGroup(HGroup(Item('submit_button', show_label=False),
                                     Item('remove_button', show_label=False),
                                     Item('resubmit_button', show_label=False),
                                     Item('priority'),
                                     Item('state', style='readonly'),
                                     Item('run_time', style='readonly', format_str='%.f'),
                                     Item('stop_time'),
                                     ),
                              HGroup(Item('filename', springy=True),
                                     Item('save_button', show_label=False),
                                     Item('load_button', show_label=False)
                                     ),
                              HGroup(Item('bin_width', width=-80, enabled_when='state != "run"'),
                                     Item('record_length', width=-80, enabled_when='state != "run"'),
                                     ),
                              ),
                       title='PulsedTau Measurement',
                       )


if __name__ == '__main__':
    logging.getLogger().addHandler(logging.StreamHandler())
    logging.getLogger().setLevel(logging.DEBUG)
    logging.getLogger().info('Starting logger.')

    from tools.emod import JobManager

    JobManager().start()

    from hardware.dummy import PulseGenerator, TimeTagger

    pulse_generator = PulseGenerator()
    time_tagger = TimeTagger()

    pulsed = PulsedTau(pulse_generator, time_tagger)
    pulsed.edit_traits()
