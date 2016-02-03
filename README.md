robotics
========

Python code for FIRST Robotics

* initcv.py
    Using a logitech C270 webcam for vision processing on a beaglebone black using python-opencv.
    Game is Stronghold, 2016. This file is run once upon boot to configure opencv nicer.
    We thought it was necessary, but it seems to run okay without it sometimes.
    python-opencv is missing a few things..  might need to call some C code directly

* vision.py 
    Synchronizes turning an LED on and off using a multithreaded approach.
    The instance of AcquireThread (at) is responsible for grabbing the images
    and processing them. It runs as fast as it can to keep the buffer empty.
    LedThread's instance (lt) waits until the Acquisition Thread tells it that it just 
    acquired a pair. Then, it delays, turns on the LED,  delays some more, and turns it off.
    the led thread also measures the actual times of the sleep calls.
    Some sort of realtime performance on both of these threads would be helpful.
    It can be run at the command line with "sudo python -i vision.py". While in the
    interpreter, you can look at the attributes of both threads.
    show(at.idiff) will put the difference image in a matplotlib window.
    at.sig and at.back show the signal and background images (led on and led off respectively)
    at.fps keeps the average frames per second. If you plot(at.rsum) or plot(at.csum) you can check
    out the row sum function and the column sum function.

