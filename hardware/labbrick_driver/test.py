import numpy as np

from .labbrick import *

fnLSG_SetTestMode(0)


def show():
    n = fnLSG_GetNumDevices()
    print('num devs ' + str(n))

    devs = np.zeros(n, dtype=np.uint32)
    fnLSG_GetDevInfo(devs)

    print('devices ' + str(devs))

    for dev in devs:
        name = fnLSG_GetModelName(int(dev))[1]
        print('device ' + str(dev) + ' , name ' + str(name))


def open(index):
    fnLSG_InitDevice(index)


def close(index):
    fnLSG_CloseDevice(index)


def get_frequency(index):
    return fnLSG_GetFrequency(index) * 1e5


if __name__ == '__main__':
    show()

    print(open(1))
    print(get_frequency(1))
    # show()
    # show()
    print(open(2))
    print(get_frequency(2))
    print(get_frequency(1))
