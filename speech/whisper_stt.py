from __future__ import annotations

import re
import subprocess
from pathlib import Path

from llm.german_terms import build_whisper_prompt


DEFAULT_WHISPER_CLI = Path.home() / "whisper.cpp/build/bin/whisper-cli"
DEFAULT_MODEL = Path.home() / "whisper.cpp/models/ggml-tiny.bin"


def clean_transcript(text: str) -> str:
    """Bereinigt die Konsolenausgabe von Whisper."""

    text = text.strip()

    # Whisper-Markierungen wie [Musik], [Applaus] usw. entfernen.
    text = re.sub(r"\[[^\]]+\]", " ", text)
    text = re.sub(r"\([^\)]+musik[^\)]*\)", " ", text, flags=re.IGNORECASE)

    # Mehrfache Leerzeichen reduzieren.
    text = re.sub(r"\s+", " ", text).strip()

    return text


def transcribe(
    audio_file: Path,
    language: str = "de",
    threads: int = 4,
    whisper_cli: Path = DEFAULT_WHISPER_CLI,
    model: Path = DEFAULT_MODEL,
) -> str:
    """Transkribiert eine WAV-Datei vollständig lokal mit whisper.cpp.

    Nutzt ``--prompt`` und ``--carry-initial-prompt``, um Whisper bei
    der deutschen Aussprache englischer / gemischter Begriffe zu
    unterstützen („Südkultur“, „Production Labor“, Künstlernamen usw.).
    """

    audio_file = audio_file.resolve()
    whisper_cli = whisper_cli.expanduser().resolve()
    model = model.expanduser().resolve()

    if not whisper_cli.exists():
        raise RuntimeError(f"whisper-cli fehlt: {whisper_cli}")

    if not model.exists():
        raise RuntimeError(f"Whisper-Modell fehlt: {model}")

    if not audio_file.exists():
        raise RuntimeError(f"Audiodatei fehlt: {audio_file}")

    command = [
        str(whisper_cli),
        "-m", str(model),
        "-f", str(audio_file),
        "-l", language,
        "-t", str(threads),
        "-nt",
        "-np",
        "-bs", "1",
        "-bo", "1",
        "--prompt", build_whisper_prompt(),
        "--carry-initial-prompt",
    ]

    try:
        result = subprocess.run(
            command,
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
    except subprocess.CalledProcessError as exc:
        error = exc.stderr.strip() or exc.stdout.strip()
        raise RuntimeError(f"Whisper ist fehlgeschlagen:\n{error}") from exc

    transcript = clean_transcript(result.stdout)

    if not transcript:
        raise RuntimeError("Whisper hat keine verständliche Sprache erkannt.")

    return transcript