from dataclasses import replace

from audio.pho import Phoneme, PitchTarget
from music.events import MusicalEvent, MusicalPhrase


VOWELS = {
    "a", "a:",
    "e", "e:",
    "i", "i:",
    "o", "o:",
    "u", "u:",
    "y", "y:",
    "2", "2:",
    "9", "9:",
    "E", "I", "O", "U", "Y",
    "@",
    "aU", "aI", "OY",
}

LONG_VOWELS = {
    "a:",
    "e:",
    "i:",
    "o:",
    "u:",
    "y:",
    "2:",
    "9:",
}

DIPHTHONGS = {
    "aU",
    "aI",
    "OY",
}

REDUCED_VOWELS = {
    "@",
    "6",
}

PLOSIVES = {
    "p", "b",
    "t", "d",
    "k", "g",
}

AFFRICATES = {
    "ts",
    "tS",
    "pf",
}

FRICATIVES = {
    "f", "v",
    "s", "z",
    "S", "Z",
    "C", "x",
    "h",
}

NASALS = {
    "m", "n", "N",
}

LIQUIDS = {
    "l", "R", "r", "j",
}


class BalancedSinger:
    """
    Verteilt die musikalisch geplante Silbendauer anhand
    phonologischer Gewichte auf die einzelnen Phoneme.

    Vokale erhalten ein deutlich höheres Gewicht als
    Konsonanten, da sie im Gesang den Ton tragen.
    """

    def __init__(
        self,
        vowel_weight: float = 6.0,
        long_vowel_weight: float = 7.0,
        diphthong_weight: float = 7.0,
        reduced_vowel_weight: float = 4.5,
        plosive_weight: float = 1.6,
        affricate_weight: float = 2.6,
        fricative_weight: float = 2.2,
        nasal_weight: float = 2.0,
        liquid_weight: float = 1.8,
        default_consonant_weight: float = 2.0,
    ) -> None:
        self.vowel_weight = vowel_weight
        self.long_vowel_weight = long_vowel_weight
        self.diphthong_weight = diphthong_weight
        self.reduced_vowel_weight = reduced_vowel_weight

        self.plosive_weight = plosive_weight
        self.affricate_weight = affricate_weight
        self.fricative_weight = fricative_weight
        self.nasal_weight = nasal_weight
        self.liquid_weight = liquid_weight

        self.default_consonant_weight = (
            default_consonant_weight
        )

    def sing_phrase(
        self,
        phrase: MusicalPhrase,
    ) -> list[Phoneme]:
        result: list[Phoneme] = []

        for event in phrase.events:
            result.extend(
                self.sing_event(event)
            )

        return result

    def sing_event(
        self,
        event: MusicalEvent,
    ) -> list[Phoneme]:
        if not event.phonemes:
            return []

        durations = self._calculate_weighted_durations(
            phonemes=event.phonemes,
            target_duration_ms=event.note.duration_ms,
        )

        sung_phonemes: list[Phoneme] = []

        for index, phoneme in enumerate(event.phonemes):
            is_vowel = phoneme.symbol in VOWELS

            sung_phonemes.append(
                replace(
                    phoneme,
                    duration_ms=durations[index],
                    pitch_targets=(
                        self._make_pitch_targets(
                            event.note.pitch_hz
                        )
                        if is_vowel
                        else []
                    ),
                )
            )

        return sung_phonemes

    def _calculate_weighted_durations(
        self,
        phonemes: list[Phoneme],
        target_duration_ms: int,
    ) -> list[int]:
        """
        Verteilt target_duration_ms anhand der Lautgewichte.

        Die Summe der ausgegebenen Dauern entspricht exakt
        der musikalischen Vorgabe.
        """

        if not phonemes:
            return []

        target_duration_ms = max(
            len(phonemes),
            target_duration_ms,
        )

        weights = [
            self._phoneme_weight(phoneme.symbol)
            for phoneme in phonemes
        ]

        total_weight = sum(weights)

        if total_weight <= 0:
            weights = [
                1.0
                for _ in phonemes
            ]

            total_weight = sum(weights)

        exact_durations = [
            target_duration_ms
            * weight
            / total_weight
            for weight in weights
        ]

        durations = [
            max(
                1,
                int(duration),
            )
            for duration in exact_durations
        ]

        difference = (
            target_duration_ms
            - sum(durations)
        )

        if difference > 0:
            fractional_order = sorted(
                range(len(exact_durations)),
                key=lambda index: (
                    exact_durations[index]
                    - int(exact_durations[index])
                ),
                reverse=True,
            )

            for index in fractional_order:
                if difference <= 0:
                    break

                durations[index] += 1
                difference -= 1

        while difference > 0:
            longest_index = max(
                range(len(weights)),
                key=lambda index: weights[index],
            )

            durations[longest_index] += 1
            difference -= 1

        while difference < 0:
            candidates = [
                index
                for index, duration in enumerate(durations)
                if duration > 1
            ]

            if not candidates:
                break

            longest_index = max(
                candidates,
                key=lambda index: durations[index],
            )

            durations[longest_index] -= 1
            difference += 1

        return durations

    def _phoneme_weight(
        self,
        symbol: str,
    ) -> float:
        if symbol in LONG_VOWELS:
            return self.long_vowel_weight

        if symbol in DIPHTHONGS:
            return self.diphthong_weight

        if symbol in REDUCED_VOWELS:
            return self.reduced_vowel_weight

        if symbol in VOWELS:
            return self.vowel_weight

        if symbol in PLOSIVES:
            return self.plosive_weight

        if symbol in AFFRICATES:
            return self.affricate_weight

        if symbol in FRICATIVES:
            return self.fricative_weight

        if symbol in NASALS:
            return self.nasal_weight

        if symbol in LIQUIDS:
            return self.liquid_weight

        return self.default_consonant_weight

    def _make_pitch_targets(
        self,
        pitch_hz: int,
    ) -> list[PitchTarget]:
        return [
            PitchTarget(
                position_percent=0,
                frequency_hz=pitch_hz,
            ),
            PitchTarget(
                position_percent=100,
                frequency_hz=pitch_hz,
            ),
        ]


