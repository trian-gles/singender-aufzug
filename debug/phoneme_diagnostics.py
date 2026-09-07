from audio.pho import Phoneme
from music.events import MusicalEvent, MusicalPhrase


def print_event_report(
    event: MusicalEvent,
    sung_phonemes: list[Phoneme],
) -> None:
    """
    Zeigt die Dauerverteilung einer einzelnen musikalischen Silbe.
    """

    print()
    print(f"Silbe: {event.syllable}")
    print(
        f"Musikalische Vorgabe: "
        f"{event.note.pitch_hz} Hz, "
        f"{event.duration_ms} ms"
    )

    print("Phoneme vor Singer:")

    for phoneme in event.phonemes:
        print(
            f"  {phoneme.symbol:<5} "
            f"{phoneme.duration_ms:>4} ms"
        )

    print("Phoneme nach Singer:")

    total_duration = 0

    for phoneme in sung_phonemes:
        total_duration += phoneme.duration_ms

        pitch_description = _format_pitch_targets(
            phoneme
        )

        print(
            f"  {phoneme.symbol:<5} "
            f"{phoneme.duration_ms:>4} ms"
            f"{pitch_description}"
        )

    difference = total_duration - event.duration_ms

    print(
        f"Phonemdauer gesamt: {total_duration} ms"
    )

    if difference == 0:
        print("Abweichung: 0 ms")
    elif difference > 0:
        print(
            f"Abweichung: +{difference} ms "
            f"(Singer verlängert die Silbe)"
        )
    else:
        print(
            f"Abweichung: {difference} ms "
            f"(Singer verkürzt die Silbe)"
        )


def sing_phrase_with_report(
    phrase: MusicalPhrase,
    singer,
) -> list[Phoneme]:
    """
    Ruft den Singer ereignisweise auf und gibt für jede Silbe
    einen Diagnosebericht aus.

    Der Rückgabewert entspricht singer.sing_phrase(...).
    """

    result: list[Phoneme] = []

    print()
    print("=" * 55)
    print("PHONEM-DIAGNOSE")
    print("=" * 55)

    for event in phrase.events:
        sung_phonemes = singer.sing_event(event)

        print_event_report(
            event=event,
            sung_phonemes=sung_phonemes,
        )

        result.extend(sung_phonemes)

    print()
    print("=" * 55)
    print(
        "Gesamtdauer aller ausgegebenen Phoneme: "
        f"{sum(p.duration_ms for p in result)} ms"
    )
    print("=" * 55)

    return result


def _format_pitch_targets(
    phoneme: Phoneme,
) -> str:
    if not phoneme.pitch_targets:
        return ""

    targets = ", ".join(
        (
            f"{target.position_percent}%="
            f"{target.frequency_hz} Hz"
        )
        for target in phoneme.pitch_targets
    )

    return f"  Tonhöhe: {targets}"
