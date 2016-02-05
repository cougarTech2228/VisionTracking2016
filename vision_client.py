#! /usr/bin/python

import socket, struct
from time import time, sleep
s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

s.bind(('', 8474))
s.settimeout(10)

message = '192.168.7.1'

while True:
	start_time = (time() * 1000.0)
	s.sendto(message, ('192.168.7.2', 8474))
	rx = s.recv(1024)
	
	loop_time = (time() * 1000.0) - start_time
	print "Received message from beaglebone, with %sms round trip." % loop_time
	sleep(0.5)