class ConnectedSinger(BalancedSinger):
    """
    Legato-orientierter Sänger für vollständige Sätze.

    Die Silben bleiben rhythmisch getrennt, werden aber ohne künstliche
    Stille aneinandergesetzt. Die tragenden Vokale gleiten leicht von der
    vorherigen zur aktuellen und weiter in Richtung der nächsten Tonhöhe.
    Dadurch wirkt die Ausgabe weniger wie eine Folge einzelner Bausteine.
    """

    def __init__(self) -> None:
        super().__init__(
            vowel_weight=7.2,
            long_vowel_weight=8.6,
            diphthong_weight=8.2,
            reduced_vowel_weight=5.0,
            plosive_weight=2.2,
            affricate_weight=3.0,
            fricative_weight=2.0,
            nasal_weight=1.8,
            liquid_weight=1.6,
            default_consonant_weight=1.8,
        )

        # Mindestdauern sichern die Verständlichkeit. Besonders Plosive
        # verschwinden bei MBROLA schnell, wenn sie durch die reine
        # Gewichtsverteilung nur wenige Millisekunden erhalten.
        self.minimum_durations_ms = {
            "plosive": 55,
            "affricate": 80,
            "fricative": 45,
            "nasal": 38,
            "liquid": 32,
            "default_consonant": 35,
            "vowel": 75,
        }

    def _calculate_weighted_durations(
        self,
        phonemes: list[Phoneme],
        target_duration_ms: int,
    ) -> list[int]:
        """Gewichtsverteilung mit artikulatorischen Mindestdauern.

        Die Gesamtdauer der Silbe bleibt exakt erhalten. Benötigt ein
        Konsonant zusätzliche Zeit, wird sie zuerst von den tragenden
        Vokalen und danach von den längsten übrigen Lauten genommen.
        """
        durations = super()._calculate_weighted_durations(
            phonemes=phonemes,
            target_duration_ms=target_duration_ms,
        )

        if not durations:
            return durations

        minimums = [
            self._minimum_duration_ms(phoneme.symbol)
            for phoneme in phonemes
        ]

        # Bei sehr kurzen Silben müssen die Mindestwerte gemeinsam in die
        # verfügbare Dauer passen. Die Proportionen bleiben dabei erhalten.
        minimum_sum = sum(minimums)
        if minimum_sum > target_duration_ms:
            scale = target_duration_ms / minimum_sum
            minimums = [max(1, int(value * scale)) for value in minimums]

        for index, minimum in enumerate(minimums):
            missing = minimum - durations[index]
            if missing <= 0:
                continue

            durations[index] += missing
            self._take_duration_from_donors(
                durations=durations,
                minimums=minimums,
                protected_index=index,
                amount=missing,
                phonemes=phonemes,
            )

        # Rundungsfehler oder nicht vollständig entziehbare Millisekunden
        # werden abschließend exakt korrigiert.
        difference = target_duration_ms - sum(durations)
        while difference > 0:
            donor = max(range(len(durations)), key=lambda i: durations[i])
            durations[donor] += 1
            difference -= 1
        while difference < 0:
            candidates = [
                i for i, value in enumerate(durations)
                if value > minimums[i]
            ]
            if not candidates:
                candidates = [i for i, value in enumerate(durations) if value > 1]
            if not candidates:
                break
            donor = max(candidates, key=lambda i: durations[i] - minimums[i])
            durations[donor] -= 1
            difference += 1

        return durations

    def _minimum_duration_ms(self, symbol: str) -> int:
        if symbol in PLOSIVES:
            return self.minimum_durations_ms["plosive"]
        if symbol in AFFRICATES:
            return self.minimum_durations_ms["affricate"]
        if symbol in FRICATIVES:
            return self.minimum_durations_ms["fricative"]
        if symbol in NASALS:
            return self.minimum_durations_ms["nasal"]
        if symbol in LIQUIDS:
            return self.minimum_durations_ms["liquid"]
        if symbol in VOWELS or symbol in REDUCED_VOWELS:
            return self.minimum_durations_ms["vowel"]
        return self.minimum_durations_ms["default_consonant"]

    @staticmethod
    def _take_duration_from_donors(
        durations: list[int],
        minimums: list[int],
        protected_index: int,
        amount: int,
        phonemes: list[Phoneme],
    ) -> None:
        remaining = amount

        # Vokale tragen den Ton und haben meist den größten Spielraum.
        donor_order = sorted(
            (
                i for i in range(len(durations))
                if i != protected_index
            ),
            key=lambda i: (
                phonemes[i].symbol in VOWELS,
                durations[i] - minimums[i],
            ),
            reverse=True,
        )

        for donor in donor_order:
            if remaining <= 0:
                break
            available = max(0, durations[donor] - minimums[donor])
            taken = min(available, remaining)
            durations[donor] -= taken
            remaining -= taken

        # Nur bei extrem kurzen Silben unter die Komfort-Mindestwerte gehen.
        if remaining > 0:
            donor_order = sorted(
                (i for i in range(len(durations)) if i != protected_index),
                key=lambda i: durations[i],
                reverse=True,
            )
            for donor in donor_order:
                if remaining <= 0:
                    break
                available = max(0, durations[donor] - 1)
                taken = min(available, remaining)
                durations[donor] -= taken
                remaining -= taken

    def sing_event(
        self,
        event: MusicalEvent,
    ) -> list[Phoneme]:
        """Singt eine Silbe mit ihrer vollständigen Melodiekontur."""
        sung = super().sing_event(event)
        self._apply_melodic_contour(
            phonemes=sung,
            pitches=event.pitches_hz,
            previous_pitch=event.pitches_hz[0],
            next_pitch=event.pitches_hz[-1],
        )
        return sung

    def sing_phrase(
        self,
        phrase: MusicalPhrase,
    ) -> list[Phoneme]:
        result: list[Phoneme] = []

        for index, event in enumerate(phrase.events):
            pitches = event.pitches_hz
            previous_pitch = (
                phrase.events[index - 1].pitches_hz[-1]
                if index > 0
                else pitches[0]
            )
            next_pitch = (
                phrase.events[index + 1].pitches_hz[0]
                if index < len(phrase.events) - 1
                else pitches[-1]
            )

            sung = super().sing_event(event)
            self._apply_melodic_contour(
                phonemes=sung,
                pitches=pitches,
                previous_pitch=previous_pitch,
                next_pitch=next_pitch,
            )
            result.extend(sung)

        return result

    @staticmethod
    def _apply_melodic_contour(
        phonemes: list[Phoneme],
        pitches: tuple[int, ...],
        previous_pitch: int,
        next_pitch: int,
    ) -> None:
        """Legt ein- oder mehrtönige Konturen ausschließlich auf Vokale.

        Der erste Zielton wird sehr schnell erreicht. So bleiben anlautende
        Konsonanten deutlich und die Silbe beginnt nicht mit einem langen
        Portamento aus der vorherigen Tonhöhe.
        """
        if not pitches:
            return

        for phoneme in phonemes:
            if phoneme.symbol not in VOWELS:
                continue

            targets: list[PitchTarget] = []
            start_pitch = round(pitches[0] + 0.08 * (previous_pitch - pitches[0]))
            targets.append(PitchTarget(position_percent=0, frequency_hz=start_pitch))

            if len(pitches) == 1:
                targets.extend([
                    PitchTarget(position_percent=12, frequency_hz=pitches[0]),
                    PitchTarget(position_percent=88, frequency_hz=pitches[0]),
                ])
            else:
                # Die eigentlichen Noten werden über den zentralen Vokalbereich
                # verteilt. Ein Drei-Ton-Melisma liegt z. B. bei 12/50/88 %.
                first_position = 12
                last_position = 88
                step = (last_position - first_position) / (len(pitches) - 1)
                for index, pitch in enumerate(pitches):
                    targets.append(
                        PitchTarget(
                            position_percent=round(first_position + index * step),
                            frequency_hz=pitch,
                        )
                    )

            outgoing = round(pitches[-1] + 0.08 * (next_pitch - pitches[-1]))
            targets.append(PitchTarget(position_percent=100, frequency_hz=outgoing))
            phoneme.pitch_targets[:] = targets


