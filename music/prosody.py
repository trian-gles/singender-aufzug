from dataclasses import dataclass, replace


@dataclass(frozen=True)
class ProsodyStyle:
    """
    Rendererunabhängige Beschreibung des musikalischen Ausdrucks.
    """
    tempo: float = 1.0
    articulation: float = 0.5
    energy: float = 0.5
    warmth: float = 0.5
    playfulness: float = 0.0
    emphasis: float = 0.0
    pitch_span: float = 0.0
    phrase_shape: str = "flat"
    cadence: str = "neutral"

    def __post_init__(self) -> None:
        if self.tempo <= 0:
            raise ValueError(
                "tempo muss größer als 0 sein."
            )

        normalized_values = {
            "articulation": self.articulation,
            "energy": self.energy,
            "warmth": self.warmth,
            "playfulness": self.playfulness,
            "emphasis": self.emphasis,
            "pitch_span": self.pitch_span,
        }

        for name, value in normalized_values.items():
            if not 0.0 <= value <= 1.0:
                raise ValueError(
                    f"{name} muss zwischen 0.0 und 1.0 liegen."
                )

        allowed_shapes = {
            "flat",
            "rising",
            "falling",
            "arch",
            "valley",
        }

        if self.phrase_shape not in allowed_shapes:
            raise ValueError(
                "Unbekannte phrase_shape: "
                f"{self.phrase_shape}"
            )

        allowed_cadences = {
            "neutral",
            "falling",
            "rising",
            "open",
        }

        if self.cadence not in allowed_cadences:
            raise ValueError(
                "Unbekannte cadence: "
                f"{self.cadence}"
            )

    def with_changes(
        self,
        **changes: object,
    ) -> "ProsodyStyle":
        return replace(self, **changes)

    @classmethod
    def neutral(cls) -> "ProsodyStyle":
        return cls()

    @classmethod
    def friendly(cls) -> "ProsodyStyle":
        return cls(
            tempo=1.05,
            articulation=0.65,
            energy=0.55,
            warmth=0.85,
            playfulness=0.25,
            emphasis=0.55,
            pitch_span=0.55,
            phrase_shape="arch",
            cadence="falling",
        )

    @classmethod
    def playful(cls) -> "ProsodyStyle":
        return cls(
            tempo=0.9,
            articulation=0.75,
            energy=0.8,
            warmth=0.65,
            playfulness=0.9,
            emphasis=0.7,
            pitch_span=0.8,
            phrase_shape="arch",
            cadence="open",
        )

    @classmethod
    def calm(cls) -> "ProsodyStyle":
        return cls(
            tempo=1.25,
            articulation=0.55,
            energy=0.25,
            warmth=0.75,
            playfulness=0.05,
            emphasis=0.35,
            pitch_span=0.25,
            phrase_shape="flat",
            cadence="falling",
        )

    @classmethod
    def clear_information(cls) -> "ProsodyStyle":
        return cls(
            tempo=1.0,
            articulation=0.85,
            energy=0.5,
            warmth=0.45,
            playfulness=0.0,
            emphasis=0.55,
            pitch_span=0.35,
            phrase_shape="flat",
            cadence="falling",
        )
