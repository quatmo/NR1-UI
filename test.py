#!/usr/bin/python3
#      ____  ____  ___   __  ___   __     _   ______ ___
#     / __ )/ __ \/   | / / / / | / /    / | / / __ <  /
#    / __  / /_/ / /| |/ / / /  |/ /    /  |/ / /_/ / / 
#   / /_/ / _, _/ ___ / /_/ / /|  /    / /|  / _, _/ /  
#  /_____/_/ |_/_/  |_\____/_/ |_/    /_/ |_/_/ |_/_/   
#    __  __              ____     __          ___            
#   / / / /__ ___ ____  /  _/__  / /____ ____/ _/__ ________ 
#  / /_/ (_-</ -_) __/ _/ // _ \/ __/ -_) __/ _/ _ `/ __/ -_)
#  \____/___/\__/_/   /___/_//_/\__/\__/_/ /_/ \_,_/\__/\__/ 
#
#  For more Informations visit: https://github.com/Maschine2501/NR1-UI
#   _           __  __ ___ ___ ___  __  _ 
#  | |__ _  _  |  \/  / __|_  ) __|/  \/ |
#  | '_ \ || | | |\/| \__ \/ /|__ \ () | |
#  |_.__/\_, | |_|  |_|___/___|___/\__/|_|
#        |__/                                                                                       
#  www.github.com/Maschine2501                                                         
#
from __future__ import unicode_literals

import requests
import os
import sys
import time
import threading
import signal
import json
import pycurl
import pprint
import subprocess
import RPi.GPIO as GPIO
GPIO.setmode(GPIO.BCM) 
GPIO.setwarnings(False)

from time import*
from datetime import timedelta as timedelta
from threading import Thread
from socketIO_client import SocketIO
from datetime import datetime as datetime
from io import BytesIO 

# Imports for OLED display
from luma.core.interface.serial import spi
from luma.oled.device import ssd1322
from PIL import Image
from PIL import ImageDraw
from PIL import ImageFont

from modules.pushbutton import PushButton
from modules.rotaryencoder import RotaryEncoder
from modules.display import*
#from modules.StatusLED import*

volumio_host = 'localhost'
volumio_port = 3000

volumioIO = SocketIO(volumio_host, volumio_port)

GPIO.setup(13, GPIO.OUT)
GPIO.setup(26, GPIO.IN)

GPIO.output(13, GPIO.HIGH)

#imports for REST API (MediaInfoScreen)
b_obj = BytesIO() 
crl = pycurl.Curl() 

STATE_NONE = -1
STATE_PLAYER = 0
STATE_QUEUE_MENU = 1
STATE_LIBRARY_INFO = 2
STATE_SPECTRUM_DISPLAY = 3

UPDATE_INTERVAL = 0.034
PIXEL_SHIFT_TIME = 120    #time between picture position shifts in sec.

interface = spi(device=0, port=0)
oled = ssd1322(interface, rotate=2) 
#without rotate display is 0 degrees, with rotate=2 its 180 degrees

oled.WIDTH = 256
oled.HEIGHT = 64
oled.state = 'stop'
oled.stateTimeout = 0
oled.spectrumTimer = 0
oled.timeOutRunning = False
oled.activeSong = ''
oled.activeArtist = 'VOLuMIO'
oled.playState = 'unknown'
oled.playPosition = 0
oled.seek = 1000
oled.duration = 1.0
oled.modal = False
oled.playlistoptions = []
oled.queue = []
oled.libraryFull = []
oled.libraryNames = []
oled.volumeControlDisabled = True
oled.volume = 100
now = datetime.now()                                                             #current date and time
oled.time = now.strftime("%H:%M:%S")                                             #resolves time as HH:MM:SS eg. 14:33:15
oled.date = now.strftime("%d.  %m.  %Y")                                         #resolves time as dd.mm.YYYY eg. 17.04.2020
oled.IP = ''
emit_volume = False
emit_track = False
newStatus = 0              							 #makes newStatus usable outside of onPushState
oled.activeFormat = ''      							 #makes oled.activeFormat globaly usable
oled.activeSamplerate = ''  							 #makes oled.activeSamplerate globaly usable
oled.activeBitdepth = ''                                                         #makes oled.activeBitdepth globaly usable
oled.activeArtists = ''                                                          #makes oled.activeArtists globaly usable
oled.activeAlbums = ''                                                           #makes oled.activeAlbums globaly usable
oled.activeSongs = ''                                                      	 #makes oled.activeSongs globaly usable
oled.activePlaytime = ''                                                         #makes oled.activePlaytime globaly usable
oled.Art = 'Interpreten :'                                                       #sets the Artists-text for the MediaLibrarayInfo
oled.Alb = 'Alben :'                                                             #sets the Albums-text for the MediaLibrarayInfo
oled.Son = 'Songs :'                                                             #sets the Songs-text for the MediaLibrarayInfo
oled.Pla = 'Playtime :'                                                          #sets the Playtime-text for the MediaLibrarayInfo
oled.randomTag = False                                                           #helper to detect if "Random/shuffle" is set
oled.repeatTag = False                                                           #helper to detect if "repeat" is set
oled.ShutdownFlag = False                                                        #helper to detect if "shutdown" is running. Prevents artifacts from Standby-Screen during shutdown
oled.libraryInfo = '\U0001F4D6'
oled.libraryReturn = '\u2302'
oled.ArtistIcon = '\uF0F3'
oled.AlbumIcon = '\uF2BB'
oled.SongIcon = '\U0000F001'
oled.PlaytimeIcon = '\U0000F1DA'
SpectrumStamp = 0.0
oled.selQueue = ''


image = Image.new('RGB', (oled.WIDTH, oled.HEIGHT))  #for Pixelshift: (oled.WIDTH + 4, oled.HEIGHT + 4)) 
oled.clear()

