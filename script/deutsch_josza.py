import time

import data_toolbox
import matplotlib.pyplot as plt
import numpy

from pi3diamond import pi3d

folder = "C:\\data\\LabBook\\fp8\\fp8tag4\\"

"""Init Names"""
PG = pi3d.get_pulse_generator()
FC = pi3d.get_fast_counter()
MW1 = pi3d.get_microwave()
MW2 = pi3d.get_microwave2()

"""MW 1 Attributes"""
mw1_freq = 2.83227e09
mw1_power = -12.
mw1_t_pi = 160.78
# mw1_t_pi2   = mw1_t_pi/2.
mw1_t_pi2 = 72.38
mw1_t_2pi = 2. * mw1_t_pi
# mw1_t_2pi = 353.6

"""MW 2 Attributes"""
mw2_freq = 2.909568e09
mw2_power = -12.
mw2_t_pi = 161.84
# mw2_t_pi2   = mw2_t_pi/2.
mw2_t_pi2 = 71.79
mw2_t_2pi = 2. * mw2_t_pi
# mw2_t_2pi = 360.22

"""Auswertungsvariablen"""
cutoff = 300  # ns nach flanke zur Auswertung

"""Laser, bzw. Wait Time"""
laser = 3000.
wait = 1000.

channel_map = {'laser': 0, 'mw': 1, 'mw2': 2, 'sequence': 3}


def sequence_test():
    sequence = []
    sequence.append((['mw'], mw1_t_pi))
    sequence.append((['laser'], laser))
    sequence.append(([], wait))

    sequence.append((['mw'], mw1_t_pi2))
    sequence.append((['laser'], laser))
    sequence.append(([], wait))

    sequence.append((['mw'], mw1_t_2pi))
    sequence.append((['laser'], laser))
    sequence.append(([], wait))

    sequence.append((['mw'], mw2_t_pi))
    sequence.append((['laser'], laser))
    sequence.append(([], wait))

    sequence.append((['mw'], mw2_t_pi2))
    sequence.append((['laser'], laser))
    sequence.append(([], wait))

    sequence.append((['mw'], mw2_t_2pi))
    sequence.append((['laser'], laser))
    sequence.append(([], wait))

    sequence.append((['laser'], laser))
    sequence.append(([], wait))
    sequence.append((['sequence'], 100))

    return sequence


def sequence_RDJ():
    sequence = []
    """Laser-Norm"""
    sequence.append((['laser'], laser))
    sequence.append(([], wait))

    """Hadamar + constant Funct. =1 """
    sequence.append((['mw'], mw1_t_pi2 + mw1_t_pi2))
    sequence.append((['laser'], laser))
    sequence.append(([], wait))

    """Hadamar + constant Funct. =-1 """
    sequence.append((['mw'], mw1_t_pi2 + mw1_t_2pi + mw1_t_pi2))
    sequence.append((['laser'], laser))
    sequence.append(([], wait))

    """Hadamar + balanced Funct. =+1 -1 """
    sequence.append((['mw'], mw1_t_pi2))
    sequence.append((['mw2'], mw2_t_2pi))
    sequence.append((['mw'], mw1_t_pi2))
    sequence.append((['laser'], laser))
    sequence.append(([], wait))

    """Hadamar + balanced Funct. =-1 +1 """
    sequence.append((['mw'], mw1_t_pi2 + mw1_t_2pi))
    sequence.append((['mw2'], mw2_t_2pi))
    sequence.append((['mw'], mw1_t_pi2))
    sequence.append((['laser'], laser))
    sequence.append(([], wait))

    sequence.append((['sequence'], 100))
    return sequence


def sequence_echo(times):
    sequence = []
    for i in range(0, times):
        tau = (wait * 2) / times * i
        """Laser-Norm"""
        sequence.append((['laser'], laser))
        sequence.append(([], wait))

        """Hadamar + constant Funct. =1 """
        sequence.append((['mw'], mw1_t_pi2))
        # echo
        sequence.append(([], wait))
        sequence.append((['mw'], mw1_t_pi))
        sequence.append(([], tau))
        sequence.append((['mw'], mw1_t_pi2))

        sequence.append((['laser'], laser))
        sequence.append(([], wait))

        """Hadamar + constant Funct. =-1 """
        sequence.append((['mw'], mw1_t_pi2 + mw1_t_2pi))
        # echo
        sequence.append(([], wait))
        sequence.append((['mw'], mw1_t_pi))
        sequence.append(([], tau))
        sequence.append((['mw'], mw1_t_pi2))

        sequence.append((['laser'], laser))
        sequence.append(([], wait))

        """Hadamar + balanced Funct. =+1 -1 """
        sequence.append((['mw'], mw1_t_pi2))
        sequence.append((['mw2'], mw2_t_2pi))
        # echo
        sequence.append(([], wait))
        sequence.append((['mw'], mw1_t_pi))
        sequence.append(([], tau))
        sequence.append((['mw'], mw1_t_pi2))

        sequence.append((['laser'], laser))
        sequence.append(([], wait))

        """Hadamar + balanced Funct. =-1 +1 """
        sequence.append((['mw'], mw1_t_pi2 + mw1_t_2pi))
        sequence.append((['mw2'], mw2_t_2pi))
        # echo
        sequence.append(([], wait))
        sequence.append((['mw'], mw1_t_pi))
        sequence.append(([], tau))
        sequence.append((['mw'], mw1_t_pi2))

        sequence.append((['laser'], laser))
        sequence.append(([], wait))

    sequence.append((['sequence'], 100))

    return sequence


def evaluate(data, n):
    int = numpy.zeros(n)
    length = len(data[0])
    data_smooth = numpy.zeros((n, length))
    max = 0
    for j in range(0, n):
        for i in range(5, length - 5):
            for k in range(-5, 5 + 1):
                data_smooth[j, i] += data[j, i + k]

            data_smooth[j, i] /= 11.

        """Plot Rohdata """
        x1 = numpy.arange(length)
        plt.plot(x1, data_smooth[j])
        plt.show()

        """Anstiegsflanke"""
        delta_max = 1

        for i in range(2, length - 1):
            if (data_smooth[j, i + 1] - data_smooth[j, i - 1] > data_smooth[j, delta_max + 1] - data_smooth[
                j, delta_max - 1]):
                delta_max = i

        """Integriere"""

        for i in range(delta_max, delta_max + cutoff):
            int[j] += data[j, i]

        int[j] /= cutoff

        """measure background and sustract from integral"""
        background = 0

        for i in range(length - cutoff, length):
            background += data[j, i]

        background /= cutoff

        int[j] -= background

        if (abs(int[j]) > max): max = abs(int[j])

    for m in range(0, n):
        int[m] /= max

    return int


def start(sequence, n):
    """Starts the measurement."""

    PG.Night()
    FC.Configure(laser, 1.25, n)

    MW1.setOutput(mw1_power, mw1_freq)
    MW2.setOutput(mw2_power, mw2_freq)

    FC.Start()
    time.sleep(0.5)
    PG.Sequence(sequence)


def stop():
    FC.Halt()
    MW1.setOutput(None, mw1_freq)
    MW2.setOutput(None, mw2_freq)
    PG.Light()


def output(data, filename):
    d = {'counts': data}
    print(folder + filename)
    data_toolbox.writeDictToFile(d, folder + filename)
