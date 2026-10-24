
import time
import pygame
from rpi_ws281x import PixelStrip, Color

# LED strip configuration
LED_COUNT = 50
LED_PIN = 18
LED_FREQ_HZ = 800000
LED_DMA = 10
LED_BRIGHTNESS = 40
LED_INVERT = False
LED_CHANNEL = 0

# Pulse animation
PULSE_WIDTH = 8
FRAME_DELAY = 0.055
PULSE_COLOUR = (255, 187, 40)


def clear_strip(strip):
    for i in range(LED_COUNT):
        strip.setPixelColor(i, Color(0, 0, 0))
    strip.show()


def run_pulse(strip):
    # Move pulse from start to end, then fade off
    for position in range(LED_COUNT + PULSE_WIDTH):
        for i in range(LED_COUNT):
            distance = abs(i - position)

            intensity = max(0.0, 1.0 - distance / PULSE_WIDTH)
            intensity = intensity ** 2

            r = int(PULSE_COLOUR[0] * intensity)
            g = int(PULSE_COLOUR[1] * intensity)
            b = int(PULSE_COLOUR[2] * intensity)

            strip.setPixelColor(i, Color(r, g, b))

        strip.show()
        time.sleep(FRAME_DELAY)


def main():
    strip = PixelStrip(
        LED_COUNT,
        LED_PIN,
        LED_FREQ_HZ,
        LED_DMA,
        LED_INVERT,
        LED_BRIGHTNESS,
        LED_CHANNEL
    )
    strip.begin()
    clear_strip(strip)

    pygame.init()
    screen = pygame.display.set_mode((300, 100))
    pygame.display.set_caption("LED Pulse - Press SPACE")
    print("Press SPACE to trigger a pulse. Press ESC to quit.")

    try:
        running = True

        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False

                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        running = False

                    elif event.key == pygame.K_SPACE:
                        run_pulse(strip)
                        clear_strip(strip)

            time.sleep(0.005)

    finally:
        clear_strip(strip)
        pygame.quit()


if __name__ == "__main__":
    main()
