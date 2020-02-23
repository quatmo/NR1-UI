All Credits to: https://github.com/diehardsk

This is a fork from diehrdsk/Volumio-OledUi

I'm trying to change: 
* the "Now-Playing" Screen (other fonts, add File-Info and Playtime)
* Play- Pause- and Stop- Icons
* Bootup and Shutdown Logos
* More Buttons via GPIO
* remove one Rotary
* remove rotary Button
* implement a new State : standby,which displays time & ip


## hardware
* Raspberry Pi 2B/3B/4B with Volumio2 image
* 3.2" 256x64 Pixels 4-wire SPI OLED Display with SSD1322 controller IC (e.g. ER-OLEDM032-1W)

## dependencies
* [RPi.GPIO](https://sourceforge.net/p/raspberry-gpio-python/wiki/Home/)
* [socketIO-client-2](https://pypi.python.org/pypi/socketIO-client-2)
* PIL
* [luma.oled](https://luma-oled.readthedocs.io/)


### installation steps
```
sudo apt-get update
 
sudo apt-get install -y python-dev python-pip libfreetype6-dev libjpeg-dev build-essential python-rpi.gpio
 
sudo pip install --upgrade setuptools pip wheel
 
sudo pip install --upgrade socketIO-client-2 luma.oled
 
git clone https://github.com/Maschine2501/Volumio-OledUI.git
 
chmod +x ~/Volumio-OledUI/oledui.py
 
sudo cp ~/Volumio-OledUI/oledui.service /lib/systemd/system/
 
sudo systemctl daemon-reload
 
sudo systemctl enable oledui.service

```

### Hints
```
-when Volumio is configured to remember the last Playlist and the last Playback was from a local drive (eg. USB) Artist and Trackinfo sty corrupt until another Playback was selected.
```
