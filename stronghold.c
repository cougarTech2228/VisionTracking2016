/* V4L2 video picture grabber
   Copyright (C) 2009 Mauro Carvalho Chehab <mchehab@infradead.org>

   This program is free software; you can redistribute it and/or modify
   it under the terms of the GNU General Public License as published by
   the Free Software Foundation version 2 of the License.

   This program is distributed in the hope that it will be useful,
   but WITHOUT ANY WARRANTY; without even the implied warranty of
   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
   GNU General Public License for more details.

   Modified by Derek Molloy (www.derekmolloy.ie)
   Modified to change resolution details and set paths for the Beaglebone.

gcc -O2 -Wall `pkg-config --cflags --libs libv4l2` -lpython27 stronghold.c -o stronghold 

 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <fcntl.h>
#include <errno.h>
#include <sys/ioctl.h>
#include <sys/types.h>
#include <sys/time.h>
#include <sys/mman.h>
#include <linux/videodev2.h>
#include <libv4l2.h>
#include <python2.7/Python.h>
#include <native/task.h>
#include <native/timer.h>
#include <native/mutex.h>

#define CLEAR(x) memset(&(x), 0, sizeof(x))

struct buffer {
        void   *start;
        size_t length;
};

static void xioctl(int fh, int request, void *arg)
{
        int r;

        do {
                r = v4l2_ioctl(fh, request, arg);
        } while (r == -1 && ((errno == EINTR) || (errno == EAGAIN)));

        if (r == -1) {
                fprintf(stderr, "error %d, %s\n", errno, strerror(errno));
                exit(EXIT_FAILURE);
        }
}

void embedpy();
#define WIDTH 160
#define HEIGHT 120
// #define FORMAT V4L2_PIX_FMT_RGB24 
// RGB24 is the original format
#define FORMAT V4L2_PIX_FMT_YUYV
#define NPIX 40

RT_MUTEX timerlock;
RT_TASK ticker_task;
RT_TASK other_task;

RTIME now;
// acquire thread
void ticker(void *arg)
{
    rt_task_set_periodic(NULL, TM_NOW, 341000);

    while (1) {
        rt_task_wait_period(NULL);
        now = rt_timer_read();
        rt_mutex_acquire(&timerlock, TM_INFINITE);
        rt_mutex_release(&timerlock);
    }
}


// led thread
void other(void *arg)
{
    rt_task_set_periodic(NULL, TM_NOW, 341000);

    while (1) {
        rt_task_wait_period(NULL);
        now = rt_timer_read();
        rt_mutex_acquire(&timerlock, TM_INFINITE);
        rt_mutex_release(&timerlock);
    }
}

static PyObject *acquire_callback = NULL;
static PyObject *led_callback = NULL;

static PyObject *
dsp_acquire_cb(PyObject *dummy, PyObject *args)
{
    // PyObject *result = NULL;
    PyObject *temp;
    if (PyArg_ParseTuple(args, "O:scancallback", &temp)) {
        if (!PyCallable_Check(temp)) {
			if(temp == Py_None) // None passed in? ok.
			{
		        Py_XDECREF(acquire_callback);  /* Dispose of previous callback */
				acquire_callback = NULL;
		        Py_INCREF(temp);
				return(temp);
			}
			//        PyErr_SetString(PyExc_TypeError, "parameter must be callable");
			//	return PyErr_Format(PyExc_TypeError,"parameter must be callable");
			return NULL;
        }
        Py_XINCREF(temp);         /* Add a reference to new callback */
        Py_XDECREF(acquire_callback);  /* Dispose of previous callback */
        acquire_callback = temp;       /* Remember new callback */
        /* Boilerplate to return "None" */
        return Py_BuildValue("");
    }
    return NULL;
}

static PyObject *
dsp_led_cb(PyObject *dummy, PyObject *args)
{
    // PyObject *result = NULL;
    PyObject *temp;
    if (PyArg_ParseTuple(args, "O:scancallback", &temp)) {
        if (!PyCallable_Check(temp)) {
			if(temp == Py_None) // None passed in? ok.
			{
		        Py_XDECREF(led_callback);  /* Dispose of previous callback */
				led_callback = NULL;
		        Py_INCREF(temp);
				return(temp);
			}
			//        PyErr_SetString(PyExc_TypeError, "parameter must be callable");
			//	return PyErr_Format(PyExc_TypeError,"parameter must be callable");
			return NULL;
        }
        Py_XINCREF(temp);         /* Add a reference to new callback */
        Py_XDECREF(led_callback);  /* Dispose of previous callback */
        led_callback = temp;       /* Remember new callback */
        /* Boilerplate to return "None" */
        return Py_BuildValue("");
    }
    return NULL;
}