font = load_font('Oxanium-Bold.ttf', 20)                       #used for Artist
font2 = load_font('Oxanium-Light.ttf', 12)                     #used for all menus
font3 = load_font('Oxanium-Regular.ttf', 18)                   #used for Song
font4 = load_font('Oxanium-Medium.ttf', 12)                    #used for Format/Smplerate/Bitdepth
font5 = load_font('Oxanium-Medium.ttf', 11)                    #used for MediaLibraryInfo
hugefontaw = load_font('fa-solid-900.ttf', oled.HEIGHT - 4)    #used for play/pause/stop icons -> Status change overlay
mediaicon = load_font('fa-solid-900.ttf', 10)    	       #used for icon in Media-library info
iconfont = load_font('entypo.ttf', oled.HEIGHT)                #used for play/pause/stop/shuffle/repeat... icons
labelfont = load_font('entypo.ttf', 16)                        #used for Menu-icons 
labelfont2 = load_font('entypo.ttf', 12)                       #used for Menu-icons
iconfontBottom = load_font('entypo.ttf', 10)                   #used for icons under the screen / button layout
fontClock = load_font('DSG.ttf', 30)                           #used for clock
fontDate = load_font('DSEG7Classic-Regular.ttf', 10)           #used for Date 
fontIP = load_font('DSEG7Classic-Regular.ttf', 10)             #used for IP  

#above are the "imports" for the fonts. 
#After the name of the font comes a number, this defines the Size (height) of the letters. 
#Just put .ttf file in the 'Volumio-OledUI/fonts' directory and make an import like above. 

def StandByWatcher():
# listens to GPIO 26. If Signal is High, everything is fine, raspberry will keep doing it's shit.
# If GPIO 26 is Low, Raspberry will shutdown.
    StandbySignal = GPIO.input(26)
    while True:
        StandbySignal = GPIO.input(26)
        if StandbySignal == 1:
            oled.ShutdownFlag = True
            volumioIO.emit('stop')
            GPIO.output(13, GPIO.LOW)
            sleep(1)
            oled.clear()
            show_logo("shutdown.ppm", oled)
            volumioIO.emit('shutdown')
        elif StandbySignal == 0:
            sleep(1)

#I inverted the logic above, so GPIO26 does not need an external signal.

#def sigterm_handler(signal, frame):
#    oled.ShutdownFlag = True
#    volumioIO.emit('stop')
#    GPIO.output(13, GPIO.LOW)
#    oled.clear()
#    show_logo("shutdown.ppm", oled)
#    print('booyah! bye bye')

def GetIP():
    lanip = GetLANIP()
    print(lanip)
    LANip = str(lanip.decode('ascii'))
    print('LANip: ', LANip)
    wanip = GetWLANIP()
    print(wanip)
    WLANip = str(wanip.decode('ascii'))
    print('WLANip: ', WLANip)
    if LANip != '':
       ip = LANip
       print('LanIP: ', ip)
    elif WLANip != '':
       ip = WLANip
       print('WlanIP: ', ip)
    else:
       ip = "no ip"
    oled.IP = ip

def GetLANIP():
    cmd = \
        "ip addr show eth0 | grep inet  | grep -v inet6 | awk '{print $2}' | cut -d '/' -f 1"
    p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE)
    output = p.communicate()[0]
    return output[:-1]

def GetWLANIP():
    cmd = \
        "ip addr show wlan0 | grep inet  | grep -v inet6 | awk '{print $2}' | cut -d '/' -f 1"
    p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE)
    output = p.communicate()[0]
    return output[:-1]

#signal.signal(signal.SIGTERM, sigterm_handler)

#StandByListen = threading.Thread(target=StandByWatcher, daemon=True)
#StandByListen.start()

GetIP()
#SysStart()

#Processor = threading.Thread(target=CPUload, daemon=True)
#Processor.start()

def display_update_service():
    while UPDATE_INTERVAL > 0 and oled.ShutdownFlag == False:
        prevTime = time()
        dt = time() - prevTime
        if oled.stateTimeout > 0:
            oled.timeOutRunning = True
            oled.stateTimeout -= dt
        elif oled.stateTimeout <= 0 and oled.timeOutRunning:
            oled.timeOutRunning = False
            oled.stateTimeout = 0
            SetState(STATE_PLAYER)
        image.paste("black", [0, 0, image.size[0], image.size[1]])
        try:
            oled.modal.DrawOn(image)
        except AttributeError:
            print("render error")
            sleep(1)
        cimg = image.crop((0, 0, oled.WIDTH, oled.HEIGHT)) 
        oled.display(cimg)
        sleep(UPDATE_INTERVAL)

#Example to SetState:
#oled.modal = NowPlayingScreen(oled.HEIGHT, oled.WIDTH, oled.activeArtist, oled.activeSong, oled.time, oled.IP, font, hugefontaw, fontClock)
#here you have to define which variables you want to use in "class" (following below)
#simply define which "data" (eg. oled.IP...) you want to display followed by the fonts you want to use
#Hint: the "data" is equal to row1, row2... etc. in the classes, first "data" is row1 and so on...
#oled.activeArtist = row1 / oled.activeSong = row2 ....
	
def SetState(status):
    oled.state = status
    if oled.state == STATE_PLAYER:
        oled.modal = NowPlayingScreen(oled.HEIGHT, oled.WIDTH, oled.activeArtist, oled.activeSong, oled.time, oled.IP, oled.date, oled.activeFormat, oled.activeSamplerate, oled.activeBitdepth, oled.libraryInfo, oled.duration, oled.seek, font, fontClock, fontDate, fontIP, font3, font4, iconfont, iconfontBottom)
        oled.modal.SetPlayingIcon(oled.playState, 0)
    elif oled.state == STATE_QUEUE_MENU:
        oled.modal = MenuScreen(oled.HEIGHT, oled.WIDTH, font2, iconfontBottom, labelfont, oled.queue, rows=4, selected=oled.playPosition, showIndex=True, label='\u2630')
    elif oled.state == STATE_LIBRARY_INFO:
        oled.modal = MediaLibrarayInfo(oled.HEIGHT, oled.WIDTH, oled.activeArtists, oled.activeAlbums, oled.activeSongs, oled.activePlaytime, oled.Art, oled.Alb, oled.Son, oled.Pla, oled.libraryInfo, oled.libraryReturn, oled.ArtistIcon, oled.AlbumIcon, oled.SongIcon, oled.PlaytimeIcon, hugefontaw, font5, iconfontBottom, labelfont, labelfont2, mediaicon)
    elif oled.state == STATE_SPECTRUM_DISPLAY:
        oled.modal = SpectrumScreen(oled.HEIGHT, oled.WIDTH, oled.activeArtist, oled.activeSong, oled.activeFormat, oled.activeSamplerate, oled.activeBitdepth, font4)

