#!/bin/sh

export SDL_FBDEV=/dev/fb0
dn=$(dirname "$0")
cd "$dn"
./http-pi2kf.py
