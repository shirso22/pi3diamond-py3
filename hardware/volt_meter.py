"""
single point voltmeter based on NI card
"""

import numpy as np

from .ni import AnalogIn


class VoltMeter(AnalogIn):
    """
    Voltmeter based on NI card
    """

    def get_voltage(self):
        return np.mean(self.getData())

    def get_rms_voltage(self):
        return (np.sum(self.getData() ** 2) / self.n_samples) ** 0.5
