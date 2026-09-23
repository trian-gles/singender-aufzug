from __future__ import annotations

import ast
import re
from time import monotonic
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
CONFIG_DIR = PROJECT_ROOT / "config"
DIALOGUES_DIR = PROJECT_ROOT / "dialogues"
KNOWLEDGE_DIR = CONFIG_DIR / "knowledge"
PROGRAM_MEMORY_SECONDS = 45
UNKNOWN_RESPONSES = (
    "Das weiß ich nicht. Ich bin ja ein Aufzug und nicht Wikipedia.",
    "Frag lieber die Menschen hier. Ich bin mir nicht sicher.",
    "Da bin ich überfragt. Mit Stockwerken kenne ich mich besser aus.",
    "Keine Ahnung. Mein Wissen fährt gerade in einem anderen Stockwerk.",
    "Das kann ich nicht sicher sagen. Frag bitte das Team.",
    "Diese Antwort hat meinen Aufzug verpasst. Frag lieber einen Menschen.",
)
UNKNOWN_RESPONSE = UNKNOWN_RESPONSES[0]

KNOWLEDGE_STOPWORDS = {
    "aber", "alle", "auch", "auf", "aus", "bei", "das", "dass", "dem",
    "den", "der", "die", "ein", "eine", "einer", "einen", "einem", "es",
    "für", "hat", "hier", "ich", "ihr", "ist", "man", "mit", "nach",
    "oder", "sich", "sind", "über", "und", "vom", "von", "was", "welche",
    "welcher", "welches", "wie", "wir", "wo", "zum", "zur", "etwas",
}


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
        "simon": "sonomathematische impulsarchitekten",
        "rolf bader": "sonomathematische impulsarchitekten",
        "rolf": "sonomathematische impulsarchitekten",
        "bader": "sonomathematische impulsarchitekten",
        "guan yanyi": "guan yanyi",
        "guan": "guan yanyi",
        "dai jianhua": "interaktive installationen und ausstellung von dai jianhua",
        "dai": "interaktive installationen und ausstellung von dai jianhua",
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
        knowledge_dir: Path | None = None,
    ) -> None:
        self.config_dir = config_dir
        self.dialogues_dir = dialogues_dir
        self.knowledge_dir = knowledge_dir or config_dir / "knowledge"
        self.last_program_entry: dict | None = None
        self.last_program_entry_at: float | None = None
        self.response_variants: dict[str, int] = {}

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

        smalltalk_answer = self._smalltalk_direct_response(text)
        if smalltalk_answer:
            return smalltalk_answer

        program_answer = self._program_direct_response(text)
        if program_answer:
            return program_answer

        category = self._classify(text)

        if category == "orientation":
            if self._contains_any(
                text,
                ("wo bin ich", "wo sind wir", "welcher ort ist das"),
            ):
                return "Du bist im ligeti zentrum in Hamburg-Harburg."
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
            if self._is_greeting(text):
                return "Einen wunderschönen guten Abend!"

        if "tanzen" in text:
            return "Ich kann nur hoch und runter fahren."
        if self._contains_any(text, ("weißt du alles", "weisst du alles")):
            return "Nein. Am besten kenne ich mich mit dem heutigen Abend aus."
        if self._contains_any(text, ("noch einmal mitfahren", "nochmal mitfahren")):
            return "Komm gerne so oft du möchtest!"

        # Sachfragen ohne belegten Treffer dürfen nicht frei beantwortet werden.
        # Sobald in config/knowledge ein passender Fakt ergänzt wird, gelangt die
        # Frage stattdessen mit genau diesem Beleg zum Sprachmodell.
        if category == "general":
            knowledge_answer = self._knowledge_direct_response(text)
            if knowledge_answer:
                return knowledge_answer
            return self.unknown_response()

        return None

    def _smalltalk_direct_response(self, text: str) -> str | None:
        """Kurze, sichere Smalltalk-Antworten ohne fehleranfälligen Modellaufruf."""

        if self._contains_any(text, ("witz", "scherz", "etwas lustig")):
            return self._choose_variant(
                "smalltalk:joke",
                [
                    "Mein Lieblingswitz fährt gerade in den zehnten Stock.",
                    "Ich erzähle lieber keinen Witz, sonst bleibt er im Erdgeschoss stecken.",
                    "Mein Humor fährt am liebsten mit Musik nach oben.",
                ],
            )

        if (
            self._contains_any(text, ("lieber", "am liebsten"))
            or "liber" in text
        ) and (
            ("hoch" in text or "nach oben" in text)
            and ("runter" in text or "nach unten" in text)
        ):
            return self._choose_variant(
                "smalltalk:direction",
                [
                    "Beides. Hoch klingt nach Vorfreude, runter nach einer Zugabe.",
                    "Ich mag jede Richtung, solange Musik mitfährt.",
                    "Nach oben klingt es heute besonders schön.",
                ],
            )

        if self._contains_any(text, ("wie geht", "alles gut", "wie geht es dir")):
            return self._choose_variant(
                "smalltalk:mood",
                [
                    "Mir geht es bestens. Die nächste Melodie wartet schon.",
                    "Sehr gut, danke. Ich bin bereit für die nächste Fahrt.",
                    "Mir geht es wunderbar. Musik macht mich wach.",
                ],
            )

        if self._contains_any(text, ("schön", "toll", "super", "großartig", "grossartig")):
            return self._choose_variant(
                "smalltalk:compliment",
                [
                    "Das freut mich. Mit Gesellschaft klingt Musik noch besser.",
                    "Danke, das hört man gern zwischen zwei Etagen.",
                    "Wie schön. Dann singe ich gleich noch lieber.",
                ],
            )

        return None

    def unknown_response(self) -> str:
        """Wählt eine freundliche, selbstironische Nichtwissen-Antwort."""
        return self._choose_variant("fallback:unknown", list(UNKNOWN_RESPONSES))

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

        wide_response = self._program_wide_response(program, text)
        if wide_response:
            return wide_response

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
        instruments = entry.get("instruments", [])

        if self._contains_any(
            text,
            ("wann", "uhr", "beginnt", "startet", "zeit", "wie lange", "bis wann", "endet"),
        ):
            return self._time_answer(name, start, end)

        if participants and self._asks_for_participants(text):
            other_participants = [
                str(person)
                for person in participants
                if str(person).casefold() != name.casefold()
            ]
            if other_participants:
                return self._participant_answer(name, other_participants)

        if self._contains_any(
            text,
            ("welche musik", "was für musik", "genre", "musikrichtung", "was spielt"),
        ) and genre:
            return f"{name} spielt {genre}."

        if instruments and self._contains_any(
            text,
            ("instrument", "womit", "was spielt", "besetzung"),
        ):
            return self._instrument_answer(name, instruments)

        if self._contains_any(
            text,
            ("was macht", "erzähl", "erzaehl", "was ist", "wer ist", "mehr über", "mehr von"),
        ):
            return self._short_program_description(name, genre, description, start)

        # Die Nennung eines Acts ohne weitere Frage ist eine Einladung zu
        # einer kurzen, gesicherten Einführung.
        return self._short_program_description(name, genre, description, start)

    def _program_wide_response(self, program: list, text: str) -> str | None:
        """Beantwortet Fragen, die sich auf das gesamte Programm beziehen."""

        if "gitarre" in text:
            acts = []
            for entry in program:
                instruments = [
                    str(value).casefold()
                    for value in entry.get("instruments", [])
                ]
                if any(value in ("gitarre", "e-gitarre") for value in instruments):
                    name = str(entry.get("name", "")).strip()
                    if name:
                        acts.append(name)
            if acts:
                examples = acts[:3]
                if len(examples) == 1:
                    act_text = examples[0]
                else:
                    act_text = ", ".join(examples[:-1])
                    act_text += f" und {examples[-1]}"
                return f"Gitarre hörst du bei {act_text}."

        if "zither" in text:
            acts = [
                str(entry.get("name", "")).strip()
                for entry in program
                if any(
                    str(value).casefold() == "zither"
                    for value in entry.get("instruments", [])
                )
            ]
            if acts:
                if len(acts) == 1:
                    return f"Zither hörst du bei {acts[0]}."
                return (
                    "Zither hörst du bei den Sonomathematischen "
                    "Impulsarchitekten und bei oscheat."
                )

        if self._contains_any(
            text,
            ("als letztes", "zum schluss", "den abschluss", "wer beendet"),
        ):
            artists = [
                entry for entry in program
                if entry.get("type") != "installation" and entry.get("name")
            ]
            if artists:
                last = artists[-1]
                name = str(last["name"]).replace(" & ", " und ")
                start = last.get("start")
                if start:
                    return f"Zum Abschluss hörst du {name} um {start} Uhr."
                return f"Zum Abschluss hörst du {name}."

        if "instrument" in text and not self._find_artist(text):
            available = {
                str(value).casefold()
                for entry in program
                for value in entry.get("instruments", [])
            }
            preferred = [
                ("Zither", "zither"),
                ("Gitarren", "gitarre"),
                ("Mundharmonika", "mundharmonika"),
                ("Synthesizer", "synthesizer"),
                ("Yangqin", "yangqin"),
                ("Suona", "suona"),
            ]
            names = [
                label for label, needle in preferred
                if any(needle in value for value in available)
            ]
            if names:
                instrument_text = ", ".join(names[:-1])
                if len(names) > 1:
                    instrument_text += f" und {names[-1]}"
                else:
                    instrument_text = names[0]
                return f"Heute hörst du unter anderem {instrument_text}."

        return None

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

    def _time_answer(
        self,
        name: str,
        start: object,
        end: object,
    ) -> str | None:
        if not start:
            return None

        if end:
            return self._choose_variant(
                f"time:{name}",
                [
                    f"Der Auftritt von {name} geht von {start} bis {end} Uhr.",
                    f"Von {start} bis {end} Uhr ist {name} zu hören.",
                    f"Um {start} Uhr beginnt der Auftritt von {name}.",
                ],
            )

        return self._choose_variant(
            f"time:{name}",
            [
                f"{name} beginnt um {start} Uhr.",
                f"Um {start} Uhr ist {name} zu hören.",
            ],
        )

    def _participant_answer(
        self,
        name: str,
        participants: list[str],
    ) -> str:
        people = ", ".join(participants)
        return self._choose_variant(
            f"participants:{name}",
            [
                f"Zum Auftritt von {name} gehören {people}.",
                f"{people} stehen hinter dem Act {name}.",
                f"Bei {name} sind {people} mit dabei.",
            ],
        )

    @staticmethod
    def _instrument_answer(name: str, instruments: list[str]) -> str:
        if len(instruments) == 1:
            instrument_text = instruments[0]
        else:
            instrument_text = ", ".join(instruments[:-1])
            instrument_text += f" und {instruments[-1]}"
        return f"Bei {name} sind {instrument_text} zu hören."

    def _choose_variant(self, key: str, options: list[str]) -> str:
        index = self.response_variants.get(key, 0)
        self.response_variants[key] = index + 1
        return options[index % len(options)]

    @staticmethod
    def _asks_for_participants(text: str) -> bool:
        if PromptRouter._contains_any(
            text,
            (
                "wer spielt", "wer macht mit", "mit wem", "besetzung",
                "wer ist dabei", "wer sind", "wie heißt die künstler",
                "wie heisst die künstler",
            ),
        ):
            return True
        return "künstler" in text and "heißt" in text

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
                "wer", "mit wem", "besetzung", "instrument", "womit", "welche musik",
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

        name = event_data.get("name", "Südkultur Music-Night")
        start = event_data.get("start")
        price = event_data.get("price")
        genres = event_data.get("genres", [])
        location = event_data.get("location")
        room = event_data.get("room")
        floor = event_data.get("floor")
        subtitle = event_data.get("subtitle")

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
        if self._contains_any(
            text,
            ("wo findet", "wo ist die veranstaltung", "veranstaltungsort"),
        ):
            if room and floor:
                return f"Die Veranstaltung findet im {room} im {floor} statt."
            if location:
                return f"Die Veranstaltung findet im {location} statt."
        if self._contains_any(text, ("musik", "genre", "musikrichtung")) and genres:
            return (
                "Heute reicht das musikalische Menü von Improvisation und "
                "Avantgarde-Pop bis zu Jazz, Irish Folk und elektronischer Klangforschung."
            )
        if self._contains_any(
            text,
            ("was passiert hier", "was ist denn los", "was ist los", "was passiert heute", "was ist heute", "warum bin ich heute hier"),
        ):
            title = str(subtitle or name).rstrip(".!?")
            return self._choose_variant(
                "event:overview",
                [
                    f"Heute erwartet dich {title}: ein musikalisches Dinner von experimenteller Improvisation bis Irish Folk.",
                    "Hier gibt es heute Konzerte, interaktive Installationen und eine gemeinsame Jam-Session.",
                    f"Heute steigt die {name} mit vielfältiger Musik, Kunst und einer Jam-Session.",
                ],
            )
        if self._contains_any(text, ("veranstaltung", "music night", "music-night", "südkultur", "suedkultur", "programm", "konzert", "jam session")):
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
            "Jede Sachbehauptung muss wörtlich durch die relevanten Informationen belegt sein.\n"
            "Erfinde, ergänze oder vermute keine Fakten.\n"
            "Wenn die Informationen nicht ausreichen, gib das freundlich und selbstironisch zu "
            "und verweise auf die Menschen vor Ort.\n"
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
                "wo bin ich",
                "wo sind wir",
                "welcher ort ist das",
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
                "was passiert hier",
                "was ist denn los",
                "was ist los",
                "warum bin ich heute hier",
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

        if self._is_greeting(text) or self._contains_any(
            text,
            (
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
        searched_context = self._knowledge_context(transcript)

        if category == "orientation":
            return self._join_context(self._orientation_context(), searched_context)

        if category == "event":
            return self._join_context(
                self._event_context(transcript), searched_context
            )

        if category == "artist":
            return self._join_context(
                self._artist_context(transcript), searched_context
            )

        if category == "identity":
            return """Elfi ist ein singender Aufzug im ligeti zentrum.

Elfi bringt Gäste vom Erdgeschoss zum Veranstaltungsort.

Elfi ist keine allgemeine Assistenz und kein gewöhnlicher Chatbot."""

        if category == "smalltalk":
            return """Elfi begrüßt Gäste freundlich und möchte Vorfreude auf den Abend wecken.

Elfi darf leicht verspielt reagieren, erzählt aber keine langen Geschichten."""

        return searched_context

    @staticmethod
    def _join_context(*parts: str) -> str:
        unique: list[str] = []
        for part in parts:
            cleaned = part.strip()
            if cleaned and cleaned not in unique:
                unique.append(cleaned)
        return "\n\n".join(unique)

    def _knowledge_context(self, transcript: str) -> str:
        """Durchsucht alle Wissensdateien und liefert nur belegte Treffer.

        Das Format ist absichtlich redaktionell einfach. Jeder ``##``-Abschnitt
        kann eine ``SCHLAGWÖRTER:``-Zeile und beliebig viele Fakten enthalten.
        Platzhalter mit ``[OFFEN:`` gelten nie als Wissen.
        """
        query = self._search_tokens(transcript)
        if not query or not self.knowledge_dir.is_dir():
            return ""

        matches: list[tuple[int, str, str]] = []
        for path in sorted(self.knowledge_dir.glob("*.txt")):
            if path.name.casefold() == "readme.txt":
                continue
            for title, keywords, facts in self._knowledge_sections(path):
                keyword_text = " ".join(keywords)
                keyword_tokens = self._search_tokens(keyword_text)
                fact_text = " ".join(facts)
                fact_tokens = self._search_tokens(f"{title} {fact_text}")

                exact_hits = sum(
                    1 for keyword in keywords
                    if self._normalize_search_text(keyword) in
                    self._normalize_search_text(transcript)
                )
                score = (
                    exact_hits * 6
                    + len(query & keyword_tokens) * 3
                    + len(query & fact_tokens)
                )
                if score >= 3 and facts:
                    matches.append((score, title, fact_text))

        if not matches:
            return ""

        matches.sort(key=lambda item: (-item[0], item[1].casefold()))
        selected = matches[:2]
        return "\n".join(
            f"{title}: {facts}" for _, title, facts in selected
        )[:1200]

    def _knowledge_direct_response(self, transcript: str) -> str:
        """Gibt einen redaktionellen Fakt ohne kreative LLM-Erweiterung aus."""
        context = self._knowledge_context(transcript)
        if not context:
            return ""
        first_match = context.splitlines()[0]
        answer = first_match.split(": ", 1)[-1].strip()
        sentences = re.split(r"(?<=[.!?])\s+", answer)
        return sentences[0].strip()

    @staticmethod
    def _knowledge_sections(path: Path) -> list[tuple[str, list[str], list[str]]]:
        text = path.read_text(encoding="utf-8")
        sections: list[tuple[str, list[str], list[str]]] = []
        title = ""
        keywords: list[str] = []
        facts: list[str] = []

        def finish() -> None:
            if title:
                sections.append((title, keywords.copy(), facts.copy()))

        for raw_line in text.splitlines():
            line = raw_line.strip()
            if line.startswith("## "):
                finish()
                title = line[3:].strip()
                keywords = []
                facts = []
                continue
            if not title or not line or line.startswith("#"):
                continue
            if line.upper().startswith("SCHLAGWÖRTER:"):
                keywords = [
                    item.strip() for item in line.split(":", 1)[1].split(",")
                    if item.strip()
                ]
                continue
            if "[OFFEN:" in line.upper():
                continue
            if line.startswith("-"):
                fact = line[1:].strip()
                if fact:
                    facts.append(fact)

        finish()
        return sections

    @staticmethod
    def _normalize_search_text(text: str) -> str:
        normalized = text.casefold()
        normalized = normalized.replace("ä", "ae").replace("ö", "oe")
        normalized = normalized.replace("ü", "ue").replace("ß", "ss")
        return re.sub(r"[^a-z0-9 ]+", " ", normalized)

    @classmethod
    def _search_tokens(cls, text: str) -> set[str]:
        return {
            token for token in cls._normalize_search_text(text).split()
            if len(token) >= 3 and token not in KNOWLEDGE_STOPWORDS
        }

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
                "Heute findet die Südkultur Music-Night statt. "
                "Das Programm beginnt um 17:15 Uhr."
            )

        name = event_data.get("name", "Südkultur Music-Night")
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
    def _is_greeting(text: str) -> bool:
        return bool(re.search(
            r"\b(hallo|hi|moin|guten tag|guten abend)\b",
            text,
            flags=re.IGNORECASE,
        ))

    @staticmethod
    def _normalize_input(text: str) -> str:
        normalized = " ".join(text.split()).strip()
        # Whisper schreibt das Fragewort gelegentlich als "wehm".
        normalized = re.sub(
            r"\bwehm\b", "wem", normalized, flags=re.IGNORECASE
        )
        normalized = re.sub(
            r"\bzitter\b", "Zither", normalized, flags=re.IGNORECASE
        )
        return re.sub(
            r"\bliber\b", "lieber", normalized, flags=re.IGNORECASE
        )

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
