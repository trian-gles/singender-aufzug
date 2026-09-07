#!/usr/bin/env python3
"""Singender Aufzug – LLM-Demo mit Endlos-Event-Loop.

Workflow:
    Enter → Aufnahme (12 s) → Whisper-STT → Elfi-LLM (llama-server)
    → TechScore → MBROLA → Wiedergabe → nächster Durchlauf

Nur Ctrl+C beendet das Programm.
"""

from __future__ import annotations

import argparse
import re
import shutil
import sys
from pathlib import Path
from time import time

from llm.local_response_generator import LocalResponseGenerator
from speech.recorder_vad import record_audio
from speech.whisper_stt import transcribe

# ---------------------------------------------------------------------------
# Sing-Rendering (direkt, nicht via Subprozess)
# ---------------------------------------------------------------------------
from config import MBROLA_VOICE_PATH
from language.aligner import SyllableAligner
from language.analyzer import TextAnalyzer
from language.phoneme_normalizer import GermanMbrolaNormalizer
from language.phonemizer import SyllablePhonemizer
from music.tech_composer import TechScoreComposer, WordMaterial
from music.tech_duration import TechDurationPlanner
from music.tech_score import TechScore
from singing.tech_singer import TechScoreSinger
from music.performance import PerformancePlanner
from audio.pho import Phoneme
from audio.pho_writer import PhoWriter
from audio.renderer import MbrolaRenderer
from datetime import datetime
import zipfile
import subprocess

# ---------------------------------------------------------------------------
# Konstanten
# ---------------------------------------------------------------------------
PROJECT_DIR = Path(__file__).resolve().parent
RECORDING_FILE = PROJECT_DIR / "aufnahme.wav"
OUTPUT_WAV = PROJECT_DIR / "singender_aufzug.wav"
OUTPUT_PHO = PROJECT_DIR / "singender_aufzug.pho"
PHO_ARCHIVE = PROJECT_DIR / "pho_archiv.zip"

RECORDING_SECONDS = 12
BPM = 96
TOKEN_PATTERN = re.compile(r"[A-Za-zÄÖÜäöüß]+(?:[-'][A-Za-zÄÖÜäöüß]+)*|[,.!?;:]")
PUNCTUATION = {",", ":", ";", ".", "!", "?"}

# ---------------------------------------------------------------------------
# System-Check
# ---------------------------------------------------------------------------

def check_system() -> None:
    """Prüft vor Beginn, ob alle wichtigen Komponenten vorhanden sind."""

    errors: list[str] = []

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
        PROJECT_DIR / "models/llm/Qwen3-1.7B-Q4_K_M.gguf",
    ]

    for path in required_files:
        if not path.exists():
            errors.append(f"Datei fehlt: {path}")

    if errors:
        raise RuntimeError("\n".join(errors))


# ---------------------------------------------------------------------------
# Text-Bereinigung
# ---------------------------------------------------------------------------

def remove_duplicate_sentences(text: str) -> str:
    """Entfernt direkt wiederholte vollständige Sätze."""

    normalized = " ".join(text.split()).strip()

    for ending in (".", "!", "?"):
        parts = [
            part.strip()
            for part in normalized.split(ending)
            if part.strip()
        ]

        if len(parts) == 2 and parts[0].lower() == parts[1].lower():
            return parts[0] + ending

    return normalized


def prepare_transcript(text: str) -> str:
    """Bereinigt das Whisper-Ergebnis für das LLM."""

    text = " ".join(text.split()).strip()
    text = remove_duplicate_sentences(text)
    return text


def prepare_llm_answer(text: str) -> str:
    """Bereinigt Elfis Antwort vor der Gesangserzeugung."""

    text = " ".join(text.split()).strip()
    text = remove_duplicate_sentences(text)

    for prefix in ("Elfi:", "Aufzug:", "Assistant:"):
        if text.lower().startswith(prefix.lower()):
            text = text[len(prefix):].strip()

    return text


