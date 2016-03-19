
import os, sys
sys.path.append(os.getcwd())
import numpy as np
from ctypes import c_ubyte
from collections import namedtuple
import copy
from py import keys
import socket
from time import sleep

from stronghold import WIDTH, HEIGHT, vidconf_s
Image=(((c_ubyte*3)*WIDTH)*HEIGHT)
from numpy.ctypeslib import as_array

try :
        # are we running embedded?
        import _ct # cougar tech C threads
        a,b,vid_conf_addr = _ct.addrs()
        vc = vidconf_s.from_address(vid_conf_addr)
        ia = Image.from_address(a)
        ib = Image.from_address(b)
except ImportError :
        # we are running with no c code running the camera
        _ct = None
        vc = vidconf_s()
        ia = Image()
        ib = Image()
        import sys
        if len(sys.argv) == 2 :
                testdat = sys.argv[1]
        else :
                testdat = "./testdata/rally1/"

sig = as_array(ia)
back = as_array(ib)

vc.on_time = 1250000 * 8 # units are nanoseconds. 
vc.led_enabled = False
# frame time is 30 milliseconds, so make it smaller than that.

import cv2, threading
import cPickle as pickle
from pylab import plot, ion
ion()
from cv2 import cv
from time import time
from networktables import NetworkTable
try:
        NetworkTable.setIPAddress("roboRIO-2228-FRC.local")
        NetworkTable.setClientMode()
        NetworkTable.initialize()
except:
        print("ERROR in creating network tables: " + str(sys.exc_info()[0]))

sd = NetworkTable.getTable("SmartDashboard")

class Struct:
        #useful one liner for creating struct like variables
        #see declaration of Utils.show
        def __init__(self, **entries): self.__dict__.update(entries)

class Utils:
        #class containing various extrenuous functions
        #including those for displaying images
        def __init__(self):
                self.verbose = False    #print log messages to the console
                self.show = Struct(     #object containing all image display flags
                        sig= False,             #display signal image
                        back= False,            #display back image
                        diff= Struct(           
                                r= False,       #display rdiff
                                g= False,       #display gdiff
                                b= False,       #display bdiff
                                sum= False      #display diff
                                ),
                        mono= False,            #display mono_diff
                        found= False)           #display crosshairs
                self.last_logged = ""   #the last thing logged by Utils.log
                self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM) #socket client for remote viewer
                self.disp_img = None    #last image shown by the display function

        def enable(self):
                #enable the leds
                sd.putBoolean(keys.KEY_VISION, True)

        def disable(self):
                #disable the leds
                sd.putBoolean(keys.KEY_VISION, False)

        def reload(self, hard=False):
                #this is supposed to halt this file and re-exec it
                #TODO fix this code
                vt.halt = True
                execfile("xenovid.py")

        def display(self, found, code=""):
                #displays the current camera feed with 
                #with crosshairs if the target is found
                #and string <code> if it is not
                if not self.show.found : return
                
                disp_img = sig.copy()
                for s in vt.segments:
                    cv2.line(disp_img,(s.center,0),(s.center,HEIGHT),(0,255,255),2)
        
                if(found):
                        offX = int(vt.target.offsetX)
                        offY = int(vt.target.offsetY)
                        cv2.line(disp_img,(WIDTH/2 + offX,0),(WIDTH/2 + offX,HEIGHT),(0,0,255),4)
                        cv2.line(disp_img,(0, HEIGHT/2 +offY),(WIDTH, HEIGHT/2 + offY),(0,0,255),4)
                else:
                        cv2.putText(disp_img, code, (WIDTH/2-10, HEIGHT/2-10), cv2.FONT_HERSHEY_PLAIN, 4, (0,0,255),4)    
                
                self.imshow(disp_img)
                self.disp_img = disp_img

        def imshow(self, img):
            #shows an image, meant for configuration
            cv2.imshow("found",img) 

        def update(self, sig, back, diff, r,g,b,mono):
                #updates all the displays
                #called by vt.process()
                if sig is not None and self.show.sig:
                        cv2.imshow("sig",sig)
                if back is not None and self.show.back:
                        cv2.imshow("back",back)
                if diff is not None and self.show.diff.sum:
                        cv2.imshow("diff",diff)
                if r is not None and self.show.diff.r:
                        cv2.imshow("rdiff",r)
                if g is not None and self.show.diff.g:
                        cv2.imshow("gdiff",g)
                if b is not None and self.show.diff.b:
                        cv2.imshow("bdiff",b)
                if mono is not None and self.show.mono:
                        cv2.imshow("mono",mono)

        def log(self, message):
                #logs a message, unless that message was the last on logged
                #enabled/disabled by self.verbose
                if self.verbose and self.last_logged != message: 
                        print(message)
                        self.last_logged = message

        def connect(self):
                self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.sock.connect(("192.168.7.1", 50007))
        
        def send_img(self,img) :
                icop = np.array(img, dtype=np.uint8)
                l, w = icop.shape
                text = icop.tostring()
                text = text + '<HEAD>{0}#{1}'.format(l,w)
                self.sock.sendall(text)
                self.sock.sendall(b"<ENDMSG>")
         
        def feed(self,delay):
                while True:
                        sleep(delay)
                        try:
                                self.send_img(self.disp_img[:,:,0])
                        except:
                                print("no connection")
                                try:
                                        self.connect()
                                except:
                                        sleep(1)
                                
