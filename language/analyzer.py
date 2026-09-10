from dataclasses import dataclass
import re

import pyphen


PRONUNCIATION_SYLLABLES = {
    "production": ["Pro", "duc", "tion"],
    "music": ["Mu", "sic"],
    "music-night": ["Mu", "sic", "Night"],
    "irish": ["I", "rish"],
    "session": ["Ses", "sion"],
    "jam-session": ["Jam", "Ses", "sion"],
    "improvisation": ["Im", "pro", "vi", "sa", "tion"],
    "conceptual": ["Con", "cep", "tu", "al"],
    "interface": ["In", "ter", "face"],
}


@dataclass(frozen=True)
class Word:
    text: str
    syllables: list[str]


class TextAnalyzer:
    def __init__(self, language: str = "de_DE") -> None:
        self.hyphenator = pyphen.Pyphen(lang=language)

    def split_into_words(self, text: str) -> list[str]:
        return re.findall(r"[A-Za-zÄÖÜäöüß]+(?:[-'][A-Za-zÄÖÜäöüß]+)*", text)

    def split_into_syllables(self, word: str) -> list[str]:
        pronunciation_syllables = PRONUNCIATION_SYLLABLES.get(word.lower())
        if pronunciation_syllables:
            return pronunciation_syllables

        # Zuerst an vorhandenen Bindestrichen und Apostrophen
        # in Teilwörter zerlegen, dann jedes Teilwort einzeln
        # mit pyphen silbifizieren.
        subwords = re.split(r"[-']", word)
        syllables: list[str] = []
        for subword in subwords:
            separated = self.hyphenator.inserted(subword)
            if not separated:
                syllables.append(subword)
            else:
                syllables.extend(separated.split("-"))
        return syllables

    def analyze(self, text: str) -> list[Word]:
        words = self.split_into_words(text)

        return [
            Word(
                text=word,
                syllables=self.split_into_syllables(word),
            )
            for word in words
        ]