def prepare_for_singing(text: str, max_words: int = 12) -> str:
    """Bereitet den Text vorsichtig für den Sänger vor."""

    text = text.strip()

    # Sondermarkierungen entfernen
    text = re.sub(r"\[[^\]]+\]", " ", text)
    text = re.sub(r"[^A-Za-zÄÖÜäöüß0-9.,!?'\- ]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()

    words = text.split()
    if len(words) > max_words:
        text = " ".join(words[:max_words])
        if text[-1] not in ".!?":
            text += "."

    return text


# ---------------------------------------------------------------------------
# Sing-Rendering
# ---------------------------------------------------------------------------

def tokenize(text: str) -> list[str]:
    return TOKEN_PATTERN.findall(text)


def split_sentences(tokens: list[str]):
    current: list[str] = []
    for token in tokens:
        if token not in PUNCTUATION:
            current.append(token)
        elif current:
            yield current, token
            current = []
    if current:
        yield current, "."


def prepare_word(
    text: str,
    analyzer: TextAnalyzer,
    phonemizer: SyllablePhonemizer,
    aligner: SyllableAligner,
    normalizer: GermanMbrolaNormalizer,
) -> WordMaterial | None:
    words = analyzer.analyze(text)
    if not words:
        return None

    word = words[0]
    phonemes = [
        p
        for p in phonemizer.phonemize_text(word.text)
        if p.symbol != "_"
    ]
    groups = aligner.align_to_syllable_count(
        phonemes=phonemes,
        syllable_count=len(word.syllables),
    )
    groups = normalizer.normalize_word(word.text, groups)

    if len(groups) != len(word.syllables):
        print(
            f"WARNUNG: {word.text!r}: "
            f"{len(word.syllables)} Silben, "
            f"{len(groups)} Phonemgruppen; "
            "Fallback konnte das Wort nicht vollständig ausrichten."
        )
        return None

    return WordMaterial(word, groups)


def archive_previous_pho(
    path: Path = OUTPUT_PHO,
    archive: Path = PHO_ARCHIVE,
) -> str | None:
    """Archiviert die bisherige PHO, bevor sie überschrieben wird."""

    if not path.exists():
        return None

    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S_%f")
    archived_name = f"pho/{timestamp}_{path.name}"

    with zipfile.ZipFile(archive, mode="a", compression=zipfile.ZIP_DEFLATED) as bundle:
        existing = set(bundle.namelist())
        counter = 1
        candidate = archived_name
        while candidate in existing:
            candidate = f"pho/{timestamp}_{counter}_{path.name}"
            counter += 1
        bundle.write(path, arcname=candidate)

    return candidate


def print_score(score: TechScore) -> None:
    print("\n" + "=" * 104)
    print(
        f"TECH-SCORE V4  ({score.bpm} BPM, "
        f"{score.meter_numerator}/{score.meter_denominator})"
    )
    print("=" * 104)
    print(
        f"{'Wort':<16}{'Silbe':<12}"
        f"{'MIDI / Hz / Beats / Typ':<50}"
        f"{'Beats':>8}{'Akzent':>18}"
    )
    print("-" * 104)

    for phrase in score.phrases:
        for syllable in phrase.syllables:
            notes = "  ".join(
                f"{n.midi}/{n.frequency_hz}/{n.beats:.2f}/{n.note_type.value}"
                for n in syllable.notes
            )
            print(
                f"{syllable.word:<16}{syllable.syllable:<12}"
                f"{notes:<50}{syllable.beats:>8.2f}{syllable.accent.value:>18}"
            )
        print(
            f"Kadenz: {phrase.cadence.value} | "
            f"Pause: {phrase.pause_beats:.2f} Beats"
        )


def render_text(
    text: str,
    bpm: int,
    diagnostics: bool,
) -> str:
    """Rendert Text zu Gesang (TechScore → MBROLA). Gibt den WAV-Pfad zurück."""

    analyzer = TextAnalyzer()
    phonemizer = SyllablePhonemizer()
    aligner = SyllableAligner()
    normalizer = GermanMbrolaNormalizer()
    composer = TechScoreComposer(bpm=bpm)
    duration = TechDurationPlanner()
    performance_planner = PerformancePlanner()
    singer = TechScoreSinger()

    output: list[Phoneme] = []

    for words, punctuation in split_sentences(tokenize(text)):
        materials = [
            m
            for token in words
            if (m := prepare_word(token, analyzer, phonemizer, aligner, normalizer))
        ]
        if not materials:
            continue

        score = composer.compose(materials, punctuation)
        print_score(score)

        realized = duration.realize(score)

        if diagnostics:
            print("\nPHONEM- UND NOTEN-TIMING")
            print("-" * 104)
            for phrase in realized.phrases:
                for syllable in phrase.syllables:
                    phon = " ".join(
                        f"{p.symbol}:{d}"
                        for p, d in zip(
                            syllable.score.phonemes,
                            syllable.phoneme_durations_ms,
                        )
                    )
                    notes = " ".join(
                        f"{n.note.midi}@{n.start_ms}+{n.duration_ms}"
                        for n in syllable.notes
                    )
                    print(
                        f"{syllable.score.word:<16}"
                        f"{syllable.score.syllable:<12}"
                        f"{phon:<42}{notes}"
                    )

        performance = performance_planner.plan(realized)

        if diagnostics:
            print("\nGESTEN- UND F0-PLAN")
            print("-" * 104)
            for phrase in performance.phrases:
                for syllable in phrase.syllables:
                    g = syllable.gesture
                    targets = " ".join(
                        f"{t.position_percent}%:{t.frequency_hz}"
                        for t in syllable.pitch_targets
                    )
                    print(
                        f"{syllable.timed.score.word:<16}"
                        f"{syllable.timed.score.syllable:<12}"
                        f"A:{g.attack_ms:>3} H:{g.hold_ms:>3} "
                        f"R:{g.release_ms:>3}  {targets}"
                    )

        output.extend(singer.sing(performance))

    if not output:
        raise RuntimeError("Es konnten keine Phoneme erzeugt werden.")

    archived = archive_previous_pho()
    pho = PhoWriter().write(output, str(OUTPUT_PHO))
    MbrolaRenderer(MBROLA_VOICE_PATH).render(pho_path=pho, wav_path=str(OUTPUT_WAV))

    total = sum(p.duration_ms for p in output)

    print("\n" + "=" * 104 + f"\nERGEBNIS\n{'=' * 104}")
    print(f"Gesamtdauer: {total / 1000:.2f} Sekunden")
    print(f"PHO-Datei: {pho} (wird beim nächsten Lauf überschrieben)")
    print(f"WAV-Datei: {OUTPUT_WAV} (wird immer überschrieben)")
    if archived:
        print(f"Vorherige PHO archiviert: {PHO_ARCHIVE} → {archived}")

    return str(OUTPUT_WAV)


def play_audio(audio_file: Path) -> None:
    subprocess.run(["aplay", "-q", str(audio_file)], check=True)


# ---------------------------------------------------------------------------
# Einzelner Durchlauf
# ---------------------------------------------------------------------------

def one_cycle(generator: LocalResponseGenerator) -> None:
    """Ein kompletter Durchlauf: Aufnahme → Transkription → Elfi → Gesang."""
    t = time()
    print()
    print("-" * 54)
    print(f"AUFNAHME: Ich höre {RECORDING_SECONDS} Sekunden zu …")
    print("Bitte jetzt deutlich und nah am Mikrofon sprechen.")

    record_audio(
        output_file=RECORDING_FILE,
        duration_seconds=RECORDING_SECONDS,
        device="plughw:0,0",
    )

    print("STT: Sprache wird vollständig lokal erkannt …")
    print(f"{time() - t:.2f} Sec")
    t = time()
    transcript = transcribe(RECORDING_FILE)
    transcript = prepare_transcript(transcript)

    if not transcript:
        print("Es wurde kein verständlicher Text erkannt – überspringe.")
        return

    print()
    print("ERKANNT:")
    print(f'  "{transcript}"')

    print(f"{time() - t:.2f} Sec")
    t = time()
    # --- Elfi-Antwort ---
    print()
    print("ELFI DENKT NACH …")

    answer = generator.generate(transcript)
    answer = prepare_llm_answer(answer)

    if not answer:
        print("Das Sprachmodell hat keine verwendbare Antwort erzeugt.")
        return

    print(f"{time() - t:.2f} Sec")
    t = time()
    print()
    print("ELFI ANTWORTET:")
    print(f'  "{answer}"')

    # --- Gesang ---
    singing_text = prepare_for_singing(answer)

    if not singing_text:
        print("Aus Elfis Antwort konnte kein singbarer Text erzeugt werden.")
        return

    if singing_text != answer:
        print()
        print("FÜR DEN GESANG AUFBEREITET:")
        print(f'  "{singing_text}"')

    print()
    print("GESANG: TechScore und MBROLA arbeiten …")

    print(f"{time() - t:.2f} Sec")
    t = time()
    wav_path = render_text(
        text=singing_text,
        bpm=BPM,
        diagnostics=False,
    )

    print()
    print("WIEDERGABE …")
    play_audio(Path(wav_path))

    print(f"{time() - t:.2f} Sec")
    t = time()

# ---------------------------------------------------------------------------
# Hauptprogramm
# ---------------------------------------------------------------------------

def main() -> int:
    print()
    print("=" * 54)
    print("       SINGENDER AUFZUG – LLM-DEMO 0.4")
    print("=" * 54)
    print()
    print("Lokale Verarbeitung:")
    print("Enter → Mikrofon → Whisper → Elfi-LLM (llama-server)")
    print("       → TechScore → MBROLA → Lautsprecher → nächster Durchlauf")
    print()
    print("Beenden: Ctrl+C")

    # ------------------------------------------------------------------
    # Argumente für schnellen Text-Direktmodus (optional)
    # ------------------------------------------------------------------
    parser = argparse.ArgumentParser(
        description="Singender Aufzug – TechScore V4"
    )
    parser.add_argument("text", nargs="*")
    parser.add_argument("--bpm", type=int, default=BPM)
    parser.add_argument("--diagnostics", action="store_true")
    args = parser.parse_args()

    text_arg = " ".join(args.text).strip()
    if text_arg:
        # Direktmodus: nur singen, kein LLM, keine Aufnahme
        render_text(text_arg, args.bpm, args.diagnostics)
        return 0

    # ------------------------------------------------------------------
    # Interaktiver LLM-Modus
    # ------------------------------------------------------------------
    llm_generator: LocalResponseGenerator | None = None

    try:
        print()
        print("SYSTEMCHECK …")
        check_system()
        print("SYSTEMCHECK: OK")

        print()
        print("LLM: Elfi wird vorbereitet …")
        llm_generator = LocalResponseGenerator()
        llm_generator.start_server()
        llm_generator.check_system()
        print("LLM: Elfi ist bereit.")

        durchlauf = 0

        while True:
            durchlauf += 1
            print()
            print("=" * 54)
            print(f"       DURCHLAUF {durchlauf}")
            print("=" * 54)

            input("\nDrücke ENTER zum Aufnehmen (oder Ctrl+C zum Beenden).")

            try:
                one_cycle(llm_generator)
            except Exception as exc:
                print()
                print(f"Fehler in Durchlauf {durchlauf}: {exc}")
                print("Starte nächsten Durchlauf …")

    except KeyboardInterrupt:
        print("\n\nAuf Wiedersehen! Elfi verabschiedet sich.")
        return 0

    except Exception as exc:
        print()
        print("=" * 54)
        print("DAS PROGRAMM KONNTE NICHT GESTARTET WERDEN")
        print("=" * 54)
        print(exc)
        return 1

    finally:
        if llm_generator is not None:
            print()
            llm_generator.stop_server()


if __name__ == "__main__":
    raise SystemExit(main())
