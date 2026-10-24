
import time
import colorsys
import struct
import subprocess
import threading
import queue
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
PULSE_SPEED = 1.0 / FRAME_DELAY
PULSE_COLOUR = (255, 187, 51)  # Retained for reference; rainbow is used below.

# Microphone configuration
MIC_DEVICE = "plughw:3,0"
MIC_RATE = 16000
MIC_CHUNK = 320             # 20 ms of mono audio
MIC_PEAK_THRESHOLD = 4000   # Adjust after testing
MIC_COOLDOWN = 0.25         # Minimum time between triggers


def clear_strip(strip):
    for i in range(LED_COUNT):
        strip.setPixelColor(i, Color(0, 0, 0))
    strip.show()


def rainbow_colour(position):
    """Return a rainbow RGB colour for a position along the pulse."""
    hue = (position % PULSE_WIDTH) / PULSE_WIDTH
    r, g, b = colorsys.hsv_to_rgb(hue, 1.0, 1.0)
    return int(r * 255), int(g * 255), int(b * 255)


def microphone_worker(events, stop_event):
    """Read microphone audio and queue clap triggers."""
    command = [
        "arecord",
        "-q",
        "-D", MIC_DEVICE,
        "-t", "raw",
        "-f", "S16_LE",
        "-r", str(MIC_RATE),
        "-c", "1",
    ]

    process = None
    last_trigger = 0.0
    chunk_size = MIC_CHUNK * 2

    try:
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            bufsize=0,
        )

        print("Microphone listening. Clap to trigger a pulse.")

        while not stop_event.is_set():
            data = bytearray()

            # Collect a complete audio chunk.
            while len(data) < chunk_size and not stop_event.is_set():
                part = process.stdout.read(chunk_size - len(data))

                if not part:
                    break

                data.extend(part)

            if stop_event.is_set():
                break

            if len(data) != chunk_size:
                if process.poll() is None:
                    print("Microphone stream returned incomplete audio.")
                else:
                    error = process.stderr.read().decode(
                        "utf-8", errors="replace"
                    )
                    print(f"Microphone stream ended. {error}")
                break

            samples = struct.unpack(
                "<" + "h" * MIC_CHUNK, data
            )
            peak = max(abs(sample) for sample in samples)
            now = time.monotonic()

            if (
                peak >= MIC_PEAK_THRESHOLD
                and now - last_trigger >= MIC_COOLDOWN
            ):
                events.put("clap")
                last_trigger = now

    except Exception as error:
        if not stop_event.is_set():
            print(f"Microphone error: {error}")

    finally:
        if process is not None:
            if process.poll() is None:
                process.terminate()

            try:
                process.wait(timeout=1)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()

            if process.stderr:
                process.stderr.close()

            if process.stdout:
                process.stdout.close()


def main():
    strip = PixelStrip(
        LED_COUNT,
        LED_PIN,
        LED_FREQ_HZ,
        LED_DMA,
        LED_INVERT,
        LED_BRIGHTNESS,
        LED_CHANNEL,
    )
    strip.begin()
    clear_strip(strip)

    pygame.init()
    pygame.display.set_mode((300, 100))
    pygame.display.set_caption("Rainbow Pulse - Space or Clap")

    print("SPACE = trigger pulse | ESC = quit")

    events = queue.Queue()
    stop_event = threading.Event()

    mic_thread = threading.Thread(
        target=microphone_worker,
        args=(events, stop_event),
        daemon=True,
    )
    mic_thread.start()

    active_pulses = []
    previous_frame = time.monotonic()
    running = True

    try:
        while running:
            now = time.monotonic()
            delta_time = min(now - previous_frame, 0.1)
            previous_frame = now

            # Process keyboard input.
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False

                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        running = False
                    elif event.key == pygame.K_SPACE:
                        events.put("manual")

            # Add a pulse for every queued trigger.
            while True:
                try:
                    trigger = events.get_nowait()
                except queue.Empty:
                    break

                active_pulses.append({"position": 0.0})
                print(f"Pulse triggered: {trigger}")

            # Advance all pulses independently.
            for pulse in active_pulses:
                pulse["position"] += PULSE_SPEED * delta_time

            # Remove pulses after their tails leave the strip.
            active_pulses = [
                pulse for pulse in active_pulses
                if pulse["position"] < LED_COUNT + PULSE_WIDTH
            ]

            # Render all active pulses together.
            for i in range(LED_COUNT):
                red = 0.0
                green = 0.0
                blue = 0.0

                for pulse in active_pulses:
                    distance = abs(i - pulse["position"])
                    intensity = max(
                        0.0, 1.0 - distance / PULSE_WIDTH
                    ) ** 2

                    r, g, b = rainbow_colour(
                        i - pulse["position"] + PULSE_WIDTH
                    )

                    red += r * intensity
                    green += g * intensity
                    blue += b * intensity

                strip.setPixelColor(
                    i,
                    Color(
                        min(255, int(red)),
                        min(255, int(green)),
                        min(255, int(blue)),
                    ),
                )

            strip.show()
            time.sleep(FRAME_DELAY)

    finally:
        stop_event.set()
        clear_strip(strip)
        pygame.quit()


if __name__ == "__main__":
    main()
