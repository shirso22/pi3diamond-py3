# PY3-PORT: pickle.load(..., encoding='latin1') throughout this file.
# Python 2 pickled `str` as bytes; without an explicit codec every string
# in a historical .pys file comes back as bytes, or raises
# UnicodeDecodeError. latin-1 round-trips bytes 0-255 one-to-one, so numpy
# arrays and ASCII dict keys both survive. No-op for Python 3 pickles.
"""
This file contains scripts for data analysis in cPickle'd form.

We define classes and functions that make live easier in, as we get the .pyc files and automatically
run an analysis on it, which means fitting and graphic visualization.
"""
import pickle

import matplotlib.pyplot as plt
import numpy as np

from analysis.fitting import fit, ExponentialZero, ExponentialZeroEstimator
from tools.data_toolbox import string_to_file


def unpickle(filename):
    object = pickle.load(open(filename, 'rb'), encoding='latin1')
    return object


def plot_data(measurement):
    """Plot Data.
    
    This function produces a visual representation of tau over the spin_state
    """
    try:
        tau = measurement['tau']
    except Exception as e:
        print(type(e))
        print(e)
        print('something went wrong while trying to read tau of dictionary')
    try:
        spin_state = measurement['spin_state']
    except Exception as e:
        print(type(e))
        print(e)
        print('something went wrong while trying to read spin_state of dictionary')
    # if we are facing a double tau sequence, extract the two different sequences
    if len(spin_state) > len(tau):
        n = len(spin_state) // 2
        first = spin_state[:n]
        second = spin_state[n:2 * n]
        diff = first - second
        plt.plot(tau, first, tau, second)
    else:
        plt.plot(tau, spin_state)


def fit_exp_dec(measurement):
    """Fit and plot Data.    
    
    This Function extracts the tau and spin_state values of a dictionary, fits them with a single
    exponential decay and plots the results. For data with two seperate pulse sequences, the
    difference between them is taken first.
    """
    try:
        tau = measurement['tau']
    except Exception as e:
        print(type(e))
        print(e)
        print('something went wrong while trying to read tau of dictionary')
    try:
        spin_state = measurement['spin_state']
    except Exception as e:
        print(type(e))
        print(e)
        print('something went wrong while trying to read spin_state of dictionary')
    # if we are facing a double tau sequence, extract the two different sequences
    if len(spin_state) > len(tau):
        n = len(spin_state) // 2
        first = spin_state[:n]
        second = spin_state[n:2 * n]
        diff = first - second
        nv_contrast = diff + (first.mean() + second.mean()) / 2.0
        # model: a*exp(-x/w) + c
        a, w, c = fit(tau, nv_contrast, ExponentialZero, ExponentialZeroEstimator)
        plt.figure(1)
        plt.subplot(211)
        plt.plot(tau, nv_contrast, 'bs', tau, a * np.exp(-tau / w) + c, 'r')
        plt.subplot(212)
        plt.plot(tau, first, 'b', tau, second, 'g')
        plt.show()
    else:
        # model: a*exp(-x/w) + c
        a, w, c = fit(tau, spin_state, ExponentialZero, ExponentialZeroEstimator)
    return a, w, c


def generate_txt(measurement, filename):
    """Generate a txt file from a pyd file.
    
    The txt contains the tau and both the sequences, seperated by tabulators.
    """
    try:
        dict = {}
        dict['tau'] = measurement['tau']
        # distinguish between single and double sequence measurements
        if measurement['tau'].size == measurement['spin_state'].size:
            dict['spin_state'] = measurement['spin_state']
        else:
            n = len(measurement['spin_state']) // 2
            dict['spin state w sequence1: '] = measurement['spin_state'][:n]
            dict['spin state w sequence2: '] = measurement['spin_state'][n:2 * n]
        datastring = ''
        for key in list(dict.keys()):
            datastring += key + '\t'
        datastring += '\n'
        for i in range(np.array(dict['tau']).size):
            for value in list(dict.values()):
                datastring += (str(value[i]) + '\t')
            datastring += '\n'
        string_to_file(datastring, filename, mode='w')
    except Exception as e:
        print(type(e))
        print(e)
        print('something went wrong while saving spin_state over tau, check that ...')


