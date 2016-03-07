
import os, sys
sys.path.append(os.getcwd())
import numpy as np
from ctypes import c_ubyte
from collections import namedtuple
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
		self.verbose = False	#print log messages to the console
		self.show = Struct(	#object containing all image display flags
			sig= False,		#display signal image
			back= False,		#display back image
			diff= Struct(		
				r= False,	#display rdiff
				g= False,	#display gdiff
				b= False,	#display bdiff
				sum= False 	#display diff
				),
			mono= False,		#display mono_diff
			found= False)		#display crosshairs
		self.last_logged = ""	#the last thing logged by Utils.log

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
	
		if(found):
			offX = int(vt.target.offsetX)
			offY = int(vt.target.offsetY)
			cv2.line(disp_img,(WIDTH/2 + offX,0),(WIDTH/2 + offX,HEIGHT),(0,0,255),3)
			cv2.line(disp_img,(0, HEIGHT/2 +offY),(WIDTH, HEIGHT/2 + offY),(0,0,255),3)
		else:
			cv2.putText(disp_img, code, (WIDTH/3, HEIGHT/3), cv2.FONT_HERSHEY_PLAIN, 4, (0,0,255),4)    
	
		cv2.imshow("found",disp_img)

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

class VideoThread(threading.Thread):
	#main thread for image processing
	def __init__(self):
		threading.Thread.__init__(self)
		self.daemon = True	#not sure what this does
		self.halt = False	#set to true to kill thread

		self.Segment = namedtuple("Segment", ["start","end","center","area"])	
		self.Target = namedtuple("Target", ["offsetX", "offsetY", "width", "v_threshold", "h_threshold", "segments", "index"])
		sd.putBoolean(keys.KEY_VISION, False)
		
		self.MIN_VERT_THRESH = 1500 #minimum threshold for finding the vertical bars

	def run(self):
		#starts the image processing loop
		#kills the thread when self.halt is set to true
		while not self.halt:
			#get enabled flag from net tables and update c variable
			vc.led_enabled = sd.getBoolean(keys.KEY_VISION)
			if vc.led_enabled :
				#if net tables tells us to process the process
				self.process()
	
	def process(self):
		#processes images aquired by the c code
		diff = cv2.subtract(sig, back) # could do the diff in C code.
		bdiff, gdiff, rdiff = [diff[:,:,i] for i in range(3)]
		
		#subtract the rdifff from the gdiff to get rid of motion artifacts
		mono_diff = cv2.subtract(gdiff, rdiff) 

		self.vsum = vsum = np.sum(mono_diff, axis=0)
		v_threshold = (np.max(vsum) + np.min(vsum)) / 2 
		if v_threshold < self.MIN_VERT_THRESH:
			v_threshold = self.MIN_VERT_THRESH

		search = True 
		segments = []

		for x, value  in enumerate(vsum) :
			if value > v_threshold and search: 
				start = x
				area = value
				search = False
			if value > v_threshold and not search:
				area += value
			if value < v_threshold and not search:
				end = x-1
				segments.append(self.Segment(start, end, (start+end)/2, area))
				search = True

		if len(segments) < 2:
			self.result(False,"=| Not Enough Segments. {0} Segments.".format(len(segments)))
		elif len(segments) > 6:
			self.result(False,"=| Too Many Segments. {0} Segments.".format(len(segments)))
		else:
			targets = []
			for index, segment in enumerate(segments):
				if index == len(segments) - 1: break

				seg1= segments[index]
				seg2= segments[index+1]

				offsetX = (seg1.center + seg2.center)/2 - WIDTH/2

				hsum = np.sum(mono_diff[:, seg1.end : seg2.start], axis=1) 
				width = abs(seg1.center - seg2.center)

				search = True 
				hmax = np.max(hsum)

				h_threshold = hmax * .8
				for y, value in enumerate(hsum) :
					if value > h_threshold and search:
						start = y
						search = False
					if value < h_threshold and not search:
						end = y
						offsetY = (float(start + end)-HEIGHT)/2
						targets.append(self.Target(offsetX, offsetY, width, v_threshold, h_threshold, (seg1, seg2), len(targets)))
						break

			if len(targets) < 1:
				self.result(False,"=| Found 0 Targets. Found {0} Segments.".format(len(segments)))
			else:
				selected = targets[0]			
				for target in targets:
					if target.width > selected.width:
						select = target
				self.target = selected
				self.result(True,"8) Selected Target: {0}/{1}".format(self.target.index, len(targets)))

		utils.update(sig, back, diff, rdiff, gdiff, bdiff, mono_diff)
		
	def result(self, found, message="", code="?"):
		self.found = found			
		utils.display(self.found,code)
		utils.log(message)
		if found:
			sd.putNumber(keys.KEY_X, self.target.offsetX)
			sd.putNumber(keys.KEY_Y, self.target.offsetY)
			sd.putBoolean(keys.KEY_FOUND, True)
		else:
			sd.putBoolean(keys.KEY_FOUND, False)

utils = Utils()
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
if _ct :
	import code
	code.interact(local=locals())

