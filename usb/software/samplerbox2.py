#  SamplerBox
#
#  author:    Joseph Ernest
#  contact:   twitter: @JosephErnest, mail: contact@samplerbox.org
#  url:       http://www.samplerbox.org/
#  license:   Creative Commons ShareAlike 3.0
#  (http://creativecommons.org/licenses/by-sa/3.0/)
#
#  Contributor : HansEhv
#  url: http://homspace.xs4all.nl/homspace/samplerbox/
#
#  Contributor : Erik
#  url: http://www.nickyspride.nl/sb2/
#
#  Contributor : Remi Sarrailh
#  url (en): http://madnerd.org/en/samplerbox
#  url (fr): http://madnerd.org/fr/samplerbox
#  contact: remi@madnerd.org
#
#  samplerbox.py: Main file

#########################################
# DEFAULT CONFIGURATION
#########################################

# Version
VERSION1 = " -=SAMPLERBOX=- "
VERSION2 = " V2.2.0 09-2016 "

# Files
LOCAL_CONFIG = "/media/config.py"
# The root directory containing the sample-sets.
# Example: "/media/" to look for samples on a USB stick / SD card
SAMPLES_DIR = "/media/samples"
MIDI_DIR = "/media/midi"

#########
# Audio #
#########

# Device ID of Soundcard (aplay -l)
AUDIO_DEVICE_ID = 0
# 2:stereo, 4:4 channel playback
CHANNELS = 4
# lower buffersize means less latency, higher more polyphony and stability
BUFFERSIZE = 64
SAMPLERATE = 48000
# Polyphony can be set higher, but 80 is a safe value
MAX_POLYPHONY = 80
# Enable FreeVerb
USE_FREEVERB = True
# Enable Tonecontrol (also remove comments in code)
USE_TONECONTOL = False

# Fade out (release) sampler parameters
FADEOUTLENGTH = 30000

########
# Midi #
########
# Only get midi message from one channel
MIDI_CHANNEL_IGNORE = False
MIDI_CHANNEL = 16
USE_MIDI_VIRTUAL_PORT = True

##############
# Components #
##############

# Tell samplerbox to clean gpio when stopped
USE_GPIO = False

# Enable display function for 16x2
USE_LCD16x2 = False
# Enable MIDI IN via SerialPort (e.g. GPIO UART pins)
USE_SERIALPORT_MIDI = False

# 7-segment display via I2C
USE_I2C_7SEGMENTDISPLAY = False

# Adafruit LCD Display
USE_ADAFRUITLCD = False

# HD44780 based 16x2 LCD
USE_HD44780_16x2_LCD = False

# Use momentary buttons (GPIO) to change preset
USE_BUTTONS = False

# ToneControl
LOW_EQ_FREQ = 80.0
HIGH_EQ_FREQ = 8000.0
HIGH_EQ = (2 * HIGH_EQ_FREQ) / SAMPLERATE
LOW_EQ = (2 * LOW_EQ_FREQ) / SAMPLERATE

# Load local config if available
import os.path
if os.path.isfile(LOCAL_CONFIG):
    execfile(LOCAL_CONFIG)

print "\n"
print VERSION1
print VERSION2
print "\nLoading soundcard ...."


#########################################
# IMPORT
# MODULES
#########################################

import wave
import time
import curses
import numpy
import os
import glob
import re
import sounddevice
import threading
from chunk import Chunk
import struct
import rtmidi_python as rtmidi
import samplerbox_audio
import ctypes
from filters import FilterType, Filter, FilterChain
from utility import byteToPCM, floatToPCM, pcmToFloat, sosfreqz
from collections import OrderedDict
from time import sleep
import RPi.GPIO as GPIO

from ctypes import *

#############################################################
# Alsa error management
#############################################################
# Solution by livibetter
# Source: http://stackoverflow.com/questions/7088672/pyaudio-working-but-spits-out-error-messages-each-time
# From alsa-lib Git 3fd4ab9be0db7c7430ebd258f2717a976381715d
# $ grep -rn snd_lib_error_handler_t
# include/error.h:59:typedef void (*snd_lib_error_handler_t)(const char *file, int line, const char *function, int err, const char *fmt, ...) /* __attribute__ ((format (printf, 5, 6))) */;
# Define our error handler type
ERROR_HANDLER_FUNC = CFUNCTYPE(None, c_char_p, c_int, c_char_p, c_int, c_char_p)


