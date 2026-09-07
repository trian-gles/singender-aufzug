from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import math

from audio.pho import Phoneme


class NoteType(str, Enum):
    LYRIC = "lyric"
    SLUR = "slur"
    REST = "rest"


class AccentLevel(str, Enum):
    NONE = "unbetont"
    LEXICAL = "Wortakzent"
    SECONDARY = "Nebenakzent"
    NUCLEAR = "Satzakzent"


class Cadence(str, Enum):
    STATEMENT = "Aussage"
    QUESTION = "Frage"
    EXCLAMATION = "Ausruf"
    CONTINUATION = "Fortsetzung"


@dataclass(frozen=True)
class ScoreNote:
    midi: int
    beats: float
    note_type: NoteType = NoteType.LYRIC

    @property
    def frequency_hz(self) -> int:
        return round(440.0 * math.pow(2.0, (self.midi - 69) / 12.0))


@dataclass(frozen=True)
class ScoreSyllable:
    word: str
    syllable: str
    phonemes: tuple[Phoneme, ...]
    notes: tuple[ScoreNote, ...]
    accent: AccentLevel
    word_index: int
    syllable_index: int
    phrase_index: int

    @property
    def beats(self) -> float:
        return sum(note.beats for note in self.notes)


@dataclass(frozen=True)
class ScorePhrase:
    syllables: tuple[ScoreSyllable, ...]
    cadence: Cadence
    pause_beats: float


@dataclass(frozen=True)
class TechScore:
    phrases: tuple[ScorePhrase, ...]
    bpm: int
    meter_numerator: int = 4
    meter_denominator: int = 4

    @property
    def beat_ms(self) -> float:
        return 60_000.0 / self.bpm


@dataclass(frozen=True)
class TimedNote:
    note: ScoreNote
    start_ms: int
    duration_ms: int


@dataclass(frozen=True)
class TimedSyllable:
    score: ScoreSyllable
    duration_ms: int
    phoneme_durations_ms: tuple[int, ...]
    vowel_index: int
    notes: tuple[TimedNote, ...]


@dataclass(frozen=True)
class TimedPhrase:
    syllables: tuple[TimedSyllable, ...]
    pause_ms: int


@dataclass(frozen=True)
class RealizedTechScore:
    phrases: tuple[TimedPhrase, ...] = field(default_factory=tuple)
