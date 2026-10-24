
import time
import colorsys
import struct
import subprocess
import threading
import queue

from rpi_ws281x import PixelStrip, Color

# --------------------------------------------------
# LED SETTINGS
# --------------------------------------------------

LED_COUNT = 50

LED_FREQ_HZ = 800000
LED_DMA = 10
LED_BRIGHTNESS = 75
LED_INVERT = False

# Select the LED strings to use.
USE_GPIO_18 = True
USE_GPIO_13 = True

# --------------------------------------------------
# ANIMATION SETTINGS
# --------------------------------------------------

PULSE_WIDTH = 15
FRAME_DELAY = 1/60
PULSE_SPEED = 1.0 / FRAME_DELAY

# --------------------------------------------------
# MICROPHONE SETTINGS
# --------------------------------------------------

MIC_DEVICE = "plughw:3,0"
MIC_RATE = 16000
MIC_CHUNK = 320

# Increase this if background noise triggers pulses.
# Decrease it if claps are not detected.
MIC_PEAK_THRESHOLD = 4000

# Minimum time between microphone triggers.
MIC_COOLDOWN = 0.25


def create_strips():
    """Initialise the selected LED strings."""
    strips = []

    if USE_GPIO_18:
        strips.append(
            PixelStrip(
                LED_COUNT, 18, LED_FREQ_HZ,
                LED_DMA, LED_INVERT,
                LED_BRIGHTNESS, 0
            )
        )

    if USE_GPIO_13:
        strips.append(
            PixelStrip(
                LED_COUNT, 13, LED_FREQ_HZ,
                LED_DMA, LED_INVERT,
                LED_BRIGHTNESS, 1
            )
        )

    if not strips:
        raise ValueError("Enable at least one LED string.")

    for strip in strips:
        strip.begin()

    return strips


def clear_strips(strips):
    """Turn off every LED on every selected string."""
    for strip in strips:
        for i in range(LED_COUNT):
            strip.setPixelColor(i, Color(0, 0, 0))
        strip.show()


def rainbow_colour(position):
    """Calculate a rainbow colour."""
    hue = (position % PULSE_WIDTH) / PULSE_WIDTH
    r, g, b = colorsys.hsv_to_rgb(hue, 1.0, 1.0)

    return int(r * 255), int(g * 255), int(b * 255)


def microphone_worker(events, stop_event):
    """Listen for loud sounds and queue pulse triggers."""
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
            stderr=subprocess.DEVNULL,
            bufsize=0,
        )

        print("Microphone listening for sounds...", flush=True)

        while not stop_event.is_set():
            data = bytearray()

            # Collect one complete audio chunk.
            while len(data) < chunk_size and not stop_event.is_set():
                part = process.stdout.read(
                    chunk_size - len(data)
                )

                if not part:
                    break

                data.extend(part)

            if stop_event.is_set():
                break

            if len(data) != chunk_size:
                if process.poll() is not None:
                    print(
                        "Microphone stopped. Check the device setting.",
                        flush=True,
                    )
                    break
                continue

            samples = struct.unpack(
                "<" + "h" * MIC_CHUNK, data
            )

            peak = max(abs(sample) for sample in samples)
            now = time.monotonic()

            if (
                peak >= MIC_PEAK_THRESHOLD
                and now - last_trigger >= MIC_COOLDOWN
            ):
                events.put("sound")
                last_trigger = now

    except Exception as error:
        if not stop_event.is_set():
            print(f"Microphone error: {error}", flush=True)

    finally:
        if process is not None:
            if process.poll() is None:
                process.terminate()

            try:
                process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()

            if process.stdout:
                process.stdout.close()


def main():
    strips = create_strips()
    clear_strips(strips)

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

    print("LED pulse installation running.", flush=True)

    if USE_GPIO_18:
        print("GPIO 18: enabled", flush=True)

    if USE_GPIO_13:
        print("GPIO 13: enabled", flush=True)

    try:
        while True:
            now = time.monotonic()
            delta_time = min(now - previous_frame, 0.1)
            previous_frame = now

            # Start a pulse for each microphone trigger.
            while True:
                try:
                    events.get_nowait()
                except queue.Empty:
                    break

                active_pulses.append({"position": 0.0})
                print("Pulse triggered", flush=True)

            # Move all active pulses along the strings.
            for pulse in active_pulses:
                pulse["position"] += PULSE_SPEED * delta_time

            active_pulses = [
                pulse for pulse in active_pulses
                if pulse["position"] < LED_COUNT + PULSE_WIDTH
            ]

            # Calculate one shared frame for both strings.
            frame = []

            for i in range(LED_COUNT):
                red = 0.0
                green = 0.0
                blue = 0.0

                for pulse in active_pulses:
                    distance = abs(i - pulse["position"])

                    intensity = max(
                        0.0,
                        1.0 - distance / PULSE_WIDTH,
                    ) ** 2

                    r, g, b = rainbow_colour(
                        i - pulse["position"] + PULSE_WIDTH
                    )

                    red += r * intensity
                    green += g * intensity
                    blue += b * intensity

                frame.append(
                    Color(
                        min(255, int(red)),
                        min(255, int(green)),
                        min(255, int(blue)),
                    )
                )

            # Write the same animation to each selected string.
            for strip in strips:
                for i, colour in enumerate(frame):
                    strip.setPixelColor(i, colour)

                strip.show()

            time.sleep(FRAME_DELAY)

    except KeyboardInterrupt:
        print("\nStopping LED installation.", flush=True)

    finally:
        stop_event.set()
        clear_strips(strips)
        print("LEDs cleared.", flush=True)


if __name__ == "__main__":
    main()