def py_error_handler(filename, line, function, err, fmt):
    pass
c_error_handler = ERROR_HANDLER_FUNC(py_error_handler)

asound = cdll.LoadLibrary('libasound.so')
# Set error handler
asound.snd_lib_error_set_handler(c_error_handler)


#############
# Freeverb
#############

if USE_FREEVERB:
    print "Loading Freeverb ...."
    freeverb = cdll.LoadLibrary('./freeverb/revmodel.so')

    # Room size
    fvsetroomsize = freeverb.setroomsize
    fvsetroomsize.argtypes = [c_float]
    fvgetroomsize = freeverb.getroomsize
    fvgetroomsize.restype = c_float

    # Damp
    fvsetdamp = freeverb.setdamp
    fvsetdamp.argtypes = [c_float]
    fvgetdamp = freeverb.getdamp
    fvgetdamp.restype = c_float

    # Wet
    fvsetwet = freeverb.setwet
    fvsetwet.argtypes = [c_float]
    fvgetwet = freeverb.getwet
    fvgetwet.restype = c_float

    # Dry
    fvsetdry = freeverb.setdry
    fvsetdry.argtypes = [c_float]
    fvgetdry = freeverb.getdry
    fvgetdry.restype = c_float

    # Width
    fvsetwidth = freeverb.setwidth
    fvsetwidth.argtypes = [c_float]
    fvgetwidth = freeverb.getwidth
    fvgetwidth.restype = c_float

    # Mode
    fvsetmode = freeverb.setmode
    fvsetmode.argtypes = [c_float]
    fvgetmode = freeverb.getmode
    fvgetmode.restype = c_float

    c_float_p = ctypes.POINTER(ctypes.c_float)
    c_short_p = ctypes.POINTER(ctypes.c_short)
    freeverbprocess = freeverb.process
    freeverbprocess.argtypes = [c_float_p, c_float_p, c_int]

    # This part is not used:
    freeverbmix = freeverb.mix
    freeverbmix.argtypes = [c_short_p, c_float_p, c_float, c_int]
    freeverbmixback = freeverb.mixback
    freeverbmixback.argtypes = [c_float_p, c_float_p, c_float, c_short_p, c_float, c_short_p, c_float, c_int]

# Functions
def setroomsize(val):
    fvsetroomsize(val/127.0)
    display('Roomsize: '+str(val))


def setdamp(val):
    fvsetdamp(val/127.0)
    display('Damping: '+str(val))


def setwet(val):
    fvsetwet(val/127.0)
    display('Wet: '+str(val))


def setdry(val):
    fvsetdry(val/127.0)
    display('Dry: '+str(val))


def setwidth(val):
    fvsetwidth(val/127.0)
    display('Width: '+str(val))


# Backing Track variables
wf_back = None
wf_click = None
BackingRunning = False

#########################################
# Fade out of samples
#########################################

# By default, float64
FADEOUT = numpy.linspace(1., 0., FADEOUTLENGTH)
FADEOUT = numpy.power(FADEOUT, 6)
FADEOUT = numpy.append(FADEOUT, numpy.zeros(FADEOUTLENGTH, numpy.float32)).astype(numpy.float32)
SPEED = numpy.power(2, numpy.arange(0.0, 84.0)/12).astype(numpy.float32)

# Samples variables
samples = {}
playingnotes = {}
sustainplayingnotes = []
sustain = False
playingsounds = []
globaltranspose = 0
basename = "<Empty>"

######################################
# Volumes from 0-127 0=-20db, 127=0db
######################################

# add to selection of samples, not to Velocity Volume
VelocitySelectionOffset = 0

globalvolume = 0
globalvolumeDB = 0
backvolume = 0
backvolumeDB = 0
clickvolume = 0
clickvolumeDB = 0

# Set Sampler volume


