import RPi.GPIO as GPIO
print "Loading HD44780 ..."
#########################################
#  based on 16x2 LCD interface code by Rahul Kar, see:
#  http://www.rpiblog.com/2012/11/interfacing-16x2-lcd-with-raspberry-pi.html
#########################################
USE_GPIO = True

usleep = lambda x: time.sleep(x/1000000.0)
msleep = lambda x: time.sleep(x/1000.0)


class HD44780:

    def __init__(self, pin_rs=7, pin_e=8, pins_db=[25, 24, 23, 18]):
        self.pin_rs = pin_rs
        self.pin_e = pin_e
        self.pins_db = pins_db

        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.pin_e, GPIO.OUT)
        GPIO.setup(self.pin_rs, GPIO.OUT)
        for pin in self.pins_db:
            GPIO.setup(pin, GPIO.OUT)

        self.clear()

    def clear(self):
        """ Blank / Reset LCD """

        self.cmd(0x33)  # Initialization by instruction
        msleep(5)
        self.cmd(0x33)
        usleep(100)
        self.cmd(0x32)  # set to 4-bit mode
        self.cmd(0x28)  # Function set: 4-bit mode, 2 lines
        # self.cmd(0x38) # Function set: 8-bit mode, 2 lines
        # Display control: Display on, cursor off, cursor blink off
        self.cmd(0x0C)
        self.cmd(0x06)  # Entry mode set: Cursor moves to the right
        # Clear Display: Clear & set cursor position to line 1 column 0
        self.cmd(0x01)

    def cmd(self, bits, char_mode=False):
        """ Send command to LCD """

        sleep(0.002)
        bits = bin(bits)[2:].zfill(8)

        GPIO.output(self.pin_rs, char_mode)

        for pin in self.pins_db:
            GPIO.output(pin, False)

        # for i in range(8):       # use range 4 for 4-bit operation
        for i in range(4):       # use range 4 for 4-bit operation
            if bits[i] == "1":
                GPIO.output(self.pins_db[::-1][i], True)

        GPIO.output(self.pin_e, True)
        usleep(1)      # command needs to be > 450 nsecs to settle
        GPIO.output(self.pin_e, False)
        usleep(100)    # command needs to be > 37 usecs to settle

        """ 4-bit operation start """
        for pin in self.pins_db:
            GPIO.output(pin, False)

        for i in range(4, 8):
            if bits[i] == "1":
                GPIO.output(self.pins_db[::-1][i-4], True)

        GPIO.output(self.pin_e, True)
        usleep(1)      # command needs to be > 450 nsecs to settle
        GPIO.output(self.pin_e, False)
        usleep(100)    # command needs to be > 37 usecs to settle
        """ 4-bit operation end """

    def message(self, text):
        """ Send string to LCD. Newline wraps to second line"""

        # Home Display: set cursor position to line 1 column 0
        self.cmd(0x02)
        x = 0
        for char in text:
            if char == '\n':
                self.cmd(0xC0)  # next line
                x = 0
            else:
                x += 1
                if x < 17: self.cmd(ord(char), True)


global TimeOut
lcd = HD44780()
DS1 = "Starting..."
DS1Cur = "--"
DS2 = "  "
DS2Cur = "  "
TimeOut = 0


def display(s):
    global DS1, DS2

    DS2 = s
    if DS2 == "":
        DS2 = basename
        TimeOutReset = 30   # 3 sec
        TimeOut = TimeOutReset
        DisplaySamplerName = True


def LCD_Process():
    global DS1, DS1Cur, DS2, DS2Cur
    global TimeOut, TimeOutReset, basename
    global basename, MIDI_CHANNEL, globalvolumeDB, backvolumeDB, clickvolumeDB, BackingRunning, BackLoaded, BackLoadingPerc, BackLen, BackIndex

    lcd.message('{:<16}'.format(VERSION1) + "\n" + '{:<16}'.format(VERSION2))
    sleep(3)

    while True:
        if TimeOut > 0:
            TimeOut -= 1

        if BackingRunning:
            ttotsec = (BackLen-BackIndex)/SAMPLERATE/2
            tmin = ttotsec/60
            tsec = ttotsec % 60
            ba = " %02d:%02d" % (tmin, tsec)
        elif BackLoaded:
            ba = Backbasename[-6:]  # " Ready"
        elif BackLoadingPerc > 0:
            ba = "  %3d%%" % BackLoadingPerc
        else:
            ba = " Empty"

    DS1 = "%03d%03d%03d %s" % (globalvolumeDB, backvolumeDB, clickvolumeDB, ba)

    if TimeOut == 1:
        DS2 = basename

    if (DS2Cur != DS2) or (DS1Cur != DS1):
        if (DS2Cur != DS2):
            TimeOut = TimeOutReset
        lcd.message(DS1 + "\n" + '{:<16}'.format(DS2))
        DS1Cur = DS1
        DS2Cur = DS2
        sleep(0.1)

LCDThread = threading.Thread(target=LCD_Process)
LCDThread.deamon = True
LCDThread.start()
