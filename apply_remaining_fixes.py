"""Apply the remaining fixes to the pi3diamond py3 tree, preserving line endings.

    python apply_remaining_fixes.py          # current directory
    python apply_remaining_fixes.py <root>

Run from the repo root. Edits in place; keeps originals as *.hwbak, like
fix_hardware_paths.py. Idempotent: a patch already present is skipped, so a
second run reports what is already done and writes nothing.

If a file has been edited since this script was written, the literal it looks
for will not match and the script stops with PATTERN MISS before touching that
file, rather than guessing.
"""
import io, os, shutil, sys

ROOT = sys.argv[1] if len(sys.argv) > 1 else '.'
APPLIED = []
SKIPPED = []

def load(rel):
    p = os.path.join(ROOT, rel)
    raw = open(p, 'rb').read()
    eol = '\r\n' if raw.count(b'\r\n') > raw.count(b'\n') - raw.count(b'\r\n') else '\n'
    return p, raw.decode('utf-8'), eol

def save(p, text):
    bak = p + '.hwbak'
    if not os.path.exists(bak):
        shutil.copy2(p, bak)
    open(p, 'wb').write(text.encode('utf-8'))

def sub(text, eol, old, new, count=1, label=''):
    old_e = old.replace('\n', eol)
    new_e = new.replace('\n', eol)
    if new_e in text:                       # already patched
        SKIPPED.append(label)
        return text
    n = text.count(old_e)
    if n != count:
        raise SystemExit('PATTERN MISS (%s): found %d, expected %d\n%r'
                         % (label, n, count, old_e[:120]))
    APPLIED.append(label)
    return text.replace(old_e, new_e)

# ---------------------------------------------------------------- nidaq.py
p, t, eol = load('hardware/nidaq.py')

t = sub(t, eol,
"#     This file used ctypes.c_void_p(), which is 4. DAQmxCreateTask would write",
"#     This file used a 4-byte integer type. DAQmxCreateTask would write",
1, 'nidaq comment')

t = sub(t, eol,
"""    def Read(self):
        CHK(dll.DAQmxReadAnalogF64(self.Task,
                                   ctypes.c_long(self.N),
                                   ctypes.c_double(self.read_timeout),
                                   DAQmx_Val_GroupByChannel,
                                   np.ascontiguousarray(self.data, dtype=np.float64).ctypes.data_as(c_float64_p),""",
"""    def Read(self):
        # HW-FIX: this is a READ. DAQmx fills the buffer we hand it, so the
        # pointer must address self.data itself -- np.ascontiguousarray() here
        # would silently hand over a COPY on any dtype change, the DAQ would
        # fill the copy, and Read() would return untouched zeros for ever.
        # self.data is allocated float64 C-contiguous above; assert it stays so.
        assert self.data.dtype == np.float64 and self.data.flags['C_CONTIGUOUS'], \\
            'AITask.data must stay float64 and C-contiguous'
        CHK(dll.DAQmxReadAnalogF64(self.Task,
                                   ctypes.c_long(self.N),
                                   ctypes.c_double(self.read_timeout),
                                   DAQmx_Val_GroupByChannel,
                                   self.data.ctypes.data_as(c_float64_p),""",
1, 'nidaq AI read')

t = sub(t, eol,
"c_uint32_p = c_ulong_p = ctypes.POINTER(ctypes.c_uint32)",
"c_uint32_p = c_ulong_p = ctypes.POINTER(ctypes.c_uint32)\nc_uint8_p = ctypes.POINTER(ctypes.c_uint8)  # HW-FIX: DAQmxWriteDigitalLines takes uInt8",
1, 'nidaq uint8 ptr')