#In 'onPushState' the whole set of media-information is linked to the variables (eg. artist, song...)
#On every change in the Playback (pause, other track, etc.) Volumio pushes a set of informations on port 3000.
#Volumio-OledUI is always listening on this port. If there's new 'data', the "def onPushState(data):" runs again.

def onPushState(data):
    global OPDsave	
    global newStatus #global definition for newStatus, used at the end-loop to update standby
    global newSong
    global newArtist
    OPDsave = data

    if 'title' in data:
        newSong = data['title']
    else:
        newSong = ''
    if newSong is None:
        newSong = ''
        
    if 'artist' in data:
        newArtist = data['artist']
    else:
        newArtist = ''
    if newArtist is None:   #volumio can push NoneType
        newArtist = ''
	
    if 'stream' in data:
        newFormat = data['stream']
    else:
        newFormat = ''
    if newFormat is None:
        newFormat = ''
    if newFormat == True:
       newFormat = 'WebRadio'

	#If a stream (like webradio) is playing, the data set for 'stream'/newFormat is a boolian (True)
	#drawOn can't handle that and gives an error. 
	#therefore we use "if newFormat == True:" and define a placeholder Word, you can change it.

    if 'samplerate' in data:
        newSamplerate = data['samplerate']
    else:
        newSamplerate = ' '
    if newSamplerate is None:
        newSamplerate = ' '

    if 'bitdepth' in data:
        newBitdepth = data['bitdepth']
    else:
        newBitdepth = ' '
    if newBitdepth is None:
        newBitdepth = ' '  
        
    if 'position' in data:                      # current position in queue
        oled.playPosition = data['position']    # didn't work well with volumio ver. < 2.5
        
    if 'status' in data:
        newStatus = data['status']
        specstatus1 = newStatus
        spectstatus2 = oled.playState
        
#    if 'channels' in data:
#        channels = data['channels']
#        if channels == 2:
#           StereoLEDon()
#        else:
#           StereoLEDoff()

    if 'duration' in data:
        oled.duration = data['duration']
    else:
        oled.duration = None
    if oled.duration == int(0):
        oled.duration = None

    if 'seek' in data:
        oled.seek = data['seek']
    else:
        oled.seek = None

    if newArtist is None:   #volumio can push NoneType
        newArtist = ''
    
    oled.activeFormat = newFormat
    oled.activeSamplerate = newSamplerate
    oled.activeBitdepth = newBitdepth

    if (newSong != oled.activeSong) or (newArtist != oled.activeArtist):                                # new song and artist
        oled.activeSong = newSong
        oled.activeArtist = newArtist
        print('oled.state: ', oled.state)
        print('StatePlayer: ',STATE_PLAYER)
        if oled.state == STATE_PLAYER and newStatus != 'stop':                                          #this is the "NowPlayingScreen"
            SpectrumStamp = 0.0
            SetState(STATE_PLAYER)
#            PlayLEDon()
            oled.modal.UpdatePlayingInfo(newArtist, newSong, newFormat, newSamplerate, newBitdepth, oled.duration, oled.seek)     #here is defined which "data" should be displayed in the class
        if oled.state == STATE_PLAYER and newStatus == 'stop':                                          #this is the "Standby-Screen"
#            PlayLEDoff()
            SpectrumStamp = 0.0
            SetState(STATE_PLAYER)
            oled.modal.UpdateStandbyInfo(oled.time, oled.IP, oled.date, oled.libraryInfo)                                 #here is defined which "data" should be displayed in the class
        if oled.state == 3 and newStatus != 'stop':                                          #this is the "NowPlayingScreen"
            SpectrumStamp = 0.0
            oled.state = 0
            SetState(STATE_PLAYER)
#            PlayLEDon()
            oled.modal.UpdatePlayingInfo(newArtist, newSong, newFormat, newSamplerate, newBitdepth, oled.duration, oled.seek)     #here is defined which "data" should be displayed in the class
#            print(oled.state)
        if oled.state == 3 and newStatus == 'stop':                                          #this is the "Standby-Screen"
#            PlayLEDoff()
            SpectrumStamp = 0.0
            oled.state = 0
            SetState(STATE_PLAYER)
            oled.modal.UpdateStandbyInfo(oled.time, oled.IP, oled.date, oled.libraryInfo)                                 #here is defined which "data" should be displayed in the class

    if newStatus != oled.playState:
        oled.playState = newStatus
        if oled.state == STATE_PLAYER:
            if oled.playState == 'play':
                iconTime = 35
            else:
                iconTime = 80
            SetState(STATE_PLAYER)    
            oled.modal.SetPlayingIcon(oled.playState, iconTime)

def onPushCollectionStats(data):
    data = json.loads(data.decode("utf-8"))             #data import from REST-API (is set when ButtonD short-pressed in Standby)
#    data = data.decode("utf-8")

    if "artists" in data:               #used for Media-Library-Infoscreen
        newArtists = data["artists"]
    else:
        newArtists = ''
    if newArtists is None:
        newArtists = ''

    if 'albums' in data:                #used for Media-Library-Infoscreen
        newAlbums = data["albums"]
    else:
        newAlbums = ''
    if newAlbums is None:
        newAlbums = ''

    if 'songs' in data:                 #used for Media-Library-Infoscreen
        newSongs = data["songs"]
    else:
        newSongs = ''
    if newSongs is None:
        newSongs = ''

    if 'playtime' in data:               #used for Media-Library-Infoscreen
        newPlaytime = data["playtime"]
    else:
        newPlaytime = ''
    if newPlaytime is None:
        newPlaytime = ''

    oled.activeArtists = str(newArtists) 
    oled.activeAlbums = str(newAlbums)
    oled.activeSongs = str(newSongs)
    oled.activePlaytime = str(newPlaytime)
	
    if oled.state == STATE_LIBRARY_INFO and oled.playState == 'info':                                   #this is the "Media-Library-Info-Screen"
       oled.modal.UpdateLibraryInfo(oled.activeArtists, oled.activeAlbums, oled.activeSongs, oled.activePlaytime, oled.Art, oled.Alb, oled.Son, oled.Pla, oled.libraryInfo, oled.libraryReturn, oled.ArtistIcon, oled.AlbumIcon, oled.SongIcon, oled.PlaytimeIcon)  #



