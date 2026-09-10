"""Schreibt Zahlen für die deutsche Sprach- und Gesangsausgabe aus."""

from __future__ import annotations

import re


ONES = (
    "null", "eins", "zwei", "drei", "vier", "fünf", "sechs", "sieben",
    "acht", "neun",
)
TEENS = (
    "zehn", "elf", "zwölf", "dreizehn", "vierzehn", "fünfzehn",
    "sechzehn", "siebzehn", "achtzehn", "neunzehn",
)
TENS = (
    "", "", "zwanzig", "dreißig", "vierzig", "fünfzig", "sechzig",
    "siebzig", "achtzig", "neunzig",
)


def number_to_words(number: int) -> str:
    """Gibt eine nichtnegative ganze Zahl als deutsches Wort aus."""

    if number < 0:
        return "minus " + number_to_words(-number)
    if number < 10:
        return ONES[number]
    if number < 20:
        return TEENS[number - 10]
    if number < 100:
        tens, ones = divmod(number, 10)
        if ones == 0:
            return TENS[tens]
        prefix = "ein" if ones == 1 else ONES[ones]
        return f"{prefix}und{TENS[tens]}"
    if number < 1_000:
        hundreds, remainder = divmod(number, 100)
        prefix = "einhundert" if hundreds == 1 else f"{ONES[hundreds]}hundert"
        return prefix + (number_to_words(remainder) if remainder else "")
    if number < 1_000_000:
        thousands, remainder = divmod(number, 1_000)
        prefix = "eintausend" if thousands == 1 else f"{number_to_words(thousands)}tausend"
        return prefix + (number_to_words(remainder) if remainder else "")
    return str(number)


def normalize_for_speech(text: str) -> str:
    """Schreibt Uhrzeiten, Eurobeträge und Zahlen für eSpeak aus."""

    def replace_money(match: re.Match[str]) -> str:
        euros = int(match.group("euros"))
        cents_text = match.group("cents")
        euro_word = "ein Euro" if euros == 1 else f"{number_to_words(euros)} Euro"
        if not cents_text:
            return euro_word
        cents = int(cents_text.ljust(2, "0"))
        if cents == 0:
            return euro_word
        return f"{euro_word} {number_to_words(cents)}"

    def replace_time(match: re.Match[str]) -> str:
        hour = int(match.group("hour"))
        minute = int(match.group("minute"))
        hour_word = "ein" if hour == 1 else number_to_words(hour)
        if minute == 0:
            return f"{hour_word} Uhr"
        return f"{hour_word} Uhr {number_to_words(minute)}"

    text = re.sub(
        r"\b(?P<euros>\d+)(?:[,.](?P<cents>\d{1,2}))?\s*(?:€|Euro\b)",
        replace_money,
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r"\b(?P<hour>[01]?\d|2[0-3]):(?P<minute>[0-5]\d)(?:\s*Uhr)?",
        replace_time,
        text,
    )
    text = re.sub(
        r"\b\d+\b",
        lambda match: number_to_words(int(match.group(0))),
        text,
    )
    return text
