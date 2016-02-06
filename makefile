XENO ?= /usr/xenomai
XENOCONFIG=$(shell PATH=$(XENO):$(XENO)/bin:$(PATH) which xeno-config 2>/dev/null)

CC=$(shell $(XENOCONFIG) --cc)

EXTRA_CFLAGS := $(shell $(XENOCONFIG) --skin=native --cflags)

CFLAGS= -O3 -Ofast -g3 -Wall -Wno-strict-aliasing -c -save-temps -fmessage-length=0 -march=armv7-a -mtune=cortex-a8 -mfpu=neon -ftree-vectorize -ftree-vectorizer-verbose=1 -mfloat-abi=hard -ffast-math $(EXTRA_CFLAGS) -I.

LDLIBS=$(shell $(XENOCONFIG) --skin=native --ldflags)
LDFLAGS= $(MY_LDFLAGS) -lpython2.7 -lv4l2 $(LDLIBS)
SOURCES=stronghold.c

OBJECTS=$(SOURCES:.c=.o)
EXECUTABLE=stronghold
# Python files created from .h files
# compiled python files created from python files.
# not sure all depends on sources?
# also the dtbo and zip may belong elsewhere.
all: $(EXECUTABLE) stronghold.py

.SUFFIXES: .py .pyc .asm .h .xml

.h.xml: 
	h2xml -I . $< -D BEAGLEBONE -D _dsp -D H2XML -c -o $@ 

.xml.py:
	xml2py $< -o $@ 

$(EXECUTABLE): $(OBJECTS) 
	$(CC) $(LDFLAGS) $(OBJECTS) -o $@

.asm.o:
	as -march=armv7-a -mfpu=neon $< -g -o $@

.c.o:
	$(CC) $(CFLAGS) $< -g -o $@

.cpp.o:
	$(CC) $(CFLAGS) $< -g -o $@