t = sub(t, eol,
"""    def Write(self, data):
        # CHK( dll.DAQmxWriteDigitalScalarU32(self.Task, ctypes.c_long(1), ctypes.c_double(self.write_timeout), ctypes.c_uint32(value), None)  )
        CHK(dll.DAQmxWriteDigitalLines(self.Task,
                                       ctypes.c_long(1),
                                       1,
                                       ctypes.c_double(self.write_timeout),
                                       1,
                                       data.ctypes.data_as(c_uint32_p),""",
"""    def Write(self, data):
        # CHK( dll.DAQmxWriteDigitalScalarU32(self.Task, ctypes.c_long(1), ctypes.c_double(self.write_timeout), ctypes.c_uint32(value), None)  )
        # HW-FIX: DAQmxWriteDigitalLines reads a uInt8 array, one byte per
        # line. The buffer was cast to c_uint32_p, which is merely a wrong
        # label -- ctypes passes the address either way -- but nothing forced
        # the dtype, so a caller passing np.array((1, 0)) (int64 on NumPy 2)
        # would have had its line states read out of the wrong bytes.
        data = np.ascontiguousarray(data, dtype=np.uint8)
        CHK(dll.DAQmxWriteDigitalLines(self.Task,
                                       ctypes.c_long(1),
                                       1,
                                       ctypes.c_double(self.write_timeout),
                                       1,
                                       data.ctypes.data_as(c_uint8_p),""",
1, 'nidaq DO write')
save(p, t)

# ------------------------------------------------------- socket_instrument.py
p, t, eol = load('hardware/socket_instrument.py')
t = sub(t, eol,
"""    def __init__(self, device, chunk_size=2048, term_chars='\\r\\n'):
        host, port = device.split(':')
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((host, int(port)))
        self.sock = sock
        self.chunk_size = chunk_size
        self.term_chars = term_chars

    def write(self, cmd):
        \"\"\"Sends a command over the socket\"\"\"
        cmd_string = cmd + '\\n'
        sent = self.sock.sendall(cmd_string)
        if sent != None:
            raise RuntimeError('Transmission failed')
        # time.sleep(.1) #add a timeout for the transfer to take place. Should be replaced by a proper error handling at some point

    def ask(self, question, timeout=1.0, poll_time=0.02):
        \"\"\"sends the question and receives the answer\"\"\"
        self.write(question)
        answer = ''
        start_time = time.time()
        while not self.term_chars in answer:
            answer += self.sock.recv(self.chunk_size)
            time.sleep(poll_time)
            if time.time() - start_time > timeout:
                raise RuntimeError(\"Timeout occurred.\")
        return answer[:-len(self.term_chars)]""",
"""    # HW-FIX: sockets speak bytes in Python 3. sendall() rejected the str
    # command outright, and `answer = ''` + recv() bytes raised TypeError, so
    # every ask() failed. Commands are encoded on the way out and the reply is
    # accumulated as bytes and decoded once, at the end -- decoding each chunk
    # would break if a multi-byte character straddled a recv() boundary.
    # The socket also had no timeout of its own, so recv() could block for ever
    # and the timeout check below was never reached.
    def __init__(self, device, chunk_size=2048, term_chars='\\r\\n', encoding='ascii'):
        host, port = device.split(':')
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((host, int(port)))
        self.sock = sock
        self.chunk_size = chunk_size
        self.term_chars = term_chars
        self.encoding = encoding

    def write(self, cmd):
        \"\"\"Sends a command over the socket\"\"\"
        cmd_string = cmd + '\\n'
        if isinstance(cmd_string, str):
            cmd_string = cmd_string.encode(self.encoding)
        sent = self.sock.sendall(cmd_string)
        if sent != None:
            raise RuntimeError('Transmission failed')
        # time.sleep(.1) #add a timeout for the transfer to take place. Should be replaced by a proper error handling at some point

    def ask(self, question, timeout=1.0, poll_time=0.02):
        \"\"\"sends the question and receives the answer\"\"\"
        self.write(question)
        term = self.term_chars.encode(self.encoding)
        answer = b''
        start_time = time.time()
        old_timeout = self.sock.gettimeout()
        self.sock.settimeout(max(poll_time, 0.05))
        try:
            while not term in answer:
                try:
                    chunk = self.sock.recv(self.chunk_size)
                except socket.timeout:
                    chunk = b''
                if chunk:
                    answer += chunk
                else:
                    time.sleep(poll_time)
                if time.time() - start_time > timeout:
                    raise RuntimeError(\"Timeout occurred.\")
        finally:
            self.sock.settimeout(old_timeout)
        return answer[:-len(term)].decode(self.encoding, 'replace')""",
1, 'socket_instrument')
save(p, t)

