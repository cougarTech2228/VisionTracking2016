# Echo server program
import socket
import msgpack
import numpy
from numpy import array, int16, uint8, clip
import sys

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
        try:
            parse(data)
        except:
            print(sys.exc_info()[0])
    conn.close()


import matplotlib

matplotlib.use('TkAgg')
import matplotlib.pyplot as plt

plt.ion()
plt.show()


def parse(msg):
    global buff, active, f
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
    array = numpy.fromstring(s[0], dtype=dtype )

    l,w =s[1].split(b"#")
    array = array.reshape(int(l), int(w))

    if active:
        print("plotting image")
        plt.clf()
        plt.imshow(array)
        plt.draw()
        plt.pause(.0001)
        print("done plotting")

listen()