class LegatoSinger(BalancedSinger):
    def __init__(self) -> None:
        super().__init__(
            vowel_weight=7.0,
            long_vowel_weight=8.5,
            diphthong_weight=8.0,
            reduced_vowel_weight=5.0,
            plosive_weight=1.2,
            affricate_weight=2.0,
            fricative_weight=1.8,
            nasal_weight=1.8,
            liquid_weight=1.6,
            default_consonant_weight=1.7,
        )


class StrongLegatoSinger(BalancedSinger):
    def __init__(
        self,
        duration_factor: float = 1.8,
    ) -> None:
        super().__init__(
            vowel_weight=8.0,
            long_vowel_weight=10.0,
            diphthong_weight=9.0,
            reduced_vowel_weight=5.5,
            plosive_weight=1.0,
            affricate_weight=1.8,
            fricative_weight=1.6,
            nasal_weight=1.6,
            liquid_weight=1.4,
            default_consonant_weight=1.5,
        )

        self.duration_factor = duration_factor

    def sing_event(
        self,
        event: MusicalEvent,
    ) -> list[Phoneme]:
        extended_event = replace(
            event,
            note=replace(
                event.note,
                duration_ms=round(
                    event.note.duration_ms
                    * self.duration_factor
                ),
            ),
        )

        phonemes = super().sing_event(
            extended_event
        )

        for phoneme in phonemes:
            if phoneme.symbol not in VOWELS:
                continue

            phoneme.pitch_targets[:] = [
                PitchTarget(
                    position_percent=0,
                    frequency_hz=round(
                        event.note.pitch_hz
                        * 0.96
                    ),
                ),
                PitchTarget(
                    position_percent=30,
                    frequency_hz=event.note.pitch_hz,
                ),
                PitchTarget(
                    position_percent=100,
                    frequency_hz=event.note.pitch_hz,
                ),
            ]

        return phonemes


