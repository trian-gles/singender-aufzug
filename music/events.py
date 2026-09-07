from dataclasses import dataclass, field

from audio.pho import Phoneme
from music.melody import Note


@dataclass
class MusicalEvent:
    syllable: str
    note: Note
    phonemes: list[Phoneme] = field(default_factory=list)
    # Eine Silbe darf mehrere melodische Zieltonhöhen tragen. Die Gesamtdauer
    # steht weiterhin in ``note.duration_ms``; der Singer verteilt die Kontur
    # auf den tragenden Vokal.
    melody_pitches_hz: tuple[int, ...] = field(default_factory=tuple)

    @property
    def duration_ms(self) -> int:
        return self.note.duration_ms

    @property
    def pitches_hz(self) -> tuple[int, ...]:
        return self.melody_pitches_hz or (self.note.pitch_hz,)


@dataclass
class MusicalPhrase:
    events: list[MusicalEvent] = field(default_factory=list)

    def add_event(self, event: MusicalEvent) -> None:
        self.events.append(event)

    def total_duration_ms(self) -> int:
        return sum(event.duration_ms for event in self.events)
