import os.path
from ftplib import FTP

ftp = FTP()
ftp.set_debuglevel(2)
ftp.connect('192.168.1.101', '21')
ftp.login()
print(ftp.getwelcome())
bufsize = 1024
filename = 'testFTP.txt'
file_handler = open(filename, 'w')
line1 = "Here is the test for FTP\n"
file_handler.write(line1)
file_handler.close()
file_handler = open(filename, 'rb')
ftp.storbinary('STOR %s' % os.path.basename(filename), file_handler, bufsize)
ftp.set_debuglevel(0)
file_handler.close()
ftp.quit()
print("ftp up OK")
