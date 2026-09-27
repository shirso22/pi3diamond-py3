import time

import numpy as np

from tools.data_toolbox import writeDictToFile
from tools.emod import Job


def points_on_circle(radius=0.1, spacing=1.0):
    """
    Return points on a sphere in x, y coordinates with given radius and spacing in degree.
    :param radius: radius of circle
    :return:
    """
    coordinates = []
    for phi in np.arange(0.0, 360.0, spacing):
        coordinates.append(np.array([radius * np.cos(phi * np.pi / 180.),
                                     radius * np.sin(phi * np.pi / 180.)]))
    return coordinates


def field_from_angles(Babs, angles, radian=True):
    """
    Return Bx, By, Bz for a field with Babs strength and angles(=phi,theta)
    """
    phi, theta = angles
    if radian is False:
        preF = np.pi / 180
        phi *= preF
        theta *= preF

    return [Babs * np.sin(theta) * np.cos(phi), Babs * np.sin(theta) * np.sin(phi),
            Babs * np.cos(theta)]


def points_on_sphere(radius=0.1, spacing=1.0):
    """
    Return points on a sphere in x, y coordinates with given radius and spacing in degree.
    :param radius: radius of circle
    :return:
    """
    coordinates = []
    anglegrid = []
    for theta in np.arange(0, 180, spacing):
        for phi in np.arange(0, 360, spacing):
            anglegrid.append(np.array([phi, theta]))
            coordinates.append(np.array(field_from_angles(radius, (phi, theta), radian=False)))
    return anglegrid, coordinates


class MagnetCalibration(Job):
    d_angle = 5.
    angels, currents = points_on_sphere(0.45, 5.)
    counts = []
    progress = 0
    file = 'Z:\\data\\20170308 p190-1 clean cryo\\magnet_calibration\\spherescan_zoom_tip_position_2_I=0,9Imax_dAngle=3deg'

    def __init__(self, d_angle, max_current):
        self.d_angle = d_angle
        self.max_current = max_current
        self.angels, self.currents = points_on_sphere(max_current, d_angle)

    def _run(self):
        self.progress = 0
        print('Calibrating magnetic field ...')
        for i in self.currents:
            vector_magnet.i_rel_coil_1 = 0.5 + i[0]
            vector_magnet.i_rel_coil_2 = 0.5 + i[1]
            vector_magnet.i_rel_coil_3 = 0.5 + i[2]
            vector_magnet._set_field_button_fired()
            time.sleep(2)
            self.counts.append(time_trace.C0C1[0:20].sum() / 20.)
            self.progress += 1
            if self.progress % 10 == 0:
                print('\r' + 'Calibrating... {:04.1f} % done '.format(
                    float(self.progress) / np.array(self.currents).shape[0] * 100.))
        dict = {'angle': self.angels, 'current': self.currents, 'counts': self.counts}
        writeDictToFile(dict, self.file)
