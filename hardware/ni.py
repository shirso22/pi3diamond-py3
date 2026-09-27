import ctypes
import time

import numpy

def _lazy_dll(loader, name):
    """PY3-PORT: defer a vendor DLL load until something actually calls into it.

    Returns a proxy that loads on first attribute access, so importing this
    module works on a machine without the driver installed. Only real use
    raises, and with a message saying which DLL and why.
    """
    import ctypes as _ctypes

    class _LazyDLL(object):
        _dll = None

        def __getattr__(self, attr):
            if _LazyDLL._dll is None:
                try:
                    _LazyDLL._dll = loader(name)
                except OSError as exc:
                    bits = 64 if _ctypes.sizeof(_ctypes.c_void_p) == 8 else 32
                    raise OSError(
                        "%s could not be loaded, so %r is unavailable. Install the "
                        "vendor driver and check that its bitness matches this "
                        "Python interpreter (%d-bit). Original error: %s"
                        % (name, attr, bits, exc))
            return getattr(_LazyDLL._dll, attr)

    return _LazyDLL()


# PY3-PORT: was a module-level DLL load, which made importing this
# module require the vendor driver to be installed.
dll = _lazy_dll(ctypes.windll.LoadLibrary, 'nicaiu.dll')

DAQmx_Val_Cfg_Default = ctypes.c_int32(-1)
DAQmx_Val_GroupByChannel = 0
DAQmx_Val_GroupByScanNumber = 1
DAQmx_Val_ContSamps = 10123
DAQmx_Val_FiniteSamps = 10178
DAQmx_Val_Hz = 10373
DAQmx_Val_Low = 10214
DAQmx_Val_Volts = 10348
DAQmx_Val_Voltage = 10322
DAQmx_Val_RSE = 10083
DAQmx_Val_VoltageRMS = 10350
DAQmx_Val_MostRecentSamp = 10428
DAQmx_Val_OverwriteUnreadSamps = 10252
DAQmx_Val_Rising = 10280
DAQmx_Val_Ticks = 10304

c_uint32_p = c_ulong_p = ctypes.POINTER(ctypes.c_uint32)
c_float64_p = c_double_p = ctypes.POINTER(ctypes.c_double)


def CHK(err):
    """a simple error checking routine"""
    if err < 0:
        buf_size = 1000
        buf = ctypes.create_string_buffer('\000' * buf_size)
        dll.DAQmxGetErrorString(err, ctypes.byref(buf), buf_size)
        raise RuntimeError('nidaq call failed with error %d: %s' % (err, repr(buf.value)))


class Counter():

    def __init__(self, counter_out_device, counter_in_device, input_pad, bin_width, length):
        self.length = length
        self.bin_width = bin_width

        f = 1. / bin_width
        buffer_size = max(1000, length)

        self.COTask = ctypes.c_ulong()
        self.CITask = ctypes.c_ulong()

        CHK(dll.DAQmxCreateTask('', ctypes.byref(self.COTask)))
        CHK(dll.DAQmxCreateTask('', ctypes.byref(self.CITask)))

        CHK(dll.DAQmxCreateCOPulseChanFreq(self.COTask,
                                           counter_out_device, '',
                                           DAQmx_Val_Hz, DAQmx_Val_Low, ctypes.c_double(0),
                                           ctypes.c_double(f),
                                           ctypes.c_double(0.9))
            )

        CHK(dll.DAQmxCreateCIPulseWidthChan(self.CITask,
                                            counter_in_device, '',
                                            ctypes.c_double(0),
                                            ctypes.c_double(1e7),
                                            DAQmx_Val_Ticks, DAQmx_Val_Rising, '')
            )

        CHK(dll.DAQmxSetCIPulseWidthTerm(self.CITask, counter_in_device, counter_out_device + 'InternalOutput'))
        CHK(dll.DAQmxSetCICtrTimebaseSrc(self.CITask, counter_in_device, input_pad))

        CHK(dll.DAQmxCfgImplicitTiming(self.COTask, DAQmx_Val_ContSamps, ctypes.c_ulonglong(buffer_size)))
        CHK(dll.DAQmxCfgImplicitTiming(self.CITask, DAQmx_Val_ContSamps, ctypes.c_ulonglong(buffer_size)))

        # read most recent samples, overwrite buffer
        CHK(dll.DAQmxSetReadRelativeTo(self.CITask, DAQmx_Val_MostRecentSamp))
        CHK(dll.DAQmxSetReadOffset(self.CITask, -length))
        CHK(dll.DAQmxSetReadOverWrite(self.CITask, DAQmx_Val_OverwriteUnreadSamps))

        CHK(dll.DAQmxStartTask(self.COTask))
        CHK(dll.DAQmxStartTask(self.CITask))

        self.n_read = ctypes.c_int32()
        self.data = numpy.empty((length,), dtype=numpy.uint32)
        self.timeout = 4 * length * bin_width

    def getData(self):
        try:
            CHK(dll.DAQmxReadCounterU32(self.CITask,
                                        ctypes.c_int32(self.length),
                                        ctypes.c_double(self.timeout),
                                        self.data.ctypes.data,
                                        ctypes.c_uint32(self.length),
                                        ctypes.byref(self.n_read), None)
                )
        except:
            time.sleep(self.timeout)
            CHK(dll.DAQmxReadCounterU32(self.CITask,
                                        ctypes.c_int32(self.length),
                                        ctypes.c_double(self.timeout),
                                        self.data.ctypes.data,
                                        ctypes.c_uint32(self.length),
                                        ctypes.byref(self.n_read), None)
                )
        return self.data

    def __del__(self):
        try:
            CHK(dll.DAQmxStopTask(self.COTask))
            CHK(dll.DAQmxStopTask(self.CITask))
            CHK(dll.DAQmxClearTask(self.COTask))
            CHK(dll.DAQmxClearTask(self.CITask))
        except:
            pass