def setSamplerVol(vol):                 # volume in db
    global globalvolume, globalvolumeDB
    vol = (vol * 20.0/127.0) - 20
    globalvolumeDB = vol
    globalvolume = 10 ** (vol/20.0)

# Set Backing volume


def setBackVol(vol):                 # volume in db
    global backvolume, backvolumeDB
    vol = (vol * 20.0/127.0) - 20
    backvolumeDB = vol
    backvolume = 10 ** (vol/20.0)

# Set Click volume


def setClickVol(vol):                 # volume in db
    global clickvolume, clickvolumeDB
    vol = (vol * 20.0/127.0) - 20
    clickvolumeDB = vol
    clickvolume = 10 ** (vol/20.0)

setSamplerVol(0.6)
setBackVol(50)
setClickVol(50)


#########################################
# SLIGHT MODIFICATION OF PYTHON'S WAVE MODULE
# TO READ CUE MARKERS & LOOP MARKERS
#########################################

class waveread(wave.Wave_read):

    def initfp(self, file):
        self._convert = None
        self._soundpos = 0
        self._cue = []
        self._loops = []
        self._ieee = False
        self._file = Chunk(file, bigendian=0)
        if self._file.getname() != 'RIFF':
            raise Error, 'file does not start with RIFF id'
        if self._file.read(4) != 'WAVE':
            raise Error, 'not a WAVE file'
        self._fmt_chunk_read = 0
        self._data_chunk = None
        while 1:
            self._data_seek_needed = 1
            try:
                chunk = Chunk(self._file, bigendian=0)
            except EOFError:
                break
            chunkname = chunk.getname()
            if chunkname == 'fmt ':
                self._read_fmt_chunk(chunk)
                self._fmt_chunk_read = 1
            elif chunkname == 'data':
                if not self._fmt_chunk_read:
                    raise Error, 'data chunk before fmt chunk'
                self._data_chunk = chunk
                self._nframes = chunk.chunksize // self._framesize
                self._data_seek_needed = 0
            elif chunkname == 'cue ':
                numcue = struct.unpack('<i', chunk.read(4))[0]
                for i in range(numcue):
                    id, position, datachunkid, chunkstart, blockstart, sampleoffset = struct.unpack('<iiiiii', chunk.read(24))
                    self._cue.append(sampleoffset)
            elif chunkname == 'smpl':
                manuf, prod, sampleperiod, midiunitynote, midipitchfraction, smptefmt, smpteoffs, numsampleloops, samplerdata = struct.unpack(
                    '<iiiiiiiii', chunk.read(36))
                for i in range(numsampleloops):
                    cuepointid, type, start, end, fraction, playcount = struct.unpack('<iiiiii', chunk.read(24))
                    self._loops.append([start, end])
            chunk.skip()
        if not self._fmt_chunk_read or not self._data_chunk:
            raise Error, 'fmt chunk and/or data chunk missing'

    def getmarkers(self):
        return self._cue

    def getloops(self):
        return self._loops


#########################################
# MIXER CLASSES
#########################################

class PlayingSound:

    def __init__(self, sound, note, vel):
        self.sound = sound
        self.pos = 0
        self.fadeoutpos = 0
        self.isfadeout = False
        self.note = note
        self.vel = vel

    def fadeout(self, i):
        self.isfadeout = True

    def stop(self):
        try:
            playingsounds.remove(self)
        except:
            pass


class Sound:

    def __init__(self, filename, midinote, velocity):
        wf = waveread(filename)
        self.fname = filename
        self.midinote = midinote
        self.velocity = velocity
        if wf.getloops():
            self.loop = wf.getloops()[0][0]
            self.nframes = wf.getloops()[0][1] + 2
        else:
            self.loop = -1
            self.nframes = wf.getnframes()

        self.data = self.frames2array(wf.readframes(self.nframes), wf.getsampwidth(), wf.getnchannels())

        wf.close()

    def play(self, note, vel):
        snd = PlayingSound(self, note, vel)
        print "[  WAV   ] " + self.fname
        playingsounds.append(snd)
        return snd

    def frames2array(self, data, sampwidth, numchan):
        if sampwidth == 2:
            npdata = numpy.fromstring(data, dtype=numpy.int16)
        elif sampwidth == 3:
            npdata = samplerbox_audio.binary24_to_int16(data, len(data)/3)
        if numchan == 1:
            npdata = numpy.repeat(npdata, 2)
        return npdata