def save_hahn(filename="Z:/data/20150225/NP1_PAAGd3_4K_B1=8mT_NVD01_T2.txt"):
    file = open(filename, 'w')
    file.write('free evolution time \t Hahn pi2 \t Hahn 3pi2 \n')
    for i in np.arange(hahn.tau.shape[0]):
        line = ''
        line += '%f\t' % hahn.tau[i]
        line += '%s\t' % hahn.spin_state[i]
        line += '%s\t' % hahn.spin_state[i + hahn.tau.shape[0]]
        file.write(line + '\n')
    file.close()


def save_t1(filename="Z:/data/20150225/NP1_PAAGd3_4K_B1=8mT_NVD41_T1.txt"):
    file = open(filename, 'w')
    file.write('free evolution time \t wo pi2 \t w pi2 \n')
    for i in np.arange(t1pi.tau.shape[0]):
        line = ''
        line += '%f\t' % t1pi.tau[i]
        line += '%s\t' % t1pi.spin_state[i]
        line += '%s\t' % t1pi.spin_state[i + t1pi.tau.shape[0]]
        file.write(line + '\n')
    file.close()


def save_xy8(filename="Z:/data/20150225/NP1_PAAGd3_4K_B1=8mT_NVD01_xy8-1.txt"):
    file = open(filename, 'w')
    file.write('free evolution time \t xy8-n pi2 \t xy8-n 3pi2 \n')
    for i in np.arange(xy8.tau.shape[0]):
        line = ''
        line += '%f\t' % xy8.tau[i]
        line += '%s\t' % xy8.spin_state[i]
        line += '%s\t' % xy8.spin_state[i + xy8.tau.shape[0]]
        file.write(line + '\n')
    file.close()


def save_deer_spectrum(frequency, spin_state, filename="Z:/data/20150326/NPP1_RT_B=7mT_NV09_DEER.txt"):
    file = open(filename, 'w')
    file.write('RadioFrequency (MHz) \t XY8 3pi2 \t XY8 pi2 \t XY8+rf 3pi2 \t XY8+rf pi2 \n')
    for i in np.arange(frequency.shape[0]):
        line = ''
        line += '%f\t' % frequency[i]
        line += '%s\t' % spin_state[i][0]
        line += '%s\t' % spin_state[i][1]
        line += '%s\t' % spin_state[i][2]
        line += '%s\t' % spin_state[i][3]
        file.write(line + '\n')
    file.close()
    # contrast_pi2 = spin_state[0] - spin_state[2]
    # contrast_3pi2 = spin_state[1]- spin_state[3]


def save_deer_rabi(tau, spin_state,
                   filename="Z:/python_data_temp/NP1_thickGd_4K_NVD41_blind_deer_xy8_rf_-30dBm_mw_7000ns.txt"):
    file = open(filename, 'w')
    file.write('Rf tau (ns) \t XY8 pi2 \t XY8 3pi2 \t XY8+rf pi2 \t XY8+rf 3pi2 \n')
    n = tau.shape[0]
    xy8_pi2 = spin_state[0:n]
    xy8_3pi2 = spin_state[n:2 * n]
    xy8_rf_pi2 = spin_state[2 * n:3 * n]
    xy8_rf_3pi2 = spin_state[3 * n:4 * n]
    for i in np.arange(tau.shape[0]):
        line = ''
        line += '%f\t' % tau[i]
        line += '%s\t' % xy8_pi2[i]
        line += '%s\t' % xy8_3pi2[i]
        line += '%s\t' % xy8_rf_pi2[i]
        line += '%s\t' % xy8_rf_3pi2[i]
        file.write(line + '\n')
    file.close()
    # contrast_pi2 = spin_state[0] - spin_state[2]
    # contrast_3pi2 = spin_state[1]- spin_state[3]
