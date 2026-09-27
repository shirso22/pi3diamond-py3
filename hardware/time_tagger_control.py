# PY3-PORT: threading camelCase aliases (currentThread, isSet,
# setDaemon, ...) were deprecated in Python 3.10 and REMOVED in 3.13.
# Rewritten to the snake_case names, which have worked since 2.6.
import threading
import weakref

from traits.api import HasTraits, Range, Float, Bool
from traitsui.api import View, Item, Group, Label

from . import TimeTagger
from tools.utility import StoppableThread


class TimeTaggerControl(HasTraits):
    trigger_level_0 = Range(low=0., high=2.5, value=0.5, desc='trigger level for channel 0 in volts',
                            label='trigger level 0 [V]')
    trigger_level_1 = Range(low=0., high=2.5, value=0.5, desc='trigger level for channel 1 in volts',
                            label='trigger level 1 [V]')
    trigger_level_2 = Range(low=0., high=2.5, value=0.5, desc='trigger level for channel 2 in volts',
                            label='trigger level 2 [V]')
    trigger_level_3 = Range(low=0., high=2.5, value=0.5, desc='trigger level for channel 3 in volts',
                            label='trigger level 3 [V]')
    trigger_level_4 = Range(low=0., high=2.5, value=0.5, desc='trigger level for channel 4 in volts',
                            label='trigger level 4 [V]')
    trigger_level_5 = Range(low=0., high=2.5, value=0.5, desc='trigger level for channel 5 in volts',
                            label='trigger level 5 [V]')
    trigger_level_6 = Range(low=0., high=2.5, value=0.5, desc='trigger level for channel 6 in volts',
                            label='trigger level 6 [V]')
    trigger_level_7 = Range(low=0., high=2.5, value=0.5, desc='trigger level for channel 7 in volts',
                            label='trigger level 7 [V]')

    count_rate_0 = Float(default_value=0.0, desc='count rate for channel 0 in volts', label='count rate 0 [1/s]')
    count_rate_1 = Float(default_value=0.0, desc='count rate for channel 1 in volts', label='count rate 1 [1/s]')
    count_rate_2 = Float(default_value=0.0, desc='count rate for channel 2 in volts', label='count rate 2 [1/s]')
    count_rate_3 = Float(default_value=0.0, desc='count rate for channel 3 in volts', label='count rate 3 [1/s]')
    count_rate_4 = Float(default_value=0.0, desc='count rate for channel 4 in volts', label='count rate 4 [1/s]')
    count_rate_5 = Float(default_value=0.0, desc='count rate for channel 5 in volts', label='count rate 5 [1/s]')
    count_rate_6 = Float(default_value=0.0, desc='count rate for channel 6 in volts', label='count rate 6 [1/s]')
    count_rate_7 = Float(default_value=0.0, desc='count rate for channel 7 in volts', label='count rate 7 [1/s]')

    enable_filter = Bool(desc='Enable sync filter for channel 7. Events are filtered against channel 0.')

    refresh_interval = Range(low=0.01, high=1, value=0.5, desc='Refresh interval [s]', label='Refresh interval [s]')

    def __init__(self, time_tagger, **kwargs):
        self.time_tagger = time_tagger
        self._create_counter()
        super(TimeTaggerControl, self).__init__(**kwargs)
        # self._stoppable_thread = StoppableThread(target=self._run)
        self._stoppable_thread = StoppableThread(target=TimeTaggerControl._run, args=(weakref.proxy(self),))
        self._stoppable_thread.start()

    def _create_counter(self):
        self._counter = TimeTagger.Countrate(self.time_tagger, [0, 1, 2, 3, 4, 5, 6, 7])

    def _refresh_counter(self):
        self.count_rate_0, self.count_rate_1, self.count_rate_2, self.count_rate_3, self.count_rate_4, self.count_rate_5, self.count_rate_6, self.count_rate_7 = self._counter.getData()
        self._counter.clear()

    def _run(self):
        while not threading.current_thread().stop_request.is_set():
            self._refresh_counter()
            threading.current_thread().stop_request.wait(self.refresh_interval)

    def _trigger_level_0_default(self):
        return self.time_tagger.getTriggerLevel(0)

    def _trigger_level_1_default(self):
        return self.time_tagger.getTriggerLevel(1)

    def _trigger_level_2_default(self):
        return self.time_tagger.getTriggerLevel(2)

    def _trigger_level_3_default(self):
        return self.time_tagger.getTriggerLevel(3)

    def _trigger_level_4_default(self):
        return self.time_tagger.getTriggerLevel(4)

    def _trigger_level_5_default(self):
        return self.time_tagger.getTriggerLevel(5)

    def _trigger_level_6_default(self):
        return self.time_tagger.getTriggerLevel(6)

    def _trigger_level_7_default(self):
        return self.time_tagger.getTriggerLevel(7)

    def _trigger_level_0_changed(self, new):
        self.time_tagger.setTriggerLevel(0, new)

    def _trigger_level_1_changed(self, new):
        self.time_tagger.setTriggerLevel(1, new)

    def _trigger_level_2_changed(self, new):
        self.time_tagger.setTriggerLevel(2, new)

    def _trigger_level_3_changed(self, new):
        self.time_tagger.setTriggerLevel(3, new)

    def _trigger_level_4_changed(self, new):
        self.time_tagger.setTriggerLevel(4, new)

    def _trigger_level_5_changed(self, new):
        self.time_tagger.setTriggerLevel(5, new)

    def _trigger_level_6_changed(self, new):
        self.time_tagger.setTriggerLevel(6, new)

    def _trigger_level_7_changed(self, new):
        self.time_tagger.setTriggerLevel(7, new)

    def _enable_filter_default(self):
        return self.time_tagger.getFilter()

    def _enable_filter_changed(self, new):
        self.time_tagger.setFilter(new)

    def __del__(self):
        self._stoppable_thread.stop()

    def Countrate(self, *args):
        return TimeTagger.Countrate(self.time_tagger, *args)

    def Counter(self, *args):
        return TimeTagger.Counter(self.time_tagger, *args)

    def Pulsed(self, *args):
        """Backward compatibility to old pulsed class"""
        n_bins, binwidth, n_histograms, click_channel, start_channel, sync_channel = args
        return TimeTagger.TimeDifferences(self.time_tagger,
                                          click_channel,
                                          start_channel,
                                          start_channel,
                                          sync_channel,
                                          binwidth,
                                          n_bins,
                                          n_histograms)

    def TimeDifferences(self, *args):
        return TimeTagger.TimeDifferences(self.time_tagger, *args)

    traits_view = View(Group(Label('Channel'), Label('Trigger level [V]'), Label('count rate [1/s]'),
                             Label('0'), Item('trigger_level_0', show_label=False),
                             Item('count_rate_0', show_label=False, style='readonly', format_str='%.f', width=-80),
                             Label('1'), Item('trigger_level_1', show_label=False),
                             Item('count_rate_1', show_label=False, style='readonly', format_str='%.f', width=-80),
                             Label('2'), Item('trigger_level_2', show_label=False),
                             Item('count_rate_2', show_label=False, style='readonly', format_str='%.f', width=-80),
                             Label('3'), Item('trigger_level_3', show_label=False),
                             Item('count_rate_3', show_label=False, style='readonly', format_str='%.f', width=-80),
                             Label('4'), Item('trigger_level_4', show_label=False),
                             Item('count_rate_4', show_label=False, style='readonly', format_str='%.f', width=-80),
                             Label('5'), Item('trigger_level_5', show_label=False),
                             Item('count_rate_5', show_label=False, style='readonly', format_str='%.f', width=-80),
                             Label('6'), Item('trigger_level_6', show_label=False),
                             Item('count_rate_6', show_label=False, style='readonly', format_str='%.f', width=-80),
                             Label('7'), Item('trigger_level_7', show_label=False),
                             Item('count_rate_7', show_label=False, style='readonly', format_str='%.f', width=-80),
                             orientation='vertical', columns=3,
                             ),
                       Item('enable_filter'),
                       title='Time Tagger'
                       )


if __name__ == '__main__':
    from .TimeTagger import createTimeTagger

    time_tagger = createTimeTagger(serial='12220003BR')

    control = TimeTaggerControl(time_tagger)
    control.edit_traits()
