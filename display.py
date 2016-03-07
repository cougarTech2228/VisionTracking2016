# Echo server program
import socket
import numpy
from numpy import array, int16, uint8, clip
import sys
import cv2

params = b'2295';

HOST = ''                 # Symbolic name meaning all available interfaces
PORT = 50007              # Arbitrary non-privileged port
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.bind((HOST, PORT))
s.listen(1)

buff = b''
active = True

def listen():
    conn, addr = s.accept()

    print('Connected by', addr)
    while True:
        data = conn.recv(4096)
        if not data: break
        conn.sendall(params)
        parse(data)
        continue
        try:
            parse(data)
        except:
            print(sys.exc_info()[0])
    conn.close()


def parse(msg):
    global buff, active, f, a
    dtype = uint8

    buff+=msg

    try:
        i = buff.index(b"<ENDMSG>")
        data = buff[:i]
        buff = buff[i+8:]
        try:
            while True:
                i = buff.index("<ENDMSG>")
                buff=buff[i+8:]

        except:
            pass
    except:
        return

    s = data.split(b"<HEAD>")
    a = numpy.fromstring(s[0], dtype=uint8 )

    l,w =s[1].split(b"#")
    a = a.reshape(int(l), int(w))

    if active:
        cv2.imshow("found",a)
        cv2.waitKey(10)
listen()

