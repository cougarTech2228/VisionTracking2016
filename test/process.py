#!/usr/bin/python

from pylab import plot, imshow as show, ion, axvline as vline, axhline as hline
import cPickle as pickle, numpy as np

WIDTH = 320
HEIGHT = 240

ion()

with open("diff.np", "r") as f:
	diff = pickle.load(f)

print("code start")

mono_diff = np.sum(diff, axis=2) 
vsum = np.sum(mono_diff, axis=0)

#constant to filter peaks in vsum (middle of range)
threshold = (np.max(vsum) - np.min(vsum)) / 2 

search = True #is loop if looking for a peak
segments = [] #peaks collapsed to line segments

#scans through vsum to find peaks
for i, v in enumerate(vsum):
	if search:
		if v>threshold:
			search=False
			tmp_point = i
	else:
		if v<threshold:
			search= True
			segments[-1] = (tmp_point,i)

print("segments: " + str(segments)) 

if len(segments) == 2:
	p0 = (segments[0][0] + segments[0][1])/2 #middle of first hill
	p1 = (segments[1][0] + segments[1][1])/2 #middle of second hill

	#distance from the center of the image tot the center of the target, in pixels
	offsetX = (p0 + p1)/2 - WIDTH/2
   	
	#gap in pixels between the center of two hills
	gap = abs(p0 - p1)
 
	hsum = np.sum(mono_diff[..., segments[0][0] : segments[1][1]], axis=1) #horizontal sum
	
   
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

	print("points: " + str(points))  

	if len(points) == 3:
		#distance from the bottom of the view to the bottom of the target
		offsetY = HEIGHT - (points[2] + points[1])/2
		
		print("offsetX: %d offsetY: %d" % (offsetX, offsetY))
		show(diff)
		vline(offsetX + WIDTH/2)
		hline(HEIGHT - offsetY)
		
	else:
		print("ERROR: " + str(len(points)) + " hsum points instead of 3?")
		

else:
	print("ERROR: found " + str(len(segments)) + " vsum segments (vertical bars). Expected 2.")
	


