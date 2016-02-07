from ctypes import *



class vidconf_s(Structure):
    pass
vidconf_s._fields_ = [
    ('on_time', c_uint),
    ('sleep_time', c_uint),
    ('invert', c_int),
    ('led_enabled', c_int),
    ('threshold', c_double),
    ('fps', c_float),
]
WIDTH = 320 # Variable c_int '320'
_dsp = 1 # Variable c_int '1'
H2XML = 1 # Variable c_int '1'
BEAGLEBONE = 1 # Variable c_int '1'
HEIGHT = 240 # Variable c_int '240'
__all__ = ['vidconf_s', 'BEAGLEBONE', 'HEIGHT', 'WIDTH', 'H2XML',
           '_dsp']
