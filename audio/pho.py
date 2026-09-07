from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class PitchTarget:
    position_percent: int
    frequency_hz: int


@dataclass
class Phoneme:
    symbol: str
    duration_ms: int
    pitch_targets: list[PitchTarget] = field(default_factory=list)

    def to_pho_line(self) -> str:
        parts = [
            self.symbol,
            str(self.duration_ms),
        ]

        for target in self.pitch_targets:
            parts.extend(
                [
                    str(target.position_percent),
                    str(target.frequency_hz),
                ]
            )

        return " ".join(parts)


class PhoParser:
    def parse_line(self, line: str) -> Phoneme | None:
        stripped = line.strip()

        if not stripped:
            return None

        parts = stripped.split()

        if len(parts) < 2:
            raise ValueError(f"Ungültige PHO-Zeile: {line!r}")

        symbol = parts[0]
        duration_ms = int(parts[1])

        pitch_values = parts[2:]

        if len(pitch_values) % 2 != 0:
            raise ValueError(
                f"Ungültige Tonhöhenwerte in PHO-Zeile: {line!r}"
            )

        pitch_targets: list[PitchTarget] = []

        for index in range(0, len(pitch_values), 2):
            pitch_targets.append(
                PitchTarget(
                    position_percent=int(pitch_values[index]),
                    frequency_hz=int(pitch_values[index + 1]),
                )
            )

        return Phoneme(
            symbol=symbol,
            duration_ms=duration_ms,
            pitch_targets=pitch_targets,
        )

    def read(self, path: Path) -> list[Phoneme]:
        phonemes: list[Phoneme] = []

        for line in path.read_text(encoding="utf-8").splitlines():
            phoneme = self.parse_line(line)

            if phoneme is not None:
                phonemes.append(phoneme)

        return phonemes

    def write(self, phonemes: list[Phoneme], path: Path) -> Path:
        content = "\n".join(
            phoneme.to_pho_line()
            for phoneme in phonemes
        )

        path.write_text(
            content + "\n",
            encoding="utf-8",
        )

        return path