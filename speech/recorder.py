from __future__ import annotations

import subprocess
from pathlib import Path


def record_audio(
    output_file: Path,
    duration_seconds: int = 7,
    device: str = "plughw:0,0",
) -> Path:
    """Nimmt Mono-Audio mit 16 kHz und 16 Bit über ALSA auf."""

    output_file = output_file.resolve()
    output_file.parent.mkdir(parents=True, exist_ok=True)

    command = [
        "arecord",
        "-q",
        "-D",
        device,
        "-f",
        "S16_LE",
        "-r",
        "16000",
        "-c",
        "1",
        "-d",
        str(duration_seconds),
        str(output_file),
    ]

    try:
        subprocess.run(command, check=True)
    except FileNotFoundError as exc:
        raise RuntimeError("arecord wurde nicht gefunden.") from exc
    except subprocess.CalledProcessError as exc:
        raise RuntimeError(
            f"Die Aufnahme ist fehlgeschlagen: {exc}"
        ) from exc

    if not output_file.exists() or output_file.stat().st_size < 1_000:
        raise RuntimeError("Die erzeugte Audiodatei ist leer oder zu klein.")

    return output_file