def onPushQueue(data):
    oled.queue = [track['name'] if 'name' in track else 'no track' for track in data]

#if you wan't to add more textposition: double check if using STATIC or SCROLL text.
#this needs to be declared two times, first in "self.playingText" AND under: "def UpdatePlayingInfo" or "def UpdateStandbyInfo"

class NowPlayingScreen():
    def __init__(self, height, width, row1, row2, row3, row4, row5, row6, row7, row8, row17, row18, row19, font, fontClock, fontDate, fontIP, font3, font4, iconfont, iconfontBottom): #this line references to oled.modal = NowPlayingScreen
        self.height = height
        self.width = width
        self.font = font
        self.font3 = font3
        self.font4 = font4
        self.iconfont = iconfont
        self.icontfontBottom = iconfontBottom
        self.fontClock = fontClock
        self.fontDate = fontDate
        self.fontIP = fontIP
        self.duration = row18

        self.playingText1 = ScrollText(self.height, self.width, row1, font)         	#Artist /center=True
        self.playingText2 = ScrollText(self.height, self.width, row2, font3)        	#Title
        self.playingText3 = StaticText(self.height, self.width, row6, font4)        	#format / flac,MP3...
        self.playingText4 = StaticText(self.height, self.width, row7, font4)        	#samplerate / 44100
        self.playingText5 = StaticText(self.height, self.width, row8, font4)        	#bitdepth /16 Bit
        self.standbyText1 = StaticText(self.height, self.width, row3, fontClock)    	#Clock /center=True
        self.standbyText2 = StaticText(self.height, self.width, row4, fontIP)	    	#IP
        self.standbyText3 = StaticText(self.height, self.width, row5, fontDate)     	#Date
        self.standbyText7 = StaticText(self.height, self.width, row17, iconfontBottom)  #LibraryInfoIcon
        self.icon = {'play':'\u25B6', 'pause':'\u2389', 'stop':'\u25A0'}       	    	#entypo icons
        self.playingIcon = self.icon['play']
        self.iconcountdown = 0
        self.text1Pos = (0, 2)        #Artist /
        self.text2Pos = (0, 22)       #Title
        self.text3Pos = (47, 4)        #clock (clock  text is 161 pixels long) (222px viewable - text = 73 : 2 = 31 + 42offset = 73)
        self.text4Pos = (-6, 54)       #IP
        self.text5Pos = (140, 54)      #Date
        self.text6Pos = (0, 41)       #format
        self.text7Pos = (148, 41)      #samplerate
        self.text8Pos = (209, 41)      #bitdepth
        self.text17Pos = (226, 54)     #LibraryInfoIcon
        self.alfaimage = Image.new('RGBA', image.size, (0, 0, 0, 255))

# "def __init__(self,...." is the "initialization" of the "NowPlayingScreen". 
#Here you need to define the variables, which "data-string" is which textposition, where each textposition is displayed in the display...

    def UpdatePlayingInfo(self, row1, row2, row6, row7, row8, row18, row19):
        self.playingText1 = ScrollText(self.height, self.width, row1, font)   		#Artist/ center=True)
        self.playingText2 = ScrollText(self.height, self.width, row2, font3)  		#Title
        self.playingText3 = StaticText(self.height, self.width, row6, font4)  		#format
        self.playingText4 = StaticText(self.height, self.width, row7, font4)  		#samplerate
        self.playingText5 = StaticText(self.height, self.width, row8, font4)  		#bitdepth

    def UpdateStandbyInfo(self, row3, row4, row5, row17):
        self.standbyText1 = StaticText(self.height, self.width, row3, fontClock) 	#Clock center=True)
        self.standbyText2 = StaticText(self.height, self.width, row4, fontIP)    	#IP
        self.standbyText3 = StaticText(self.height, self.width, row5, fontDate)  	#Date
        self.standbyText7 = StaticText(self.height, self.width, row17, iconfontBottom)  #LibraryInfoIcon

#"def UpdateStandbyInfo" and "def UpdatePlayingInfo" collects the informations.
	
