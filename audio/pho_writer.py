from pathlib import Path

from audio.pho import Phoneme


class PhoWriter:
    def format_phoneme(self, phoneme: Phoneme) -> str:
        parts = [
            phoneme.symbol,
            str(phoneme.duration_ms),
        ]

        for target in phoneme.pitch_targets:
            parts.extend(
                [
                    str(target.position_percent),
                    str(target.frequency_hz),
                ]
            )

        return " ".join(parts)

    def to_text(
        self,
        phonemes: list[Phoneme],
    ) -> str:
        lines = [
            self.format_phoneme(phoneme)
            for phoneme in phonemes
        ]

        return "\n".join(lines) + "\n"

    def write(
        self,
        phonemes: list[Phoneme],
        path: str | Path,
    ) -> Path:
        output_path = Path(path)

        output_path.write_text(
            self.to_text(phonemes),
            encoding="utf-8",
        )

        return output_path
