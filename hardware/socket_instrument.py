import socket
import time


# helper class to represent a visa instrument via a socket
class SocketInstrument():
    """Imitate a visa instrument via raw socket."""

    # HW-FIX: sockets speak bytes in Python 3. sendall() rejected the str
    # command outright, and `answer = ''` + recv() bytes raised TypeError, so
    # every ask() failed. Commands are encoded on the way out and the reply is
    # accumulated as bytes and decoded once, at the end -- decoding each chunk
    # would break if a multi-byte character straddled a recv() boundary.
    # The socket also had no timeout of its own, so recv() could block for ever
    # and the timeout check below was never reached.
    def __init__(self, device, chunk_size=2048, term_chars='\r\n', encoding='ascii'):
        host, port = device.split(':')
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((host, int(port)))
        self.sock = sock
        self.chunk_size = chunk_size
        self.term_chars = term_chars
        self.encoding = encoding

    def write(self, cmd):
        """Sends a command over the socket"""
        cmd_string = cmd + '\n'
        if isinstance(cmd_string, str):
            cmd_string = cmd_string.encode(self.encoding)
        sent = self.sock.sendall(cmd_string)
        if sent != None:
            raise RuntimeError('Transmission failed')
        # time.sleep(.1) #add a timeout for the transfer to take place. Should be replaced by a proper error handling at some point

    def ask(self, question, timeout=1.0, poll_time=0.02):
        """sends the question and receives the answer"""
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
                    raise RuntimeError("Timeout occurred.")
        finally:
            self.sock.settimeout(old_timeout)
        return answer[:-len(term)].decode(self.encoding, 'replace')

    def close(self):
        self.sock.close()
