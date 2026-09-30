import tempfile
import unittest
from pathlib import Path

from llm.prompt_router import PromptRouter, UNKNOWN_RESPONSES


class PromptRouterKnowledgeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        root = Path(self.temp_dir.name)
        self.config_dir = root / "config"
        self.dialogues_dir = root / "dialogues"
        self.knowledge_dir = self.config_dir / "knowledge"
        self.knowledge_dir.mkdir(parents=True)
        self.dialogues_dir.mkdir()

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def router(self) -> PromptRouter:
        return PromptRouter(
            config_dir=self.config_dir,
            dialogues_dir=self.dialogues_dir,
            knowledge_dir=self.knowledge_dir,
        )

    def test_open_placeholders_are_not_treated_as_knowledge(self) -> None:
        (self.knowledge_dir / "service.txt").write_text(
            "## Toiletten\n"
            "SCHLAGWÖRTER: Toilette, WC\n"
            "- [OFFEN: Standort ergänzen.]\n",
            encoding="utf-8",
        )
        self.assertIsNone(self.router().direct_response("Wo ist die Toilette?"))

    def test_filled_knowledge_is_selected_for_the_prompt(self) -> None:
        (self.knowledge_dir / "service.txt").write_text(
            "## Trinkwasser\n"
            "SCHLAGWÖRTER: Trinkwasser, Wasserflasche\n"
            "- Trinkwasser gibt es an der Bar im Foyer.\n",
            encoding="utf-8",
        )
        router = self.router()
        self.assertEqual(
            router.direct_response("Wo gibt es Trinkwasser?"),
            "Trinkwasser gibt es an der Bar im Foyer.",
        )
        prompt = router.build_prompt("Wo gibt es Trinkwasser?")
        self.assertIn("Trinkwasser gibt es an der Bar im Foyer.", prompt)

    def test_unknown_general_fact_question_is_delegated_to_the_llm(self) -> None:
        self.assertIsNone(
            self.router().direct_response("Kann ich hier mein Fahrrad reparieren?")
        )

    def test_unknown_responses_rotate(self) -> None:
        router = self.router()
        answers = [
            router.unknown_response()
            for number in range(len(UNKNOWN_RESPONSES))
        ]
        self.assertEqual(tuple(answers), UNKNOWN_RESPONSES)

    def test_readme_examples_are_not_searchable_knowledge(self) -> None:
        (self.knowledge_dir / "README.txt").write_text(
            "## Fahrrad\nSCHLAGWÖRTER: Fahrrad\n- Fahrräder stehen im Keller.\n",
            encoding="utf-8",
        )
        self.assertIsNone(self.router().direct_response("Wo steht mein Fahrrad?"))

    def test_hier_is_not_mistaken_for_hi(self) -> None:
        self.assertIsNone(
            self.router().direct_response("Gibt es hier Schließfächer?")
        )

    def test_asr_context_exposes_canonical_artist_names(self) -> None:
        (self.config_dir / "program.txt").write_text(
            "program = [{'name': 'Guan Yanyi', 'start': '18:00', "
            "'end': '18:20', 'genre': 'Improvisation'}]\n",
            encoding="utf-8",
        )
        router = self.router()
        self.assertIsNone(router.direct_response("Wann spielt Juan Jani?"))
        prompt = router.build_prompt("Wann spielt Juan Jani?")
        self.assertIn("automatischer Spracherkennung", prompt)
        self.assertIn("Guan Yanyi", prompt)
        self.assertIn("Beginn 18:00 Uhr", prompt)
        self.assertIn("möglicherweise Guan Yanyi", prompt)

    def test_event_location_remains_tenth_floor(self) -> None:
        self.assertEqual(
            self.router().direct_response("In welchem Stock ist das Production Lab?"),
            "Wir fahren ins Production Lab im zehnten Stock.",
        )

    def test_event_location_uses_structured_room_and_floor(self) -> None:
        (self.config_dir / "event.txt").write_text(
            "event = {\n"
            "    'name': 'Testabend',\n"
            "    'location': 'ligeti zentrum',\n"
            "    'room': 'Production Lab',\n"
            "    'floor': 'zehnten Stock',\n"
            "}\n",
            encoding="utf-8",
        )
        self.assertEqual(
            self.router().direct_response("Wo findet die Veranstaltung statt?"),
            "Die Veranstaltung findet im Production Lab im zehnten Stock statt.",
        )


if __name__ == "__main__":
    unittest.main()
