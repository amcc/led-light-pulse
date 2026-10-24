
import time
import pygame
import colorsys
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
PULSE_WIDTH = 15
FRAME_DELAY = 0.06
PULSE_COLOUR = (255, 187, 51)

# Each pulse moves this many LEDs per second.
# This preserves approximately your original animation speed.
PULSE_SPEED = 1.0 / FRAME_DELAY

def rainbow_colour(position):
    # Convert position along the pulse to a hue from 0–1.
    hue = (position % PULSE_WIDTH) / PULSE_WIDTH
    r, g, b = colorsys.hsv_to_rgb(hue, 1.0, 1.0)

    return int(r * 255), int(g * 255), int(b * 255)

def clear_strip(strip):
    for i in range(LED_COUNT):
        strip.setPixelColor(i, Color(0, 0, 0))
    strip.show()


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
    pygame.display.set_mode((300, 100))
    pygame.display.set_caption("LED Pulse - Press SPACE")

    print("Press SPACE to add a pulse. Press ESC to quit.")

    # Each pulse stores its current position.
    active_pulses = []

    # Use a steady animation clock.
    previous_frame = time.monotonic()
    running = True

    try:
        while running:
            now = time.monotonic()
            delta_time = now - previous_frame
            previous_frame = now

            # Handle keyboard events without blocking the animation.
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False

                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        running = False

                    elif event.key == pygame.K_SPACE:
                        active_pulses.append({
                            "position": 0.0
                        })

            # Move every pulse independently.
            for pulse in active_pulses:
                pulse["position"] += PULSE_SPEED * delta_time

            # Remove pulses once their tails have left the strip.
            active_pulses = [
                pulse for pulse in active_pulses
                if pulse["position"] < LED_COUNT + PULSE_WIDTH
            ]

            # Render all active pulses together.
                        # Render all active pulses together.
            for i in range(LED_COUNT):
                red = 0.0
                green = 0.0
                blue = 0.0

                for pulse in active_pulses:
                    distance = abs(i - pulse["position"])

                    intensity = max(
                        0.0,
                        1.0 - distance / PULSE_WIDTH
                    ) ** 2

                    # Give each LED its own rainbow colour.
                    r, g, b = rainbow_colour(
                        i - pulse["position"] + PULSE_WIDTH
                    )

                    red += r * intensity
                    green += g * intensity
                    blue += b * intensity

                # Clamp combined brightness to the valid range.
                red = min(255, int(red))
                green = min(255, int(green))
                blue = min(255, int(blue))

                strip.setPixelColor(i, Color(red, green, blue))

            strip.show()
            time.sleep(FRAME_DELAY)

    finally:
        clear_strip(strip)
        pygame.quit()


if __name__ == "__main__":
    main()
