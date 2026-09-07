from dataclasses import dataclass
import math


NOTE_OFFSETS = {
    "C": -9,
    "C#": -8,
    "D": -7,
    "D#": -6,
    "E": -5,
    "F": -4,
    "F#": -3,
    "G": -2,
    "G#": -1,
    "A": 0,
    "A#": 1,
    "B": 2,
}


def note_to_hz(note_name: str) -> int:
    note = note_name[:-1]
    octave = int(note_name[-1])

    semitone_distance = NOTE_OFFSETS[note] + (octave - 4) * 12
    frequency = 440 * math.pow(2, semitone_distance / 12)

    return round(frequency)


@dataclass(frozen=True)
class Note:
    pitch_hz: int
    duration_ms: int

    @classmethod
    def from_name(cls, note_name: str, duration_ms: int) -> "Note":
        return cls(
            pitch_hz=note_to_hz(note_name),
            duration_ms=duration_ms,
        )


class Melody:
    @staticmethod
    def welcome() -> list[Note]:
        return [
            Note.from_name("C3", 250),
            Note.from_name("E3", 250),
            Note.from_name("G3", 350),
            Note.from_name("E3", 250),
            Note.from_name("C3", 450),
        ]