class ExpressiveSinger(BalancedSinger):
    def __init__(self) -> None:
        super().__init__(
            vowel_weight=6.0,
            long_vowel_weight=7.5,
            diphthong_weight=7.0,
            reduced_vowel_weight=4.2,
            plosive_weight=1.6,
            affricate_weight=2.6,
            fricative_weight=2.2,
            nasal_weight=2.0,
            liquid_weight=1.8,
            default_consonant_weight=2.0,
        )

    def sing_event(
        self,
        event: MusicalEvent,
    ) -> list[Phoneme]:
        phonemes = super().sing_event(event)

        for phoneme in phonemes:
            if phoneme.symbol not in VOWELS:
                continue

            base_pitch = event.note.pitch_hz

            phoneme.pitch_targets[:] = [
                PitchTarget(
                    position_percent=0,
                    frequency_hz=round(
                        base_pitch * 0.99
                    ),
                ),
                PitchTarget(
                    position_percent=20,
                    frequency_hz=base_pitch,
                ),
                PitchTarget(
                    position_percent=80,
                    frequency_hz=base_pitch,
                ),
                PitchTarget(
                    position_percent=100,
                    frequency_hz=round(
                        base_pitch * 0.985
                    ),
                ),
            ]

        return phonemes


class StaccatoSinger(BalancedSinger):
    def __init__(self) -> None:
        super().__init__(
            vowel_weight=4.5,
            long_vowel_weight=5.2,
            diphthong_weight=5.0,
            reduced_vowel_weight=3.5,
            plosive_weight=2.4,
            affricate_weight=3.2,
            fricative_weight=2.8,
            nasal_weight=2.4,
            liquid_weight=2.2,
            default_consonant_weight=2.5,
        )


