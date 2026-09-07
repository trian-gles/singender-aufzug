from __future__ import annotations

from dataclasses import replace

from audio.pho import Phoneme
from music.performance import PerformanceScore


class TechScoreSinger:
    """Überträgt einen geplanten Performance-Score auf MBROLA-Phoneme."""

    def sing(self, performance: PerformanceScore) -> list[Phoneme]:
        output: list[Phoneme] = []
        for phrase in performance.phrases:
            for syllable in phrase.syllables:
                output.extend(
                    replace(
                        phoneme,
                        duration_ms=duration,
                        pitch_targets=list(syllable.pitch_targets) if i == syllable.timed.vowel_index else [],
                    )
                    for i, (phoneme, duration) in enumerate(
                        zip(syllable.timed.score.phonemes, syllable.phoneme_durations_ms)
                    )
                )
            output.append(Phoneme("_", phrase.pause_ms, []))
        return output
