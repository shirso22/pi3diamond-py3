"""
parse zeeman 2 results and calculate B field fomr splittings using magnetometry.py
"""

DEBUG = False

import numpy as np
from traits.api import File, Int  # Instance, Button, Enum, Range, Array
from traitsui.api import View, Item, HGroup, VGroup

from .magnetometry import Magnetometer
from tools.emod import Job


# import scipy.optimize
# import scipy.special
# import cPickle
# import sys
# from tools.utility import timestamp, GetSetItemsMixin#, GetSetItemsHandler
# from chaco.api import ArrayPlotData, Plot
# from enable.api import ComponentEditor
# import logging#, logging.handlers


class MagCoilCalibBField(Job, GetSetItemsMixin):
    """ """
    # Gui
    path_data_1 = File()
    path_data_2 = File()
    path_data_3 = File()
    path_data_4 = File()
    path_save = File()

    file_columns = Int()

    calc_button = Button(label='start', desc='Calculates the b-field calculation.')

    hams = (TripletSpin(), TripletSpin(), TripletSpin(), TripletSpin())
    magnetometer = Magnetometer(hams)

    def __init__(self):
        self.file_columns = 5

    def _calc_button_fired(self):
        """React to calc button."""
        self._run()

    traits_view = View(VGroup(VGroup(Item('file_columns'),
                                     Item('path_data_1'),
                                     Item('path_data_2'),
                                     Item('path_data_3'),
                                     Item('path_data_4'),
                                     Item('path_save'),
                                     ),
                              HGroup(Item('calc_button', show_label=False),
                                     Item('state', style='readonly'),
                                     ),
                              ),
                       title='Magnetic field calibration for one coil/magnet', buttons=[], resizable=True
                       )

    get_set_items = ['path_data_1', 'path_data_2', 'path_data_3', 'path_data_4', 'path_save', '__doc__']

    def _run(self):
        """ """
        try:
            self.state = 'run'

            if self.path_data_1 == '':
                raise ValueError('Filename missing. Please specify a filename and try again.')
            if self.path_data_2 == '':
                raise ValueError('Filename missing. Please specify a filename and try again.')
            if self.path_data_3 == '':
                raise ValueError('Filename missing. Please specify a filename and try again.')
            if self.path_data_4 == '':
                raise ValueError('Filename missing. Please specify a filename and try again.')
            if self.path_save == '':
                raise ValueError('Filename missing. Please specify a filename and try again.')

            # spin_models, rotations, bx, by, bz, table = self.load_table_file()
            self.data_array = self.read_data()
            # self.calc_bfield(data_array, spin_models, rotations, bx, by, bz, table)

            self.state = 'done'
        except:
            logging.getLogger().exception('Error in MagCoilCalibration_BField.')
            self.state = 'error'

            # helper functions

    def string_to_file(self, datastring, path):
        """writes datastring to file"""
        try:
            f = open(path, 'a')
            try:
                f.write(datastring)
            finally:
                f.close()
        except IOError:
            print('Error exporting data')
            return False
        return True

    def list_to_file(self, list, path):
        """writes simple list to file"""
        datastring = ''
        for m in range(len(list)):
            datastring = datastring + ', ' + str(list[m])
        datastring = datastring.strip(', ') + '\n'
        self.string_to_file(datastring, path)

    # Run methods

    def read_data(self):
        """read in data with the format used from MagCoilCalibration"""
        # get number of data points
        data_file = open(self.path_data_1)
        number_data_lines = len(data_file.readlines())
        # open files and read data
        data_array_all = np.zeros((4, number_data_lines, self.file_columns))
        j = -1
        for k in [self.path_data_1, self.path_data_2, self.path_data_3, self.path_data_4]:
            j += 1
            data_file = open(k)
            data_lines = data_file.readlines()
            data_array = np.zeros((number_data_lines, self.file_columns))
            for p in range(number_data_lines):
                data_array[p] = list(eval(data_lines[p]))
            data_array_all[j] = data_array
        return data_array_all


if __name__ == '__main__':
    # Calculation for a set of given splittings
    magcoilcalibana = MagCoilCalibBField()
    magcoilcalibana.path_data_1 = 'D:\\data\\LabBook\\2012-11-30\\calib\\cal_nv99_ch1.txt'
    magcoilcalibana.path_data_2 = 'D:\\data\\LabBook\\2012-11-30\\calib\\cal_nv112_ch1.txt'
    magcoilcalibana.path_data_3 = 'D:\\data\\LabBook\\2012-11-30\\calib\\cal_nv103_ch1.txt'
    # magcoilcalibana.path_data_4 =
    magcoilcalibana.path_save = 'D:\\data\\LabBook\\2012-11-30\\calib.txt'
    magcoilcalibana.edit_traits()
    """
    #load pre-computed data
    #table_file='table_200_4_111.pys'
    #table_file='table_200.pys'
    table_file='table_50.pys'
    if not 'table' in dir():
        print 'loading table file...'
        fil = open(table_file,'rb')
        spin_models, rotations, bx, by, bz, table = cPickle.load(fil)
        fil.close()

    #normally we have as experimental data the ESR resonance lines. in this case, we have only the splittings and compute 'fake' transition frequencies
    #splittings = np.array((39.806, 10.974, 14.303, 52.830))
    #splittings = np.array((58.542, 17.495, 23.013, 18.001))
    #splittings = np.array((41.055, 54.013, 27.010, 13.533))
    #splittings = np.array((0, 6.459, 54.250, 47.597))
    splittings = np.array((12.840, 34.773, 5.279, 52.528))
    
    transitions = np.vstack((np.zeros_like(splittings), splittings)).transpose()
    orientations = [0,1,2,3]

    b, s_b, chisqr, q = find_field(spin_models,rotations,orientations,bx,by,bz,table,transitions,method='splittings')

    [x,y,z] = b[2]
    theta = np.arccos(z/np.linalg.norm(b[2]))
    phi = np.arctan2(y,x)
    theta = np.degrees(theta)
    phi = np.degrees(phi)
    
    print b[2]
    print np.linalg.norm(b[2])
    print theta
    print phi
    """
