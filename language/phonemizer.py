import subprocess

from audio.pho import Phoneme, PhoParser
from language.analyzer import Word


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
        result = subprocess.run(
            [
                "espeak-ng",
                "-v",
                self.voice,
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

        return phonemes    

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