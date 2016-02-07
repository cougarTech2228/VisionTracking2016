#!/usr/bin/python

from pylab import plot, imshow as show, ion
import cPickle as pickle, numpy as np

ion()

with open("diff.np", "r") as f:
	diff = pickle.load(f)

print("code start")

mono_diff = np.sum(diff, axis=2)
vsum = np.sum(mono_diff, axis=0)
hsum = np.sum(mono_diff, axis=1)

#hv = [v for v in range(len(vsum)) if vsum[v] > not_median]

#constant to filter peaks in vsum (middle of range)
threshold = (np.max(vsum) - np.min(vsum)) / 2 

search = True #is loop if looking for a peak
segments = [] #peaks collapsed to line segments

#scans through vsum to find peaks
for i, v in enumerate(vsum):
	if search:
		if v>threshold:
			search=False
			segments.append(i)
	else:
		if v<threshold:
			search= True
			segments[-1] = (segments[-1],i)

print("segments: " + str(segments)) 

if len(segments) == 2:
	p0 = (segments[0][0] + segments[0][1])/2 #middle of first hill
	p1 = (segments[1][0] + segments[1][1])/2 #middle of second hill

    #distance from the center of the image tot the center of the target, in pixels
	offset = (p0 + p1)/2 - 180 
   	
    #gap in pixels between the center of two hills
    gap = abs(p0 - p1)

	print(str(offset) + " " + str(gap))

else:
	print("ERROR: found " + str(len(segments)) + " segments. Expected 2.")
	
