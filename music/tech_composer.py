from __future__ import annotations

from dataclasses import dataclass
import unicodedata

from audio.pho import Phoneme
from language.analyzer import Word
from music.tech_score import AccentLevel, Cadence, NoteType, ScoreNote, ScorePhrase, ScoreSyllable, TechScore
from random import choice
from random import randrange
REDUCED_VOWELS = {"@", "6"}
FUNCTION_WORDS = {"am","an","auf","aus","bei","bis","das","dem","den","der","des","die","du","ein","eine","einer","eines","er","es","für","fuer","im","in","ist","isst","mit","mir","nach","sie","und","vom","von","vor","wir","zu","zum","zur"}
PARTICLES = {"auch","bloß","bloss","denn","doch","eben","eigentlich","halt","ja","mal","nur","schon","so","vielleicht"}
FOCUS_PARTICLES = {"wohl","wirklich","sehr"}
STRESS_LEXICON = {"hallo":0,"herzlich":0,"willkommen":0,"singenden":0,"aufzug":0,"hereinspaziert":3,"gerne":0,"grünzeug":0,"gruenzeug":0,"frage":0}

@dataclass(frozen=True)
class WordMaterial:
    word: Word
    phoneme_groups: list[list[Phoneme]]

class TechScoreComposer:
    """Symbolischer Score-Generator mit zurückhaltender Prosodie.

    Der Score speichert MIDI und Beats. Die Tonbewegungen bleiben bewusst klein,
    damit MBROLA nicht wie hartes Auto-Tune klingt.
    """

    def __init__(self, bpm: int = 96, root_midi: int = 54) -> None:
        if not 45 <= bpm <= 220:
            raise ValueError("bpm muss zwischen 45 und 220 liegen")
        self.bpm = bpm
        self.root = root_midi

    def compose(self, materials: list[WordMaterial], punctuation: str = ".") -> TechScore:
        if not materials:
            return TechScore((), self.bpm)
        cadence = self._cadence(punctuation)
        stress_indices = [self._stress_index(m) for m in materials]
        nuclear = self._nuclear_word(materials)
        secondary = self._secondary_word(materials, nuclear)
        final_ref = (len(materials)-1, len(materials[-1].word.syllables)-1)
        syllables: list[ScoreSyllable] = []

        for wi, material in enumerate(materials):
            norm = self._normalize(material.word.text)
            for si, (text, phonemes) in enumerate(zip(material.word.syllables, material.phoneme_groups)):
                lexical = si == stress_indices[wi]
                accent = AccentLevel.NONE
                if wi == nuclear and lexical:
                    accent = AccentLevel.NUCLEAR
                elif wi == secondary and lexical:
                    accent = AccentLevel.SECONDARY
                elif lexical and norm not in FUNCTION_WORDS and norm not in PARTICLES and wi != nuclear:
                    accent = AccentLevel.LEXICAL

                final = (wi, si) == final_ref
                beats = self._beats(norm, phonemes, accent, final)
                midis = self._midis(wi, accent, cadence, final)
                notes = self._notes(midis, beats)
                syllables.append(ScoreSyllable(material.word.text, text, tuple(phonemes), notes, accent, wi, si, 0))

        return TechScore((ScorePhrase(tuple(syllables), cadence, self._pause_beats(cadence)),), self.bpm)

    def _beats(self, word: str, phonemes: list[Phoneme], accent: AccentLevel, final: bool) -> float:
        reduced = any(p.symbol in REDUCED_VOWELS for p in phonemes)
        if accent is AccentLevel.NUCLEAR:
            value = 0.88
        elif accent is AccentLevel.SECONDARY:
            value = 0.62
        elif accent is AccentLevel.LEXICAL:
            value = 0.48
        elif word in FUNCTION_WORDS:
            value = 0.38 if word == "du" else 0.48 if word in {"isst", "ist"} else 0.42
        elif reduced:
            value = 0.30
        else:
            value = 0.46
        if final:
            value += 0.14
        return value

    def transpose(self, note):
        t_dict= {
        -5: -3,
        -3: -1,
        -1: 0,
         0: 2,
         2: 4,
         4: 5,
         5: 7,
         7: 9,
         9: 11,
         11: 12,
    }
        while note > 12:
            note -= 12

        if randrange(0, 3) == 1:
            return self.transpose(t_dict[note])
        else:
            return note

    def _midis(self, wi: int, accent: AccentLevel, cadence: Cadence, final: bool) -> tuple[int, ...]:
        # Nach einem Nebenakzent fällt die Linie wieder auf den Grundton zurück.
        if accent is AccentLevel.SECONDARY:
            return choice([(self.root + self.transpose(0),), (self.root + self.transpose(-1),)])
        if accent is AccentLevel.NUCLEAR:
            if cadence is Cadence.QUESTION:
                return choice([(self.root + self.transpose(4),), (self.root + self.transpose(7),)])
            if cadence is Cadence.EXCLAMATION:
                return (self.root + self.transpose(4),)
            return (self.root + self.transpose(4),)
        if final:
            if cadence is Cadence.QUESTION:
                return (self.root + self.transpose(4),)
            if cadence is Cadence.STATEMENT:
                return (self.root + self.transpose(-5),)
            if cadence is Cadence.EXCLAMATION:
                return (self.root + self.transpose(7),)
        return choice([(self.root,), (self.root + self.transpose(-1),)])

    @staticmethod
    def _notes(midis: tuple[int, ...], beats: float) -> tuple[ScoreNote, ...]:
        if len(midis) == 1:
            ratios = (1.0,)
        elif len(midis) == 2:
            ratios = (0.58, 0.42)
        else:
            ratios = (0.30, 0.42, 0.28)
        return tuple(ScoreNote(midi, beats * ratio, NoteType.LYRIC if i == 0 else NoteType.SLUR)
                     for i, (midi, ratio) in enumerate(zip(midis, ratios)))

    def _nuclear_word(self, materials: list[WordMaterial]) -> int:
        for i in range(len(materials)-1, -1, -1):
            word = self._normalize(materials[i].word.text)
            if word not in FUNCTION_WORDS and word not in PARTICLES and word not in FOCUS_PARTICLES:
                return i
        return len(materials)-1

    def _secondary_word(self, materials: list[WordMaterial], nuclear: int) -> int | None:
        focus = [i for i in range(nuclear) if self._normalize(materials[i].word.text) in FOCUS_PARTICLES]
        if focus:
            return focus[-1]
        candidates = [i for i in range(nuclear) if self._normalize(materials[i].word.text) not in FUNCTION_WORDS and self._normalize(materials[i].word.text) not in PARTICLES]
        return candidates[-1] if candidates else None

    def _stress_index(self, material: WordMaterial) -> int:
        word = self._normalize(material.word.text)
        if word in STRESS_LEXICON:
            return min(STRESS_LEXICON[word], len(material.word.syllables)-1)
        for i, group in enumerate(material.phoneme_groups):
            if not any(p.symbol in REDUCED_VOWELS for p in group):
                return i
        return 0

    @staticmethod
    def _cadence(punctuation: str) -> Cadence:
        return {"?":Cadence.QUESTION,"!":Cadence.EXCLAMATION,",":Cadence.CONTINUATION,";":Cadence.CONTINUATION,":":Cadence.CONTINUATION}.get(punctuation, Cadence.STATEMENT)

    @staticmethod
    def _pause_beats(cadence: Cadence) -> float:
        return {Cadence.QUESTION:0.90,Cadence.EXCLAMATION:0.85,Cadence.CONTINUATION:0.45,Cadence.STATEMENT:0.90}[cadence]

    @staticmethod
    def _normalize(text: str) -> str:
        value = unicodedata.normalize("NFKD", text.lower())
        value = "".join(ch for ch in value if not unicodedata.combining(ch))
        return value.replace("ß", "ss")