int main(int argc, char **argv)
{
        struct v4l2_format              fmt;
        struct v4l2_buffer              buf;
        struct v4l2_requestbuffers      req;
        enum v4l2_buf_type              type;
        fd_set                          fds;
        struct timeval                  tv;
        int                             r, fd = -1;
        unsigned int                    i, n_buffers;
        char                            *dev_name = "/dev/video0";
        // char                            out_name[256];
        FILE                            *fout;
        struct buffer                   *buffers;

        fd = v4l2_open(dev_name, O_RDWR | O_NONBLOCK, 0);
        if (fd < 0) {
                perror("Cannot open device");
                exit(EXIT_FAILURE);
        }

        rt_mutex_create(&timerlock,"Timer");
        rt_task_create(&ticker_task, "ticker", 0, 99, 0); // 99 = highest priority. Ticker loop
        rt_task_create(&other_task, "other", 0, 90, 0) ; // socket thread (new for beaglebone)
        CLEAR(fmt);
        fmt.type = V4L2_BUF_TYPE_VIDEO_CAPTURE;
        fmt.fmt.pix.width       = WIDTH;
        fmt.fmt.pix.height      = HEIGHT;
        fmt.fmt.pix.pixelformat = FORMAT;
        fmt.fmt.pix.field       = V4L2_FIELD_INTERLACED;
        xioctl(fd, VIDIOC_S_FMT, &fmt);
        if (fmt.fmt.pix.pixelformat != FORMAT) {
                printf("Libv4l didn't accept requested format. Can't proceed.\n");
                exit(EXIT_FAILURE);
        }
        if ((fmt.fmt.pix.width != WIDTH) || (fmt.fmt.pix.height != HEIGHT))
                printf("Warning: driver is sending image at %dx%d\n",
                        fmt.fmt.pix.width, fmt.fmt.pix.height);

        CLEAR(req);
        req.count = 2;
        req.type = V4L2_BUF_TYPE_VIDEO_CAPTURE;
        req.memory = V4L2_MEMORY_MMAP;
        xioctl(fd, VIDIOC_REQBUFS, &req);

        buffers = calloc(req.count, sizeof(*buffers));
        for (n_buffers = 0; n_buffers < req.count; ++n_buffers) {
                CLEAR(buf);

                buf.type        = V4L2_BUF_TYPE_VIDEO_CAPTURE;
                buf.memory      = V4L2_MEMORY_MMAP;
                buf.index       = n_buffers;

                xioctl(fd, VIDIOC_QUERYBUF, &buf);

                buffers[n_buffers].length = buf.length;
                buffers[n_buffers].start = v4l2_mmap(NULL, buf.length,
                              PROT_READ | PROT_WRITE, MAP_SHARED,
                              fd, buf.m.offset);

                if (MAP_FAILED == buffers[n_buffers].start) {
                        perror("mmap");
                        exit(EXIT_FAILURE);
                }
        }

        for (i = 0; i < n_buffers; ++i) {
                CLEAR(buf);
                buf.type = V4L2_BUF_TYPE_VIDEO_CAPTURE;
                buf.memory = V4L2_MEMORY_MMAP;
                buf.index = i;
                xioctl(fd, VIDIOC_QBUF, &buf);
        }
        type = V4L2_BUF_TYPE_VIDEO_CAPTURE;

        xioctl(fd, VIDIOC_STREAMON, &type);
        for (i = 0; i < NPIX; i++) {
                do {
                        FD_ZERO(&fds);
                        FD_SET(fd, &fds);

                        /* Timeout. */
                        tv.tv_sec = 2;
                        tv.tv_usec = 0;

                        r = select(fd + 1, &fds, NULL, NULL, &tv);
                } while ((r == -1 && (errno = EINTR)));
                if (r == -1) {
                        perror("select");
                        return errno;
                }

                CLEAR(buf);
                buf.type = V4L2_BUF_TYPE_VIDEO_CAPTURE;
                buf.memory = V4L2_MEMORY_MMAP;
                xioctl(fd, VIDIOC_DQBUF, &buf);

                /*
                sprintf(out_name, "grabber%03d.ppm", i);
                fout = fopen(out_name, "w");
                if (!fout) {
                        perror("Cannot open image");
                        exit(EXIT_FAILURE);
                }
                fprintf(fout, "P6\n%d %d 255\n",
                        fmt.fmt.pix.width, fmt.fmt.pix.height);
                fwrite(buffers[buf.index].start, buf.bytesused, 1, fout);
                fclose(fout);
                */

                xioctl(fd, VIDIOC_QBUF, &buf);
        }
        printf("done!\n");

        rt_task_start(&ticker_task, (void (*)(void *))&ticker, NULL);
        rt_task_start(&other_task, (void (*)(void *))&other, NULL);

        type = V4L2_BUF_TYPE_VIDEO_CAPTURE;
        xioctl(fd, VIDIOC_STREAMOFF, &type);
        for (i = 0; i < n_buffers; ++i)
                v4l2_munmap(buffers[i].start, buffers[i].length);
        v4l2_close(fd);
        embedpy();

        return 0;
}

static PyMethodDef CTMethods[] = {
};

void init_cougartech(void)
{
  Py_InitModule3("_cougartech", CTMethods, "cougar tech interface");
}

void embedpy()
{
  Py_Initialize();
  PyImport_AppendInittab("_cougartech",init_cougartech);
  PyEval_InitThreads();
  PyRun_SimpleString("import code; code.interact()\n");
  // PyRun_SimpleString("execfile('stronghold.py')\n");
  Py_Finalize();
}

void embedit2()
{
}