# ------------------------------------------------------------ vector_magnet.py
p, t, eol = load('hardware/vector_magnet.py')
t = sub(t, eol,
"""        self.instrument.write_raw('MSxrrrX')
        readout_string = ''
        try:
            for i in range(6):
                readout_string += self.instrument.visalib.read(self.instrument.session, 1)[0]
        except Exception as e:
            print('Error in LTC2422 Readout. Possibly too few bytes were returned.')
            raise
        return readout_string, self._hex_to_rel_voltage(readout_string)""",
"""        # HW-FIX: write_raw() takes bytes in pyvisa 1.x, and visalib.read()
        # returns (bytes, status), so the old `'' + bytes` raised TypeError and
        # the magnet readout never worked. Bytes are collected and decoded once.
        self.instrument.write_raw(b'MSxrrrX')
        readout_bytes = b''
        try:
            for i in range(6):
                chunk = self.instrument.visalib.read(self.instrument.session, 1)[0]
                if isinstance(chunk, str):          # some visalib backends decode for us
                    chunk = chunk.encode('ascii', 'replace')
                readout_bytes += chunk
        except Exception as e:
            print('Error in LTC2422 Readout. Possibly too few bytes were returned.')
            raise
        readout_string = readout_bytes.decode('ascii', 'replace')
        return readout_string, self._hex_to_rel_voltage(readout_string)""",
1, 'vector_magnet read')
save(p, t)

# -------------------------------------------------------------------- hameg.py
p, t, eol = load('hardware/hameg.py')
t = sub(t, eol,
"""    def write(self, cmd):
        \"\"\"Sends a command over the socket\"\"\"
        cmd_string = cmd + '\\n'
        sent = self.sock.sendall(cmd_string)
        if sent != None:
            raise RuntimeError('Transmission failed')
        time.sleep(
            .1)  # add a timeout for the transfer to take place. Should be replaced by a proper error handling at some point

    def ask(self, question):
        \"\"\"sends the question and receives the answer\"\"\"
        self.write(question)
        answer = self.sock.recv(2048)  # 2000
        return answer[:-1]""",
"""    def write(self, cmd):
        \"\"\"Sends a command over the socket\"\"\"
        # HW-FIX: sendall() takes bytes in Python 3.
        cmd_string = cmd + '\\n'
        if isinstance(cmd_string, str):
            cmd_string = cmd_string.encode('ascii')
        sent = self.sock.sendall(cmd_string)
        if sent != None:
            raise RuntimeError('Transmission failed')
        time.sleep(
            .1)  # add a timeout for the transfer to take place. Should be replaced by a proper error handling at some point

    def ask(self, question):
        \"\"\"sends the question and receives the answer\"\"\"
        # HW-FIX: recv() returns bytes; callers do float(...) on the result.
        self.write(question)
        answer = self.sock.recv(2048)  # 2000
        if isinstance(answer, bytes):
            answer = answer.decode('ascii', 'replace')
        return answer[:-1]""",
1, 'hameg socket')

t = sub(t, eol,
"""    def _connect_serial(self, device):
        import pyvisa as visa
        instr = visa.instrument('ASRL11::INSTR')
        instr.term_chars = '\\n'
        instr.chunk_size = 4096
        instr.timeout = 1.0
        self.instr = instr""",
"""    def _connect_serial(self, device):
        # HW-FIX: visa.instrument() was removed in pyvisa 1.6, and the address
        # was hard-coded to ASRL11 regardless of the `device` argument passed
        # in. Also: pyvisa timeouts are in MILLISECONDS, so `timeout = 1.0`
        # meant 1 ms, not 1 s -- every read would have timed out.
        import pyvisa as visa
        rm = visa.ResourceManager()
        instr = rm.open_resource(device)
        instr.read_termination = '\\n'
        instr.write_termination = '\\n'
        instr.chunk_size = 4096
        instr.timeout = 1000.0  # ms
        self.instr = instr""",
1, 'hameg serial')

