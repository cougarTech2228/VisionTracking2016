"""
vision processing code for Stronghold, FRC 2016 game
runs on a beaglebone black. We're using a logitech c290 but other video sources 
will probably work better!
the c290 is uvcvideo and doesn't use a v24l driver.

run as:

sudo python -i stronghold.py

you can inspect the led thread and acquire thread objects from the console.
show(at.idiff) will show the difference image.
plot(at.rsum) and plot(at.csum) show the 1D marginal sums
 
if it doesn't work
try
sudo rmmod uvcvideo
sudo modprobe uvcvideo nodrop=1 timeout=5000 quirks=0x80
(thanks nuts and volts, derek molloy, etc..!)

sudo apt-get install libcv-dev
sudo apt-get install python-opencv opencv-apps
"""

import cv2
from cv2 import cv
from Adafruit_BBIO import GPIO
GPIO.setup("P9_24", GPIO.OUT)
import numpy as np
from numpy import array, int16, uint8, clip

cap = cv2.VideoCapture(0)
opened = cap.isOpened()
if not opened :
    print "no video stream! exiting.."
    exit()

WIDTH = 160.
HEIGHT = 120.

cap.set(cv.CV_CAP_PROP_FRAME_WIDTH, WIDTH)
cap.set(cv.CV_CAP_PROP_FRAME_HEIGHT, HEIGHT)
if (cap.get(3), cap.get(4)) != (WIDTH, HEIGHT) :
    print "can't set resolution to %d by %d, exiting.." % (WIDTH, HEIGHT)
    exit()

import time
import threading

class AcquireThread(threading.Thread) :
    """
    The acquire Thread runs as fast as it can and tries to keep the video buffer empty...
    Grabbing video and then processing it.
    It notifies the LED thread when it wants another LED pulse.
    """
    def __init__(self, lt) :
        threading.Thread.__init__(self)
        self.daemon = True # this thread will be stopped abruptly when the program exits.
        self.lt = lt
        self.tavg = 0.0666 # 30 Frames per second

    def run(self) :
        self.sig = array(cap.read()[1], dtype=int16) # signal.. illuminator is on
        self.back = array(cap.read()[1], dtype=int16) # background. illuminator is off.
        self.start=time.time()
        while True :
            self.sig[:,:,:] = cap.read()[1]  # first frame is signal (illuminator is on)
            self.back[:,:,:] = cap.read()[1] # next frame is background (illuminator is off)
            # check the measured on time of the last led pulse
            # as well as the measured sleeptime before the pulse ?
            error = self.lt.error
            # if either is too long, we could just forget this image pair.
            self.lt.notify() # notify the led thread we want another pair
            # image processing goes here
            # (or you could have a processing thread, but why?)
            self.idiff = self.sig - self.back # signal minus background image
            if error :
                self.ierr = self.idiff
            isum = np.sum(self.idiff, axis=2) # add rgb together in each pixel.
            self.csum = np.sum(isum, axis=0) # sum rows with each other, get sum of each column.
            self.rsum = np.sum(isum, axis=1) # sum columns together, get sum of each row.
            # okay, we are done for now.
            # but more processing might be needed.
            self.end = time.time()
            self.tdiff = self.end - self.start
            self.start = self.end # reset our loop timer.
            self.tavg += 0.05 * (self.tdiff - self.tavg) # average time per frame pair.
            self.fps = 2.0 / self.tavg # average frames per second

            
class LedThread(threading.Thread) :
    # separate thread that turns the LED on and off
    def __init__(self, delay, ontime) :
        threading.Thread.__init__(self)
        self.delay = delay
        self.ontime = ontime
        self.request = threading.Event()
        self.result = threading.Event()
        self.daemon = True # this thread will be stopped abruptly when the program exits.
        self.error = True #
    def run(self) :
        while True :
            # continuous loop. wait until sync is called 
            self.request.wait()
            self.start = time.time()
            time.sleep(self.delay)
            wake = time.time()
            self.sleeptime = wake - self.start
            GPIO.output("P9_24", 1)
            time.sleep(self.ontime)
            GPIO.output("P9_24", 0)
            off = time.time()
            self.ot = off - wake
            self.error = (self.sleeptime > (self.delay + 0.05)) or (self.ot > (self.ontime + 0.05))
            self.request.clear()

    def notify(self) :
        # video thread calls this to ask for another LED pulse.
        self.request.set()
        
lt = LedThread(delay=0.000, ontime=0.008)
at = AcquireThread(lt)
lt.start()        
at.start()

from pylab import interactive, imshow, plot
interactive(True)

def show(img) :
    """
    make an 8 bit copy of the image.
    swap the red and the green pixels.
    this will mess up the timing of the other threads
    """
    img = clip(img,0,255)
    icop = array(img, dtype=uint8)
    icop[:,:,0] = img[:,:,2]
    icop[:,:,2] = img[:,:,0]
    imshow(icop, interpolation="nearest")