#########################################
# AUDIO CALLBACK
#########################################

def AudioCallback(outdata, frame_count, time_info, status):
    global playingsounds, SampleLoading
    global BackingRunning
    global BackWav, BackIndex, ClickWav, ClickIndex
    global globalvolume, backvolume, clickvolume
    rmlist = []
    # print "sounds: " +str(len(playingsounds)) + " notes: " + str(len(playingnotes)) + " sust: " + str(len(sustainplayingnotes))
    playingsounds = playingsounds[-MAX_POLYPHONY:]
    b = samplerbox_audio.mixaudiobuffers(playingsounds, rmlist, frame_count, FADEOUT, FADEOUTLENGTH, SPEED)

    for e in rmlist:
        try:
            playingsounds.remove(e)
        except:
            pass

    # b *= globalvolume

    if USE_FREEVERB:
        b_temp = b
        freeverbprocess(b_temp.ctypes.data_as(c_float_p), b.ctypes.data_as(c_float_p), frame_count)

    # IF USE_TONECONTOL
    #   b = numpy.array(chain.filter(bb))
    #   b=bb

    if CHANNELS == 4:  # 4 channel playback
        # if backingtrack running: add in the audio
        if BackingRunning:
            BackData = BackWav[BackIndex:BackIndex+2*frame_count]
            ClickData = ClickWav[ClickIndex:ClickIndex+2*frame_count]
            BackIndex += 2*frame_count
            ClickIndex += 2*frame_count
            if len(b) != len(BackData) or len(b) != len(ClickData):
                BackingRunning = False
                BackData = None
                BackIndex = 0
                ClickData = None
                ClickIndex = 0

        if BackingRunning:
            newdata = (backvolume * BackData + b * globalvolume)
            Click = ClickData * clickvolume
        else:
            Click = numpy.zeros(frame_count*2, dtype=numpy.float32)
            newdata = b * globalvolume

        #  putting streams in 4 channel audio by magic in numpy reshape
        a1 = newdata.reshape(frame_count, 2)
        a2 = Click.reshape(frame_count, 2)
        ch4 = numpy.hstack((a1, a2)).reshape(1, frame_count*4)

        # Mute while loading Sample or BackingTrack
        # otherwise there could be dirty hick-ups
        if SampleLoading or (BackLoadingPerc > 0 and BackLoadingPerc < 100):
            ch4 *= 0
        return (ch4.astype(numpy.int16).tostring(), pyaudio.paContinue)

    else:  # 2 Channel playback
        # if backingtrack running: add in the audio
        if BackingRunning:
            BackData = BackWav[BackIndex:BackIndex+2*frame_count]
            BackIndex += 2*frame_count
            if len(b) != len(BackData):
                BackingRunning = False
                BackData = None
                BackIndex = 0

        if BackingRunning:
            newdata = (backvolume * BackData + b * globalvolume)
        else:
            newdata = b * globalvolume

    outdata[:] = newdata.reshape(outdata.shape)


#########################################
# MIDI CALLBACK
#########################################

