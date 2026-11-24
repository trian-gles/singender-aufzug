"""Deutsche Aussprache-Hilfen für Whisper und das LLM."""

from __future__ import annotations


WHISPER_PROMPT_WORDS = [
    "ligeti zentrum", "Hamburg-Harburg", "Veritaskai", "Production Lab",
    "Exhibition Floor", "Tag der offenen Tür", "Disziplinen im Dialog",
    "Science Slam", "strg+alt+ligeti", "Moving Sound Pictures",
    "The Ear Wants to Hear", "Klangskulpturen", "Healing Soundscapes",
    "InnoLab", "Haptic Lab", "Computer Music Lab", "MusiXSpace",
    "diskurs-o-mat", "Elfi", "Aufzug", "Erdgeschoss", "siebter Stock",
    "neunter Stock", "zehnter Stock",
]


def build_whisper_prompt() -> str:
    """Liefert einen Prompt-String für ``whisper-cli --prompt``."""

    return " ".join(WHISPER_PROMPT_WORDS)


LLM_GERMAN_GUIDE = """Aussprache:
Verwende die Original-Schreibweise der belegten Namen und Formate.
- "Production Lab" (nicht "Produktion Labor")
- "Science Slam strg+alt+ligeti"
- "Moving Sound Pictures"
- "The Ear Wants to Hear"
- "Healing Soundscapes"
"""
