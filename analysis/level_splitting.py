__author__ = 'schlipf'

import math

import numpy as np
import scipy.optimize as optimize
from functools import cmp_to_key


# def plot_level_splitting(E, B_limit, N=50):
#     fig = plt.figure()
#     axes = fig.add_axes([0.1, 0.1, 0.8, 0.8])
#     for j in range(0, 4):
#         B_data = []
#         Freq_data = []
#         for n in range(N + 1):
#             B_data.append([(float(n) / N) * B_limit[0], (float(n) / N) * B_limit[1], (float(n) / N) * B_limit[2]])
#         B_data = np.array(B_data)
#         b_plot_data = []
#         for B_i in B_data:
#             b_plot_data.append(absolute_value(B_i))
#             Freq_data.append(theo_res_frequencies(E, B_i))
#         b_plot_data = np.array(b_plot_data)
#         freq_plot_data = np.array(Freq_data)
#         axes.plot(b_plot_data, freq_plot_data[:, 0], 'r')
#         axes.plot(b_plot_data, freq_plot_data[:, 1], 'b')
#     axes.set_xlabel('absolute B value in T of direction ' + repr(B_limit))
#     axes.set_ylabel('rel Freqency [Hz]')
#     axes.set_title('Frequency shift of NV center with B = ' + repr(B_limit))


# here we include functions for the Hamiltonian of the S=1 ground state of a molecule in an
# arbitrary (small) magnetic field.
def hamiltonian(E, B, D=2.87e9):
    """ parameters: E in Hz, array of fields in Tesla
    returns the 3x3 ground state spin Hamiltonian matrix in units of frequency"""
    gamma = 28e9  # Hz/T
    B = [float(B[0]), float(B[1]), float(B[2])]
    Bterm = -gamma * (B[0] + 1j * B[1]) / math.sqrt(2)  # '1j' is the imaginary unit, as naturally expressed in python
    return np.matrix([[D / 3 - gamma * B[2], Bterm.conjugate(), E],
                      [Bterm, -2 * D / 3, Bterm.conjugate()],
                      [E, Bterm, D / 3 + gamma * B[2]]])


def theo_res_frequencies(E, B, D):
    """ parameters: E in Hz, array of fields in Tesla
    returns array of eigenfrequencies of ms=+-1 levels relative to ms=0.
    Works for small fields only (real eigenvalues assumed!)"""
    a = np.sort(
        key=cmp_to_key(np.linalg.eig(hamiltonian(E, B, D))[
            0].real))  # eig[0] is the array of eigenvalues (eig[1] = the diagonal matrix)
    return a[1:3] - a[0]  # return rel. freqs. Notation: element '1' until 3rd element (=index '2')


def absolute_value(B):
    return np.sqrt(B[0] ** 2 + B[1] ** 2 + B[2] ** 2)


def find_b(f_transitions, D=2.87e9):
    """
    Calculates the magnetic field that induces the given transition frequencies in an electronic S=1 system. The
    uncertainty on the xy-plane is removed by restricting the B-Field to the yz-plane.
    :param f_transitions: Electron spin transition frequencies
    :return: B-Field array [x, y, z] in NV-coordinate-system
    """

    def f_NV(param):
        return theo_res_frequencies(0.0, [0.0, param[0], param[1]], D) \
               - np.array([f_transitions[0], f_transitions[1]])

    x0 = [0.2 * (D - f_transitions[0]) / 28e9, (D - f_transitions[0]) / 28e9]
    xz_field = optimize.root(f_NV, x0)
    print(("XZ", xz_field))
    return [0.0, xz_field['x'][0], xz_field['x'][1]]


def all_res_frequencies(E, B):
    """
    Calculates the transition frequencies for a given magnetic field orientation in the coordination system of one NV-
    center.

    :param E: strain parameter
    :param B: external static magnetic field as 3 component list
    :return: all 8 resonant frequencies, that show up in an ODMR scan on a dense spot
    """
    pass

