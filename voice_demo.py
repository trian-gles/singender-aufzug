from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

from speech.recorder import record_audio
from speech.whisper_stt import transcribe


PROJECT_DIR = Path(__file__).resolve().parent
RECORDING_FILE = PROJECT_DIR / "aufnahme.wav"
OUTPUT_WAV = PROJECT_DIR / "singender_aufzug.wav"


def prepare_for_singing(text: str, max_words: int = 12) -> str:
    """Bereitet das Transkript vorsichtig für den aktuellen Singer vor."""

    text = text.strip()

    # Whisper-Sondermarkierungen entfernen.
    text = re.sub(r"\[[^\]]+\]", " ", text)

    # Ungewöhnliche Zeichen entfernen, Satzzeichen aber behalten.
    text = re.sub(
        r"[^A-Za-zÄÖÜäöüß0-9.,!?'\- ]+",
        " ",
        text,
    )

    text = re.sub(r"\s+", " ", text).strip()

    words = text.split()
    if len(words) > max_words:
        text = " ".join(words[:max_words])

        if text[-1] not in ".!?":
            text += "."

    return text


def run_singer(text: str, bpm: int, diagnostics: bool) -> None:
    command = [
        sys.executable,
        str(PROJECT_DIR / "main.py"),
        "--bpm",
        str(bpm),
    ]

    if diagnostics:
        command.append("--diagnostics")

    command.append(text)

    subprocess.run(
        command,
        cwd=PROJECT_DIR,
        check=True,
    )

    if not OUTPUT_WAV.exists():
        raise RuntimeError(
            f"Die erwartete Ausgabedatei wurde nicht erzeugt: {OUTPUT_WAV}"
        )


def play_audio(audio_file: Path) -> None:
    subprocess.run(
        ["aplay", "-q", str(audio_file)],
        check=True,
    )


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Lokale Sprachaufnahme, Whisper-STT und Gesangsausgabe."
    )
    parser.add_argument(
        "--duration",
        type=int,
        default=7,
        help="Aufnahmedauer in Sekunden.",
    )
    parser.add_argument(
        "--bpm",
        type=int,
        default=96,
        help="Tempo des Gesangs.",
    )
    parser.add_argument(
        "--device",
        default="plughw:0,0",
        help="ALSA-Aufnahmegerät.",
    )
    parser.add_argument(
        "--diagnostics",
        action="store_true",
        help="Diagnoseausgabe von TechScore anzeigen.",
    )
    parser.add_argument(
        "--no-play",
        action="store_true",
        help="WAV erzeugen, aber nicht automatisch abspielen.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_arguments()

    print()
    print("=" * 54)
    print("          SINGENDER AUFZUG – PROTOTYP 0.1")
    print("=" * 54)
    print()
    print("Drücke ENTER und sprich danach einen kurzen Satz.")
    input()

    try:
        print(f"AUFNAHME: Ich höre {args.duration} Sekunden zu ...")

        record_audio(
            output_file=RECORDING_FILE,
            duration_seconds=args.duration,
            device=args.device,
        )

        print("STT: Sprache wird lokal transkribiert ...")
        transcript = transcribe(RECORDING_FILE)

        print()
        print("ERKANNT:")
        print(f'"{transcript}"')

        singing_text = prepare_for_singing(transcript)

        if not singing_text:
            raise RuntimeError(
                "Nach der Textbereinigung ist kein singbarer Text übrig."
            )

        if singing_text != transcript:
            print()
            print("FÜR DEN PROTOTYPEN GEKÜRZT/BEREINIGT:")
            print(f'"{singing_text}"')

        print()
        print("GESANG: TechScore und MBROLA erzeugen die Antwort ...")

        run_singer(
            text=singing_text,
            bpm=args.bpm,
            diagnostics=args.diagnostics,
        )

        if not args.no_play:
            print()
            print("WIEDERGABE:")
            play_audio(OUTPUT_WAV)

        print()
        print("FERTIG.")
        return 0

    except KeyboardInterrupt:
        print("\nAbgebrochen.")
        return 130
    except Exception as exc:
        print()
        print(f"FEHLER: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
