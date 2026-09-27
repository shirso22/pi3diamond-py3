# PY3-PORT: threading camelCase aliases (currentThread, isSet,
# setDaemon, ...) were deprecated in Python 3.10 and REMOVED in 3.13.
# Rewritten to the snake_case names, which have worked since 2.6.
import pickle
import logging
import os
import threading
import time
# PY3-PORT: was `from exceptions import IOError`. The `exceptions`
# module is gone in Python 3; these are builtins.

from chaco.api import PlotGraphicsContext
# Enthought library imports
from traits.api import HasTraits, Str, File, Button
from traitsui.api import View, Item, OKButton, CancelButton, HGroup

from .data_toolbox import writeDictToFile, load_pickle


def timestamp():
    """Returns the current time as a human readable string."""
    return time.strftime('%y-%m-%d_%Hh%Mm%S', time.localtime())


class Singleton(type):
    """
    Singleton using metaclass.
    
    Usage:
    
    class Myclass( MyBaseClass )
        __metaclass__ = Singleton
    
    Taken from stackoverflow.com.
    http://stackoverflow.com/questions/6760685/creating-a-singleton-in-python
    """
    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]


# class Singleton(object):
#    """
#    Singleton overwriting __new__.
#
#    Cons: multiple inheritance
#          __new__ could be overwritten
#          __init__ is called upon every 'instantiation'
#    """
#    def __new__(cls, *a, **k):
#        if not hasattr(cls, '_inst'):
#            cls._inst = super(Singleton, cls).__new__(cls)
#        return cls._inst

class History(object):
    """History of length 'length'."""

    def __init__(self, length):
        self.length = length
        self.items = []
        self.i = 0

    def get(self):
        return self.items[self.i]

    def back(self):
        if self.i != 0:
            self.i = self.i - 1
        return self.items[self.i]

    def forward(self):
        if self.i != len(self.items) - 1:
            self.i = self.i + 1
        return self.items[self.i]

    def put(self, item):
        while self.i < len(self.items) - 1:
            self.items.pop()
        if self.i == self.length - 1:
            self.items.pop(0)
        self.items.append(item)
        self.i = len(self.items) - 1

    def setlength(self, length):
        while len(self.items) > length:
            self.items.pop(0)
            self.i = self.i - 1
        self.length = length


class StoppableThread(threading.Thread):
    """
    A thread that can be stopped.
    
    Parameters:
        target:    callable that will be execute by the thread
        name:      string that will be used as a name for the thread
    
    Methods:
        stop():    stop the thread
        
    Use threading.current_thread().stop_request.is_set()
    or threading.current_thread().stop_request.wait([timeout])
    in your target callable to react to a stop request.
    """

    def __init__(self, *arguments, **kwargs):
        self.stop_request = threading.Event()
        threading.Thread.__init__(self, *arguments, **kwargs)

    #    def __init__(self, target=None, name=None):
    #        threading.Thread.__init__(self, target=target, name=name)
    #        self.stop_request = threading.Event()

    def stop(self, timeout=10.):
        name = str(self)
        logging.getLogger().debug('attempt to stop thread ' + name)
        if threading.current_thread() is self:
            logging.getLogger().debug('Thread ' + name + ' attempted to stop itself. Ignoring stop request...')
            return
        elif not self.is_alive():
            logging.getLogger().debug('Thread ' + name + ' is not running. Continuing...')
            return
        self.stop_request.set()
        self.join(timeout)
        if self.is_alive():
            logging.getLogger().warning(
                'Thread ' + name + ' failed to join after ' + str(timeout) + ' s. Continuing anyway...')


# PY3-PORT: Traits 6.0 removed the Singleton* base classes.
from traits.api import HasPrivateTraits
from .ets_compat import SingletonHasPrivateTraits


class DialogBox(HasPrivateTraits):
    """Dialog box for showing a message."""
    message = Str


class FileDialogBox(SingletonHasPrivateTraits):
    """Dialog box for selection of a filename string."""
    filename = File


def warning(message='', buttons=[OKButton, CancelButton]):
    """
    Displays 'message' in a dialog box and returns True or False
    if 'OK' respectively 'Cancel' button pressed.
    """
    dialog_box = DialogBox(message=message)
    ui = dialog_box.edit_traits(view=View(Item('message', show_label=False, style='readonly'),
                                          buttons=buttons,
                                          width=400, height=150,
                                          kind='modal'
                                          )
                                )
    return ui.result


def save_file(title=''):
    """
    Displays a dialog box that lets the user select a file name.
    Returns None if 'Cancel' button is pressed or overwriting
    an existing file is canceled.
    
    The title of the window is set to 'title'.
    """
    dialog_box = FileDialogBox()

    ui = dialog_box.edit_traits(View(Item('filename'),
                                     buttons=[OKButton, CancelButton],
                                     width=400, height=150,
                                     kind='modal',
                                     title=title
                                     )
                                )
    if ui.result:
        if not os.access(dialog_box.filename, os.F_OK) or warning('File exists. Overwrite?'):
            return dialog_box.filename
        else:
            return