t = sub(t, eol,
"""        elif min(seq_ary[:, 2]) < .5:
            raise ValueError('The set time is shorter than 0.5s.')
        elif seq <= 0:
            raise ValueError('Negative value of voltage, current or time.')""",
"""        elif min(seq_ary[:, 2]) < .5:
            raise ValueError('The set time is shorter than 0.5s.')
        elif seq_ary.min() <= 0:
            # HW-FIX: was `seq <= 0`, comparing a list against an int. Python 2
            # allowed that and always returned False, so the check never fired;
            # Python 3 raises TypeError. Compare the values instead.
            raise ValueError('Negative value of voltage, current or time.')""",
1, 'hameg seq check')

t = sub(t, eol,
"""            self.instr.write('ARB:DATA' + ' ' + str(seq).translate(None, '[()] '))""",
"""            # HW-FIX: str.translate(None, chars) is Python 2 only.
            self.instr.write('ARB:DATA' + ' ' +
                             str(seq).translate({ord(c): None for c in '[()] '}))""",
1, 'hameg translate')

t = sub(t, eol,
"""        import serial
        self.port = serial.Serial(serPort, 19200, timeout=1, xonxoff=0, rtscts=0)""",
"""        import serial
        # HW-FIX: pyserial 3 dropped integer port numbers. The old default of 2
        # meant COM3; a bare int now raises. Ints are mapped for compatibility.
        if isinstance(serPort, int):
            serPort = 'COM%d' % (serPort + 1)
        self.port = serial.Serial(serPort, 19200, timeout=1, xonxoff=0, rtscts=0)""",
1, 'hameg serial port')

t = sub(t, eol,
"""    def sendFrame(self, a, b, c):
        \"\"\"The frame consists of 4byts (CMD,Address,Data,Checksum)\"\"\"
        self.port.write('%c%c%c%c' % (chr(a), chr(b), chr(c), chr(a ^ b ^ c)))""",
"""    def sendFrame(self, a, b, c):
        \"\"\"The frame consists of 4byts (CMD,Address,Data,Checksum)\"\"\"
        # HW-FIX: pyserial 3 writes bytes, not str. The old '%c%c%c%c' string
        # would also have been encoded as UTF-8 for values above 127, turning a
        # 4-byte frame into 5 or more bytes on the wire.
        self.port.write(bytes((a & 0xFF, b & 0xFF, c & 0xFF, (a ^ b ^ c) & 0xFF)))""",
1, 'hameg sendFrame')

t = sub(t, eol,
"""        s = self.port.read(4)
        self.port.flushInput()
        if not s:
            return s
        r = tuple(map(ord, s))""",
"""        s = self.port.read(4)
        self.port.flushInput()
        if not s:
            return s
        # HW-FIX: read() returns bytes; iterating already yields ints, so
        # map(ord, ...) raised TypeError.
        r = tuple(bytearray(s))""",
1, 'hameg readFrame')

t = sub(t, eol,
"""        if not s:
            raise RuntimError('Communication failure error: received empty string')
        r = tuple(map(ord, s))""",
"""        if not s:
            # HW-FIX: was RuntimError -- a typo that turned this failure into a
            # NameError, hiding what actually went wrong.
            raise RuntimeError('Communication failure error: received empty string')
        r = tuple(bytearray(s))  # HW-FIX: bytes iterate as ints""",
1, 'hameg NOP')

