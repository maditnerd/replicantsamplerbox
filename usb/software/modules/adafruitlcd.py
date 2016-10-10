import Adafruit_CharLCD as LCD
import os
import subprocess

global lcd_inuse
print "Loading RGB LCD Plate ...."
USE_LCD16x2 = False
lcd_inuse = False

lcd = LCD.Adafruit_CharLCDPlate()
lcd.clear()
lcd.set_color(0.0, 1.0, 0.0)
lcd.message(VERSION1 + "\n" + VERSION2)
time.sleep(0.5)
lastbuttontime = 0
midiPreset = 0
lcd.set_color(0.0, 0.0, 0.0)
# Display a string


def displayText(s):
    lcd.clear()
    lcd.message(s)

# Display menu
def LCDMenu():
    global lastbuttontime
    global preset, lastbuttontime, globalvolume, globaltranspose, sustain, samplesList, nbInstruments
    global reverbSetting
    global midiList, midiPreset, nbMidi
    global midiPlaying
    global midiFileThread
    global debugMode
    global current_reverb, reverbPreset

    current_reverb = 1
    reverbPreset = ["Off", "Room", "Plate", "Hall", "Cavern"]
    midiPlaying = False
    debugMode = False
    menu = ["Instrument", "Volume", "Midi",  "Reverb", "Sustain", "Transpose", "Debug", "Quit"]
    menuItem = 0
    LastMenuItem = len(menu) - 1

    # Get instruments name
    samplesList = []
    for samplesDir in os.listdir(SAMPLES_DIR):
        nbsamples = int(samplesDir.split(" ", 2)[0])
        if nbsamples < 10:
            samplesList.append("0" + samplesDir)
        # samplesSplitted = samplesDir.split(" ", 2)
    for samplesDir in os.listdir(SAMPLES_DIR):
        nbsamples = int(samplesDir.split(" ", 2)[0])
        if nbsamples >= 10:
            samplesList.append(samplesDir)

    samplesList.sort()
    print samplesList

    nbInstruments = len(samplesList)
    displayText(menu[menuItem] + "\n" + samplesList[0])

    # Get midi name
    midiList = []
    for midiFile in os.listdir(MIDI_DIR):
        midiList.append(midiFile)

    midiList.sort()
    print midiList

    nbMidi = len(midiList) - 1
    print nbMidi

    while True:
        now = time.time()

        # If RIGHT pressed
        if lcd.is_pressed(LCD.RIGHT) and (now - lastbuttontime) > 0.2:
            # Change item
            lastbuttontime = now
            print menuItem
            if menuItem == LastMenuItem:
                menuItem = 0
            else:
                menuItem = menuItem + 1
            #  Display value
            displayValue(menu[menuItem])

        # If LEFT pressed
        if lcd.is_pressed(LCD.LEFT) and (now - lastbuttontime) > 0.2:
            lastbuttontime = now
            menuItem = menuItem - 1
            if menuItem == -1:
                menuItem = LastMenuItem
            displayValue(menu[menuItem])

        # If UP pressed
        if lcd.is_pressed(LCD.UP) and (now - lastbuttontime) > 0.2:
            lastbuttontime = now
            if menu[menuItem] == "Quit":
                lcd.set_color(0.0, 0.0, 1.0)
                os.system("reboot")
            else:
                raiseValue(menu[menuItem])                        

        # If DOWN pressed
        if lcd.is_pressed(LCD.DOWN) and (now - lastbuttontime) > 0.2:
            lastbuttontime = now

            if menu[menuItem] == "Quit":
                lcd.set_color(0.0, 0.0, 1.0)
                os.system("reboot")
            else:
                lowerValue(menu[menuItem])

        # If SELECT pressed
        if lcd.is_pressed(LCD.SELECT) and (now - lastbuttontime) > 0.2:
            lastbuttontime = now
            if menu[menuItem] == "Debug":
                lcd.set_color(0.0, 1.0, 1.0)
                os.system("/media/debug.sh")
            if menu[menuItem] == "Quit":
                lcd.set_color(1.0, 0.0, 0.0)
                os.system("poweroff")
            if menu[menuItem] == "Midi":
                midifile = MIDI_DIR + "/" + midiList[midiPreset]
                if midiPlaying:
                    lcd.set_color(0.0,0.0,0.0)
                    os.system('kill -9 $(pgrep "aplaymidi")')
                    midiPlaying = False
                else:
                    midiFileThread = threading.Thread(target=playmidi, args=(midifile,))
                    midiFileThread.daemon = True
                    midiFileThread.start()
            else:
                LoadSamples()
        time.sleep(0.020)