# "def DrawON(..." takes informations from above and creates a "picture" which then is transfered to your display	

    def DrawOn(self, image):
        if self.playingIcon != self.icon['stop'] and oled.duration != None:
            self.playingText1.DrawOn(image, self.text1Pos)    #Artist
            self.playingText2.DrawOn(image, self.text2Pos)    #Title
            self.playingText3.DrawOn(image, self.text6Pos)    #Format
            self.playingText4.DrawOn(image, self.text7Pos)    #Samplerate
            self.playingText5.DrawOn(image, self.text8Pos)    #Bitdep
            self.alfaimage.paste((0, 0, 0, 0), [0, 0, image.size[0], image.size[1]])                 #(0, 0, 0, 200) means Background (nowplayingscreen with artist, song etc.) is darkend. Change 200 to 0 -> Background is completely visible. 255 -> Bachground is not visible. scale = 0-255
            drawalfa = ImageDraw.Draw(self.alfaimage)
            self.playbackPoint = oled.seek / oled.duration / 10
            self.barwidth = 156
            self.bar = 156 * self.playbackPoint / 100
            drawalfa.text((1, 54), str(timedelta(seconds=round(float(oled.seek) / 1000))), font=self.font4, fill='white')
            drawalfa.text((210, 54), str(timedelta(seconds=oled.duration)), font=self.font4, fill='white')
            drawalfa.rectangle((50 , 59, 206, 59), outline='white', fill='black')
            drawalfa.rectangle((50, 56, 50 + self.bar, 62), outline='white', fill='black')
            compositeimage = Image.composite(self.alfaimage, image.convert('RGBA'), self.alfaimage)
            image.paste(compositeimage.convert('RGB'), (0, 0))

        if self.playingIcon != self.icon['stop'] and oled.duration == None:
            self.playingText1.DrawOn(image, self.text1Pos)    #Artist
            self.playingText2.DrawOn(image, self.text2Pos)    #Title
            self.playingText3.DrawOn(image, self.text6Pos)    #Format
            self.playingText4.DrawOn(image, self.text7Pos)    #Samplerate
            self.playingText5.DrawOn(image, self.text8Pos)    #Bitdep
           	
        if self.playingIcon == self.icon['stop']:
            self.standbyText1.DrawOn(image, self.text3Pos)    #Clock
            self.standbyText2.DrawOn(image, self.text4Pos)    #IP
            self.standbyText3.DrawOn(image, self.text5Pos)    #Date
            self.standbyText7.DrawOn(image, self.text17Pos)   #libraryInfo

        if self.iconcountdown > 0:
            compositeimage = Image.composite(self.alfaimage, image.convert('RGBA'), self.alfaimage)
            image.paste(compositeimage.convert('RGB'), (0, 0))
            self.iconcountdown -= 1
            
    def SetPlayingIcon(self, state, time=0):
        if state in self.icon:
           self.playingIcon = self.icon[state]
        self.alfaimage.paste((0, 0, 0, 200), [0, 0, image.size[0], image.size[1]])                 #(0, 0, 0, 200) means Background (nowplayingscreen with artist, song etc.) is darkend. Change 200 to 0 -> Background is completely visible. 255 -> Bachground is not visible. scale = 0-255
        drawalfa = ImageDraw.Draw(self.alfaimage)
        iconwidth, iconheight = drawalfa.textsize(self.playingIcon, font=self.iconfont)            #entypo
        left = (self.width - iconwidth + 34) / 2						   #here is defined where the play/pause/stop icons are displayed. 
        drawalfa.text((left, 4), self.playingIcon, font=self.iconfont, fill=(255, 255, 255, 200))  #(255, 255, 255, 200) means Icon is nearly white. Change 200 to 0 -> icon is not visible. scale = 0-255
        self.iconcountdown = time

class MediaLibrarayInfo():
    def __init__(self, height, width, row1, row2, row3, row4, row5, row6, row7, row8, row9, row10, row11, row12, row13, row14, fontaw, font5, iconfontBottom, labelfont, lablefont2, mediaicon): 
        self.height = height
        self.width = width
        self.font4 = font4
        self.fontaw = fontaw
        self.iconfontBottom = iconfontBottom
        self.labelfont = labelfont
        self.labelfont2 = labelfont2
        self.mediaicon = mediaicon
        self.LibraryInfoText1 = StaticText(self.height, self.width, row5, font4)   	      #Text for Artists
        self.LibraryInfoText2 = StaticText(self.height, self.width, row1, font4)  	      #Number of Artists
        self.LibraryInfoText3 = StaticText(self.height, self.width, row6, font4)  	      #Text for Albums
        self.LibraryInfoText4 = StaticText(self.height, self.width, row2, font4)    	      #Number of Albums
        self.LibraryInfoText5 = StaticText(self.height, self.width, row7, font4)   	      #Text for Songs
        self.LibraryInfoText6 = StaticText(self.height, self.width, row3, font4)   	      #Number of Songs
        self.LibraryInfoText7 = StaticText(self.height, self.width, row8, font4)   	      #Text for duration
        self.LibraryInfoText8 = StaticText(self.height, self.width, row4, font4)   	      #Summary of duration
        self.LibraryInfoText9 = StaticText(self.height, self.width, row9, labelfont2)  	      #Menu-label Icon
        self.LibraryInfoText10 = StaticText(self.height, self.width, row10, iconfontBottom)   #LibraryInfo Return
        self.LibraryInfoText11 = StaticText(self.height, self.width, row11, mediaicon)        #icon for Artists
        self.LibraryInfoText12 = StaticText(self.height, self.width, row12, mediaicon)        #icon for Albums
        self.LibraryInfoText13 = StaticText(self.height, self.width, row13, mediaicon)        #icon for Songs
        self.LibraryInfoText14 = StaticText(self.height, self.width, row14, mediaicon)        #icon for duration
        self.icon = {'info':'\F0CA'}
        self.mediaIcon = self.icon['info']
        self.iconcountdown = 0
        self.text1Pos = (138, 2)        					   #Number of Artists
        self.text2Pos = (138, 15)      						   #Number of Albums4
        self.text3Pos = (138, 28)      						   #Number of Songs
        self.text4Pos = (138, 41)      						   #Summary of duration
        self.text5Pos = (14, 2)      						   #Text for Artists
        self.text6Pos = (14, 15)     						   #Text for Albums
        self.text7Pos = (14, 28)     						   #Text for Songs
        self.text8Pos = (14, 41)     						   #Text for duration
        self.text9Pos = (134, 52)      						   #Menu-Label Icon
        self.text10Pos = (226, 54)     						   #LibraryInfoIcon
        self.text11Pos = (0, 2)      						   #icon for Artists
        self.text12Pos = (0, 15)     						   #icon for Albums
        self.text13Pos = (0, 28)     						   #icon for Songs
        self.text14Pos = (0, 41)     						   #icon for duration
        self.alfaimage = Image.new('RGBA', image.size, (0, 0, 0, 0))

    def UpdateLibraryInfo(self, row1, row2, row3, row4, row5, row6, row7, row8, row9, row10, row11, row12, row13, row14):
        self.LibraryInfoText1 = StaticText(self.height, self.width, row5, font4)  		#Text for Artists
        self.LibraryInfoText2 = StaticText(self.height, self.width, row1, font4)  		#Number of Artists
        self.LibraryInfoText3 = StaticText(self.height, self.width, row6, font4)  		#Text for Albums
        self.LibraryInfoText4 = StaticText(self.height, self.width, row2, font4)  		#Number of Albums
        self.LibraryInfoText5 = StaticText(self.height, self.width, row7, font4)  		#Text for Songs
        self.LibraryInfoText6 = StaticText(self.height, self.width, row3, font4)  		#Number of Songs
        self.LibraryInfoText7 = StaticText(self.height, self.width, row8, font4)  		#Text for duration
        self.LibraryInfoText8 = StaticText(self.height, self.width, row4, font4)  		#Summary of duration
        self.LibraryInfoText9 = StaticText(self.height, self.width, row9, labelfont2)   	#Menu-label Icon
        self.LibraryInfoText10 = StaticText(self.height, self.width, row10, iconfontBottom)     #LibraryInfo Return
        self.LibraryInfoText11 = StaticText(self.height, self.width, row11, mediaicon)        #icon for Artists
        self.LibraryInfoText12 = StaticText(self.height, self.width, row12, mediaicon)        #icon for Albums
        self.LibraryInfoText13 = StaticText(self.height, self.width, row13, mediaicon)        #icon for Songs
        self.LibraryInfoText14 = StaticText(self.height, self.width, row14, mediaicon)        #icon for duration


    def DrawOn(self, image):
        if self.mediaIcon == self.icon['info']:
            self.LibraryInfoText1.DrawOn(image, self.text5Pos)     #Text for Artists
            self.LibraryInfoText2.DrawOn(image, self.text1Pos)     #Number of Artists
            self.LibraryInfoText3.DrawOn(image, self.text6Pos)     #Text for Albums
            self.LibraryInfoText4.DrawOn(image, self.text2Pos)     #Number of Albums
            self.LibraryInfoText5.DrawOn(image, self.text7Pos)     #Text for Songs
            self.LibraryInfoText6.DrawOn(image, self.text3Pos)     #Number of Songs
            self.LibraryInfoText7.DrawOn(image, self.text8Pos)     #Text for duration
            self.LibraryInfoText8.DrawOn(image, self.text4Pos) 	   #Number of durati
            self.LibraryInfoText9.DrawOn(image, self.text9Pos)     #menulabelIcon
            self.LibraryInfoText10.DrawOn(image, self.text10Pos)   #LibraryInfo Return
            self.LibraryInfoText11.DrawOn(image, self.text11Pos)   #icon for Artists
            self.LibraryInfoText12.DrawOn(image, self.text12Pos)   #icon for Albums
            self.LibraryInfoText13.DrawOn(image, self.text13Pos)   #icon for Songs
            self.LibraryInfoText14.DrawOn(image, self.text14Pos)   #icon for duration
                    

