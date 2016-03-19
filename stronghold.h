#define WIDTH 160
#define HEIGHT 120

struct vidconf_s
    {
    unsigned int on_time;
    unsigned int sleep_time;
    int invert;
    int led_enabled;
    double threshold;
    float fps;
    };