def MidiCallback(message, time_stamp):
    global playingnotes, sustain, sustainplayingnotes
    global preset, VelocitySelectionOffset

    # Type
    messagetype = message[0] >> 4
    if messagetype == 13:
            return

    # Channel
    messagechannel = (message[0] & 15) + 1

    # Note
    note = message[1] if len(message) > 1 else None
    midinote = note

    # Velocity
    velocity = message[2] if len(message) > 2 else None

    print "[C:" + str(messagechannel) + "][T:" + str(messagetype) + "] " + str(note) + " -- " + str(velocity)

    # Special keys from Kurzweil
    if len(message) == 1 and message[0] == 250:  # playbutton Kurzweil
        StartTrack()

    if len(message) == 1 and message[0] == 252:  # stopbutton Kurzweil
        StopTrack()

    # You can ignore midi message from other midi channel
    if messagechannel == MIDI_CHANNEL or MIDI_CHANNEL_IGNORE:

        # If messagetype is note on and velocity 0
        # Send note off
        if messagetype == 9 and velocity == 0:
            messagetype = 8

        # Note on
        if messagetype == 9:
            midinote += globaltranspose

            # Scale the selected sample based on velocity
            # The volume will be kept, this will normally make the sound brighter
            SelectVelocity = (velocity * (127-VelocitySelectionOffset)/127) + VelocitySelectionOffset

            # Sustain
            for n in sustainplayingnotes:
                if n.note == midinote:
                    n.fadeout(500)
            try:
                playingnotes.setdefault(midinote, []).append(samples[midinote, SelectVelocity].play(midinote, velocity))
            except:
                pass

        # Note Off
        elif messagetype == 8:
            midinote += globaltranspose
            if midinote in playingnotes:
                for n in playingnotes[midinote]:
                    if sustain:
                        sustainplayingnotes.append(n)
                    else:
                        n.fadeout(50)
                playingnotes[midinote] = []

        # Program change
        elif messagetype == 12:
            print 'Program change ' + str(note)

            if preset != note:
                preset = note
                LoadSamples()

        # Sustain pedal off
        elif (messagetype == 11) and (note == 64) and (velocity < 64):
            for n in sustainplayingnotes:
                n.fadeout(50)
            sustainplayingnotes = []
            sustain = False

        # Sustain pedal on
        elif (messagetype == 11 and
              note == 64 and
              velocity >= 64):
            sustain = True

        # Start Track
        elif (message[0] == 176 and
              message[1] == 29 and
              message[2] == 127):
            StartTrack()

        else:

            if messagetype == 11:  # CC
                # if message[1]==1:  #Modwheel

                # Volume
                if message[1] == 6:               # slider A
                    #setSamplerVol(message[2])
                    pass
                # Velocity Offset
                elif message[1] == 13:            # slider B
                    VelocitySelectionOffset = message[2]
                    print "Velocity Offset: "+str(message[2])
                    display('Vel Offset:'+str(message[2]))
                # BackVolume track
                elif message[1] == 22:            # slider C
                    setBackVol(message[2])
                # Click track
                elif message[1] == 23:            # slider D
                    setClickVol(message[2])

                # elif message[1]==25:
                #    updateFilter(0, LOW_EQ, message[2]/8.0 , 1 )
                # elif message[1]==26:
                #    updateFilter(1, HIGH_EQ, message[2]/8.0 , 0.5 )

                elif message[1] == 25:            # slider F
                    setwidth(message[2])
                elif message[1] == 26:            # slider G
                    setdamp(message[2])
                elif message[1] == 27:            # slider H
                    setroomsize(message[2])
                elif message[1] == 28:            # slider I
                    setwet(message[2])

                elif message[1] == 32:    # midibank --> load sampletrack
                    LoadTrack(message[2])

                else:
                    display('C'+str(messagechannel)+'CC'+str(message[1])+'>'+str(message[2]))


#########################################
# LOAD SAMPLES
#
#########################################

LoadingThread = None
LoadingInterrupt = False


def LoadSamples():
    global LoadingThread
    global LoadingInterrupt

    if LoadingThread:
        LoadingInterrupt = True
        LoadingThread.join()
        LoadingThread = None

    LoadingInterrupt = False
    LoadingThread = threading.Thread(target=ActuallyLoad)
    LoadingThread.daemon = True
    LoadingThread.start()

NOTES = ["c", "c#", "d", "d#", "e", "f", "f#", "g", "g#", "a", "a#", "b"]

SampleLoading = False


