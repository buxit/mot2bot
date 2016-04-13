#!/bin/sh

export SDL_FBDEV=/dev/fb1
dn="$(dirname "$0")"
cd "$dn"
./http-pi2kf.py
