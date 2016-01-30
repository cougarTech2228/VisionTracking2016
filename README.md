robotics
========

Python code for FIRST Robotics

* catapult.py 
    Design code from Aerial Assist, 2014. We were looking at optimal gearing for a direct-drive catapult. 
    Simulation of voltage and current vs time.

* initcv.py
    Using a logitech C270 webcam for vision processing on a beaglebone black using python-opencv.
    Game is Stronghold, 2016. This file is run once upon boot to configure opencv nicer.
    python-opencv is missing a few things..  might need to call some C code directly

* testcv.py 
    trying to synchronize turning an LED on and off using a multithreaded approach.
    varying the delay in the LED thread yields unexpected results sometimes.
    The issue is that there are buffered video frames in the stream, and you have to
    pull them from the stream as fast as you can to get the most recent video.


