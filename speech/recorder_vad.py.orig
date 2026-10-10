import math
import subprocess
import time
import wave
from array import array
from collections import deque
from pathlib import Path


SAMPLE_RATE = 16000
CHANNELS = 1
SAMPLE_WIDTH = 2

CHUNK_MS = 20
CHUNK_SAMPLES = SAMPLE_RATE * CHUNK_MS // 1000
CHUNK_BYTES = CHUNK_SAMPLES * SAMPLE_WIDTH


def calculate_rms(data):
    """Berechnet die Lautstärke eines 16-Bit-PCM-Blocks."""

    if not data:
        return 0.0

    samples = array("h")
    samples.frombytes(data)

    if not samples:
        return 0.0

    square_sum = sum(sample * sample for sample in samples)
    return math.sqrt(square_sum / len(samples))


def save_wav(output_file, frames):
    """Speichert PCM-Blöcke als WAV-Datei."""

    with wave.open(str(output_file), "wb") as wav_file:
        wav_file.setnchannels(CHANNELS)
        wav_file.setsampwidth(SAMPLE_WIDTH)
        wav_file.setframerate(SAMPLE_RATE)
        wav_file.writeframes(b"".join(frames))


def record_audio(
    output_file,
    duration_seconds=12,
    device="plughw:0,0",
    silence_seconds=0.9,
    speech_timeout_seconds=6,
):
    """
    Nimmt auf, bis nach erkannter Sprache eine Sprechpause entsteht.

    duration_seconds:
        Maximale Gesamtdauer als Sicherheitsgrenze.

    silence_seconds:
        So lange muss es still sein, damit die Aufnahme endet.

    speech_timeout_seconds:
        Abbruch, wenn innerhalb dieser Zeit niemand spricht.
    """

    output_file = Path(output_file).resolve()
    output_file.parent.mkdir(parents=True, exist_ok=True)

    command = [
        "arecord",
        "-q",
        "-D",
        device,
        "-f",
        "S16_LE",
        "-r",
        str(SAMPLE_RATE),
        "-c",
        str(CHANNELS),
        "-t",
        "raw",
    ]

    process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    if process.stdout is None:
        raise RuntimeError("Der Audiostream konnte nicht geöffnet werden.")

    frames = []

    # Die letzten 300 ms bleiben erhalten, damit Wortanfänge
    # nicht durch die Spracherkennung abgeschnitten werden.
    pre_roll_chunks = max(1, int(300 / CHUNK_MS))
    pre_roll = deque(maxlen=pre_roll_chunks)

    speech_started = False
    speech_chunks = 0
    silent_chunks = 0

    required_speech_chunks = max(1, int(60 / CHUNK_MS))
    required_silent_chunks = max(
        1,
        int((silence_seconds * 1000) / CHUNK_MS),
    )

    start_time = time.monotonic()

    # In den ersten 400 ms wird das Grundrauschen gemessen.
    calibration_chunks = max(1, int(400 / CHUNK_MS))
    calibration_values = []

    threshold = 500.0

    try:
        print("VAD: Grundrauschen wird kurz gemessen ...")

        while True:
            data = process.stdout.read(CHUNK_BYTES)

            if not data:
                break

            rms = calculate_rms(data)
            elapsed = time.monotonic() - start_time

            if len(calibration_values) < calibration_chunks:
                calibration_values.append(rms)
                pre_roll.append(data)

                if len(calibration_values) == calibration_chunks:
                    noise_level = sum(calibration_values) / len(
                        calibration_values
                    )

                    threshold = max(
                        350.0,
                        noise_level * 3.0,
                    )

                    print(
                        "VAD: Bereit – bitte jetzt sprechen "
                        f"(Schwelle: {threshold:.0f})"
                    )

                continue

            if not speech_started:
                pre_roll.append(data)

                if rms >= threshold:
                    speech_chunks += 1
                else:
                    speech_chunks = 0

                if speech_chunks >= required_speech_chunks:
                    speech_started = True
                    frames.extend(pre_roll)
                    pre_roll.clear()
                    frames.append(data)

                    print("VAD: Sprache erkannt.")

            else:
                frames.append(data)

                if rms < threshold:
                    silent_chunks += 1
                else:
                    silent_chunks = 0

                if silent_chunks >= required_silent_chunks:
                    print("VAD: Sprechpause erkannt.")
                    break

            if not speech_started and elapsed >= speech_timeout_seconds:
                raise RuntimeError(
                    "Innerhalb der Wartezeit wurde keine Sprache erkannt."
                )

            if elapsed >= duration_seconds:
                print("VAD: Maximale Aufnahmedauer erreicht.")
                break

    finally:
        process.terminate()

        try:
            process.wait(timeout=2)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()

    if not speech_started:
        raise RuntimeError("Es wurde keine Sprache erkannt.")

    if len(frames) < 5:
        raise RuntimeError("Die Sprachaufnahme ist zu kurz.")

    save_wav(output_file, frames)

    if not output_file.exists() or output_file.stat().st_size < 1000:
        raise RuntimeError("Die erzeugte Audiodatei ist leer oder zu klein.")

    return output_file
