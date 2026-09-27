__author__ = 'Lukas Schlipf'

"""Script for recording an ODMR map depending on the Tip position

This script runs a series of odmrs on recieving trigger from the Nanonis.
The odmr is run and saved accordning to its coordinates.
For this we use the 'grid' option of the Nanonis, each grid point will correspond to a magnetic field."""

import pickle
import threading
import time

import numpy as np

path = 'D:/Data/2015/04/17/ODMR/scans/2362-354-1459_1850G_fine/'
filename = '2362-354-1459_1850G_fine'

abort = False
recordBWD = False
saveODMRs = True
# odmr scan's pixels in µm.
# Keep a bit off the edges to make sure the ASC actually sets the scan range offsets to theses pixels.
xR = np.linspace(1, 8, 40)
yR = np.linspace(4, 11, 40)
yRRev = yR[::-1]

freqs = np.zeros((len(xR), len(yR)))
freqsBWD = np.zeros((len(xR), len(yR)))
topo = np.zeros((len(xR), len(yR)))
topoBWD = np.zeros((len(xR), len(yR)))
odmr.stop_time = 25
interpixel = 8
ASC.set_ScanPixels(x=100, y=100, pix=1e-11)  # 1 nm overall scan range


def odmr_Scan():
    for i, x in enumerate(xR):
        # FWD direction
        for j, y in enumerate(yR):
            if abort:
                return
            ASC.set_ScanOffset(x, y)
            ASC.start_Scanner()
            time.sleep(2)
            ASC.stop_Scanner()
            print('X: %05.2f, Y: %05.2f - step %04d of %04d (%02d perc)' % (
                x, y, i * len(xR) + j + 1, len(xR) * len(yR),
                float(100. * (i * len(xR) + j + 1) / float(len(xR) * len(yR)))))
            odmr.submit()
            time.sleep(interpixel)
            while odmr.state == 'run' and not abort:
                time.sleep(1)
            if abort:
                return
            if saveODMRs: odmr.save_all(path + filename + '_FWD_%03d_%03d' % (i, j))
            freqs[i, j] = np.mean(odmr.fit_frequencies)
            try:
                topo[i, j] = ASC.get_Z_pos()
            except:
                pass
        # BWD direction
        for j, y in enumerate(yRRev):
            if abort:
                return
            ASC.set_ScanOffset(x, y)
            ASC.start_Scanner()
            time.sleep(interpixel)
            ASC.stop_Scanner()
            print('X: %05.2f, Y: %05.2f - bwd - step %04d of %04d' % (x, y, i * len(xR) + j + 1, len(xR) * len(yR)))
            if recordBWD:
                odmr.submit()
                time.sleep(5)
                while odmr.state == 'run' and not abort:
                    time.sleep(1)
                if abort:
                    return
                if saveODMRs: odmr.save_all(path + filename + '_BWD_%03d_%03d' % (i, j))
                freqsBWD[i, j] = np.mean(odmr.fit_frequencies)
            try:
                topoBWD[i, j] = ASC.get_Z_pos()
            except:
                pass
    print('done')
    temp_meter.setRange(0)
    fil = open(path + filename + '_freqs.pys', 'wb')
    pickle.dump([xR, yR, freqs, freqsBWD, topo, topoBWD], fil)
    fil.close()
    X, Y = np.meshgrid(xR, yR)
    Z = freqs / 1e6
    Z = Z.transpose()
    TOP = topo / 1e3
    cmap = plt.get_cmap('PiYG')
    for i in [1, 2, 3]:
        if i == 1:
            plt.contourf(X, Y, Z, 20, cmap=cmap)
        elif i == 2:
            plt.pcolor(X, Y, Z, cmap=cmap)
        else:
            plt.pcolor(X, Y, TOP.transpose(), cmap=cmap)
        plt.ylabel('y (um)')
        plt.xlabel('x (um)')
        plt.title('f (MHz)')
        plt.colorbar()
        endstring = '_pixels.png' if i == 1 else '.png'
        if i == 2:
            endstring = 'topography' + endstring
            plt.title('z (nm)')
        plt.savefig(path + '_odmr_' + filename + endstring)
        plt.close()


odmrthread = threading.Thread(target=odmr_Scan)
odmrthread.start()
