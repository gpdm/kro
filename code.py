# Itsy Bitsy M0 Express IO demo
# Welcome to CircuitPython 4 :)

import os
import time
import random
import board
from digitalio import DigitalInOut, Direction, Pull
import adafruit_dotstar
import pwmio
from analogio import AnalogIn

# Audio playback
import audioio
import audiocore


# ######################## CONFIG ##############################

# path definitions: where is our media files
p_audio = '/media'

# scanner iterations: how many times to make the swirl
scannerMaxIterations = 6

# scanner pattern: valid values are 'alpha' and 'beta'
defaultScanPattern = "alpha"

# ###################### END CONFIG ############################
# ----------- do not change anything below this line -----------


# One pixel connected internally
dot = adafruit_dotstar.DotStar(board.APA102_SCK, board.APA102_MOSI, 1, brightness=0.5)

# Built in red LED
led = DigitalInOut(board.D13)
led.direction = Direction.OUTPUT

# Analog input on A1
analog1in = AnalogIn(board.A1)

# digital input on A4
buttons = []
for p in [board.A4]:
    button = DigitalInOut(p)
    button.direction = Direction.INPUT
    button.pull = Pull.UP
    buttons.append(button)


# PWM output on D9, D10, D11
s1 = pwmio.PWMOut(board.D9,  frequency=10, duty_cycle=0)
s2 = pwmio.PWMOut(board.D10, frequency=10, duty_cycle=0)
s3 = pwmio.PWMOut(board.D11, frequency=10, duty_cycle=0)


# Scanner classes
class Scanner:
    state = False
    iterator = 0
    offset = 1

class allLightsOn:
    state = True
    iterator = 0
    brightness = 0

# Pattern Alpha uses static duty cycle
# one LED at a time, without trailing lights effect
# this one looks nicer, as it doesn't have the flickering effect
scanPatternAlpha = {}

scanPatternAlpha["1"] = [65000, 0, 0]
scanPatternAlpha["2"] = [0, 65000, 0]
scanPatternAlpha["3"] = [0, 0, 65000]
scanPatternAlpha["4"] = [0, 65000, 0]

# Pattern Beta uses dynamic duty cycle
# multiple LEDs at the time, for different brightness,
# to simulate the trailing lights effect.
# however, it has some visible flickering.
scanPatternBeta = {}

scanPatternBeta["1"] = [65000, 0, 0]
scanPatternBeta["2"] = [65000, 13000, 0]
scanPatternBeta["3"] = [65000, 26000, 0]
scanPatternBeta["4"] = [39000, 39000, 0]
scanPatternBeta["5"] = [26000, 52000, 0]
scanPatternBeta["6"] = [13000, 65000, 0]

scanPatternBeta["7"] = [0, 65000, 0]
scanPatternBeta["8"] = [0, 65000, 13000]
scanPatternBeta["9"] = [0, 52000, 25000]
scanPatternBeta["10"] = [0, 39000, 39000]
scanPatternBeta["11"] = [0, 25000, 52000]
scanPatternBeta["12"] = [0, 13000, 65000]

scanPatternBeta["13"] = [0, 0, 65000]
scanPatternBeta["14"] = [0, 13000, 65000]
scanPatternBeta["15"] = [0, 25000, 52000]
scanPatternBeta["16"] = [0, 39000, 39000]
scanPatternBeta["17"] = [0, 52000, 25000]
scanPatternBeta["18"] = [0, 65000, 13000]

scanPatternBeta["19"] = [0, 65000, 0]
scanPatternBeta["20"] = [13000, 65000, 0]
scanPatternBeta["21"] = [26000, 52000, 0]
scanPatternBeta["22"] = [39000, 39000, 0]
scanPatternBeta["23"] = [52000, 26000, 0]
scanPatternBeta["24"] = [65000, 13000, 0]


# register defined scan patterns and timers
scanPatterns = {"alpha": scanPatternAlpha, "beta": scanPatternBeta}
scanTimers = {"alpha": 0.2, "beta": 0.008}


