import pyaudio
import numpy as np
from rpi_ws281x import Color, PixelStrip, ws

from scipy.fftpack import fft

CHUNK = 1024  # signal is split into CHUNK number of frames
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 44100  # (sampling rate) number of frames per second
AMPLITUDE = 2 ** 16 / 2

# LED strip configuration:
LED_COUNT = 64  # Number of LED pixels.
LED_PIN = 18  # GPIO pin connected to the pixels (must support PWM!).
LED_FREQ_HZ = 800000  # LED signal frequency in hertz (usually 800khz)
LED_DMA = 10  # DMA channel to use for generating signal (try 10)
LED_BRIGHTNESS = 35  # Set to 0 for darkest and 255 for brightest
LED_INVERT = False  # True to invert the signal (when using NPN transistor level shift)
LED_CHANNEL = 0

# LED_STRIP = ws.SK6812_STRIP_RGBW
LED_STRIP = ws.WS2811_STRIP_RGB

p = pyaudio.PyAudio()

# GRB
DOT_COLORS_LEVEL_GYR = [Color(255, 0, 0),
                        Color(255, 0, 0),
                        Color(255, 0, 0),
                        Color(255, 0, 0),
                        Color(200, 243, 0),
                        Color(200, 243, 0),
                        Color(0, 255, 0),
                        Color(0, 255, 0)]

DOT_COLORS_LEVEL_PURPLE = [Color(0, 102, 255),
                           Color(0, 102, 255),
                           Color(0, 102, 255),
                           Color(0, 102, 255),
                           Color(0, 102, 255),
                           Color(0, 102, 255),
                           Color(0, 255, 102),
                           Color(0, 255, 102)]

stream = p.open(format=FORMAT,
                channels=CHANNELS,
                rate=RATE,
                input=True,
                frames_per_buffer=CHUNK)

print("Recording...")


strip = PixelStrip(LED_COUNT, LED_PIN, LED_FREQ_HZ, LED_DMA, LED_INVERT, LED_BRIGHTNESS, LED_CHANNEL, LED_STRIP)
strip.begin()


matrix = [[7, 15, 23, 31, 39, 47, 55, 63],
          [6, 14, 22, 30, 38, 46, 54, 62],
          [5, 13, 21, 29, 37, 45, 53, 61],
          [4, 12, 20, 28, 36, 44, 52, 60],
          [3, 11, 19, 27, 35, 43, 51, 59],
          [2, 10, 18, 26, 34, 42, 50, 58],
          [1, 9, 17, 25, 33, 41, 49, 57],
          [0, 8, 16, 24, 32, 40, 48, 56]]

prevEd = [0, 0, 0, 0, 0, 0, 0, 0]

delays = [0, 0, 0, 0, 0, 0, 0, 0]

while True:
    data = np.frombuffer(stream.read(CHUNK, exception_on_overflow=False), dtype=np.int16)
    y_fft = fft(data)

    processed_data = np.abs(y_fft[0:(CHUNK)]) * 1 / (AMPLITUDE * CHUNK) * 100

    ed = [int(max(processed_data[0:128])),
          int(max(processed_data[128:256] * 10)),
          int(max(processed_data[256:384] * 10)),
          int(max(processed_data[384:512] * 10)),
          int(max(processed_data[512:640] * 10)),
          int(max(processed_data[640:768] * 10)),
          int(max(processed_data[768:896] * 10)),
          int(max(processed_data[896:1024]))]

    for i in range(8):
        if ed[i] > 8:
            ed[i] = 8

    for i in range(8):
        if ed[i] < prevEd[i] & prevEd[i] - ed[i] < 5:
            if delays[i] == 2:
                ed[i] = prevEd[i] - 1
                delays[i] = 0
            else:
                ed[i] = prevEd[i]
                delays[i] = delays[i] + 1

    for i in range(8):
        array = matrix[i]
        for index in range(8):
            strip.setPixelColor(array[index], Color(0, 0, 0))
        for index in range(ed[i]):
            if index < 8:
                strip.setPixelColor(array[index], DOT_COLORS_LEVEL_PURPLE[index])
    strip.show()
    prevEd = ed
