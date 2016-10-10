print "Loading buttons ..."
import RPi.GPIO as GPIO
USE_GPIO = True
lastbuttontime = 0

def Buttons():
    fxGPIO.setmode(GPIO.BCM)
    GPIO.setup(18, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    GPIO.setup(17, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    global preset, lastbuttontime
    while True:
        now = time.time()
        if not GPIO.input(18) and (now - lastbuttontime) > 0.2:
            lastbuttontime = now
            preset -= 1
            if preset < 0:
                preset = 127
            LoadSamples()

        elif not GPIO.input(17) and (now - lastbuttontime) > 0.2:
            lastbuttontime = now
            preset += 1
            if preset > 127:
                preset = 0
            LoadSamples()

        time.sleep(0.020)

ButtonsThread = threading.Thread(target=Buttons)
ButtonsThread.daemon = True
ButtonsThread.start()