# When UP is pressed
def playmidi(midifile):
    global midiPlaying
    lcd.set_color(1.0,1.0,0.0)
    midiPlaying = True
    exitcode = os.system("/usr/bin/aplaymidi " + midifile + " --port 128:0")
    if exitcode != 0:
        lcd.set_color(1.0,0.0,1.0)
        exitcode = os.system("/usr/bin/aplaymidi " + midifile + " --port 128:1")
    print exitcode
    midiPlaying = False
    lcd.set_color(0.0,0.0,0.0)

def change_reverb(current_reverb):
    if current_reverb == 0:
        setwidth(0)
        setdamp(0)
        setroomsize(0)
        setwet(0)
    elif current_reverb == 1:
        setwidth(50)
        setdamp(115)
        setroomsize(55)
        setwet(127)
    elif current_reverb == 2:
        setwidth(127)
        setdamp(127)
        setroomsize(20)
        setwet(127)
    elif current_reverb == 3:
        setwidth(16)
        setdamp(70)
        setroomsize(115)
        setwet(100)
    elif current_reverb == 4:
        setwidth(16)
        setdamp(70)
        setroomsize(115)
        setwet(100)

def raiseValue(item):
    global preset, lastbuttontime, globalvolume, globaltranspose, sustain, nbInstruments
    global midiList, midiPreset, nbMidi
    global current_reverb, reverbPreset
    if item == "Instrument":
        if preset < nbInstruments - 1:
            preset += 1
            print "preset:" + str(preset)
            print "instru:" + str(nbInstruments)
            LoadSamples()
    elif item == "Midi":
        if midiPreset < nbMidi:
            midiPreset += 1
    elif item == "Volume":
        if globalvolume < 1:
            globalvolume = globalvolume + 0.1
    elif item == "Sustain":
        sustain = True
    elif item == "Transpose":
        globaltranspose = globaltranpose + 1
    elif item == "Reverb":
        if current_reverb < len(reverbPreset) - 1:
            current_reverb += 1
            change_reverb(current_reverb)
    displayValue(item)

# Display value (on change)


def displayValue(item):
    global preset, lastbuttontime, globalvolume, globaltranspose, sustain, samplesList
    global midiList, midiPreset
    global current_reverb, reverbPreset
    print item
    if item == "Instrument":
        value = samplesList[preset]
    elif item == "Midi":
        value = midiList[midiPreset]
    elif item == "Volume":
        value = globalvolume
    elif item == "Sustain":
        value = sustain
    elif item == "Transpose":
        value = globaltranspose
    elif item == "Debug":
        value = subprocess.check_output("hostname -I", shell=True).strip()
    elif item == "Reverb":
        value = reverbPreset[current_reverb]
    else:
        value = ""
    displayText(item + "\n" + str(value))

# When DOWN is pressed


def lowerValue(item):
    global preset, lastbuttontime, globalvolume, globaltranspose, sustain
    global midiList, midiPreset
    global current_reverb
    if item == "Instrument":
        if preset > 0:
            preset -= 1
            LoadSamples()
    elif item == "Midi":
        if midiPreset > 0:
            midiPreset -= 1
    elif item == "Volume":
        if globalvolume > 0:
            globalvolume = globalvolume - 0.1
    elif item == "Sustain":
        sustain = False
    elif item == "Transpose":
        globaltranpose = globaltranspose - 1
    elif item == "Reverb":
        if current_reverb > 0:
           current_reverb -= 1
           change_reverb(current_reverb)
    displayValue(item)

LCDMenuThread = threading.Thread(target=LCDMenu)
LCDMenuThread.daemon = True
LCDMenuThread.start()
