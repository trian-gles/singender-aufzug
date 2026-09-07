from __future__ import annotations

from dataclasses import dataclass
import math

from audio.pho import PitchTarget
from music.tech_score import AccentLevel, RealizedTechScore, TimedSyllable
from singing.singer import AFFRICATES, FRICATIVES, LIQUIDS, NASALS, PLOSIVES


@dataclass(frozen=True)
class GesturePlan:
    attack_ms: int
    hold_ms: int
    release_ms: int
    word_boundary_before: bool
    word_boundary_after: bool


@dataclass(frozen=True)
class PerformedSyllable:
    timed: TimedSyllable
    phoneme_durations_ms: tuple[int, ...]
    pitch_targets: tuple[PitchTarget, ...]
    gesture: GesturePlan


@dataclass(frozen=True)
class PerformedPhrase:
    syllables: tuple[PerformedSyllable, ...]
    pause_ms: int


@dataclass(frozen=True)
class PerformanceScore:
    phrases: tuple[PerformedPhrase, ...]


class PerformancePlanner:
    """Erzeugt Artikulationsgesten und eine weiche, dichte F0-Kurve.

    Wortgrenzen werden nicht durch Pausen markiert, sondern durch eine leicht
    stärkere Attack-/Release-Geste. Tonwechsel werden mit Smoothstep-Kurven
    und vielen MBROLA-Zielpunkten realisiert.
    """

    def __init__(
        self,
        transition_points: int = 9,
        transition_fraction: float = 0.28,
        vibrato_depth_cents: float = 10.0,
        vibrato_cycles: float = 1.3,
    ) -> None:
        self.transition_points = max(5, min(17, transition_points))
        self.transition_fraction = max(0.14, min(0.45, transition_fraction))
        self.vibrato_depth_cents = max(0.0, min(24.0, vibrato_depth_cents))
        self.vibrato_cycles = max(0.5, min(3.0, vibrato_cycles))

    def plan(self, score: RealizedTechScore) -> PerformanceScore:
        phrases: list[PerformedPhrase] = []
        for phrase in score.phrases:
            performed: list[PerformedSyllable] = []
            for index, syllable in enumerate(phrase.syllables):
                before = index > 0 and phrase.syllables[index - 1].score.word_index != syllable.score.word_index
                after = index + 1 < len(phrase.syllables) and phrase.syllables[index + 1].score.word_index != syllable.score.word_index
                durations = self._shape_durations(syllable, before, after)
                gesture = self._gesture(syllable, durations, before, after)
                pitch = self._pitch_curve(syllable)
                performed.append(PerformedSyllable(syllable, tuple(durations), tuple(pitch), gesture))
            phrases.append(PerformedPhrase(tuple(performed), phrase.pause_ms))
        return PerformanceScore(tuple(phrases))

    def _shape_durations(self, timed: TimedSyllable, before: bool, after: bool) -> list[int]:
        durations = list(timed.phoneme_durations_ms)
        if not durations or timed.vowel_index < 0:
            return durations

        # Statt einer Wortpause werden Wortanfang und -ende minimal profiliert.
        # Die Silbendauer bleibt exakt erhalten; Zeit wird nur vom Vokal geliehen.
        vowel = timed.vowel_index
        adjustments: list[tuple[int, int]] = []
        if before and vowel > 0:
            adjustments.append((0, self._boundary_bonus(timed.score.phonemes[0].symbol, initial=True)))
        if after and vowel < len(durations) - 1:
            adjustments.append((len(durations) - 1, self._boundary_bonus(timed.score.phonemes[-1].symbol, initial=False)))

        for index, bonus in adjustments:
            available = max(0, durations[vowel] - 105)
            applied = min(bonus, available)
            durations[index] += applied
            durations[vowel] -= applied
        return durations

    @staticmethod
    def _boundary_bonus(symbol: str, initial: bool) -> int:
        if symbol in PLOSIVES:
            return 10 if initial else 8
        if symbol in AFFRICATES:
            return 9
        if symbol in FRICATIVES:
            return 7
        if symbol in NASALS or symbol in LIQUIDS:
            return 5
        return 3

    @staticmethod
    def _gesture(timed: TimedSyllable, durations: list[int], before: bool, after: bool) -> GesturePlan:
        if timed.vowel_index < 0:
            return GesturePlan(sum(durations), 0, 0, before, after)
        attack = sum(durations[:timed.vowel_index])
        hold = durations[timed.vowel_index]
        release = sum(durations[timed.vowel_index + 1:])
        return GesturePlan(attack, hold, release, before, after)

    def _pitch_curve(self, timed: TimedSyllable) -> list[PitchTarget]:
        if not timed.notes:
            return []
        total = sum(n.duration_ms for n in timed.notes)
        if total <= 0:
            return []

        points: list[tuple[float, float]] = [(0.0, float(timed.notes[0].note.frequency_hz))]
        notes = timed.notes
        for previous, current in zip(notes, notes[1:]):
            boundary = current.start_ms / total
            half_width = min(self.transition_fraction / 2.0, previous.duration_ms / total * 0.42, current.duration_ms / total * 0.42)
            start = max(0.0, boundary - half_width)
            end = min(1.0, boundary + half_width)
            points.append((start, float(previous.note.frequency_hz)))
            for i in range(1, self.transition_points + 1):
                x = i / (self.transition_points + 1)
                smooth = x * x * (3.0 - 2.0 * x)
                pos = start + (end - start) * x
                hz = previous.note.frequency_hz + (current.note.frequency_hz - previous.note.frequency_hz) * smooth
                points.append((pos, hz))
            points.append((end, float(current.note.frequency_hz)))
        points.append((1.0, float(notes[-1].note.frequency_hz)))

        # Sehr dezente Lebendigkeit nur auf langen, betonten Vokalen.
        if timed.duration_ms >= 480 and timed.score.accent in {AccentLevel.NUCLEAR, AccentLevel.SECONDARY} and self.vibrato_depth_cents > 0:
            base_hz = float(notes[-1].note.frequency_hz)
            for i in range(5):
                pos = 0.58 + i * 0.085
                if pos >= 0.96:
                    break
                phase = 2.0 * math.pi * self.vibrato_cycles * ((pos - 0.58) / 0.38)
                cents = self.vibrato_depth_cents * math.sin(phase)
                hz = base_hz * math.pow(2.0, cents / 1200.0)
                points.append((pos, hz))

        compact: dict[int, int] = {}
        for pos, hz in sorted(points, key=lambda item: item[0]):
            percent = max(0, min(100, round(pos * 100)))
            compact[percent] = round(hz)
        return [PitchTarget(pos, compact[pos]) for pos in sorted(compact)]
