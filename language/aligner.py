from audio.pho import Phoneme


VOWELS = {
    "a",
    "a:",
    "e",
    "e:",
    "i",
    "i:",
    "o",
    "o:",
    "u",
    "u:",
    "2",
    "2:",
    "9",
    "9:",
    "E",
    "I",
    "O",
    "U",
    "Y",
    "@",
    "6",
    "aU",
    "aI",
    "OY",
        # --- Entlehnte Nasalvokale (für französische Lehnwörter wie "Teint", "Balkon") ---
    "A~",  # Chance, Restaurant
    "E~",  # Teint, Cousin
    "O~",  # Balkon, Chanson
    "9~",  # Parfüm
}


class SyllableAligner:
    def split_by_vowel_cores(
        self,
        phonemes: list[Phoneme],
    ) -> list[list[Phoneme]]:
        """
        Reguläre Aufteilung anhand der erkannten Vokalkerne.
        """

        cleaned = [
            phoneme
            for phoneme in phonemes
            if phoneme.symbol != "_"
        ]

        vowel_indices = [
            index
            for index, phoneme in enumerate(cleaned)
            if phoneme.symbol in VOWELS
        ]

        if not vowel_indices:
            return [cleaned] if cleaned else []

        groups: list[list[Phoneme]] = []
        start_index = 0

        for vowel_position in range(len(vowel_indices) - 1):
            current_vowel = vowel_indices[vowel_position]
            next_vowel = vowel_indices[vowel_position + 1]

            consonants_between = (
                next_vowel - current_vowel - 1
            )

            if consonants_between <= 1:
                split_index = next_vowel
            else:
                split_index = next_vowel - 1

            groups.append(
                cleaned[start_index:split_index]
            )

            start_index = split_index

        groups.append(cleaned[start_index:])

        return groups

    def align_to_syllable_count(
        self,
        phonemes: list[Phoneme],
        syllable_count: int,
    ) -> list[list[Phoneme]]:
        """
        Erzeugt möglichst genau eine Phonemgruppe pro Silbe.

        Zuerst wird die reguläre Vokalkernanalyse verwendet.
        Nur bei einer Abweichung greift ein Fallback:

        - Zu wenige Gruppen:
          Die längste noch teilbare Gruppe wird geteilt.

        - Zu viele Gruppen:
          Das kürzeste benachbarte Gruppenpaar wird verbunden.
        """

        groups = self.split_by_vowel_cores(phonemes)

        if syllable_count <= 0:
            return groups

        if len(groups) == syllable_count:
            return groups

        original_count = len(groups)

        if len(groups) < syllable_count:
            groups = self._split_until_count(
                groups=groups,
                target_count=syllable_count,
            )

        elif len(groups) > syllable_count:
            groups = self._merge_until_count(
                groups=groups,
                target_count=syllable_count,
            )

        if len(groups) == syllable_count:
            print(
                "ALIGNER-FALLBACK: "
                f"{original_count} Phonemgruppen wurden "
                f"an {syllable_count} Silben angepasst."
            )
        else:
            print(
                "WARNUNG: Der Aligner konnte "
                f"{len(groups)} Phonemgruppen nicht vollständig "
                f"an {syllable_count} Silben anpassen."
            )

        return groups

    def _split_until_count(
        self,
        groups: list[list[Phoneme]],
        target_count: int,
    ) -> list[list[Phoneme]]:
        """
        Teilt schrittweise die längste Gruppe.

        Eine Gruppe mit nur einem Phonem kann nicht weiter
        sinnvoll geteilt werden.
        """

        result = [
            list(group)
            for group in groups
            if group
        ]

        while len(result) < target_count:
            candidates = [
                (index, group)
                for index, group in enumerate(result)
                if len(group) >= 2
            ]

            if not candidates:
                break

            group_index, group = max(
                candidates,
                key=lambda item: len(item[1]),
            )

            split_index = self._best_fallback_split_index(
                group
            )

            left = group[:split_index]
            right = group[split_index:]

            if not left or not right:
                break

            result[group_index:group_index + 1] = [
                left,
                right,
            ]

        return result

    def _best_fallback_split_index(
        self,
        group: list[Phoneme],
    ) -> int:
        """
        Sucht eine möglichst plausible Trennstelle.

        Bevorzugt wird eine Stelle nach einem Vokal.
        Falls das nicht möglich ist, wird ungefähr
        in der Mitte geteilt.
        """

        middle = len(group) / 2

        vowel_boundaries = [
            index + 1
            for index, phoneme in enumerate(group[:-1])
            if phoneme.symbol in VOWELS
        ]

        if vowel_boundaries:
            return min(
                vowel_boundaries,
                key=lambda index: abs(index - middle),
            )

        return max(
            1,
            min(
                len(group) - 1,
                len(group) // 2,
            ),
        )

    def _merge_until_count(
        self,
        groups: list[list[Phoneme]],
        target_count: int,
    ) -> list[list[Phoneme]]:
        """
        Verbindet schrittweise das kürzeste Paar
        benachbarter Gruppen.
        """

        result = [
            list(group)
            for group in groups
            if group
        ]

        while (
            len(result) > target_count
            and len(result) >= 2
        ):
            pair_index = min(
                range(len(result) - 1),
                key=lambda index: (
                    len(result[index])
                    + len(result[index + 1])
                ),
            )

            merged = (
                result[pair_index]
                + result[pair_index + 1]
            )

            result[pair_index:pair_index + 2] = [
                merged
            ]

        return result