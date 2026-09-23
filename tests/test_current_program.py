import unittest

from llm.prompt_router import CONFIG_DIR, PromptRouter, UNKNOWN_RESPONSES


class CurrentProgramTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.router = PromptRouter()
        cls.program = cls.router._read_assignment(
            CONFIG_DIR / "program.txt", variable_name="program"
        )

    def test_current_running_order_and_times(self) -> None:
        expected = [
            ("Interaktive Installationen und Ausstellung von Dai Jianhua", "17:00", None),
            ("Sonomathematische Impulsarchitekten", "17:15", "17:45"),
            ("Guan Yanyi", "18:00", "18:20"),
            ("Liang Yiyuan", "18:35", "19:05"),
            ("Potluck", "19:30", "20:00"),
            ("oscheat", "20:10", "20:40"),
            ("Clarks Planet", "21:00", "21:45"),
            ("Kieran McAuliffe & Friends", "22:00", "22:50"),
        ]
        actual = [
            (entry["name"], entry["start"], entry["end"])
            for entry in self.program
        ]
        self.assertEqual(actual, expected)

    def test_removed_act_is_not_in_program(self) -> None:
        names = {entry["name"] for entry in self.program}
        self.assertNotIn("Jacob", names)

    def test_new_time_is_used_in_answer(self) -> None:
        answer = self.router.direct_response("Wann spielt Liang Yiyuan?")
        self.assertIn("18:35", answer)
        self.assertIn("19:05", answer)

    def test_instruments_can_be_answered(self) -> None:
        answer = self.router.direct_response(
            "Welche Instrumente spielt Guan Yanyi?"
        )
        self.assertIn("Mundharmonika", answer)
        self.assertIn("Synthesizer", answer)

    def test_whisper_zitter_is_understood_as_zither(self) -> None:
        answer = self.router.direct_response("Wer spielt zitter?")
        self.assertIn("Sonomathematischen Impulsarchitekten", answer)
        self.assertIn("oscheat", answer)

    def test_guitar_answer_fits_singing_limit(self) -> None:
        answer = self.router.direct_response("Wer spielt heute Abend Gitarre?")
        self.assertLessEqual(len(answer.split()), 12)
        self.assertIn("Clarks Planet", answer)

    def test_service_and_orientation_questions_from_recording(self) -> None:
        cases = {
            "Wo bin ich hier?": "ligeti zentrum",
            "Kann ich da oben etwas trinken?": "gegen Spende",
            "Das Heute Abend Bier": "gegen Spende",
            "Gibt es heute etwas zu trinken?": "gegen Spende",
            "Wer spielt als Letztes?": "Kieran McAuliffe und Friends",
            "Wo ist die Garderobe?": "Garderobe ist im zehnten Stock",
            "Ist das barrierefrei?": "barrierefrei erreichbar",
            "Wo darf ich rauchen?": "Erdgeschoss",
            "Was mache ich im Notfall?": "Mitarbeitenden",
        }
        for question, expected in cases.items():
            with self.subTest(question=question):
                self.assertIn(expected, self.router.direct_response(question))

        self.assertIn(
            self.router.direct_response("Gibt es etwas zu essen?"),
            UNKNOWN_RESPONSES,
        )

    def test_event_name_always_uses_umlaut(self) -> None:
        answer = self.router.direct_response("Welche Veranstaltung ist heute?")
        self.assertIn("Südkultur", answer)
        self.assertNotIn("Sued" + "Kultur", answer)

    def test_recorded_conversation_questions_route_correctly(self) -> None:
        cases = {
            "Hallo, was ist denn los?": ("musikalisches Dinner", "Konzerte", "Music-Night"),
            "Was passiert hier?": ("Installationen", "Jam-Session"),
            "Was passiert hier heute Abend?": ("Music-Night", "Musik", "musikalisches Dinner", "Konzerte"),
            "Spielt heute jemand Gitarre?": ("Gitarre", "Guan Yanyi"),
            "Was für Musik kann ich erwarten?": ("Improvisation", "Jazz"),
            "Welche Instrumente kann ich heute hören?": ("Zither", "Mundharmonika"),
        }
        for question, expected_terms in cases.items():
            with self.subTest(question=question):
                answer = self.router.direct_response(question)
                self.assertTrue(
                    any(term in answer for term in expected_terms),
                    msg=f"Unerwartete Antwort auf {question!r}: {answer!r}",
                )


if __name__ == "__main__":
    unittest.main()