def ActuallyLoad():
    # print "Thread load"
    global preset
    global samples
    global playingsounds, SampleLoading
    global globalvolume, globaltranspose, basename

    playingsounds = []
    samples = {}
    globalvolume = 0.1 #Default volume
    globaltranspose = 0
    basename = next((f for f in os.listdir(SAMPLES_DIR) if f.startswith("%d " % preset)), None)      # or next(glob.iglob("blah*"), None)
    if basename:
        dirname = os.path.join(SAMPLES_DIR, basename)
    if not basename:
        print 'Preset empty: ' + str(preset)
        display('Preset empty: %s' % preset)
        return
    print "[SAMPLES]: " + basename
    display('load: ' + basename)

    SampleLoading = True
    definitionfname = os.path.join(dirname, "definition.txt")
    if os.path.isfile(definitionfname):
        with open(definitionfname, 'r') as definitionfile:
            for i, pattern in enumerate(definitionfile):
                try:
                    if r'%%volume' in pattern:        # %%paramaters are global parameters
                        globalvolume = float(pattern.split('=')[1].strip())
                        continue
                    if r'%%transpose' in pattern:
                        globaltranspose = int(pattern.split('=')[1].strip())
                        continue
                    defaultparams = {'midinote': '0', 'velocity': '127', 'notename': ''}
                    if len(pattern.split(',')) > 1:
                        defaultparams.update(dict([item.split('=') for item in pattern.split(',', 1)[1].replace(' ', '').replace('%', '').split(',')]))
                    pattern = pattern.split(',')[0]
                    pattern = re.escape(pattern.strip())
                    pattern = pattern.replace(r"\%midinote", r"(?P<midinote>\d+)").replace(r"\%velocity", r"(?P<velocity>\d+)")\
                                     .replace(r"\%notename", r"(?P<notename>[A-Ga-g]#?[0-9])").replace(r"\*", r".*?").strip()    # .*? => non greedy
                    FileCnt = len(os.listdir(dirname))
                    FileCntCur = 0
                    for fname in os.listdir(dirname):
                        s = basename+"                  "
                        display(s[:12] + "%3d%%" % (FileCntCur*100/FileCnt))
                        FileCntCur += 1
                        if LoadingInterrupt:
                            SampleLoading = False
                            return
                        m = re.match(pattern, fname)
                        if m:
                            info = m.groupdict()
                            midinote = int(info.get('midinote', defaultparams['midinote']))
                            velocity = int(info.get('velocity', defaultparams['velocity']))
                            notename = info.get('notename', defaultparams['notename'])
                            if notename:
                                midinote = NOTES.index(notename[:-1].lower()) + (int(notename[-1])+2) * 12
                            samples[midinote, velocity] = Sound(os.path.join(dirname, fname), midinote, velocity)
                except:
                    print "Error in definition file, skipping line %s." % (i+1)

    else:
        for midinote in range(0, 127):
            if LoadingInterrupt:
                SampleLoading = False
                return
            file = os.path.join(dirname, "%d.wav" % midinote)
            if os.path.isfile(file):
                # print str(midinote) + ".wav"
                samples[midinote, 127] = Sound(file, midinote, 127)

    initial_keys = set(samples.keys())
    for midinote in xrange(128):
        lastvelocity = None
        for velocity in xrange(128):
            if (midinote, velocity) not in initial_keys:
                samples[midinote, velocity] = lastvelocity
            else:
                if not lastvelocity:
                    for v in xrange(velocity):
                        samples[midinote, v] = samples[midinote, velocity]
                lastvelocity = samples[midinote, velocity]
        if not lastvelocity:
            for velocity in xrange(128):
                try:
                    samples[midinote, velocity] = samples[midinote-1, velocity]
                except:
                    pass

    if len(initial_keys) == 0:
        print 'Preset empty: ' + str(preset)
        display('Preset empty: ' + str(preset))
    else:
        display('Loaded 100%')
        SampleLoading = False


########################################################################
# EN background playing
########################################################################

BackWav = 0
BackIndex = 0
BackLoaded = False
BackLoadingPerc = 0
Backbasename = 'Backing: Empty'
ClickWav = 0
ClickIndex = 0
BackNr = 0

BackLoadNr = -1


def LoadTrack(nr):
    global BackLoadNr
    print 'load: ' + str(nr)
    BackLoadNr = nr


