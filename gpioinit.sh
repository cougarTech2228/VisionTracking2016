#! /bin/sh
echo 15 > /sys/class/gpio/export
echo out > /sys/class/gpio/gpio15/direction
