
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
PULSE_WIDTH = 15
FRAME_DELAY = 0.055
PULSE_COLOUR = (255, 187, 51)

# Each pulse moves this many LEDs per second.
# This preserves approximately your original animation speed.
PULSE_SPEED = 1.0 / FRAME_DELAY


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
            for i in range(LED_COUNT):
                intensity_total = 0.0

                for pulse in active_pulses:
                    distance = abs(i - pulse["position"])

                    intensity = max(
                        0.0,
                        1.0 - distance / PULSE_WIDTH
                    )
                    intensity = intensity ** 2

                    # Combine overlapping pulses without exceeding 1.
                    intensity_total = min(
                        1.0,
                        intensity_total + intensity
                    )

                r = int(PULSE_COLOUR[0] * intensity_total)
                g = int(PULSE_COLOUR[1] * intensity_total)
                b = int(PULSE_COLOUR[2] * intensity_total)

                strip.setPixelColor(i, Color(r, g, b))

            strip.show()
            time.sleep(FRAME_DELAY)

    finally:
        clear_strip(strip)
        pygame.quit()


if __name__ == "__main__":
    main()
