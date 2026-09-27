# PY3-PORT: pickle.load(..., encoding='latin1') throughout this file.
# Python 2 pickled `str` as bytes; without an explicit codec every string
# in a historical .pys file comes back as bytes, or raises
# UnicodeDecodeError. latin-1 round-trips bytes 0-255 one-to-one, so numpy
# arrays and ASCII dict keys both survive. No-op for Python 3 pickles.
"""
This file contains scripts for data analysis in cPickle'd form.

We define classes and functions that make live easier, as we get the .pyc files and automatically
run an analysis on it, which means fitting and graphic visualization. For this the user has to
supply some input, as for what should be analzed and how.
"""

import pickle

import matplotlib.pyplot as plt


def unpickle(filename):
    object = pickle.load(open(filename, 'rb'), encoding='latin1')
    return object


def plot_data(measurement, variables, fitting='exp', data_range=[0., 1.]):
    """Funtion that plots data from any measurement
    
    measurement = dictionary containing the actual data
    variables = list of strings of the measurement variables that should be plotted, which must
    obviously in the measurement dictionary! The first variable is x of the plot, the second is y.
    Plotting is done by pyplot.
    """

    # check if variables are contained in measurement
    for var in variables:
        try:
            measurement.get(var)
        except Exception as e:
            print('Variable' + var + 'is not in measurement... exiting')
            print(type(e))
            print(e)
    x = measurement.get(variables[0])
    y = measurement.get(variables[1])
    # Data range user specifies
    start = int(len(x) * data_range[0])
    end = int(len(x) * data_range[1])
    # if we are facing a double tau sequence, extract the two different sequences and plot the
    # difference and the raw data
    if len(y) > len(x):
        n = len(y) // 2
        first = y[:n]
        second = y[n:2 * n]
        diff = first - second
        x = x[start:end]
        first = first[start:end]
        second = second[start:end]
        diff = diff[start:end]
        plt.figure(1)
        plt.subplot(211)
        plt.plot(x, diff, 'bs')
        plt.subplot(212)
        plt.plot(x, first, 'b', x, second, 'g')
    else:
        plt.figure(1)
        plt.subplot(111)
        x = x[start:end]
        y = y[start:end]
        plt.plot(x, y, 'bs')
    plt.show()
    return 0.
