
import os, sys
sys.path.append(os.getcwd())
import numpy as np
import _ct
a,b,vid_conf_addr = _ct.addrs()
from ctypes import c_ubyte
import copy

from stronghold import WIDTH, HEIGHT, vidconf_s
vc = vidconf_s.from_address(vid_conf_addr)

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

class VideoThread(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
        self.daemon = True
        self.watch_keys = False
        self.showsig = False
        self.showback = False
        self.showdiff = False
        self.verbose = False

    def run(self):
        while True :
            if self.showsig :
                cv2.imshow("sig", sig)
            if self.showback :
                cv2.imshow("back", back)
            if self.showdiff :
                cv2.imshow("diff", self.diff) 
            
            self.process()            

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
                cv2.waitKey(1) 

    def process(self):
        global offsetX, offsetY
    
        self.diff = cv2.subtract(sig, back) # could do the diff in C code.
        bdiff, gdiff, rdiff = cv2.split(self.diff)
        
        mono_diff = cv2.subtract(gdiff, rdiff)
        vsum = np.sum(mono_diff, axis=0)
        
        #cv2.imshow("gdiff", gdiff)
        #cv2.imshow("rdiff", rdiff)
        #cv2.imshow("bdiff", bdiff)
        #cv2.imshow("mono", mono_diff)
    
        #constant to filter peaks in vsum (middle of range)
        threshold = (np.max(vsum) - np.min(vsum)) / 2 
    
        search = True #is loop if looking for a peak
        segments = [] #peaks collapsed to line segments
    
        #scans through vsum to find peaks
        colsums = enumerate(vsum)

        for col, csum in colsums :
            if csum > threshold : # we found a column over threshold
                peaksum = csum
                peakstart = col
                for col, csum in colsums : # continue iterating over the columns...
                    if csum > threshold :
                        peaksum += csum
                    else : # we have fallen below threshold again. peak has been found.
                        peakend = col - 1
                        # each segment is the TOTAL sum in the peak, plus the start and end pixel
                        segments.append((peaksum, (peakstart, peakend)))
                        break
                
        # we will VERY often get more than 2.. camera might see 6!!
        # find two peaks next to each other of sensible separation and strength.
        # we want the two strongest ones.
        if len(segments) > 2 :  # if we DO get more than 2
            sums = [seg[0] for seg in segments] # just look at their strengths.
            strongest = max(sums) 
            if sums[0] == strongest :
                segments = segments[:2]
            elif sums[-1] == strongest :
                segments = segments[-2:]
            else :
                ix = sums.index(strongest)
                if sums[ix + 1] > sums[ix - 1] :
                    segments = segments[ix : ix + 2]
                else :
                    segments = segments[ix - 1 : ix + 1]
        # actually, we pick the strongest peak
        # and its strongest neighbor.
        if len(segments) == 2 :
            peaks = [sum(s[1])/2 for s in segments]

            #distance from the center of the image tot the center of the target, in pixels
            offsetX = sum(peaks)/2 - WIDTH/2
        
            #gap in pixels between the center of two hills
            gap = peaks[1] - peaks[0]
            # We can do a sanity check on the gap, too.
     
            hsum = np.sum(mono_diff[..., peaks[0] : peaks[1]], axis=1) #horizontal sum
        
            state = 0 #state of the hsum scanner
            hmax = np.max(hsum)
            thresholds = (hmax/10, hmax/2) #thresholds 
            points = [] #[v-bars, h-bar, bottom]

            for i, v in enumerate(hsum):
                #above target
                if state == 0:
                    if v > thresholds[0]:
                        state = 1
                        points.append(i)
    

                #vertical bars
                elif state == 1:
                    if v > thresholds[1]:
                        state = 2
                        points.append(i)

                    elif v < thresholds[0]:
                        state = 0
                        points.pop()

                #horizontal bar
                elif state == 2:
                    if v < thresholds[0]:           
                        points.append(i)
                        break

            if len(points) == 3:
                #distance from the bottom of the view to the bottom of the target
                offsetY = HEIGHT - (points[2] + points[1])/2
                self.display(True)
            else:
                if self.verbose :
                    print("ERROR: " + str(len(points)) + " hsum points instead of 3?")
                self.display(False)
        else:
            if self.verbose :
                print("ERROR: found " + str(len(segments)) + " vsum segments (vertical bars). Expected 2.")
            self.display(False)

        
    def display(self, found):
        disp_img = sig.copy()
    
        if(found):
            cv2.line(disp_img,(WIDTH/2 + offsetX,0),(WIDTH/2 + offsetX,HEIGHT),(0,0,255),3)
            cv2.line(disp_img,(0,HEIGHT - offsetY),(WIDTH, HEIGHT - offsetY),(0,0,255),3)
        else:
            cv2.putText(disp_img, "?", (WIDTH/3, HEIGHT/3), cv2.FONT_HERSHEY_PLAIN, 4, (0,0,255),4)    
    
        cv2.imshow("display",disp_img)

vt = VideoThread()
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
