/* 
 stronghold vision program..
 embeds xenomai and python 2.7
 */

// TO RUN, you need to, as SU:
// first expose the GPIO pins to 
// echo 15 > /sys/class/gpio/export
// echo out /sys/class/gpio/gpio15/direction

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
#include <native/event.h>
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
#define FORMAT V4L2_PIX_FMT_BGR24 
// RGB24 is the original format
// #define FORMAT V4L2_PIX_FMT_YUYV
#define NPIX 40
#define SYNC_EVENT 1L

RT_MUTEX timerlock;
RT_EVENT vid_sync;
RT_TASK led_task;
RT_TASK acquire_task;

RTIME now;

int led_fd = -1;

// led thread
void led(void *arg)
{
    unsigned long mask;
    while (1) {
        rt_event_wait(&vid_sync, SYNC_EVENT, &mask, EV_ALL, TM_INFINITE);
        rt_task_sleep(800000);
        write(led_fd, "1", 1);
        rt_task_sleep(5000000);
        write(led_fd, "0", 1);
        rt_event_clear(&vid_sync, SYNC_EVENT, &mask);
    }
}


void grab_image();

// acquire thread
void acquire(void *arg)
{
    init_video();
    while (1) {
        grab_image();
    }
}

struct buffer                   *buffers;

struct v4l2_format              fmt;
struct v4l2_buffer              buf;
struct v4l2_requestbuffers      req;
enum v4l2_buf_type              type;
fd_set                          fds;
struct timeval                  tv;
int                             r, vid_fd = -1;
unsigned int                    i, n_buffers;
char                            *dev_name = "/dev/video0";
char img[2][160*120*3];

int init_video()
{
    vid_fd = v4l2_open(dev_name, O_RDWR | O_NONBLOCK, 0);
    if (vid_fd < 0)
        return vid_fd;

    led_fd = open("/sys/class/gpio/gpio15/value",O_WRONLY);
    if (led_fd < 0)
        return led_fd;

    CLEAR(fmt);
    fmt.type = V4L2_BUF_TYPE_VIDEO_CAPTURE;
    fmt.fmt.pix.width       = WIDTH;
    fmt.fmt.pix.height      = HEIGHT;
    fmt.fmt.pix.pixelformat = FORMAT;
    fmt.fmt.pix.field       = V4L2_FIELD_INTERLACED;
    xioctl(vid_fd, VIDIOC_S_FMT, &fmt);
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
    xioctl(vid_fd, VIDIOC_REQBUFS, &req);
    buffers = calloc(req.count, sizeof(*buffers));
    for (n_buffers = 0; n_buffers < req.count; ++n_buffers) {
        CLEAR(buf);

        buf.type        = V4L2_BUF_TYPE_VIDEO_CAPTURE;
        buf.memory      = V4L2_MEMORY_MMAP;
        buf.index       = n_buffers;

        xioctl(vid_fd, VIDIOC_QUERYBUF, &buf);

        buffers[n_buffers].length = buf.length;
        buffers[n_buffers].start = v4l2_mmap(NULL, buf.length,
              PROT_READ | PROT_WRITE, MAP_SHARED,
              vid_fd, buf.m.offset);

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
        xioctl(vid_fd, VIDIOC_QBUF, &buf);
    }
    type = V4L2_BUF_TYPE_VIDEO_CAPTURE;
    xioctl(vid_fd, VIDIOC_STREAMON, &type);
    return vid_fd;
}

void grab_image()
{
    do {
        FD_ZERO(&fds);
        FD_SET(vid_fd, &fds);

        // Timeout. 
        tv.tv_sec = 2;
        tv.tv_usec = 0;

        r = select(vid_fd + 1, &fds, NULL, NULL, &tv);
    } while ((r == -1 && (errno = EINTR)));
    if (r == -1) {
        perror("select");
        // return errno;
    }

    CLEAR(buf);
    buf.type = V4L2_BUF_TYPE_VIDEO_CAPTURE;
    buf.memory = V4L2_MEMORY_MMAP;
    xioctl(vid_fd, VIDIOC_DQBUF, &buf);
    if (buf.index)
        rt_event_signal(&vid_sync, SYNC_EVENT);
    /*
        write(led_fd, "1", 1);
    else
        write(led_fd, "0", 1);
   
    */
    //memcpy(img[0], buf.start, buf.length)
    // actually, this is our image.
    xioctl(vid_fd, VIDIOC_QBUF, &buf);
}

void close_video()
{
    type = V4L2_BUF_TYPE_VIDEO_CAPTURE;
    xioctl(vid_fd, VIDIOC_STREAMOFF, &type);
    for (i = 0; i < n_buffers; ++i)
        v4l2_munmap(buffers[i].start, buffers[i].length);
    v4l2_close(vid_fd);
}

int main(int argc, char **argv)
{
    rt_mutex_create(&timerlock,"Timer");
    rt_task_create(&led_task, "led", 0, 99, 0); // 99 = highest priority. Ticker loop
    rt_task_create(&acquire_task, "acquire", 0, 90, 0) ; // socket thread (new for beaglebone)
    rt_event_create(&vid_sync, NULL, 0, EV_PRIO);

    rt_task_start(&led_task, (void (*)(void *))&led, NULL);
    rt_task_start(&acquire_task, (void (*)(void *))&acquire, NULL);

    embedpy();
    close_video();
    return 0;
}

/*
static PyObject* py_init(PyObject* self, PyObject* args)
{
    init_video();
	return Py_BuildValue("");
}
*/


static PyObject* py_grab(PyObject* self, PyObject* args)
{
	return Py_BuildValue("II",buffers[0].start, buffers[1].start);
}

/*
static PyObject* py_close(PyObject* self, PyObject* args)
{
    close_video();
	return Py_BuildValue("");
}
*/

static PyMethodDef CTMethods[] = {
	// {"getint", ct_gethook, METH_VARARGS, NULL},
	//{"init", py_init, METH_VARARGS, NULL},
	{"grab", py_grab, METH_VARARGS, NULL},
	//{"close", py_close, METH_VARARGS, NULL},
	{NULL, NULL, 0, NULL}
};

void init_cougartech(void)
{
  Py_InitModule3("_ct", CTMethods, "cougar tech interface");
}

void embedpy()
{
  Py_Initialize();
  PyImport_AppendInittab("_ct",init_cougartech);
  PyEval_InitThreads();
  PyRun_SimpleString("import code; code.interact()\n");
  // PyRun_SimpleString("execfile('stronghold.py')\n");
  Py_Finalize();
}

void embedit2()
{
}
