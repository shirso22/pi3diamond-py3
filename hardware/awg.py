# import time
import sys
from ftplib import FTP  # The File Transfer Protocol, The FTP class implements the client side of the FTP protocol
from socket import SOL_SOCKET, SO_KEEPALIVE

import pyvisa as visa

from measurements.awg.waveform import *


class AWG:
    """Controller for the Tektronix AWG5014C device.
    
    SCPI commands are issued via gpib.
    See device manual for command documentation.
    File management is done via FTP.
    
    """

    def __init__(self, address, host, user, passwd):
        self.address = address
        # setup ftp-connection
        self.ftp = FTP(host=host, user=user, passwd=passwd)
        self.ftp.sock.setsockopt(SOL_SOCKET, SO_KEEPALIVE, 1)
        self.ftp.sock.settimeout(5.0)
        # setup gpib connection
        # self.gpib = visa.instrument(self.address['gpib'])
        self.gpib = visa.ResourceManager().get_instrument(self.address['gpib'])
        self.gpib.timeout = 5.0

    def __del__(self):
        # HW-FIX: __init__ may not have reached these attributes (no AWG, or a
        # failed GPIB/FTP open), and __del__ then raised AttributeError at
        # shutdown -- noise that hides real errors from other destructors.
        for _attr in ('gpib', 'ftp'):
            _obj = getattr(self, _attr, None)
            if _obj is not None:
                try:
                    _obj.close()
                except Exception:
                    pass
        # self.soc.close()

    # ____________
    # File Management

    PARALLEL = 0
    SERIAL = 1

    def connect_ftp(self):
        connection_trial_number = 0
        while connection_trial_number < 5:
            try:
                self.ftp = FTP('192.168.1.101', timeout=3.0)
                connection_trial_number = 5
            except:
                print("ftp error:", sys.exc_info()[0])
                print("FTP connection did not work, retry")
                connection_trial_number += 1
        self.ftp.set_pasv(False)
        self.ftp.login()
        # self.ftp.cwd(self.ftp_cwd)

    def disconnect_ftp(self):
        self.ftp.quit()

    class UploadThread(Thread):
        """ Thread object, which uploads a single file to the AWG.
        """

        def __init__(self, address, file):
            self.ftp = FTP(address)
            self.res = self.ftp.login()
            self.file = file
            Thread.__init__(self)

        def run(self):
            try:
                if isinstance(self.file, (StringIO, Waveform)):
                    self.file.seek(0)
                    self.res = self.ftp.storbinary('STOR ' + self.file.name, self.file)
                elif isinstance(self.file, str):
                    f = open(self.file, 'rb')
                    self.res = self.ftp.storbinary('STOR ' + self.file, f)
                    f.close()
            finally:
                self.ftp.close()

    def upload(self, files, mode=PARALLEL):
        """Upload files to the AWG.
        
        """
        if not isinstance(files, (list, tuple)):
            files = [files]

        if mode == self.PARALLEL:
            threads = []
            for file in files:
                ut = self.UploadThread(self.address['ftp'], file)
                threads.append(ut)
                ut.start()
                # print 'Thread started.'
            for i, t in enumerate(threads):
                t.join()

        elif mode == self.SERIAL:
            for file in files:
                self.ftp = FTP(self.address['ftp'])
                self.ftp.login()
                if isinstance(file, (StringIO, Waveform)):
                    file.seek(0)
                    res = self.ftp.storbinary('STOR ' + file.name, file)
                elif isinstance(file, str):
                    with open(file, 'rb') as f:
                        res = self.ftp.storbinary('STOR ' + file.upper(), f)
                self.ftp.close()

    def delete(self, files):
        """Remove the specified files from the CWD.
        
        Delete a single file by providing its name as argument. Delete multiple
        files by passing a list of filenames as argument.
        
        files - string or list of strings
        
        """

        if not isinstance(files, (list, tuple)):
            files = [files]
        for filename in files:
            res = self.ftp.delete(filename)
        return res

    def delete_all(self):
        """Remove all files from the AWG's CWD.
        """
        self.ftp = FTP('192.168.1.101')
        self.ftp.login()
        res = 0
        filelist = self.ftp.nlst()
        try:
            filelist.remove('.')
            filelist.remove('..')
        except ValueError:
            pass
        for filename in filelist:
            res = self.ftp.delete(filename)
        return res

    # ____________
    # Operation Commands

    def tell(self, command):
        """Send a command string to the AWG."""
        self.gpib.write(command)

    def ask(self, query):
        """Send a query string to AWG and return the response."""
        self.gpib.write(query)
        try:
            res = self.gpib.read()
        except visa.VisaIOError as e:
            res = ''
            if 'Timeout' in e.message:
                print(query, '--- no response from AWG')
            else:
                raise e
        return res

    def run(self):
        self.tell('AWGC:RUN')

    def stop(self):
        self.tell('AWGC:STOP')

    def force_trigger(self):
        self.tell('*TRG')

    def force_event(self, bitcode):
        self.tell('AWGC:EVEN:SOFT %i' % bitcode)

    def set_output(self, channel=0b1111):
        """Set the output state of specified channels.
        
        channels - int with states encoded on 4 LSB
                   e.g. bit=0b0000 closes all, bit=0b1111 opens all,
                        bit=0b1010 opens OUTP2 and 4 and closes OUTP1 and 3
        
        """
        for i in [0, 1, 2, 3]:
            stat = channel >> i & 1
            self.tell('OUTP%i %i' % ((i + 1), stat))

    def set_mode(self, mode):
        """Change the output mode.
        
        Options for mode (case-insensitive):
        continuous - 'C', 'CONT'
        triggered  - 'T', 'TRIG'
        gated      - 'G', 'GAT'
        sequence   - 'S', 'SEQ'
        
        """
        look_up = {'C': 'CONT', 'CONT': 'CONT',
                   'T': 'TRIG', 'TRIG': 'TRIG',
                   'G': 'GAT', 'GAT': 'GAT',
                   'S': 'SEQ', 'SEQ': 'SEQ'
                   }
        self.tell('AWGC:RMOD %s' % look_up[mode.upper()])

    def set_sample(self, frequency):
        """ Set the output sampling rate [GHz].
        
        """
        self.tell('SOUR:FREQ %.4GGHz' % frequency)

    def set_vpp(self, voltage, channel=0b1111):
        """ Set output peak-to-peak voltage of specified channel.
            
        """
        if channel & 1 == 1:
            self.tell('SOUR1:VOLT %.4GV' % voltage)
        if channel & 2 == 2:
            self.tell('SOUR2:VOLT %.4GV' % voltage)
        if channel & 4 == 4:
            self.tell('SOUR3:VOLT %.4GV' % voltage)
        if channel & 8 == 8:
            self.tell('SOUR4:VOLT %.4GV' % voltage)

    def load(self, filename, channel=1, cwd=None):
        """Load sequence or waveform file into RAM, preparing it for output.
        
        Waveforms and single channel sequences can be assigned to each or both
        channels. Double channel sequences must be assigned to channel 1.
        The AWG's file system is case-sensitive.
        
        """
        if cwd is None:
            cwd = '/InetPub/ftproot'  # default C:\InetPub\ftproot
        self.tell('SOUR%i:FUNC:USER "%s/%s"' % (channel, cwd, filename))

    def reset(self):
        """ Reset the AWG settings. """
        self.tell('*RST')

    # TODO:
    # def play(self, *seq, **kw):
    # seq, waves = make(*seq, **kw)

# _____________________________________________________________________________
# EXCEPTIONS:
# TODO

# _____________________________________________________________________________
# DEBUG SCRIPT:
