import os
os.system("sudo rmmod uvcvideo")
os.system("sudo modprobe uvcvideo nodrop=1 timeout=5000 quirks=0x80")
