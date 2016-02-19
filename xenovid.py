
import os, sys
sys.path.append(os.getcwd())
import numpy as np
import _ct
a,b,vid_conf_addr = _ct.addrs()
from ctypes import c_ubyte
import copy
from py import keys

from stronghold import WIDTH, HEIGHT, vidconf_s
vc = vidconf_s.from_address(vid_conf_addr)
vc.on_time = 15000000 # units are nanoseconds. 
# frame time is 30 milliseconds, so make it smaller than that.

Image=(((c_ubyte*3)*WIDTH)*HEIGHT)
from numpy.ctypeslib import as_array
ia = Image.from_address(a)
ib = Image.from_address(b)
sig = as_array(ia)
back = as_array(ib)

import cv2, threading
import cPickle as pickle
from pylab import plot, ion
ion()
from cv2 import cv
from time import time
from networktables import NetworkTable
NetworkTable.setIPAddress("10.22.28.20")
NetworkTable.setClientMode()
NetworkTable.initialize()
sd = NetworkTable.getTable("SmartDashboard")

class VideoThread(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
        self.daemon = True
        self.watch_keys = False
        self.showsig = False
        self.showback = False
        self.showdiff = False
        self.showr = False
        self.showg = False
        self.showb = False
        self.showm = False
        self.verbose = False
        self.testmode = False
        self.showfound = False
        self.minthresh = 1000
        sd.putBoolean(keys.KEY_VISION, False)

    def run(self):
        while True :
          vc.led_enabled = sd.getBoolean(keys.KEY_VISION)
          if vc.led_enabled :
            self.process()     

            if self.showsig :
                cv2.imshow("sig", sig)
            if self.showback :
                cv2.imshow("back", back)
            if self.showdiff :
                cv2.imshow("diff", self.diff) 
            
            if self.watch_keys :
                key = cv2.waitKey(20)
                if key == -1:
                    continue
                if key == ord('s') or key == ord('S'):
                    with open("diff.np", "w") as f:
                        pickle.dump(self.diff, f)
                    with open("sig.np", "w") as f:
                        pickle.dump(sig, f)
                    with open("back.np", "w") as f:
                        pickle.dump(back, f)
                    continue
            else :
                cv2.waitKey(1) # needed to do any display!

    def process(self):
        # estimate the row and column shift..
        # look at diff of previous back and current back
        # grab a single row of the diff image
        # cross-correlation with self should yield
        # a strong dip at the horizontal shift.
        if self.testmode :
            self.diff = sig # np.array(sig, dtype="int16") # test with white on black target
        else :
            self.diff = cv2.subtract(sig, back) # could do the diff in C code.

        bdiff, gdiff, rdiff = [self.diff[:,:,i] for i in range(3)] #lightweight
        
        if self.testmode :
            self.mono = mono_diff = bdiff/3 + gdiff/3 + rdiff/3
        else :
            self.mono = mono_diff = cv2.subtract(gdiff, rdiff)

        self.vsum = vsum = np.sum(mono_diff, axis=0)
        
        if self.showr :
            cv2.imshow("rdiff", rdiff)
        if self.showg :
            cv2.imshow("gdiff", gdiff)
        if self.showb :
            cv2.imshow("bdiff", bdiff)
        if self.showm :
            cv2.imshow("mono", mono_diff)
    
        #constant to filter peaks in vsum (middle of range)
        self.threshold = (np.max(vsum) + np.min(vsum)) / 2 
        if self.threshold < self.minthresh :
            self.threshold = self.minthresh
    
        search = True #is loop if looking for a peak
        segments = [] #peaks collapsed to line segments
    
        #scans through vsum to find peaks
        colsums = enumerate(vsum)

        for col, csum in colsums :
            if csum > self.threshold : # we found a column over threshold
                peaksum = csum
                peaksumc = csum*col
                peakstart = col
                for col, csum in colsums : # continue iterating over the columns...
                    if csum > self.threshold :
                        peaksum += csum
                        peaksumc += csum*col
                    else : # we have fallen below threshold again. peak has been found.
                        peakend = col - 1
                        # each segment is the TOTAL sum in the peak, plus the start and end pixel
                        segments.append((peaksum, (peakstart, peakend), float(peaksumc)/peaksum))
                        break

        self.rawfound = len(segments)
                
        # we will VERY often get more than 2.. camera might see 6!!
        # find two peaks next to each other of sensible separation and strength.
        # we want the two strongest ones?
        # actually, we pick the strongest peak
        # and its strongest neighbor.
        if len(segments) > 2 :  # if we DO get more than 2
            sums = [seg[0] for seg in segments] # just look at their strengths.
            strongest = max(sums) 
            if sums[0] == strongest : # first peak is strongest? then first two.
                segments = segments[:2] 
            elif sums[-1] == strongest : # last peak is strongest? last two.
                segments = segments[-2:]
            else :
                ix = sums.index(strongest) # pick the strongest neighbor.
                if sums[ix + 1] > sums[ix - 1] :
                    segments = segments[ix : ix + 2]
                else :
                    segments = segments[ix - 1 : ix + 1]
        
        if len(segments) == 2 :
            # peaks = [sum(s[1])/2 for s in segments]
            peaks = [s[2] for s in segments]

            #distance from the center of the image tot the center of the target, in pixels
            self.offsetX = sum(peaks)/2 - WIDTH/2
        
            #gap in pixels between the center of two hills
            gap = peaks[1] - peaks[0]
            # We can do a sanity check on the gap, too.
            hsum = np.sum(mono_diff[:, peaks[0] : peaks[1]], axis=1) #horizontal sum
        
            state = 0 #state of the hsum scanner
            hmax = np.max(hsum)
            if False : 
                self.offsetY = hsum.tolist().index(hmax)-HEIGHT/2
                self.display(True)

            rowsums = enumerate(hsum)

            # now find the horizontal bar
            thresh = hmax * 0.8
            for row, rsum in rowsums :
                if rsum > thresh :
                    start = row
                    for row, rsum in rowsums :
                        if rsum < thresh :
                            end = row
                            self.offsetY = (float(start + end)-HEIGHT)/2
                            self.display(True)
                            if self.verbose :
                                print("found x y", self.offsetX, self.offsetY )
                            sd.putNumber(keys.KEY_X, self.offsetX)
                            sd.putNumber(keys.KEY_Y, self.offsetY)
                            sd.putBoolean(keys.KEY_FOUND, True)
                            return
            self.display(False)
            if self.verbose :
                print("missed horizontal bar! x", self.offsetX)
                sd.putNumber(keys.KEY_X, self.offsetX)
                sd.putBoolean(keys.KEY_FOUND, False)
        else:
            self.display(False)
            sd.putBoolean(keys.KEY_FOUND, False)
            if self.verbose :
                print("ERROR: found no vertical segments")

        
    def display(self, found):
        if not self.showfound :
            return
        disp_img = sig.copy()
    
        if(found):
            offX = int(self.offsetX)
            offY = int(self.offsetY)
            cv2.line(disp_img,(WIDTH/2 + offX,0),(WIDTH/2 + offX,HEIGHT),(0,0,255),3)
            cv2.line(disp_img,(0, HEIGHT/2 +offY),(WIDTH, HEIGHT/2 + offY),(0,0,255),3)
        else:
            cv2.putText(disp_img, "?", (WIDTH/3, HEIGHT/3), cv2.FONT_HERSHEY_PLAIN, 4, (0,0,255),4)    
    
        cv2.imshow("display",disp_img)

vt = VideoThread()

vt.showfound = True
vt.showdiff = True
sd.putBoolean(keys.KEY_VISION, True)

vt.start()

import socket
from time import sleep

def connect():
    global sock
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect(("192.168.7.1", 50007))

def send_img(img) :
    img = np.clip(img,0,255)
    icop = array(img, dtype=uint8)
    l, w = icop.shape
    text = icop.tostring()
    text = text + '<HEAD>{0}#{1}'.format(l,w)
    sock.sendall(text)
    sock.sendall(b"<ENDMSG>")
 
def feed(delay, frame):
    while True:
        sleep(delay)
        try:
            send_img(frame)
        except:
            print("no connection")
            try:
                connect()
            except:
                time.sleep(1)

   
#process an image   
import code
code.interact(local=locals())
