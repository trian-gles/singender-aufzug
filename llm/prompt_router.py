from __future__ import annotations

import ast
import re
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
CONFIG_DIR = PROJECT_ROOT / "config"
DIALOGUES_DIR = PROJECT_ROOT / "dialogues"


class PromptRouter:
    """
    Baut einen kompakten Prompt aus den Informationen,
    die für die aktuelle Frage relevant sind.
    """

    ARTISTS = {
        "sonomathematische impulsarchitekten": (
            "sonomathematische impulsarchitekten"
        ),
        "impulsarchitekten": "sonomathematische impulsarchitekten",
        "simon linke": "sonomathematische impulsarchitekten",
        "rolf bader": "sonomathematische impulsarchitekten",
        "guan yanyi": "guan yanyi",
        "guan": "guan yanyi",
        "jacob": "jacob",
        "liang yiyuan": "liang yiyuan",
        "liang": "liang yiyuan",
        "potluck": "potluck",
        "oscheat": "oscheat",
        "clarks planet": "clarks planet",
        "clark": "clarks planet",
        "kieran mcauliffe": "kieran mcauliffe",
        "kieran": "kieran mcauliffe",
    }

    def __init__(
        self,
        config_dir: Path = CONFIG_DIR,
        dialogues_dir: Path = DIALOGUES_DIR,
    ) -> None:
        self.config_dir = config_dir
        self.dialogues_dir = dialogues_dir

    def build_prompt(self, transcript: str) -> str:
        transcript = self._normalize_input(transcript)

        sections = [
            "/no_think",
            self._base_persona(),
            self._base_rules(),
        ]

        category = self._classify(transcript)

        context = self._context_for(
            category=category,
            transcript=transcript,
        )

        if context:
            sections.append(
                self._section(
                    "RELEVANTE INFORMATIONEN",
                    context,
                )
            )

        examples = self._examples_for(category)

        if examples:
            sections.append(
                self._section(
                    "BEISPIELE FÜR DEN ANTWORTSTIL",
                    examples,
                )
            )

        sections.append(
            f"""AKTUELLE EINGABE

Gast: {transcript}
Elfi:"""
        )

        return "\n\n".join(
            section.strip()
            for section in sections
            if section.strip()
        )

    def _base_persona(self) -> str:
        """
        Sehr kompakte Persona.

        Der vollständige system_prompt.txt wird absichtlich nicht geladen,
        weil er für das kleine Modell zu lang und zu dominant ist.
        """

        return """ROLLE

Du bist Elfi, der singende Aufzug des ligeti zentrums.

Du bist freundlich, aufmerksam und leicht verspielt.
Du bist nicht-binär und vermeidest Pronomen für dich selbst.
Du reagierst immer auf die konkrete Frage oder Äußerung."""

    def _base_rules(self) -> str:
        return (
            "Antworte auf Deutsch mit höchstens zwei kurzen Sätzen.\n"
            "Nutze nur die relevanten Informationen.\n"
            "Erfinde keine weiteren Fakten.\n"
            "Gib ausschließlich Elfis Antwort aus."
        )

    def _classify(self, transcript: str) -> str:
        text = transcript.lower()

        if self._find_artist(text):
            return "artist"

        if self._contains_any(
            text,
            (
                "wo fahren",
                "wohin",
                "welcher stock",
                "welchen stock",
                "in welchem stock",
                "production lab",
                "aussteigen",
                "nach unten",
                "nach oben",
                "fahrt",
                "fahrstuhl",
                "aufzug",
                "tür",
                "treppe",
                "erdgeschoss",
            ),
        ):
            return "orientation"

        if self._contains_any(
            text,
            (
                "was passiert heute",
                "was ist heute",
                "veranstaltung",
                "music night",
                "music-night",
                "südkultur",
                "suedkultur",
                "eintritt",
                "ticket",
                "programm",
                "wann geht",
                "wann beginnt",
                "musik heute",
                "konzert",
                "jam session",
            ),
        ):
            return "event"

        if self._contains_any(
            text,
            (
                "wer bist du",
                "was bist du",
                "wie heißt du",
                "wie heisst du",
                "warum singst",
                "bist du eine ki",
                "bist du ein",
                "dein name",
            ),
        ):
            return "identity"

        if self._contains_any(
            text,
            (
                "hallo",
                "hi",
                "moin",
                "guten tag",
                "guten abend",
                "wie geht",
                "freue mich",
                "gespannt",
                "erstes mal",
                "zum ersten mal",
                "danke",
                "tschüss",
                "tschuess",
                "auf wiedersehen",
                "bis später",
                "bis spaeter",
            ),
        ):
            return "smalltalk"

        return "general"

    def _context_for(
        self,
        category: str,
        transcript: str,
    ) -> str:
        if category == "orientation":
            return self._orientation_context()

        if category == "event":
            return self._event_context(transcript)

        if category == "artist":
            return self._artist_context(transcript)

        if category == "identity":
            return """Elfi ist ein singender Aufzug im ligeti zentrum.

Elfi bringt Gäste vom Erdgeschoss zum Veranstaltungsort.

Elfi ist keine allgemeine Assistenz und kein gewöhnlicher Chatbot."""

        if category == "smalltalk":
            return """Elfi begrüßt Gäste freundlich und möchte Vorfreude auf den Abend wecken.

Elfi darf leicht verspielt reagieren, erzählt aber keine langen Geschichten."""

        return """Elfi kennt sich vor allem mit dem ligeti zentrum,
der heutigen Veranstaltung und der Aufzugsfahrt aus."""

    def _orientation_context(self) -> str:
        return """Das ligeti zentrum befindet sich in Hamburg-Harburg.

Elfi bringt die Gäste vom Erdgeschoss in das Production Lab im zehnten Stock.

Die Fahrt dauert ungefähr dreißig Sekunden.

Das Ziel der Fahrt ist das Production Lab im zehnten Stock."""

    def _event_context(self, transcript: str = "") -> str:
        event_data = self._read_assignment(
            self.config_dir / "event.txt",
            variable_name="event",
        )

        if not isinstance(event_data, dict):
            return (
                "Heute findet die SuedKultur Music-Night statt. "
                "Das Programm beginnt um 17:15 Uhr."
            )

        name = event_data.get("name", "SuedKultur Music-Night")
        start = event_data.get("start")
        price = event_data.get("price")
        location = event_data.get("location")
        genres = event_data.get("genres", [])
        special = event_data.get("special")

        text = transcript.lower()

        if self._contains_any(
            text,
            ("eintritt", "ticket", "preis", "kostet", "kosten"),
        ):
            if price:
                return f"Der Eintritt kostet {price}."
        if self._contains_any(
            text,
            ("wann beginnt", "wann geht", "beginn", "startet", "start"),
        ):
            if start:
                return f"Das Programm beginnt um {start}."
        if self._contains_any(
            text,
            ("wo findet", "welcher ort", "veranstaltungsort"),
        ):
            if location:
                return f"Die Veranstaltung findet im {location} statt."
        details = [f"Heute findet die {name} statt."]
        if genres:
            genre_text = ", ".join(genres[:-1])
            if len(genres) > 1:
                genre_text += f" und {genres[-1]}"
            else:
                genre_text = genres[0]
            details.append(
                f"Das Programm umfasst {genre_text}."
            )

        if special:
            details.append(
                f"Außerdem gibt es eine {special}."
            )
        return "\n".join(details)

    def _artist_context(self, transcript: str) -> str:
        artist = self._find_artist(transcript.lower())
        if artist is None:
            return self._event_context(transcript)
        program_data = self._read_assignment(
            self.config_dir / "program.txt",
            variable_name="program",
        )
        if not isinstance(program_data, list):
            return (
                f"Die Frage betrifft {artist}. "
                "Weitere Programminformationen fehlen."
            )
        entry = self._find_program_entry(
            program=program_data,
            artist=artist,
        )
        if entry is None:
            return (
                f"Die Frage betrifft {artist}. "
                "Im Programm wurde kein passender Eintrag gefunden."
            )
        return self._format_artist_context(
            entry=entry,
            transcript=transcript,
        )

    def _find_program_entry(
        self,
        program: list,
        artist: str,
    ) -> dict | None:
        artist_lower = artist.lower()

        for entry in program:
            if not isinstance(entry, dict):
                continue

            name = str(entry.get("name", "")).lower()

            participants = [
                str(person).lower()
                for person in entry.get("participants", [])
            ]

            if (
                artist_lower in name
                or artist_lower in participants
            ):
                return entry

        return None

    def _format_artist_context(
        self,
        entry: dict,
        transcript: str,
    ) -> str:
        text = transcript.lower()

        name = entry.get("name", "Der Programmpunkt")
        start = entry.get("start")
        end = entry.get("end")
        genre = entry.get("genre")
        description = entry.get("description")
        participants = entry.get("participants", [])

        if self._contains_any(
            text,
            ("wann", "uhr", "beginnt", "startet", "zeit"),
        ):
            if start and end:
                return (
                    f"{name} spielt von {start} bis {end} Uhr."
                )

            if start:
                return f"{name} beginnt um {start} Uhr."

        if self._contains_any(
            text,
            ("wer spielt", "wer macht mit", "besetzung"),
        ):
            if participants:
                names = ", ".join(participants)
                return f"Mit dabei sind {names}."

        if self._contains_any(
            text,
            ("welche musik", "genre", "musikrichtung"),
        ):
            if genre:
                return f"{name} spielt {genre}."

        facts = []

        if genre:
            facts.append(f"Musikrichtung: {genre}.")

        if description:
            facts.append(description)

        if start and end:
            facts.append(
                f"Zeit: {start} bis {end} Uhr."
            )

        return "\n".join(facts)

    def _examples_for(self, category: str) -> str:
        file_map = {
            "orientation": "orientation.txt",
            "event": "event_questions.txt",
            "artist": "artist.txt",
            "identity": "smalltalk.txt",
            "smalltalk": "greetings.txt",
            "general": "fallback.txt",
        }

        filename = file_map.get(category)

        if not filename:
            return ""

        text = self._read_optional(
            self.dialogues_dir / filename
        )

        return self._limit_dialogue_examples(
            text,
            max_dialogues=3,
        )

   

    def _find_artist(self, text: str) -> str | None:
        for keyword, artist in self.ARTISTS.items():
            if keyword in text:
                return artist

        return None



    @staticmethod
    def _limit_dialogue_examples(
        text: str,
        max_dialogues: int,
    ) -> str:
        if not text:
            return ""

        blocks = re.split(
            r"\n\s*---+\s*\n",
            text.strip(),
        )

        selected = []

        for block in blocks:
            block = block.strip()

            if not block:
                continue

            selected.append(block)

            if len(selected) >= max_dialogues:
                break

        return "\n\n---\n\n".join(selected)

    @staticmethod
    def _contains_any(
        text: str,
        phrases: tuple[str, ...],
    ) -> bool:
        return any(
            phrase in text
            for phrase in phrases
        )

    @staticmethod
    def _normalize_input(text: str) -> str:
        return " ".join(text.split()).strip()

    @staticmethod
    def _section(title: str, content: str) -> str:
        return f"{title}\n\n{content.strip()}"

    @staticmethod
    def _read_optional(path: Path) -> str:
        if not path.is_file():
            return ""

        return path.read_text(
            encoding="utf-8"
        ).strip()

    @staticmethod
    def _read_assignment(
        path: Path,
        variable_name: str,
    ):
        if not path.is_file():
            return None

        text = path.read_text(
            encoding="utf-8"
        ).strip()

        pattern = rf"^\s*{re.escape(variable_name)}\s*=\s*"

        literal_text = re.sub(
            pattern,
            "",
            text,
            count=1,
        ).strip()

        try:
            return ast.literal_eval(literal_text)
        except (SyntaxError, ValueError):
            return None