class StrongStaccatoSinger(BalancedSinger):
    def __init__(
        self,
        pause_duration_ms: int = 120,
        duration_factor: float = 0.6,
    ) -> None:
        super().__init__(
            vowel_weight=4.0,
            long_vowel_weight=4.5,
            diphthong_weight=4.5,
            reduced_vowel_weight=3.0,
            plosive_weight=2.8,
            affricate_weight=3.5,
            fricative_weight=3.0,
            nasal_weight=2.5,
            liquid_weight=2.3,
            default_consonant_weight=2.6,
        )

        self.pause_duration_ms = pause_duration_ms
        self.duration_factor = duration_factor

    def sing_phrase(
        self,
        phrase: MusicalPhrase,
    ) -> list[Phoneme]:
        result: list[Phoneme] = []

        for index, event in enumerate(phrase.events):
            shortened_event = replace(
                event,
                note=replace(
                    event.note,
                    duration_ms=max(
                        100,
                        round(
                            event.note.duration_ms
                            * self.duration_factor
                        ),
                    ),
                ),
            )

            result.extend(
                self.sing_event(
                    shortened_event
                )
            )

            if index < len(phrase.events) - 1:
                result.append(
                    Phoneme(
                        symbol="_",
                        duration_ms=self.pause_duration_ms,
                        pitch_targets=[],
                    )
                )

        return result