class SpectrumScreen():
    def __init__(self, height, width, row1, row2, row3, row4, row5, font4): #this line references to oled.modal = NowPlayingScreen
        self.height = height
        self.width = width
        self.font4 = font4
        
    def UpdateSpectrumInfo(self, row1, row2, row3, row4, row5):
        self.image = Image.new('RGB', (self.width, self.height))
        self.draw = ImageDraw.Draw(self.image)

    def DrawOn(self, image):
        if oled.duration != None:
          self.image.paste((0, 0, 0), [0, 0, image.size[0], image.size[1]])  
          self.playbackPoint = oled.seek / oled.duration / 10
          self.barwidth = 156
          self.bar = 156 * self.playbackPoint / 100
          self.draw.rectangle((50 , 59, 206, 59), outline='white', fill='black')
          self.draw.rectangle((50, 56, 50 + self.bar, 62), outline='white', fill='black')
          self.draw.text((1, 54), str(timedelta(seconds=round(float(oled.seek) / 1000))), font=self.font4, fill='white')
          self.draw.text((210, 54), str(timedelta(seconds=oled.duration)), font=self.font4, fill='white')
          try: 
              subprocess.check_output('pgrep -x cava', shell = True)
          except:
              subprocess.call("cava &", shell = True)
          cava_fifo = open("/tmp/cava_fifo", 'r')
          data = cava_fifo.readline().strip().split(';')
          for i in range(0, len(data)-1):
              try:
                  self.draw.rectangle((i*16, 50, i*16+8, 50-int(data[i])), outline = 'white', fill ='white')  #(255, 255, 255, 200) means Icon is nearly white. Change 200 to 0 -> icon is not visible. scale = 0-255
                  image.paste(self.image, (0, 0))
                  if specstatus1 != specstatus2:
                       oled.activeSong = newSong
                       oled.activeArtist = newArtist
                       if oled.state == STATE_PLAYER and newStatus != 'stop':                                          #this is the "NowPlayingScreen"
                          SetState(STATE_PLAYER)
                          oled.modal.UpdatePlayingInfo(newArtist, newSong, newFormat, newSamplerate, newBitdepth, oled.playIcon, oled.pauseIcon, oled.stopIcon, oled.prevIcon, oled.nextIcon)
                       if oled.state == STATE_PLAYER and newStatus == 'stop' or oled.playState == 'stop':                                          #this is the "Standby-Screen"
                          SetState(STATE_PLAYER)
                          oled.modal.UpdateStandbyInfo(oled.time, oled.IP, oled.date, oled.libraryIcon, oled.playlistIcon, oled.queueIcon, oled.libraryInfo)                        
              except:
                  pass   

        if oled.duration == None:
          self.image.paste((0, 0, 0), [0, 0, image.size[0], image.size[1]])
          try: 
              subprocess.check_output('pgrep -x cava', shell = True)
          except:
              subprocess.call("cava &", shell = True)
          cava_fifo = open("/tmp/cava_fifo", 'r')
          data = cava_fifo.readline().strip().split(';')
          for i in range(0, len(data)-1):
              try:
                  self.draw.rectangle((i*16, 50, i*16+8, 50-int(data[i])), outline = 'white', fill ='white')  #(255, 255, 255, 200) means Icon is nearly white. Change 200 to 0 -> icon is not visible. scale = 0-255
                  image.paste(self.image, (0, 0))
                  if specstatus1 != specstatus2:
                       oled.activeSong = newSong
                       oled.activeArtist = newArtist
                       if oled.state == STATE_PLAYER and newStatus != 'stop':                                          #this is the "NowPlayingScreen"
                          SetState(STATE_PLAYER)
                          oled.modal.UpdatePlayingInfo(newArtist, newSong, newFormat, newSamplerate, newBitdepth, oled.playIcon, oled.pauseIcon, oled.stopIcon, oled.prevIcon, oled.nextIcon)
                       if oled.state == STATE_PLAYER and newStatus == 'stop' or oled.playState == 'stop':                                          #this is the "Standby-Screen"
                          SetState(STATE_PLAYER)
                          oled.modal.UpdateStandbyInfo(oled.time, oled.IP, oled.date, oled.libraryIcon, oled.playlistIcon, oled.queueIcon, oled.libraryInfo)                         
              except:
                  pass   
     