class AnalogIn(object):
    """Analog input N values with frequency f"""

    def __init__(self, channels, n_samples=1000, frequency=1000., range=(-10, 10), read_timeout=1.0):
        self.channels = channels
        self.n_samples = n_samples
        self.frequency = frequency
        self.range = range
        self.read_timeout = read_timeout
        self.task = ctypes.c_ulong()
        self.configure()

    def configure(self):
        CHK(dll.DAQmxCreateTask('', ctypes.byref(self.task)))

        CHK(dll.DAQmxCreateAIVoltageChan(self.task,
                                         self.channels,
                                         '',
                                         DAQmx_Val_RSE,
                                         ctypes.c_double(self.range[0]),
                                         ctypes.c_double(self.range[1]),
                                         DAQmx_Val_Volts,
                                         ''))

        n_channels = ctypes.c_uint32()
        CHK(dll.DAQmxGetReadNumChans(self.task, ctypes.byref(n_channels)))

        CHK(dll.DAQmxCfgSampClkTiming(self.task,
                                      'OnboardClock',
                                      ctypes.c_double(self.frequency),
                                      DAQmx_Val_Rising,
                                      DAQmx_Val_FiniteSamps,
                                      ctypes.c_ulonglong(self.n_samples)))

        self.n_channels = int(n_channels.value)
        self.timeout = ctypes.c_double(4. * self.n_samples / self.frequency)
        self.n_read = ctypes.c_long()
        self.data = numpy.zeros((int(n_channels.value), self.n_samples), dtype=numpy.double)

    def getData(self):
        CHK(dll.DAQmxStartTask(self.task))
        CHK(dll.DAQmxWaitUntilTaskDone(self.task, self.timeout))
        CHK(dll.DAQmxStopTask(self.task))
        CHK(dll.DAQmxReadAnalogF64(self.task,
                                   ctypes.c_long(self.n_samples),
                                   ctypes.c_double(self.read_timeout),
                                   DAQmx_Val_GroupByChannel,
                                   self.data.ctypes.data_as(c_float64_p),
                                   ctypes.c_ulong(self.n_channels * self.n_samples),
                                   ctypes.byref(self.n_read),
                                   None))
        return self.data

    def clear(self):
        CHK(dll.DAQmxClearTask(self.task))


class AnalogInRMS(object):
    """Single point analog input RMS voltage."""

    def __init__(self, channels, range=(-10., 10.)):

        task = ctypes.c_ulong()
        CHK(dll.DAQmxCreateTask('', ctypes.byref(task)))

        CHK(dll.DAQmxCreateAIVoltageRMSChan(task, channels, '', DAQmx_Val_RSE, ctypes.c_double(range[0]),
                                            ctypes.c_double(range[1]), DAQmx_Val_Volts, ''))

        n_channels = ctypes.c_uint32()
        CHK(dll.DAQmxGetReadNumChans(task, ctypes.byref(n_channels)))

        self.n_channels = int(n_channels.value)
        self.task = task
        self.value = ctypes.c_double()
        self.n_read = ctypes.c_long()
        self.data = numpy.zeros((int(n_channels.value), 1), dtype=numpy.double)

    def getData(self, read_timeout=1.0):
        CHK(dll.DAQmxStartTask(self.task))
        if self.n_channels == 1:
            CHK(DAQmxReadAnalogScalarF64(self.task,
                                         ctypes.c_double(read_timeout),
                                         ctypes.byref(self.value),
                                         None))
            result = self.value
        else:
            CHK(dll.DAQmxReadAnalogF64(self.task,
                                       ctypes.c_long(1),
                                       ctypes.c_double(read_timeout),
                                       DAQmx_Val_GroupByChannel,
                                       self.data.ctypes.data_as(c_float64_p),
                                       ctypes.c_ulong(self.n_channels),
                                       ctypes.byref(self.n_read),
                                       None))
            result = self.data.reshape((self.n_samples,))
        CHK(dll.DAQmxStopTask(self.task))
        return result

    def __del__(self):
        CHK(dll.DAQmxClearTask(self.task))


if __name__ == '__main__':
    ai = AnalogIn('dev1/ai0', 1000, 10000., (-10, 10))
    # c = Counter( counter_out_device='/Dev1/Ctr2', counter_in_device='/Dev1/Ctr3', input_pad='/Dev1/PFI3', bin_width=0.01, length=1000)
