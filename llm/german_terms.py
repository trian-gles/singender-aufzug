"""Deutsche Aussprache-Hilfen für Whisper und das LLM.

Whisper bekommt einen Prompt mit allen relevanten Begriffen,
damit es bei der Transkription die korrekte deutsche Schreibung
bevorzugt.  Das LLM wird angewiesen, die Original-Begriffe zu
verwenden – MBROLA/eSpeak produziert mit ``mb-de2`` automatisch
deutsche Phoneme, auch für englische Lehnwörter.
"""

from __future__ import annotations

# ------------------------------------------------------------------
# Whisper-Einblendung
# ------------------------------------------------------------------
# Diese Wörter werden dem Whisper-Sprachmodell als
# ``--prompt`` / ``--carry-initial-prompt`` mitgegeben, damit es bei
# der Transkription eher die deutsche als die englische Schreibung
# / Aussprache wählt.

WHISPER_PROMPT_WORDS = [
    # Orte / Einrichtungen
    "Production Lab",
    "Südkultur",
    "Suedkultur",
    "Suedkultur Music Night",
    "Suedkultur Music-Night",
    "Südkultur Music-Night",
    "Südkultur Music Night",
    "ligeti zentrum",
    "Ligeti Zentrum",
    "Hamburg Harburg",
    # Künstler / Bands
    "Sonomathematische Impulsarchitekten",
    "Simon Linke",
    "Rolf Bader",
    "Guan Yanyi",
    "Dai Jianhua",
    "Liang Yiyuan",
    "Potluck",
    "oscheat",
    "Clarks Planet",
    "Clara Nebel",
    "Kieran McAuliffe",
    "Moritz Wesp",
    "Eric Haupt",
    "Victor Gelling",
    "Kollektiv Visuell",
    # Genres / Formate
    "Avantgarde-Pop",
    "Improvisation",
    "Irish Folk",
    "Jam Session",
    "Jam-Session",
    "Conceptual Improvisation",
    "Free Noise Improvisation",
    "Zeitgenössische Improvisation",
    # Sonstige Fremdwörter
    "Elfi",
    "Aufzug",
    "Erdgeschoss",
    "zehnten Stock",
    "zehnte Stock",
    "Music Night",
    "Music-Night",
    "Musik Nacht",
    "Musik-Nacht",
]


def build_whisper_prompt() -> str:
    """Liefert einen Prompt-String für ``whisper-cli --prompt``."""

    # Whisper nutzt den Prompt als statistischen Anker – je mehr der
    # Ziel-Begriffe hier auftauchen, desto eher wird die deutsche
    # Variante gewählt.  Wir packen alle Varianten in einen Satz.
    return (
        "ligeti zentrum Südkultur Music-Night Production Lab "
        "zehnten Stock zehnte Stock Elfi Aufzug Erdgeschoss "
        "Jam Session Jam-Session Avantgarde-Pop Irish Folk "
        "Sonomathematische Impulsarchitekten "
        "Simon Linke Rolf Bader Guan Yanyi Dai Jianhua "
        "Liang Yiyuan Potluck oscheat Clarks Planet "
        "Clara Nebel Kieran McAuliffe Moritz Wesp Eric Haupt "
        "Victor Gelling Kollektiv Visuell"
    )


# ------------------------------------------------------------------
# LLM-Prompt-Zusatz
# ------------------------------------------------------------------
# Erscheint im Prompt für das LLM, damit Elfi die richtigen Begriffe
# verwendet.  eSpeak (mb-de2) produziert für englische Lehnwörter
# automatisch deutsche Phoneme – der Text muss also NICHT pseudo-deutsch
# umgeschrieben werden.

LLM_GERMAN_GUIDE = """Aussprache:
Deine Stimme spricht auch englische Wörter mit deutscher
Phonetik automatisch richtig aus.  Du musst die Wörter also
nicht eindeutschen.  Verwende die Original-Schreibweise:
- "Production Lab" (nicht "Produktion Labor")
- "Südkultur Music-Night" (nicht "Südkultur Musik-Nacht")
- "Conceptual Improvisation"
- "Free Noise Improvisation"
- "Irish Folk"
- "Jam Session" oder "Jam-Session"
- "Avantgarde-Pop"
Künstlernamen wie "Guan Yanyi" oder "Kieran McAuliffe"
bleiben unverändert."""
