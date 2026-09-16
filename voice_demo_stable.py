import shutil
import sys
from pathlib import Path

from llm.local_response_generator import (
    LocalResponseGenerator,
    SOURCE_LABELS,
)
from speech.recorder_vad import record_audio
from speech.whisper_stt import transcribe
from voice_demo import (
    OUTPUT_WAV,
    PROJECT_DIR,
    prepare_for_singing,
    run_singer,
    play_audio,
)


RECORDING_FILE = PROJECT_DIR / "aufnahme.wav"
MAX_ATTEMPTS = 2
RECORDING_SECONDS = 12
BPM = 96


def check_system():
    """Prüft vor Beginn, ob alle wichtigen Komponenten vorhanden sind."""

    errors = []

    required_commands = {
        "arecord": shutil.which("arecord"),
        "aplay": shutil.which("aplay"),
        "python": sys.executable,
    }

    for name, path in required_commands.items():
        if not path:
            errors.append(f"Programm fehlt: {name}")

    required_files = [
        PROJECT_DIR / "main.py",
        Path.home() / "whisper.cpp/build/bin/whisper-cli",
        Path.home() / "whisper.cpp/models/ggml-tiny.bin",
        Path.home() / "llama.cpp/build/bin/llama-server",
        PROJECT_DIR / "models/llm/Qwen3-0.6B-Q8_0.gguf",
    ]

    for path in required_files:
        if not path.exists():
            errors.append(f"Datei fehlt: {path}")

    if errors:
        raise RuntimeError("\n".join(errors))


def remove_duplicate_sentences(text):
    """
    Entfernt direkt wiederholte vollständige Sätze.

    Beispiel:
    'Das ist ein Test. Das ist ein Test.'
    wird zu:
    'Das ist ein Test.'
    """

    normalized = " ".join(text.split()).strip()

    sentence_endings = [".", "!", "?"]

    for ending in sentence_endings:
        parts = [
            part.strip()
            for part in normalized.split(ending)
            if part.strip()
        ]

        if len(parts) == 2 and parts[0].lower() == parts[1].lower():
            return parts[0] + ending

    return normalized


def prepare_transcript(text):
    """Bereinigt das Whisper-Ergebnis für das LLM."""

    text = " ".join(text.split()).strip()
    text = remove_duplicate_sentences(text)

    return text


def prepare_llm_answer(text):
    """Bereinigt Elfis Antwort vor der Gesangserzeugung."""

    text = " ".join(text.split()).strip()
    text = remove_duplicate_sentences(text)

    prefixes = [
        "Elfi:",
        "Aufzug:",
        "Assistant:",
    ]

    for prefix in prefixes:
        if text.lower().startswith(prefix.lower()):
            text = text[len(prefix):].strip()

    return text


def record_and_transcribe(attempt):
    print()
    print(f"VERSUCH {attempt} VON {MAX_ATTEMPTS}")
    print("-" * 54)
    print(f"AUFNAHME: Ich höre {RECORDING_SECONDS} Sekunden zu ...")
    print("Bitte jetzt deutlich und nah am Mikrofon sprechen.")

    record_audio(
        output_file=RECORDING_FILE,
        duration_seconds=RECORDING_SECONDS,
        device="plughw:0,0",
    )

    print("STT: Sprache wird vollständig lokal erkannt ...")

    transcript = transcribe(RECORDING_FILE)
    transcript = prepare_transcript(transcript)

    if not transcript:
        raise RuntimeError("Es wurde kein verständlicher Text erkannt.")

    return transcript


def get_valid_transcript():
    """Erlaubt bei einer schlechten Aufnahme automatisch einen zweiten Versuch."""

    last_error = None

    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            transcript = record_and_transcribe(attempt)

            print()
            print("ERKANNT:")
            print(f'"{transcript}"')

            answer = input(
                "\nENTER = verwenden | r = noch einmal aufnehmen: "
            ).strip().lower()

            if answer == "r":
                last_error = RuntimeError(
                    "Die Aufnahme wurde manuell verworfen."
                )
                continue

            return transcript

        except Exception as exc:
            last_error = exc
            print()
            print(f"Die Aufnahme konnte nicht verwendet werden: {exc}")

            if attempt < MAX_ATTEMPTS:
                input("Drücke ENTER für einen zweiten Versuch.")

    raise RuntimeError(
        f"Nach {MAX_ATTEMPTS} Versuchen keine gültige Aufnahme: "
        f"{last_error}"
    )


def generate_elfi_answer(
    generator: LocalResponseGenerator,
    transcript: str,
) -> str:
    """Erzeugt Elfis Antwort mit dem lokalen Sprachmodell."""

    print()
    print("ELFI DENKT NACH ...")

    result = generator.generate(transcript)
    answer = prepare_llm_answer(result.text)

    if not answer:
        raise RuntimeError(
            "Das Sprachmodell hat keine verwendbare Antwort erzeugt."
        )

    print()
    print(f"ELFI ANTWORTET ({SOURCE_LABELS[result.source]}):")
    print(f'"{answer}"')

    return answer


def main():
    print()
    print("=" * 54)
    print("       SINGENDER AUFZUG – LLM-DEMO 0.3")
    print("=" * 54)
    print()
    print("Lokale Verarbeitung:")
    print("Mikrofon → Whisper → Elfi-LLM (llama-server) → TechScore → MBROLA")
    print()

    llm_generator: LocalResponseGenerator | None = None

    try:
        print("SYSTEMCHECK ...")
        check_system()
        print("SYSTEMCHECK: OK")

        print()
        print("LLM: Elfi wird vorbereitet …")
        llm_generator = LocalResponseGenerator()
        llm_generator.start_server()
        llm_generator.check_system()
        print("LLM: Elfi ist bereit.")

        input("\nDrücke ENTER, um die Demo zu starten.")

        transcript = get_valid_transcript()

        elfi_answer = generate_elfi_answer(
            generator=llm_generator,
            transcript=transcript,
        )

        singing_text = prepare_for_singing(elfi_answer)

        if not singing_text:
            raise RuntimeError(
                "Aus Elfis Antwort konnte kein singbarer Text erzeugt werden."
            )

        if singing_text != elfi_answer:
            print()
            print("FÜR DEN GESANG AUFBEREITET:")
            print(f'"{singing_text}"')

        print()
        print("GESANG: TechScore und MBROLA arbeiten …")

        run_singer(
            text=singing_text,
            bpm=BPM,
            diagnostics=False,
        )

        if not OUTPUT_WAV.exists():
            raise RuntimeError(
                "Die Gesangsdatei wurde nicht erzeugt."
            )

        print("WIEDERGABE ...")
        play_audio(OUTPUT_WAV)

        print()
        print("=" * 54)
        print("DEMO ERFOLGREICH ABGESCHLOSSEN")
        print("=" * 54)

        return 0

    except KeyboardInterrupt:
        print("\nDemo abgebrochen.")
        return 130

    except Exception as exc:
        print()
        print("=" * 54)
        print("DIE DEMO KONNTE NICHT ABGESCHLOSSEN WERDEN")
        print("=" * 54)
        print(exc)
        return 1

    finally:
        if llm_generator is not None:
            print()
            llm_generator.stop_server()


if __name__ == "__main__":
    raise SystemExit(main())