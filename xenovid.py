import os, sys
sys.path.append(os.getcwd())

import _ct
a,b,vid_conf_addr = _ct.addrs()
from ctypes import c_ubyte
from stronghold import WIDTH, HEIGHT, vidconf_s

vc = vidconf_s.from_address(vid_conf_addr)

Image=(((c_ubyte*3)*WIDTH)*HEIGHT)
from numpy.ctypeslib import as_array
ia = Image.from_address(a)
ib = Image.from_address(b)
sig = as_array(ia)
back = as_array(ib)

import cv2, threading
from cv2 import cv

class DisplayThread(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
        self.daemon = True
    def run(self):
        while True :
            cv2.imshow("sig", sig)
            cv2.imshow("back", back)
            cv2.imshow("diff", cv2.subtract(sig,back))
            cv2.waitKey(20)

dt = DisplayThread()
dt.start()
import socket, time

def connect():
    global sock
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect(("192.168.7.1", 50007))

def send(img) :
    img = np.clip(img,0,255)
    icop = array(img, dtype=uint8)
    l, w = icop.shape
    text = icop.tostring()
    text = text + '<HEAD>{0}#{1}'.format(l,w)
    sock.sendall(text)
    sock.sendall(b"<ENDMSG>")

def feed(delay, frame):
    while True:
        time.sleep(delay)
        try:
            send(frame)
        except:
            print("no connection")
            try:
                connect()
            except:
                time.sleep(1)

    