def LoadTrackProcess():
    # print "BackLoad Thread launched"
    global BackWav, BackIndex
    global ClickWav, ClickIndex
    global BackingRunning, BackLoadingPerc, BackNr, BackLoaded, BackLen, Backbasename, BackLoadNr
    global CHANNELS

    # I added this check so it doesn't create a thread if it can't manage backtrack
    if CHANNELS > 2:
        while True:

            while BackLoadNr == BackNr:
                sleep(0.1)

            print ('loading: '+str(BackNr))

            BackLoaded = False
            BackLoadingPerc = 0
            BackNr = BackLoadNr
            BackingRunning = False
            BackIndex = 0     # nothing loaded
            ClickIndex = 0

            # print 'Loading backtrack'
            BackName = glob.glob(SAMPLES_DIR+str(BackNr)+"b*.wav")
            ClickName = glob.glob(SAMPLES_DIR+str(BackNr)+"c*.wav")
            # print 'Done'

            if not BackName or not ClickName:
                print 'Backing Track %s not found'
                continue

            print 'c'

            Backbasenamefull = os.path.basename(BackName[0])
            Backbasename = (((Backbasenamefull)[3:-4])+"     ")[:6]
            display('Load: '+Backbasenamefull)
            print 'd'

            BackingRunning = False
            time.sleep(1)
            print 'e'

            wf_back = wave.open(BackName[0], 'rb')
            BackWav = None
            CHUNCK = 1024*1024
            filesize = wf_back.getnframes()
            fileremain = filesize - CHUNCK
            print 'f'
            BackWav = numpy.fromstring(wf_back.readframes(CHUNCK), dtype=numpy.int16)
            while fileremain > 0:
                if BackLoadNr != BackNr:
                    break
                BackWav = numpy.append(BackWav, numpy.fromstring(wf_back.readframes(CHUNCK), dtype=numpy.int16))
                BackLoadingPerc = ((50 * (filesize-fileremain)) / filesize)
                fileremain -= CHUNCK
            print 'g'

            # BackWav = numpy.fromstring(wf_back.readframes(wf_back.getnframes()), dtype=numpy.int16)
            BackLen = len(BackWav)
            wf_back.close()

            if CHANNELS == 4:
                wf_click = wave.open(ClickName[0], 'rb')
                filesize = wf_click.getnframes()
                fileremain = filesize - CHUNCK
                ClickWav = numpy.fromstring(wf_click.readframes(CHUNCK), dtype=numpy.int16)
                print 'h'

                while fileremain > 0:
                    if BackLoadNr != BackNr:
                        break
                    ClickWav = numpy.append(ClickWav, numpy.fromstring(wf_click.readframes(CHUNCK), dtype=numpy.int16))
                    BackLoadingPerc = 50+ ((50 * (filesize-fileremain)) / filesize)
                    fileremain -= CHUNCK
                    print 'i'

                # ClickWav = numpy.fromstring(wf_click.readframes(wf_click.getnframes()), dtype=numpy.int16)
                # print "click: " + str(wf_click.getparams())
                wf_click.close()
                print 'j'

            if BackLoadNr == BackNr:
                BackLoaded = True
                BackLoadingPerc = 100
            else:
                print ('Early stop')
                BackLoaded = False
                BackLoadedPerc = 0
            display('')

        BackLoadThread = threading.Thread(target=LoadTrackProcess)
        BackLoadThread.deamon = True
        BackLoadThread.start()
    else:
        print "No enough channel to manage backtrack"


def StartTrack():
    global BackingRunning, BackLoaded, BackIndex
    # print "start Track: "
    if BackLoaded is True and BackIndex == 0:
        BackingRunning = True
        display('Playing Backing')
    else:
        pass
        print 'No Backingtrack Loaded or already running'
        display('No File Loaded')


def StopTrack():
    global BackingRunning, BackIndex, ClickIndex
    # print "stop Track: "
    if BackingRunning is True:
        display('Stop Backing')
        BackingRunning = False
        BackIndex = 0
        ClickIndex = 0


#############################
# EQ
#############################

filterTypes = OrderedDict({
    FilterType.LPButter: 'Low Pass (Flat)',
    FilterType.LPBrickwall: 'Low Pass (Brickwall)',
    FilterType.HPButter: 'High Pass (Flat)',
    FilterType.HPBrickwall: 'High Pass (Brickwall)',
    FilterType.LShelving: 'Low Shelf',
    FilterType.HShelving: 'High Shelf',
    FilterType.Peak: 'Peak'})


