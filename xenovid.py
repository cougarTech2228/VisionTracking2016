

import _ct
a,b = _ct.grab()
from ctypes import c_ubyte
Image=(((c_ubyte*3)*160)*120)
from numpy.ctypeslib import as_array
ia = Image.from_address(a)
ib = Image.from_address(b)
sig = as_array(ia)
back = as_array(ib)

import cv2
from cv2 import cv

while True :
    cv2.imshow("sig", sig)
    cv2.imshow("back", back)
    cv2.waitKey(1)
