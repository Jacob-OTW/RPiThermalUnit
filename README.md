# USB Mini2 on Raspberry Pi

This project is an example on how to use the USB interface of the Mini2 thermal camera 
(not the HikMirco one, the UV256/384/640 one) on Raspberry Pi, without using desktop env, it draws directly to the linux fb0.

## Getting started

1. Set up a Raspberry Pi (tested on Zero2W) with RaspberryPi OS lite (64bit)
2. Clone the GitHub repo onto the desktop of your account on the RPi.
3. Install the requirements found in `requirements.txt` (for OpenCv you may need to install dependencies)
[This guide worked for me](https://raspberrypi-guide.github.io/programming/install-opencv), except that I had to remove the installation for `libjasper-dev`
4. Setup the display of your choice, I tested it with both HDMI and AV video, but DSI-2 probably also works on the B-Model RPis
5. Connect the Mini2 via USB and run `main.py`

## Notes
- The file path for storing settings in `menu.py` is relative, so if you start `main.py` from a crontab, 
you need to either change to path to be absolute, or cd into the directory first, 
otherwise the file will be in a different place than normally
