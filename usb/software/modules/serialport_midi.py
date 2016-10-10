print "Loading serialport midi ..."
import serial

# see hack in /boot/cmdline.txt : 38400 is 31250 baud for MIDI!
ser = serial.Serial('/dev/ttyAMA0', baudrate=38400)

def MidiSerialCallback():
    message = [0, 0, 0]
    while True:
        i = 0
        while i < 3:
            data = ord(ser.read(1))  # read a byte
            if data >> 7 != 0:
                i = 0      # status byte!   this is the beginning of a midi message: http://www.midi.org/techspecs/midimessages.php
            message[i] = data
            i += 1
            if i == 2 and message[0] >> 4 == 12:  # program change: don't wait for a third byte: it has only 2 bytes
                message[2] = 0
                i = 3
        MidiCallback(message, None)

MidiThread = threading.Thread(target=MidiSerialCallback)
MidiThread.daemon = True
MidiThread.start()
