from __future__ import annotations

import ast
import re
from time import monotonic
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
CONFIG_DIR = PROJECT_ROOT / "config"
DIALOGUES_DIR = PROJECT_ROOT / "dialogues"
PROGRAM_MEMORY_SECONDS = 45


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
        self.last_program_entry: dict | None = None
        self.last_program_entry_at: float | None = None

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

    def direct_response(self, transcript: str) -> str | None:
        """Liefert sichere Antworten für eindeutige, lokale Faktenfragen."""

        text = self._normalize_input(transcript).lower()
        program_answer = self._program_direct_response(text)
        if program_answer:
            return program_answer

        category = self._classify(text)

        if category == "orientation":
            if self._contains_any(text, ("wie lange", "fahrt dauert")):
                return "Die Fahrt dauert ungefähr dreißig Sekunden."
            if self._contains_any(
                text,
                ("wie fühlt", "wie fuehlt", "wie ist die fahrt"),
            ):
                return "Wie eine kleine Reise mit Musik und Vorfreude."
            if self._contains_any(text, ("nach unten", "zurück", "zurueck", "eg")):
                return "Zum Erdgeschoss geht es mit der Taste EG."
            if self._contains_any(
                text,
                (
                    "wo fahren",
                    "wohin",
                    "welcher stock",
                    "welchen stock",
                    "in welchem stock",
                    "production lab",
                    "wo aussteigen",
                ),
            ):
                return "Wir fahren ins Production Lab im zehnten Stock."

        if category == "event":
            return self._event_direct_response(text)

        if category == "artist":
            if self._contains_any(
                text,
                ("wann", "uhr", "beginnt", "startet", "zeit", "wer spielt",
                 "wer macht mit", "besetzung", "welche musik", "genre", "musikrichtung"),
            ):
                return self._artist_context(text).replace("\n", " ")

        if category == "identity":
            if "warum singst" in text:
                return "Weil eine Aufzugfahrt mit Musik gleich viel schöner ist."
            return "Ich bin Elfi, der singende Aufzug."

        if category == "smalltalk":
            if self._contains_any(text, ("tschüss", "tschuess", "auf wiedersehen", "bis später", "bis spaeter")):
                return "Ich wünsche dir einen vergnüglichen Abend!"
            if "danke" in text:
                return "Sehr gern."
            if self._contains_any(text, ("hallo", "hi", "moin", "guten tag", "guten abend")):
                return "Einen wunderschönen guten Abend!"

        if "tanzen" in text:
            return "Ich kann nur hoch und runter fahren."
        if self._contains_any(text, ("weißt du alles", "weisst du alles")):
            return "Nein. Am besten kenne ich mich mit dem heutigen Abend aus."
        if self._contains_any(text, ("noch einmal mitfahren", "nochmal mitfahren")):
            return "Komm gerne so oft du möchtest!"

        return None

    def _program_direct_response(self, text: str) -> str | None:
        """Beantwortet Programmfragen aus den lokalen, strukturierten Daten."""

        program = self._read_assignment(
            self.config_dir / "program.txt",
            variable_name="program",
        )
        if not isinstance(program, list):
            return None

        next_response = self._next_program_response(program, text)
        if next_response:
            return next_response

        entry = self._entry_for_question(program, text)
        if entry is None:
            return None

        self._remember_program_entry(entry)
        name = str(entry.get("name", "Der Programmpunkt"))
        start = entry.get("start")
        end = entry.get("end")
        genre = entry.get("genre")
        participants = entry.get("participants", [])
        description = entry.get("description")

        if self._contains_any(
            text,
            ("wann", "uhr", "beginnt", "startet", "zeit", "wie lange", "bis wann", "endet"),
        ):
            if start and end:
                return f"{name} spielt von {start} bis {end} Uhr."
            if start:
                return f"{name} beginnt um {start} Uhr."

        if self._contains_any(
            text,
            ("wer spielt", "wer macht mit", "mit wem", "besetzung", "wer ist dabei"),
        ) and participants:
            other_participants = [
                str(person)
                for person in participants
                if str(person).casefold() != name.casefold()
            ]
            if len(other_participants) == 1:
                return f"Bei {name} ist {other_participants[0]} dabei."
            if other_participants:
                return f"Bei {name} sind {', '.join(other_participants)} dabei."

        if "wer sind" in text and participants:
            other_participants = [
                str(person)
                for person in participants
                if str(person).casefold() != name.casefold()
            ]
            if other_participants:
                return f"{name} sind {', '.join(other_participants)}."

        if self._contains_any(
            text,
            ("welche musik", "was für musik", "genre", "musikrichtung", "was spielt"),
        ) and genre:
            return f"{name} spielt {genre}."

        if self._contains_any(
            text,
            ("was macht", "erzähl", "erzaehl", "was ist", "wer ist", "mehr über", "mehr von"),
        ):
            return self._short_program_description(name, genre, description, start)

        # Die Nennung eines Acts ohne weitere Frage ist eine Einladung zu
        # einer kurzen, gesicherten Einführung.
        return self._short_program_description(name, genre, description, start)

    def _entry_for_question(self, program: list, text: str) -> dict | None:
        artist = self._find_artist(text)
        if artist:
            entry = self._find_program_entry(program, artist)
            if entry:
                return entry

        if self.last_program_entry and self._looks_like_program_followup(text):
            if self._program_memory_is_current():
                return self.last_program_entry
            self._clear_program_memory()

        return None

    def _remember_program_entry(self, entry: dict) -> None:
        self.last_program_entry = entry
        self.last_program_entry_at = monotonic()

    def _program_memory_is_current(self) -> bool:
        if self.last_program_entry_at is None:
            return False
        return monotonic() - self.last_program_entry_at <= PROGRAM_MEMORY_SECONDS

    def _clear_program_memory(self) -> None:
        self.last_program_entry = None
        self.last_program_entry_at = None

    def _next_program_response(self, program: list, text: str) -> str | None:
        """Findet den folgenden Act, wenn ein Act ausdrücklich genannt ist."""

        if not self._contains_any(text, ("was kommt nach", "wer kommt nach", "wer spielt nach", "nach dem", "nach der")):
            return None

        artist = self._find_artist(text)
        if not artist:
            return None

        current = self._find_program_entry(program, artist)
        if current is None:
            return None

        try:
            index = program.index(current)
        except ValueError:
            return None

        if index + 1 >= len(program):
            return "Danach endet das Programm."

        following = program[index + 1]
        name = following.get("name", "der nächste Programmpunkt")
        start = following.get("start")
        if start:
            return f"Nach {current.get('name')} spielt {name} um {start} Uhr."
        return f"Nach {current.get('name')} kommt {name}."

    @staticmethod
    def _short_program_description(
        name: str,
        genre: object,
        description: object,
        start: object,
    ) -> str:
        """Gibt einen kurzen, gut singbaren und faktischen Überblick zurück."""

        if isinstance(description, str) and description:
            sentences = re.split(r"(?<=[.!?])\s+", description.strip())
            first_sentence = sentences[0].strip()
            if len(first_sentence.split()) <= 12:
                return first_sentence

        if genre and start:
            return f"{name} spielt {genre} um {start} Uhr."
        if genre:
            return f"{name} spielt {genre}."
        if start:
            return f"{name} beginnt um {start} Uhr."
        return f"{name} ist heute im Programm."

    @staticmethod
    def _looks_like_program_followup(text: str) -> bool:
        pronoun = re.search(
            r"\b(sie|er|ihnen|ihm|dieser|diese|dieses)\b",
            text,
        )
        if not pronoun:
            return False

        return PromptRouter._contains_any(
            text,
            (
                "wann", "uhr", "wie lange", "bis wann", "endet",
                "wer", "mit wem", "besetzung", "welche musik",
                "was für musik", "genre", "musikrichtung", "was macht",
                "erzähl", "erzaehl", "mehr über",
            ),
        )

    def _event_direct_response(self, text: str) -> str | None:
        event_data = self._read_assignment(
            self.config_dir / "event.txt",
            variable_name="event",
        )
        if not isinstance(event_data, dict):
            return None

        name = event_data.get("name", "SuedKultur Music-Night")
        start = event_data.get("start")
        price = event_data.get("price")
        genres = event_data.get("genres", [])

        if self._contains_any(
            text,
            (
                "wer sind die künstler", "wer sind die künstlerin",
                "welche künstler", "welche künstlerin", "wer spielt heute",
                "wer tritt auf",
            ),
        ):
            program = self._read_assignment(
                self.config_dir / "program.txt",
                variable_name="program",
            )
            if isinstance(program, list):
                short_names = [
                    str(entry.get("name"))
                    for entry in program
                    if isinstance(entry, dict)
                    and entry.get("type") != "installation"
                    and entry.get("name")
                    and len(str(entry["name"]).split()) <= 2
                ]
                if len(short_names) >= 3:
                    return (
                        "Heute spielen unter anderem "
                        f"{short_names[0]}, {short_names[1]} und {short_names[2]}."
                    )

        if self._contains_any(text, ("eintritt", "ticket", "preis", "kostet", "kosten")) and price:
            return f"Der Eintritt kostet {price}."
        if self._contains_any(text, ("wann beginnt", "wann geht", "beginn", "startet", "start")) and start:
            return f"Das Programm beginnt um {start}."
        if self._contains_any(text, ("musik", "genre", "musikrichtung")) and genres:
            return f"Heute gibt es {', '.join(genres[:3])} und mehr."
        if self._contains_any(text, ("was passiert heute", "was ist heute", "veranstaltung", "music night", "music-night", "südkultur", "suedkultur", "programm", "konzert", "jam session")):
            return f"Heute findet die {name} statt."

        return None

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
            "Verwende keine Regieanweisungen oder eckigen Klammern.\n"
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
                "was für musik",
                "welche musik gibt es",
                "wer sind die künstler",
                "wer sind die künstlerin",
                "welche künstler",
                "welche künstlerin",
                "wer spielt heute",
                "wer tritt auf",
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

        if self._contains_any(
            text,
            (
                "wer sind die künstler", "wer sind die künstlerin",
                "welche künstler", "welche künstlerin", "wer spielt heute",
                "wer tritt auf",
            ),
        ):
            program = self._read_assignment(
                self.config_dir / "program.txt",
                variable_name="program",
            )
            if isinstance(program, list):
                acts = []
                for entry in program:
                    if not isinstance(entry, dict):
                        continue
                    name = entry.get("name")
                    start_time = entry.get("start")
                    if name and start_time:
                        acts.append(f"{start_time}: {name}")
                if acts:
                    return "HEUTIGES PROGRAMM\n" + "\n".join(acts)

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

            if artist_lower in name:
                return entry

        for entry in program:
            if not isinstance(entry, dict):
                continue

            participants = [
                str(person).lower()
                for person in entry.get("participants", [])
            ]

            if artist_lower in participants:
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
