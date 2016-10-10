import rtmidi_python as rtmidi
import os
midi_virtual = rtmidi.MidiIn()
midi_virtual.open_virtual_port("Midi")
print "Loading Midi Virtual port..."
os.system("aplaymidi -l")
