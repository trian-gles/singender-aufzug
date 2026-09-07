from pathlib import Path


class PromptLoader:
    """Lädt und kombiniert Elfis Prompt-Dateien."""

    def __init__(self, project_root: Path | None = None) -> None:
        if project_root is None:
            project_root = Path(__file__).resolve().parent.parent

        self.project_root = project_root
        self.config_dir = project_root / "config"
        self.dialogues_dir = project_root / "dialogues"

    @staticmethod
    def _read_text(path: Path) -> str:
        if not path.exists():
            raise FileNotFoundError(f"Prompt-Datei nicht gefunden: {path}")

        return path.read_text(encoding="utf-8").strip()

    def load_system_sections(self) -> list[str]:
        files = [
            self.config_dir / "system_prompt.txt",
            self.config_dir / "ligeti_zentrum.txt",
            self.config_dir / "event.txt",
            self.config_dir / "program.txt",
            self.config_dir / "conversation_rules.txt",
        ]

        return [self._read_text(path) for path in files]

    def load_dialogues(self) -> list[str]:
        files = [
            self.dialogues_dir / "greetings.txt",
            self.dialogues_dir / "orientation.txt",
            self.dialogues_dir / "event_questions.txt",
            self.dialogues_dir / "smalltalk.txt",
            self.dialogues_dir / "fallback.txt",
        ]

        return [self._read_text(path) for path in files]

    def build_prompt(self, visitor_text: str) -> str:
        visitor_text = visitor_text.strip()

        if not visitor_text:
            raise ValueError("Der Besuchertext darf nicht leer sein.")

        sections = self.load_system_sections()

        dialogue_text = "\n\n---\n\n".join(self.load_dialogues())

        sections.append(
            "BEISPIELDIALOGE\n\n"
            "Orientiere dich am Stil der folgenden Beispiele:\n\n"
            f"{dialogue_text}"
        )

        sections.append(
            "AKTUELLE EINGABE\n\n"
            f"Gast:\n{visitor_text}\n\n"
            "Elfi:"
        )

        return "\n\n====================\n\n".join(sections)