class VideoThread(threading.Thread):
        #main thread for image processing
        def __init__(self):
                threading.Thread.__init__(self)
                self.daemon = True      #not sure what this does
                self.halt = False       #set to true to kill thread

                self.Segment = namedtuple("Segment", ["start","end","center","area"])   
                self.Target = namedtuple("Target", ["offsetX", "offsetY", "width", "v_threshold", "h_threshold", "segments", "index"])
                sd.putBoolean(keys.KEY_VISION, False)
                
                self.MIN_VERT_THRESH = 1500 #minimum threshold for finding the vertical bars
                self.SMOOTH_FACTOR = 2 #amount that vsum is smoothed
                
                self.targets= []
                self.segments=[]

        def run(self):
                #starts the image processing loop
                #kills the thread when self.halt is set to true
                while not self.halt:
                        #get enabled flag from net tables and update c variable
                        vc.led_enabled = sd.getBoolean(keys.KEY_VISION)
                        if vc.led_enabled :
                                #if net tables tells us to process the process
                                self.process()
				cv2.waitKey(10)
        def process(self):
                self.sig = sig[:,:,1] #test variable, remove 

                #processes images aquired by the c code
                diff = cv2.subtract(sig, back) # could do the diff in C code.
                bdiff, gdiff, rdiff = [diff[:,:,i] for i in range(3)]
                
                #subtract the rdifff from the gdiff to get rid of motion artifacts
                self.mono = mono_diff = cv2.subtract(gdiff, rdiff) 
                
                #verticaly sum the mono_diff, then find and appropriate threshold for locating peaks
                self.vsum = vsum = np.sum(mono_diff, axis=0)**2
                self.vsum = vsum = np.roll(vsum, self.SMOOTH_FACTOR) + np.roll(vsum, -self.SMOOTH_FACTOR) + vsum
                v_threshold = (np.max(vsum) + np.min(vsum)) * .5 
                if v_threshold < self.MIN_VERT_THRESH:
                        v_threshold = self.MIN_VERT_THRESH

                search = True   #is the scanner looking for a peak (True), or the end of a peak (False)
                segments = []   #list of self.Segment objects representing peaks in the vsum
                
                for x, value  in enumerate(vsum) :
                        if value > v_threshold and search: 
                                #if start of a peak
                                start = x
                                area = value
                                search = False
                        if value > v_threshold and not search:
                                #if inside of a peak
                                area += value
                        if value < v_threshold and not search:
                                #if end of a peak
                                end = x-1
                                segments.append(self.Segment(start, end, (start+end)/2, area))
                                search = True

                targets = []

                #we have now found all the vertical bars (peaks/segments), time to look for targets
                if len(segments) < 2:
                        #we need at least 2 segments
                        self.result(False,"=| Not Enough Segments. {0} Segments.".format(len(segments)))
                elif len(segments) > 6:
                        #we should never find more then 6
                        self.result(False,"=| Too Many Segments. {0} Segments.".format(len(segments)))
                else:   
                        #iterate through each segment, and check for a target between it and a neighboring segment
                        for index, segment in enumerate(segments):
                                if index == len(segments) - 1: break 

                                seg1= segments[index]
                                seg2= segments[index+1]

                                #distance in pixels between center of camera view and center of target
                                offsetX = (seg1.center + seg2.center)/2 - WIDTH/2 

                                #horizontally sum the mono_diff between the two segments
                                hsum = np.sum(mono_diff[:, seg1.end : seg2.start], axis=1) 
                                width = abs(seg1.center - seg2.center)

                                search = True           #is the scanner looking for a peak (True), or the end of a peak (False)
                                hmax = np.max(hsum)     #maximum hsum value
                                h_threshold = hmax * .5 #threshold for finding horizontal bar
                                
                                for y, value in enumerate(hsum) :
                                        if value > h_threshold and search:
                                                #if start of peak
                                                start = y
                                                search = False
                                        if value < h_threshold and not search:
                                                #if end of peak
                                                end = y
                                                offsetY = (float(start + end)-HEIGHT)/2
                                                targets.append(self.Target(offsetX, offsetY, width, v_threshold, h_threshold, (seg1, seg2), len(targets)))
                                                break
                                        
                        if len(targets) < 1:
                                #hopefully we found at least one target, if not, log a noah face
                                self.result(False,"=| Found 0 Targets. Found {0} Segments.".format(len(segments)))
                        else:
                                #if we found at least one target, find the one which is the widest
                                #since all the targets are the same size/distance from the camera
                                #this will give us the target which is most perpendicular to the robot
                                #aka. the one which is easiest to shoot at
                                selected = targets[0]                   
                                for target in targets:
                                        if target.width > selected.width:
                                                select = target
                                self.target = selected
                                self.result(True,"8) Selected Target: {0}/{1}".format(self.target.index, len(targets)))

                #update the displays for debuging
                utils.update(sig, back, diff, rdiff, gdiff, bdiff, mono_diff)
                self.targets = targets
                self.segments = segments
                
        def result(self, found, message="", code="?"):
                #updates display (crosshairs), console log, and net tables after vt.process anylises a frame
                self.found = found              
                utils.display(self.found,code)
                utils.log(message)
                if found:
                        #push the offsets to net tables and let the robo-rio know that you have found the target
                        sd.putNumber(keys.KEY_X, self.target.offsetX)
                        sd.putNumber(keys.KEY_Y, self.target.offsetY)
                        sd.putBoolean(keys.KEY_FOUND, True)
                else:
                        #update net tables so the robo-rio knows that we cant see the target
                        sd.putBoolean(keys.KEY_FOUND, False)

utils = Utils()
vt = VideoThread()
vt.start()



#process an image   
if _ct :
        import code
        code.interact(local=locals())

