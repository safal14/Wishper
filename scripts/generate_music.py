"""Render the three original, procedural music loops bundled with Wishper."""

import math
import random
import subprocess
import tempfile
import wave
from array import array
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DESTINATION = ROOT / "static" / "music"
RATE = 22050
DURATION = 24
CHORDS = ((48, 52, 55, 59), (45, 48, 52, 55), (41, 45, 48, 52), (43, 47, 50, 57))
TRACKS = {
    "soft-ambient": {"tempo": 80, "pad": 0.18, "notes": 0.12, "bass": 0.06, "drums": 0.0},
    "steady-motion": {"tempo": 100, "pad": 0.11, "notes": 0.12, "bass": 0.11, "drums": 0.11},
    "bright-day": {"tempo": 96, "pad": 0.10, "notes": 0.19, "bass": 0.05, "drums": 0.025},
}


def frequency(midi):
    return 440.0 * 2 ** ((midi - 69) / 12)


def add_tone(samples, start, length, midi, volume, voice):
    first = int(start * RATE)
    count = min(int(length * RATE), len(samples) - first)
    hz = frequency(midi)
    for i in range(max(0, count)):
        t = i / RATE
        if voice == "pad":
            attack = min(1.0, t / 1.4)
            release = min(1.0, (length - t) / 1.5)
            envelope = max(0.0, attack * release)
            wave_value = math.sin(2 * math.pi * hz * t) + 0.16 * math.sin(2 * math.pi * 2.01 * hz * t)
        elif voice == "bass":
            envelope = math.exp(-2.5 * t)
            wave_value = math.sin(2 * math.pi * hz * t) + 0.12 * math.sin(2 * math.pi * 2 * hz * t)
        else:
            envelope = (1 - math.exp(-35 * t)) * math.exp(-3.6 * t)
            wave_value = math.sin(2 * math.pi * hz * t) + 0.22 * math.sin(2 * math.pi * 2 * hz * t)
        samples[first + i] += volume * envelope * wave_value


def add_percussion(samples, start, volume, rng):
    first = int(start * RATE)
    count = min(int(0.22 * RATE), len(samples) - first)
    for i in range(max(0, count)):
        t = i / RATE
        kick = math.sin(2 * math.pi * (62 * t + 48 * t * math.exp(-28 * t))) * math.exp(-32 * t)
        hiss = rng.uniform(-1, 1) * math.exp(-55 * t)
        samples[first + i] += volume * (0.8 * kick + 0.14 * hiss)


def render(name, settings):
    samples = array("f", [0]) * (RATE * DURATION)
    beat = 60 / settings["tempo"]
    for bar in range(4):
        start = bar * 6
        chord = CHORDS[bar]
        for note in chord:
            add_tone(samples, start, 6, note, settings["pad"] / len(chord), "pad")
        for step in range(int(6 / beat)):
            at = start + step * beat
            add_tone(samples, at, min(1.5, DURATION - at), chord[(step * 3) % len(chord)] + 24, settings["notes"], "pluck")
            if step % 2 == 0:
                add_tone(samples, at, min(1.6, DURATION - at), chord[0] - 12, settings["bass"], "bass")
    rng = random.Random(37)
    if settings["drums"]:
        step = beat * 2
        for tick in range(int(DURATION / step)):
            add_percussion(samples, tick * step, settings["drums"], rng)
    pcm = array("h")
    for i, value in enumerate(samples):
        fade = min(1.0, i / (RATE * 0.35), (len(samples) - i) / (RATE * 0.75))
        pcm.append(round(max(-1, min(1, value * fade)) * 28000))
    DESTINATION.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="wishper-music-") as temporary:
        raw = Path(temporary) / "source.wav"
        with wave.open(str(raw), "wb") as output:
            output.setnchannels(1)
            output.setsampwidth(2)
            output.setframerate(RATE)
            output.writeframes(pcm.tobytes())
        subprocess.run(
            ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-i", str(raw),
             "-c:a", "libmp3lame", "-b:a", "96k", str(DESTINATION / f"{name}.mp3")],
            check=True,
        )


if __name__ == "__main__":
    for track_name, track_settings in TRACKS.items():
        render(track_name, track_settings)
