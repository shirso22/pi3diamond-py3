"""
This module provides a connection and control of the Nanonis via Pyhton.

The way this works is via a LabView TcpIp server that listens to Pyhton calls that deliver a string
that contains the program to run. Subsequently the LabView Script 'TCPIP.Server.vi' executes the 
program and recieves a string depending on the result which it gives back as a python string. 
'TCPIP.Server.vi' has to be running in the background at all times for this to work!
"""

import socket


class Nanonis:
    """Provides software backend to the Nanonis via Python.
    
    'TCPIP.Server.vi' must be running."""

    def __init__(self, host='localhost', port=50007):
        self.host = host
        self.port = port
        self.sock = socket.socket()

    def connect(self):
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.connect((self.host, self.port))
            print('Nanonis connected.')
        except Exception as e:
            print('There was an error connecting to the Nanonis.')
            raise e

    def _execute(self, command):
        try:
            self.sock.send(command)
            reply = self.sock.recv(1024)
        except Exception as e:
            print('There was an error executing the command ' + command + ' on the Nanonis.')
            print(e)
            reply = 'failed'
        return reply

    def start_scan(self):
        self._execute("NanonisScanAction.vi(1)")

    def stop_scan(self):
        self._execute("NanonisScanAction.vi(0)")

    def get_scan_state(self):
        return int(self._execute("NanonisIsScanRunning.vi(0)"))

    def get_scan_pixels(self):
        pixels_string = self._execute("NanonisGetScanPixels.vi(0)")
        pixels = pixels_string.split(',')
        return int(pixels[0]), int(pixels[1]), float(pixels[2])

    def get_sample_time(self):
        return float(self._execute("NanonisGetSampleTime.vi(0)"))

    def get_scan_offset(self):
        offset_string = self._execute("NanonisGetScanOffset.vi(0)")
        offset = offset_string.split(',')
        offset = [float(offset[0]), float(offset[1])]
        return offset

    def disconnect(self):
        self.sock.shutdown(2)
        self.sock.close()
