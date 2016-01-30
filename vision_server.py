#! /usr/bin/python

import socket
from time import time, sleep
import struct

s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

s.bind(('', 8474))

while True:
    rx = s.recv(1024)
    print "{0}: {1}".format(str(time()), rx)
    s.sendto(rx, (rx, 8474))