class MenuScreen():
    def __init__(self, height, width, font2, iconfontBottom, labelfont, menuList, selected=0, rows=4, label='', showIndex=False):
        self.height = height
        self.width = width
        self.font2 = font2
        self.iconfontBottom = iconfontBottom
        self.labelfont = labelfont
        self.selectedOption = selected
        self.menuLabel = StaticText(self.height, self.width, label, labelfont)
        if label == '':
            self.hasLabel = 0
        else:
            self.hasLabel = 1
        self.labelPos = (140, 52)                      #here is the position of the menu label
        self.menuYPos = 2 + 12 * self.hasLabel
        self.menurows = rows
        self.menuText = [None for i in range(self.menurows)]
        self.menuList = menuList
        self.totaloptions = len(menuList)
        self.onscreenoptions = min(self.menurows, self.totaloptions)
        self.firstrowindex = 0
        self.showIndex = showIndex
        self.MenuUpdate()

    def MenuUpdate(self):
        self.firstrowindex = min(self.firstrowindex, self.selectedOption)
        self.firstrowindex = max(self.firstrowindex, self.selectedOption - (self.menurows-1))
        for row in range(self.onscreenoptions):
            if (self.firstrowindex + row) == self.selectedOption:
                color = "black"
                bgcolor = "white"
            else:
                color = "white"
                bgcolor = "black"
            optionText = self.menuList[row+self.firstrowindex]
            if self.showIndex:
                width = 1 + len(str(self.totaloptions))      # more digits needs more space
                optionText = '{0:{width}d} {1}'.format(row + self.firstrowindex + 1, optionText, width=width)
            self.menuText[row] = StaticText(self.height, self.width, optionText, self.font2, fill=color, bgcolor=bgcolor)
        if self.totaloptions == 0:
            self.menuText[0] = StaticText(self.height, self.width, 'no items..', self.font2, fill="white", bgcolor="black")
            
    def NextOption(self):
        self.selectedOption = min(self.selectedOption + 1, self.totaloptions - 1)
        self.MenuUpdate()

    def PrevOption(self):
        self.selectedOption = max(self.selectedOption - 1, 0)
        self.MenuUpdate()

    def SelectedOption(self):
        print('selectedOption', self.selectedOption)
        return self.selectedOption 

    def DrawOn(self, image):
        if self.hasLabel:
            self.menuLabel.DrawOn(image, self.labelPos)
        for row in range(self.onscreenoptions):
            self.menuText[row].DrawOn(image, (0, 4 + row*16))       #Here is the position of the list entrys from left set (42)
        if self.totaloptions == 0:
            self.menuText[0].DrawOn(image, (0, 4))                  #Here is the position of the list entrys from left set (42)
        
def ButtonA_PushEvent(hold_time):
    if hold_time < 2 and oled.state != STATE_LIBRARY_INFO:
#shortpress functions below
        print('ButtonA short press event')
        if oled.state == STATE_PLAYER or oled.state == STATE_SPECTRUM_DISPLAY and oled.playstate != 'stop':
            if oled.playstate == 'play':
                volumioIO.emit('pause')
            else:
                volumioIO.emit('play')

def ButtonB_PushEvent(hold_time):
    if hold_time < 2 and oled.state != STATE_LIBRARY_INFO:
#shortpress functions below
        print('ButtonB short press event')
        if oled.state == STATE_PLAYER or oled.state == STATE_SPECTRUM_DISPLAY and oled.playState != 'stop':
            volumioIO.emit('stop')

def ButtonC_PushEvent(hold_time):
    if hold_time < 2 and oled.state != STATE_LIBRARY_INFO:
#shortpress functions below
        print('ButtonC short press event')
        if oled.state == STATE_PLAYER or oled.state == STATE_SPECTRUM_DISPLAY and oled.playState != 'stop':
            volumioIO.emit('prev')
#Longpress functions below
    elif oled.state == STATE_PLAYER or oled.state == STATE_SPECTRUM_DISPLAY and oled.playState != 'stop':
        print('ButtonC long press event')
        if repeatTag == False:
            volumioIO.emit('setRepeat', {"value":"true"})
            repeatTag = True            
        elif repeatTag == True:
            volumioIO.emit('setRepeat', {"value":"false"})
            repeatTag = False
       
def ButtonD_PushEvent(hold_time):
    if hold_time < 2:
#shortpress functions below
        print('ButtonD short press event')
        if oled.state == STATE_PLAYER or oled.state == STATE_SPECTRUM_DISPLAY and oled.playState != 'stop':
            volumioIO.emit('next')
        if oled.state == STATE_PLAYER and oled.playState == 'stop':
            b_obj = BytesIO()
            crl = pycurl.Curl()
            crl.setopt(crl.URL, 'localhost:3000/api/v1/collectionstats')
            crl.setopt(crl.WRITEDATA, b_obj)
            crl.perform()
            crl.close()
            get_body = b_obj.getvalue()
            print('getBody',get_body)
            SetState(STATE_LIBRARY_INFO)
            oled.playState = 'info'
            onPushCollectionStats(get_body)
            sleep(0.5) 
        elif oled.state == STATE_LIBRARY_INFO:
            SetState(STATE_PLAYER)
#Longpress functions below
    elif oled.state == STATE_PLAYER or oled.state == STATE_SPECTRUM_DISPLAY and oled.playState != 'stop':
        print('ButtonD long press event')
        if randomTag == False:
            volumioIO.emit('setRandom', {"value":"true"})
            randomTag = True
        elif randomTag == True:
            volumioIO.emit('setRandom', {"value":"false"})
            randomTag = False

