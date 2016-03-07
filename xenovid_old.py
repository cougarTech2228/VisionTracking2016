
import os, sys
sys.path.append(os.getcwd())
import numpy as np
from ctypes import c_ubyte
import copy
from py import keys

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

vc.on_time = 1250000 # units are nanoseconds. 
vc.led_enabled = False
# frame time is 30 milliseconds, so make it smaller than that.

import cv2, threading
import cPickle as pickle
from pylab import plot, ion
ion()
from cv2 import cv
from time import time
from networktables import NetworkTable
NetworkTable.setIPAddress("roboRIO-2228-FRC.local")
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
		sd.putNumber(keys.KEY_NPIX, 0)
		self.picstotake = 0
		self.dumpfile = open("diffs.np","a")
		self.sigsfile = open("sigs.np","a")
		self.backsfile = open("backs.np","a")

	def reopen(self) :
		if self.dumpfile.closed :
			self.dumpfile = open("diffs.np","a")
		if self.sigsfile.closed :
			self.sigsfile = open("sigs.np","a")
		if self.backsfile.closed :
			self.backsfile = open("backs.np","a")

	def run(self):
		while True :
		  vc.led_enabled = sd.getBoolean(keys.KEY_VISION)
		  if not self.picstotake :
			self.picstotake = sd.getNumber(keys.KEY_NPIX)
			sd.putNumber(keys.KEY_NPIX, 0)
		  if vc.led_enabled :
			self.process()     
			if self.picstotake :
				self.reopen()
				pickle.dump(self.diff, self.dumpfile)
				pickle.dump(sig, self.sigsfile)
				pickle.dump(back, self.backsfile)
				self.picstotake -= 1
				#if not self.picstotake :
					#self.flush_close()

			# only used when running offline with display
			if self.showsig :
				cv2.imshow("sig", sig)
			if self.showback :
				cv2.imshow("back", back)
			if self.showdiff :
				cv2.imshow("diff", self.diff) 
			
			if self.watch_keys :
				global ix
				key = cv2.waitKey(20)
				if key == -1:
					continue
				if key == ord('n') :
					ix += 1
					if ix == len(sigs) : 
						ix = 0
					sig[:,:,:] = sigs[ix]
					back[:,:,:] = backs[ix]
				elif key == ord('b') :
					if ix == 0 :
						ix = len(sigs) 
					ix -= 1
					sig[:,:,:] = sigs[ix]
					back[:,:,:] = backs[ix]
				elif key == ord('s') or key == ord('S'):
					with open("diff.np", "w") as f:
						pickle.dump(self.diff, f)
					with open("sig.np", "w") as f:
						pickle.dump(sig, f)
					with open("back.np", "w") as f:
						pickle.dump(back, f)
					continue
			else :
				cv2.waitKey(1) # needed to do any display!
		  else :
			  # if not doing vision:
			  self.flush_close()

	def flush_close(self) :
		if not self.dumpfile.closed :
			self.dumpfile.flush()
			self.dumpfile.close()
		if not self.sigsfile.closed :
			self.sigsfile.flush()
			self.sigsfile.close()
		if not self.backsfile.closed :
			self.backsfile.flush()
			self.backsfile.close()

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
				# start accumulating 
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

		# XXX Now we have some candidate columns that we think may be targets.
		# How do we rule them out?
		# start a new empty list of "good segments"
		# for each segment just found:
			# we can look up and down the center column of the segment.
			# it should have a single stretch that goes uniformly higher than the rest.
			# find the start row and stop row of this stretch.
			# segments that don't seem right? don't waste more time on them.
			# if we didn't flag that segment as bad yet...
			# look to the right and left of the lower end of the stretch we found above.
			# find the horizontal bar that could connect the bottom of that vertical stretch
			# to a neigboring peak to the right or to the left. How high is the horizontal
			# bar where it leaves the bottom of the upright?
			# (don't worry about tracing it all the way, just find that the 
			# horizontal bar exists on one side or the other of the bottom.
			# We made it to here? append this peak to our list of good segments..
			# remembering:
				# which direction the bar exited at the bottom
				# how high the bar was when it exited.
				# how long the stretch was
				# etc etc

		# XXX this needs improvement.
		# we will VERY often get more than 2 peaks. camera might see 6!!
		# XXX Dr Moore's not-so-smart algorithm was..
		# find two peaks next to each other of sensible separation and strength.
		# we want the two strongest ones?
		# actually, we pick the strongest peak
		# and its strongest neighbor.

		# but...
		# after implementing the above code that builds a good segment list,
		# we have an improved list and more information.
		# We want to find neighboring peaks where the 
		# horizontal bars point at each other.
		# if there is only one pair of adjacent peaks that looks like this.. great.
		# if we see two or three pairs of neighboring peaks that pass this test..
		# we want to return the pair that has the greatest separation between segments.
		# also, if we can return the ANGLE of the horizontal bar that would be good.
		# the angle could simply be height difference divided by separation.
		

		if len(segments) < 2:
			self.display(False)
			if self.verbose :
				print("Not Enough Segments!")
			sd.putBoolean(keys.KEY_FOUND, False)
			return
		elif len(segments) > 6:
			self.display(False)
			if self.verbose :
				print("Too many Segments!")
			sd.putBoolean(keys.KEY_FOUND, False)
			return
		else:
			self.targets = []
			for index, segment in enumerate(segments):

				if index == len(segments) - 1: break
				seg1= segment
				seg2= segments[index+1]

				offsetX = (seg1[2] + seg2[2])/2 - WIDTH/2
				self.hsum = np.sum(mono_diff[:, seg1[1][1] : seg2[1][0]], axis=1) #horizontal sum
				#gap in pixels between the center of two hills
				gap = abs(seg1[2] - seg2[2])

				state = 0 #state of the hsum scanner
				hmax = np.max(self.hsum)

				rowsums = enumerate(self.hsum)
				thresh = hmax * .8
				in_hill = False
				for row, rsum in enumerate(self.hsum) :
					if rsum > thresh and not in_hill:
						start = row
						in_hill = True
					if rsum < thresh and in_hill:
						end = row
						offsetY = (float(start + end)-HEIGHT)/2
						self.targets.append((offsetX, offsetY, gap, hmax, seg1, seg2))
						break

			if len(self.targets) < 1:
				self.display(False)
				if self.verbose :
					print("No Targets.Missed horizontal bar!")
				sd.putBoolean(keys.KEY_FOUND, False)
			else:
				self.target = self.targets[0]			
				for target in self.targets:
					#compare gaps
					if target[2] > self.target[2]:
						self.target = target
				
				if self.verbose :
					print("found x y", self.offsetX, self.offsetY )
					sd.putNumber(keys.KEY_X, self.target[0])
					sd.putNumber(keys.KEY_Y, self.target[1])
					sd.putBoolean(keys.KEY_FOUND, True)
				self.display(True)

		
	def display(self, found):
		if not self.showfound :
			return
		disp_img = sig.copy()
	
		if(found):
			offX = int(self.target[0])
			offY = int(self.target[1])
			cv2.line(disp_img,(WIDTH/2 + offX,0),(WIDTH/2 + offX,HEIGHT),(0,0,255),3)
			cv2.line(disp_img,(0, HEIGHT/2 +offY),(WIDTH, HEIGHT/2 + offY),(0,0,255),3)
		else:
			cv2.putText(disp_img, "?", (WIDTH/3, HEIGHT/3), cv2.FONT_HERSHEY_PLAIN, 4, (0,0,255),4)    
	
		cv2.imshow("display",disp_img)

vt = VideoThread()


def allimgs_from(filename) :
	f = open(filename)
	imgs = []
	while True :
		try :
			imgs.append(pickle.load(f))
		except :
			break
	return imgs

if _ct == None :
	vt.showfound = True
	vt.showdiff = True
	vt.showback = True
	vt.watch_keys = True
	sd.putBoolean(keys.KEY_VISION, True)
	import pickle
	ix = 0
	sigs = allimgs_from(testdat+"sigs.np")
	backs = allimgs_from(testdat+"backs.np")
	sig[:,:,:]=sigs[ix]
	back[:,:,:] = backs[ix]
  

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
if _ct :
	import code
	code.interact(local=locals())

