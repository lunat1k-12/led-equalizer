import pyaudio
import numpy as np
import _rpi_ws281x as ws

from scipy.fftpack import fft

CHUNK = 1024  # signal is split into CHUNK number of frames
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 44100  # (sampling rate) number of frames per second
AMPLITUDE = 2 ** 16 / 2

# LED configuration.
LED_CHANNEL = 0
LED_COUNT = 64  # How many LEDs to light.
LED_FREQ_HZ = 800000  # Frequency of the LED signal.  Should be 800khz or 400khz.
LED_DMA_NUM = 10  # DMA channel to use, can be 0-14.
LED_GPIO = 18  # GPIO connected to the LED signal line.  Must support PWM!
LED_BRIGHTNESS = 100  # Set to 0 for darkest and 255 for brightest
LED_INVERT = 0  # Set to 1 to invert the LED signal, good if using NPN
#                             transistor as a 3.3V->5V level converter.  Keep at 0
#                             for a normal/non-inverted signal.

p = pyaudio.PyAudio()

# 0x200000 - green
# 0x001023 - purple
# yellow - 0x202000
# red - 0x002000
# DOT_COLORS_LEVEL = [0x000200,
#                     0x000020,
#                     0x000002,
#                     0x000022,
#                     0x000202,
#                     0x000222,
#                     0x022022,
#                     0x021111]

DOT_COLORS_LEVEL = [0x100000,
                    0x100000,
                    0x100000,
                    0x100000,
                    0x101000,
                    0x101000,
                    0x001000,
                    0x001000]
EMPTY_COLOR = 0x000000

stream = p.open(format=FORMAT,
                channels=CHANNELS,
                rate=RATE,
                input=True,
                frames_per_buffer=CHUNK)

print("Recording...")

# Create a ws2811_t structure from the LED configuration.
# Note that this structure will be created on the heap so you need to be careful
# that you delete its memory by calling delete_ws2811_t when it's not needed.
leds = ws.new_ws2811_t()

# Initialize all channels to off
for channum in range(2):
    channel = ws.ws2811_channel_get(leds, channum)
    ws.ws2811_channel_t_count_set(channel, 0)
    ws.ws2811_channel_t_gpionum_set(channel, 0)
    ws.ws2811_channel_t_invert_set(channel, 0)
    ws.ws2811_channel_t_brightness_set(channel, 0)

channel = ws.ws2811_channel_get(leds, LED_CHANNEL)

ws.ws2811_channel_t_count_set(channel, LED_COUNT)
ws.ws2811_channel_t_gpionum_set(channel, LED_GPIO)
ws.ws2811_channel_t_invert_set(channel, LED_INVERT)
ws.ws2811_channel_t_brightness_set(channel, LED_BRIGHTNESS)

ws.ws2811_t_freq_set(leds, LED_FREQ_HZ)
ws.ws2811_t_dmanum_set(leds, LED_DMA_NUM)

# Initialize library with LED configuration.
resp = ws.ws2811_init(leds)
if resp != ws.WS2811_SUCCESS:
    message = ws.ws2811_get_return_t_str(resp)
    raise RuntimeError('ws2811_init failed with code {0} ({1})'.format(resp, message))


# Wrap following code in a try/finally to ensure cleanup functions are called
# after library is initialized.

def avg(array):
    return sum(array) / len(array)


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


try:
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
                ws.ws2811_led_set(channel, array[index], EMPTY_COLOR)
            for index in range(ed[i]):
                if index < 8:
                    ws.ws2811_led_set(channel, array[index], DOT_COLORS_LEVEL[index])

        # Send the LED color data to the hardware.
        resp = ws.ws2811_render(leds)
        prevEd = ed
        if resp != ws.WS2811_SUCCESS:
            message = ws.ws2811_get_return_t_str(resp)
            raise RuntimeError('ws2811_render failed with code {0} ({1})'.format(resp, message))
        # print(ed)

finally:
    # Ensure ws2811_fini is called before the program quits.
    print("Finally")
    ws.ws2811_fini(leds)
    # Example of calling delete function to clean up structure memory.  Isn't
    # strictly necessary at the end of the program execution here, but is good practice.
    ws.delete_ws2811_t(leds)