# fs = 44100
fs = SAMPLERATE
eps = 0.0000001


class Params:
    TYPE = 1
    F = 2
    G = 3
    Q = 4


deffs = [80, 1000, 3000, 5000, 15000]


chain = None


def initFilter():
    global deffs, chain, fs
    chain = FilterChain()
    chain._filters.append(Filter(FilterType.LShelving, LOW_EQ, 0, 1, enabled=True))
    # chain._filters.append(Filter(FilterType.HShelving, deffs[4], 0, 1, enabled = True))
    # chain._filters.append(Filter(FilterType.Peak, deffs[0], 0, 1, enabled = True))
    chain._filters.append(Filter(FilterType.Peak, HIGH_EQ, 0, 1, enabled=True))
    # chain._filters.append(Filter(FilterType.LPButter, deffs[3], 0, 1, enabled = True))
    # chain._filters.append(Filter(FilterType.HPButter, deffs[3], 0, 1, enabled = True))
    chain.reset()


def updateFilter(i, fc, g, Q):
    global chain
    global fs
    oldf = chain._filters[i]
    type = oldf._type
    # print oldf._type, oldf._fc, oldf._g, oldf._Q

    # fc_val = fc * 2 / fs
    # print fc_val, g, Q

    f = Filter(type, fc, g, Q)
    chain.updateFilt(i, f)
    # chain.changeFilt(i, type, fc, g, Q)
    chain.reset()


#########################################
# MAIN CODE
#########################################

initFilter()
updateFilter(0, 1000.0, 12.0, 1.0)

try:
    sd = sounddevice.OutputStream(device=AUDIO_DEVICE_ID, blocksize=512, samplerate=SAMPLERATE, channels=CHANNELS, dtype='int16', callback=AudioCallback)
    sd.start()
except:
    print "[ERROR] INVALID AUDIO DEVICE: " + str(AUDIO_DEVICE_ID)
    os.system("aplay -l")
    exit(1)

##############################################
#  16x2 Display
##############################################
#  (LCD RGB Plate Adafruit)
if USE_ADAFRUITLCD:
    execfile("./modules/adafruitlcd.py")

#  (HD44780)
if USE_HD44780_16x2_LCD:
    execfile("./modules/hd44780.py")

# If not display ignore display commands
if USE_LCD16x2 is False:
    def display(s):
        pass
#########################################

if USE_BUTTONS:
    execfile("./modules/buttons.py")

#########################################
# MIDI IN via SERIAL PORT
#########################################

if USE_SERIALPORT_MIDI:
    execfile("./modules/serialport_midi.py")



#########################################
# LOAD FIRST SOUNDBANK
#
#########################################

if USE_FREEVERB:
    fvsetdry(0.7)
    print "---- Freeverb ----"
    print 'Roomsize: ' + str(fvgetroomsize())
    print 'Damp: ' + str(fvgetdamp())
    print 'Wet: ' + str(fvgetwet())
    print 'Width: ' + str(fvgetwidth())
    print "------------------"

preset = 0
LoadSamples()


#########################################
# MIDI DEVICES DETECTION
# MAIN LOOP
#########################################



midi_in = [rtmidi.MidiIn()]


print len(midi_in[0].ports)
if len(midi_in[0].ports) < 2:
    if USE_MIDI_VIRTUAL_PORT:
        midi_virtual = rtmidi.MidiOut()
        midi_virtual.open_virtual_port("Midi")
        print "No midi device detected, Loading Midi Virtual port..."
previous = []

display('Running')

try:
    while True:

        for port in midi_in[0].ports:
            if port not in previous and 'Midi Through' not in port:
                midi_in.append(rtmidi.MidiIn())
                midi_in[-1].callback = MidiCallback
                midi_in[-1].open_port(port)
                print '[MIDI]: ' + port

        previous = midi_in[0].ports
        time.sleep(2)
except KeyboardInterrupt:
    print "\n-------------------------"
    print "\nSamplerbox is stopped\n"
    print "-------------------------"
except:
    print "---------  Unexpected error --------- "
finally:
    display('Stopped')
    if USE_GPIO:
        sleep(0.5)
        GPIO.cleanup()
    print VERSION1