# sanitize config
if defaultScanPattern != "alpha" and defaultScanPattern != "beta":
    defaultScanPattern = "alpha"


# ######################## HELPERS ##############################

# Helper to get media files
def getMediaFiles():
    return [f for f in os.listdir(p_audio) if f.endswith('.wav')]

# Helper to convert analog input to voltage
def getVoltage(pin):
    return (pin.value * 3.3) / 65536

# Helper to give us a nice color swirl
def wheel(pos):
    if (pos < 0):
        return [0, 0, 0]
    if (pos > 255):
        return [0, 0, 0]
    else:
        return [int(pos * 3), 0, 0]

# Helper for media playback
def play_file(filename):
    print("")
    print("----------------------------------")
    print("playing file " + filename)
    with open(p_audio + '/' + filename, "rb") as f:
        with audiocore.WaveFile(f) as wave:
            with audioio.AudioOut(board.A0) as a:
                a.play(wave)
                while a.playing:
                    pass
    print("finished")
    print("----------------------------------")

# ######################## MAIN LOOP ##############################

# load media files
audiofiles = getMediaFiles()

# track the R(GB) pulsation up/down
rgb_r = 0
rgb_r_direction = 1

while True:
    # pulsate the status LED between various hues of red
    dot[0] = wheel(rgb_r)
    if rgb_r >= 164:
        rgb_r_direction = -1
    elif rgb_r <= 98:
        rgb_r_direction = 1
    rgb_r += 1 * rgb_r_direction

    # Read analog voltage on A1
    print("A1: %0.2f" % getVoltage(analog1in), end="\t")

    # Perform Scanner's "All Lights On" (only done once on power-up)
    #
    if allLightsOn.state:
        print("performing 'All Lights On' ...")

        if allLightsOn.brightness < 149:
            allLightsOn.brightness += 1

        for i in range(1):
            s1.duty_cycle = int(allLightsOn.brightness * 1 * 65535 / 150)
            s2.duty_cycle = int(allLightsOn.brightness * 1 * 65535 / 150)
            s3.duty_cycle = int(allLightsOn.brightness * 1 * 65535 / 150)

        allLightsOn.iterator += 1

        if allLightsOn.iterator == 149:
            time.sleep(1.0)
            s1.duty_cycle = 0
            s2.duty_cycle = 0
            s3.duty_cycle = 0
            allLightsOn.state = False
            Scanner.state = not allLightsOn.state

    # run standard scan pattern if we're past "All Lights On"
    if Scanner.state:
        print("performing 'Scanner' ...")

        # don't run Scanner more than Max Iterations
        # fixme get number of pattern entries
        if Scanner.iterator < (scannerMaxIterations * len(scanPatterns[defaultScanPattern])):
            Scanner.iterator += 1

            if Scanner.offset > len(scanPatterns[defaultScanPattern]):
                Scanner.offset = 1

            s1.duty_cycle = int(scanPatterns[defaultScanPattern][str(Scanner.offset)][0])
            s2.duty_cycle = int(scanPatterns[defaultScanPattern][str(Scanner.offset)][1])
            s3.duty_cycle = int(scanPatterns[defaultScanPattern][str(Scanner.offset)][2])

            time.sleep(scanTimers[defaultScanPattern])

            Scanner.offset += 1

        # clear Scanner if Max Iterations was reached
        else:
            Scanner.iterator = 0
            Scanner.state = False
            Scanner.offset = 1
            s1.duty_cycle = 0
            s2.duty_cycle = 0
            s3.duty_cycle = 0

    # read push button (front axis) on A5
    if not buttons[0].value:
        # don't run if scanner is active, or we see choppy scan pattern
        if not Scanner.state:
            print("front axis pressed", end="\t")
            # always play random audio first
            play_file(random.choice(audiofiles))
            # then enable the scanner
            Scanner.state = True
        else:
            print("Scanner is currently running, ignoring front axis key press")

    print("")
