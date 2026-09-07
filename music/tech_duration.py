from __future__ import annotations

from music.tech_score import RealizedTechScore, TechScore, TimedNote, TimedPhrase, TimedSyllable
from singing.singer import AFFRICATES, FRICATIVES, LIQUIDS, NASALS, PLOSIVES, REDUCED_VOWELS, VOWELS


class TechDurationPlanner:
    MINIMUMS = {"plosive":58,"affricate":82,"fricative":47,"nasal":38,"liquid":34,"vowel":82,"other":34}

    def realize(self, score: TechScore) -> RealizedTechScore:
        phrases: list[TimedPhrase] = []
        for phrase in score.phrases:
            timed_syllables: list[TimedSyllable] = []
            for syllable in phrase.syllables:
                duration_ms = max(150, round(syllable.beats * score.beat_ms))
                vowel_index = self._vowel_index(syllable.phonemes)
                durations = self._allocate(syllable.phonemes, duration_ms, vowel_index)
                note_times = self._time_notes(syllable.notes, score.beat_ms)
                timed_syllables.append(TimedSyllable(syllable, duration_ms, tuple(durations), vowel_index, note_times))
            phrases.append(TimedPhrase(tuple(timed_syllables), round(phrase.pause_beats * score.beat_ms)))
        return RealizedTechScore(tuple(phrases))

    def _time_notes(self, notes, beat_ms: float) -> tuple[TimedNote, ...]:
        raw = [max(1, round(n.beats * beat_ms)) for n in notes]
        target = round(sum(n.beats for n in notes) * beat_ms)
        if raw:
            raw[-1] += target - sum(raw)
        cursor = 0
        result = []
        for note, duration in zip(notes, raw):
            result.append(TimedNote(note, cursor, duration))
            cursor += duration
        return tuple(result)

    def _allocate(self, phonemes, total_ms: int, vowel_index: int) -> list[int]:
        if not phonemes:
            return []
        mins = [self._minimum(p.symbol) for p in phonemes]
        if sum(mins) > total_ms:
            scale = total_ms / sum(mins)
            mins = [max(1, round(v * scale)) for v in mins]
        durations = list(mins)
        durations[vowel_index if vowel_index >= 0 else len(durations)//2] += total_ms - sum(durations)
        durations[-1] += total_ms - sum(durations)
        return durations

    @staticmethod
    def _vowel_index(phonemes) -> int:
        for i, p in enumerate(phonemes):
            if p.symbol in VOWELS or p.symbol in REDUCED_VOWELS:
                return i
        return -1

    def _minimum(self, symbol: str) -> int:
        if symbol in PLOSIVES: return self.MINIMUMS["plosive"]
        if symbol in AFFRICATES: return self.MINIMUMS["affricate"]
        if symbol in FRICATIVES: return self.MINIMUMS["fricative"]
        if symbol in NASALS: return self.MINIMUMS["nasal"]
        if symbol in LIQUIDS: return self.MINIMUMS["liquid"]
        if symbol in VOWELS or symbol in REDUCED_VOWELS: return self.MINIMUMS["vowel"]
        return self.MINIMUMS["other"]