class GetSetItemsMixin(HasTraits):
    """
    Provides save, load, save figure methods. Useful with HasTraits models.
    Data is stored in a dictionary with keys that are strings and identical to
    class attribute names. To save, pass a list of strings that denote attribute names.
    Load methods accept a filename. The dictionary is read from file and attributes
    on the class are set (if necessary created) according to the dictionary content. 
    """

    filename = File()

    save_button = Button(label='save', show_label=False)
    load_button = Button(label='load', show_label=False)

    get_set_items = []  # Put class members that will be saved upon calling 'save' here.

    # BIG FAT WARNING: do not include List() traits here. This will cause inclusion of the entire
    # class definition during pickling and will result in completely uncontrolled behavior.
    # Normal [] lists are OK.

    def set_items(self, d):
        # In order to set items in the order in which they appear
        # in the get_set_items, we first iterate through the get_set_items
        # and check whether there are corresponding values in the dictionary.
        for key in self.get_set_items:
            try:
                if key in d:
                    val = d[key]
                    attr = getattr(self, key)
                    if isinstance(val, dict) and isinstance(attr, GetSetItemsMixin):  # iterate to the instance
                        attr.set_items(val)
                    else:
                        setattr(self, key, val)
            except:
                logging.getLogger().warning("failed to set item '" + key + "'")

    def get_items(self, keys=None):
        if keys is None:
            keys = self.get_set_items
        d = {}
        for key in keys:
            attr = getattr(self, key)
            if isinstance(attr, GetSetItemsMixin):  # iterate to the instance
                d[key] = attr.get_items()
            else:
                d[key] = attr
        return d

    def save_figure(self, filename):
        """Saves a figure of the plot of the class.

        For this we use PlotGraphicsContext from stupid chaco. We will just spit out a small message
        and continue with the program if we cannot find anything to plot in the class, which can
        occur for some classes
        :param filename: string of the full path of the filename
        :return: void
        """
        try:
            gc = PlotGraphicsContext(self.figure_container.outer_bounds, dpi=72)
        except AttributeError:
            # if the class uses something other than figure_container
            try:
                gc = PlotGraphicsContext(self.line_plot.outer_bounds, dpi=72)
            except AttributeError:
                # HW-FIX: third fallback for classes whose plot is just `plot`
                # -- Autocorrelation and ODMR among them. They matched neither
                # `figure_container` nor `line_plot`, so saving silently printed
                # the message below and wrote no image. This was broken in the
                # 2019 code too; it is not a porting regression.
                try:
                    gc = PlotGraphicsContext(self.plot.outer_bounds, dpi=72)
                except AttributeError:
                    # if the class really has no saveable plot...
                    print('Caught attribute error after trying to save plot of the class.')
                else:
                    gc.render_component(self.plot)
                    gc.save(filename)
            else:
                gc.render_component(self.line_plot)
                gc.save(filename)
        else:
            gc.render_component(self.figure_container)
            gc.save(filename)

    def save(self, filename, append_timestamp=False):
        """detects the format of the savefile and saves it according to the file-ending. .txt and
        .asc result in an ascii sav, .pyd in a pickled python save with mode='asc' and .pys in a
        pickled python file with mode='bin'.
        Furthermore we try to save an image of the data plot that is contained in the class, if
        possible at least.
        """
        if not filename:
            print ('Empty filename. Specify a filename and try again!')
            return
        # we do not know whether or not to put a try, except clause here, overwrite warning problems
        if append_timestamp:
            savename = filename + "_" + timestamp()
        else:
            savename = filename

        writeDictToFile(self.get_items(), savename)
        if savename.endswith(".pys"):
            savename = os.path.splitext(savename)[0]
        self.save_figure(savename + '.png')

    def load(self, filename):
        if filename == '':
            raise IOError('Empty filename. Specify a filename and try again!')
        if not filename.endswith(".pys"):
            filename += ".pys"
        if os.access(filename, os.F_OK):
            logging.getLogger().debug('attempting to restore state of ' + self.__str__() + ' from ' + filename + '...')
            # PY3-PORT: the original was a three-deep try/except cascade over
            # 'rb' / 'r' / 'rU'. On Python 3 the two text modes cannot load a
            # pickle at all, so it was two dead branches wrapped around a bare
            # `except:` that also swallowed KeyboardInterrupt. load_pickle()
            # handles the Python 2 -> 3 string decoding instead.
            try:
                self.set_items(load_pickle(filename))
            except Exception:
                logging.getLogger().debug('failed to restore state of ' + self.__str__() + '.')
                raise IOError('Load failed.')
            logging.getLogger().debug('state of ' + self.__str__() + ' restored.')
        else:
            raise IOError('File does not exist.')

    def _save_button_fired(self):
        if os.access(self.filename, os.F_OK):
            if not warning('File exists. Overwrite?'):
                return
        try:
            self.save(self.filename)
        except IOError as err:
            warning(err.message, buttons=[OKButton])

    def _load_button_fired(self):
        try:
            self.load(self.filename)
        except IOError as err:
            warning(err.message, buttons=[OKButton])

    def copy_items(self, keys):
        d = {}
        for key in keys:
            item = getattr(self, key)
            if hasattr(item, 'copy'):
                d[key] = item.copy()
            else:
                d[key] = item
        return d

    ## UI ##

    get_set_item_hgroup = HGroup(Item('filename', springy=True),
                                 Item('save_button', show_label=False),
                                 Item('load_button', show_label=False))
    # label='get & set'),
    traits_view = View(get_set_item_hgroup, title='GetSetItemsMixin')


class GetSettableHistory(History, GetSetItemsMixin):
    """
    Implements a history that can be pickled and unpickled
    in a generic way using GetSetItems. When this class is used,
    the data attached to the history is saved instead of
    the history object, which otherwise would require the definition
    of the history class to be present when unpickling the file.
    """
    get_set_items = ['items', 'length', 'i']


if __name__ == '__main__':
    pass