t = sub(t, eol,
"""            time.sleep(i * 0.1)
        raise RuntimeError('Command failed: %d-%d-%d -> %d-%d-%d' % (a, b, c, f[0], f[1], f[2]))""",
"""            time.sleep(i * 0.1)
        # HW-FIX: f is empty when the device sent nothing, so the old message
        # raised IndexError instead of reporting the failure.
        if f:
            raise RuntimeError('Command failed: %d-%d-%d -> %s' % (a, b, c, tuple(f)))
        raise RuntimeError('Command failed: %d-%d-%d -> no answer' % (a, b, c))""",
1, 'hameg sendCmd')
save(p, t)

# ------------------------------------------------------------ confocal_focus.py
p, t, eol = load('measurements/confocal_focus.py')
t = sub(t, eol,
"""            index = self.data_xy.argmax()
            xp = self.X[index % len(self.X)]
            yp = self.Y[index / len(self.X)]""",
"""            index = self.data_xy.argmax()
            xp = self.X[index % len(self.X)]
            # HW-FIX: `/` is a float in Python 3 and a float cannot index a
            # sequence. This is a row number, so it needs floor division.
            yp = self.Y[index // len(self.X)]""",
1, 'confocal index')

t = sub(t, eol,
"""            i0 = numpy.floor(center_x)
            i1 = numpy.ceil(center_x)
            x0 = self.X[i0]
            x1 = self.X[i1]
            xp = x0 + (center_x - i0) * (x1 - x0)
            i0 = numpy.floor(center_y)
            i1 = numpy.ceil(center_y)
            y0 = self.Y[i0]
            y1 = self.Y[i1]""",
"""            # HW-FIX: numpy.floor/ceil return floats, which cannot index an
            # array. int() keeps the interpolation below unchanged.
            i0 = int(numpy.floor(center_x))
            i1 = int(numpy.ceil(center_x))
            x0 = self.X[i0]
            x1 = self.X[i1]
            xp = x0 + (center_x - i0) * (x1 - x0)
            i0 = int(numpy.floor(center_y))
            i1 = int(numpy.ceil(center_y))
            y0 = self.Y[i0]
            y1 = self.Y[i1]""",
1, 'confocal gaussfit')
save(p, t)

# --------------------------------------------------------- pulsedAFMclient.py
for rel in ('measurements/pulsedAFMclient.py', 'measurements/pulsedAFMclient_old.py'):
    if not os.path.exists(os.path.join(ROOT, rel)):
        continue
    p, t, eol = load(rel)
    n = t.count('data.shape[1] / 2')
    if n:
        t = t.replace('data.shape[1] / 2', 'data.shape[1] // 2')
        APPLIED.append('%s (%d slice bounds)' % (rel, n))
        save(p, t)
    else:
        SKIPPED.append('%s slice bounds' % rel)

# ------------------------------------------------------------------ waveform.py
p, t, eol = load('measurements/awg/waveform.py')
t = sub(t, eol,
"""    def __div__(self, pulse):
        new = deepcopy(self)
        f = new.func
        new.func = lambda x: f(x) / pulse.func(x)
        return new

    def __idiv__(self, pulse):
        f = pulse.func
        g = self.func
        self.func = lambda x: g(x) / f(x)
        return self""",
"""    def __div__(self, pulse):
        new = deepcopy(self)
        f = new.func
        new.func = lambda x: f(x) / pulse.func(x)
        return new

    def __idiv__(self, pulse):
        f = pulse.func
        g = self.func
        self.func = lambda x: g(x) / f(x)
        return self

    # HW-FIX: Python 3 calls __truediv__ / __itruediv__ for `/` and `/=`;
    # __div__ and __idiv__ are never looked up, so pulse division raised
    # TypeError. The Python 2 names are kept so nothing that calls them
    # directly breaks.
    __truediv__ = __div__
    __itruediv__ = __idiv__""",
1, 'waveform div')
save(p, t)

print('')
print('applied: %d  %s' % (len(APPLIED), ', '.join(APPLIED) if APPLIED else '-'))
print('already done: %d  %s' % (len(SKIPPED), ', '.join(SKIPPED) if SKIPPED else '-'))
print('originals kept as *.hwbak')
