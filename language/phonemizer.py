from dataclasses import replace
import subprocess

from audio.pho import Phoneme, PhoParser
from language.analyzer import Word


ENGLISH_TERMS = frozenset(
    {
        "production",
        "lab",
        "music",
        "night",
        "music-night",
        "irish",
        "folk",
        "jam",
        "session",
        "jam-session",
        "free",
        "noise",
        "improvisation",
        "conceptual",
        "interface",
        "clarks",
        "planet",
        "friends",
        "drums",
    }
)

# mb-en1 erzeugt echte englische Phoneme. de4 besitzt nicht alle davon;
# diese Tabelle bildet nur die fehlenden Laute auf die nächstliegenden
# MBROLA-de4-Phoneme ab. Die vorhandenen Konsonanten bleiben erhalten.
ENGLISH_TO_DE4 = {
    "r": ("R",),
    "V": ("a",),
    "{": ("E",),
    "e": ("E",),
    "@U": ("aU",),
    "OI": ("OY",),
    "eI": ("e:",),
    "A:": ("a:",),
    "dZ": ("d", "S"),
    "5": ("@", "l"),
}


class SyllablePhonemizer:
    def __init__(self, voice: str = "mb-de2") -> None:
        self.voice = voice
        self.parser = PhoParser()

    def phonemize_syllable(self, syllable: str) -> list[Phoneme]:
        result = subprocess.run(
            [
                "espeak-ng",
                "-v",
                self.voice,
                "--pho",
                syllable,
            ],
            capture_output=True,
            text=True,
            check=True,
        )

        phonemes: list[Phoneme] = []

        for line in result.stdout.splitlines():
            phoneme = self.parser.parse_line(line)

            if phoneme is None:
                continue

            # Von eSpeak eingefügte Pausen zunächst entfernen.
            if phoneme.symbol == "_":
                continue

            phonemes.append(phoneme)

        return phonemes

    def phonemize_text(self, text: str) -> list[Phoneme]:
        english_term = text.lower() in ENGLISH_TERMS
        result = subprocess.run(
            [
                "espeak-ng",
                "-v",
                "mb-en1" if english_term else self.voice,
                "--pho",
                text,
            ],
            capture_output=True,
            text=True,
            check=True,
        )

        phonemes: list[Phoneme] = []

        for line in result.stdout.splitlines():
            phoneme = self.parser.parse_line(line)

            if phoneme is not None:
                phonemes.append(phoneme)

        if english_term:
            return self._map_english_to_de4(phonemes)

        return phonemes

    @staticmethod
    def _map_english_to_de4(phonemes: list[Phoneme]) -> list[Phoneme]:
        """Überträgt en1-Phoneme auf das Inventar der de4-Stimme."""

        mapped: list[Phoneme] = []
        for phoneme in phonemes:
            symbols = ENGLISH_TO_DE4.get(phoneme.symbol, (phoneme.symbol,))
            duration, remainder = divmod(phoneme.duration_ms, len(symbols))

            for index, symbol in enumerate(symbols):
                mapped.append(
                    replace(
                        phoneme,
                        symbol=symbol,
                        duration_ms=duration + (1 if index < remainder else 0),
                        pitch_targets=phoneme.pitch_targets if index == 0 else [],
                    )
                )

        return mapped

    def phonemize_word(
        self,
        word: Word,
    ) -> list[tuple[str, list[Phoneme]]]:
        return [
            (
                syllable,
                self.phonemize_syllable(syllable),
            )
            for syllable in word.syllables
        ]