def RightKnob_RotaryEvent(dir):
    global emit_track
    oled.stateTimeout = 6.0
    if oled.state != STATE_QUEUE_MENU:
        SetState(STATE_QUEUE_MENU)
    if oled.state == STATE_QUEUE_MENU and dir == RotaryEncoder.LEFT:
        oled.modal.PrevOption()
        oled.selQueue = oled.modal.SelectedOption()
        emit_track = True
        SpectrumStamp = 0.0 
    elif oled.state == STATE_QUEUE_MENU and dir == RotaryEncoder.RIGHT:
        oled.modal.NextOption()
        oled.selQueue = oled.modal.SelectedOption()
        emit_track = True
        SpectrumStamp = 0.0 


def RightKnob_PushEvent(hold_time):
    if hold_time < 2 and oled.state == STATE_QUEUE_MENU:
#shortpress fuctions below
        print ('RightKnob_PushEvent SHORT')
        oled.stateTimeout = 0     

#Down below is the defenition for the physical buttons.
#Sample: RightKnob_Push = PushButton(27, max_time=1) -> GPIO 27 is used
#Which Button is conected to which GPIO? (regarding to wiring diagram Maschine2501/Volumio-OledUI)
# Button A: GPIO 4
# Button B: GPIO 17
# Button C: GPIO 5
# Button D: GPIO 6
# Button right-Rotary: GPIO 27

ButtonA_Push = PushButton(4, max_time=3)
ButtonA_Push.setCallback(ButtonA_PushEvent)
ButtonB_Push = PushButton(17, max_time=1)
ButtonB_Push.setCallback(ButtonB_PushEvent)
ButtonC_Push = PushButton(5, max_time=3)
ButtonC_Push.setCallback(ButtonC_PushEvent)
ButtonD_Push = PushButton(6, max_time=3)
ButtonD_Push.setCallback(ButtonD_PushEvent)

RightKnob_Push = PushButton(27, max_time=1)
RightKnob_Push.setCallback(RightKnob_PushEvent)
RightKnob_Rotation = RotaryEncoder(22, 23, pulses_per_cycle=4)
RightKnob_Rotation.setCallback(RightKnob_RotaryEvent)

show_logo("volumio_logo.ppm", oled)
sleep(2)
SetState(STATE_PLAYER)

updateThread = Thread(target=display_update_service)
updateThread.daemon = True
updateThread.start()

def _receive_thread():
    volumioIO.wait()

receive_thread = Thread(target=_receive_thread)
receive_thread.daemon = True
receive_thread.start()

volumioIO.on('pushState', onPushState)
volumioIO.on('pushQueue', onPushQueue)

# get list of Playlists and initial state
volumioIO.emit('listPlaylist')
volumioIO.emit('getState')
volumioIO.emit('getQueue')

sleep(0.1)

try:
    with open('oledconfig.json', 'r') as f:   #load last playing track number
        config = json.load(f)
except IOError:
    pass
else:
    oled.playPosition = config['track']
    
if oled.playState != 'play':
    volumioIO.emit('play', {'value':oled.playPosition})

varcanc = True                      #helper for pause -> stop timeout counter
InfoTag = 0                         #helper for missing Artist/Song when changing sources
GetIP()

def PlaypositionHelper():
    while True:
          volumioIO.emit('getState')
          sleep(1.0)

PlayPosHelp = threading.Thread(target=PlaypositionHelper, daemon=True)
PlayPosHelp.start()

def printhelper():
  while True:
    print('oled.state: ', oled.state)
    print('oled.playState: ', oled.playState)
    print('SpectrumStamp: ', SpectrumStamp)
    print('seek: ', oled.seek)
    print('oled.playPosition', oled.playPosition)
    sleep(1.0)

Prints = threading.Thread(target=printhelper, daemon=True)
Prints.start()

while True:

    if emit_track and oled.stateTimeout < 4.5:
        emit_track = False
        try:
            print('Track selected: ', oled.selQueue)
            SpectrumStamp = 0.0
            SetState(STATE_PLAYER)
            InfoTag = 0
        except IndexError:
            pass
        volumioIO.emit('stop')
        sleep(0.2)
        volumioIO.emit('play', {'value':oled.selQueue})
    sleep(0.1)
    
    if oled.state == STATE_PLAYER and InfoTag <= 3 and newStatus != 'stop':
        oled.modal.UpdatePlayingInfo(oled.activeArtist, oled.activeSong, oled.activeFormat, oled.activeSamplerate, oled.activeBitdepth, oled.duration, oled.seek)
        InfoTag += 1
        sleep(1.5)
        SpectrumStamp = time()

    if oled.state == STATE_PLAYER and newStatus == 'play' and time() - SpectrumStamp >= 15.0:
        oled.state = 6
        SetState(STATE_SPECTRUM_DISPLAY)
        oled.modal.UpdateSpectrumInfo(oled.activeArtist, oled.activeSong, oled.activeFormat, oled.activeSamplerate, oled.activeBitdepth)

#this is the loop to push the actual time every 0.1sec to the "Standby-Screen"

    if oled.state == STATE_PLAYER and newStatus == 'stop' and oled.ShutdownFlag == False:
        InfoTag = 0  #resets the InfoTag helper from artist/song update loop
        oled.state = 0
        SetState(STATE_PLAYER)
        oled.time = strftime("%H:%M:%S")
        oled.modal.UpdateStandbyInfo(oled.time, oled.IP, oled.date, oled.libraryInfo)

#if playback is paused, here is defined when the Player goes back to "Standby"/Stop		
    if oled.state == 3 and newStatus == 'stop':
       SpectrumStamp = 0.0
       SetState(STATE_PLAYER)

    if oled.state == 3 and newStatus == 'pause':
       SpectrumStamp = 0.0
       SetState(STATE_PLAYER)

    if oled.state == STATE_PLAYER and newStatus == 'pause' and varcanc == True:

       secvar = int(round(time()))
       oled.state = 0
       SetState(STATE_PLAYER)
       varcanc = False
    elif oled.state == STATE_PLAYER and newStatus == 'pause' and int(round(time())) - secvar > 15:
         varcanc = True
         volumioIO.emit('stop')
         secvar = 0.0

sleep(0.1)