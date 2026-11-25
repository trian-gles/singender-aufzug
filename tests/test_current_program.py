import unittest

from llm.prompt_router import CONFIG_DIR, PromptRouter


class CurrentProgramTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.router = PromptRouter()
        cls.program = cls.router._read_assignment(
            CONFIG_DIR / "program.txt", variable_name="program"
        )

    def test_open_house_program_contains_key_formats(self) -> None:
        names = {entry["name"] for entry in self.program}
        self.assertIn("Moving Sound Pictures", names)
        self.assertIn("Erlebnis InnoLab", names)
        self.assertIn("strg+alt+ligeti", names)
        self.assertNotIn("Sonomathematische Impulsarchitekten", names)

    def test_science_slam_time_is_used_in_answer(self) -> None:
        answer = self.router.direct_response("Wann ist der Science Slam?")
        self.assertIn("19:00", answer)
        self.assertIn("21:00", answer)

    def test_participant_question_uses_current_program(self) -> None:
        answer = self.router.direct_response("Was weißt du über Simon Linke?")
        self.assertIn("InnoLab", answer)

    def test_program_item_is_found_by_time_range(self) -> None:
        answer = self.router.direct_response("Was passiert um 19 Uhr?")
        self.assertIn("strg+alt+ligeti", answer)

    def test_event_overview_uses_open_house(self) -> None:
        answer = self.router.direct_response("Was passiert hier heute?")
        self.assertTrue(
            "Labs" in answer or "Ausstellungen" in answer or "Mitmachformaten" in answer
        )
        self.assertNotIn("Music-Night", answer)

    def test_knowledge_answers_open_house_service_question(self) -> None:
        answer = self.router.direct_response("Gibt es Kaffee?")
        self.assertIn("Kaffee", answer)

    def test_old_music_night_artist_is_not_active(self) -> None:
        self.assertIsNone(self.router.direct_response("Wann spielt Guan Yanyi?"))

    def test_where_should_i_go_mentions_all_program_floors(self) -> None:
        answer = self.router.direct_response("Wo muss ich hin?")
        self.assertIn("siebten", answer)
        self.assertIn("neunten", answer)
        self.assertIn("zehnten", answer)

    def test_floor_questions_return_rotating_program_examples(self) -> None:
        first = self.router.direct_response("Was ist im neunten Stock?")
        second = self.router.direct_response("Was gibt es im neunten Stock?")
        self.assertIn("neunten Stock", first)
        self.assertIn("neunten Stock", second)
        self.assertNotEqual(first, second)
        self.assertIn("InnoLab", self.router.direct_response("Was gibt es im zehnten Stock?"))
        self.assertIn("Moving Sound Pictures", self.router.direct_response("Was ist im siebten Stock?"))

    def test_person_location_uses_program_floor(self) -> None:
        answer = self.router.direct_response("In welchem Stockwerk ist Simon?")
        self.assertIn("zehnten Stock", answer)

    def test_program_entry_rooms_are_populated(self) -> None:
        self.assertTrue(all(entry.get("floor") and entry.get("room") for entry in self.program))

    def test_find_person_uses_person_context_not_event_overview(self) -> None:
        answer = self.router.direct_response("Wo finde ich Michel?")
        self.assertIn("InnoLab", answer)
        self.assertIn("zehnten Stock", answer)

    def test_room_question_lists_program_for_room(self) -> None:
        answer = self.router.direct_response("Was passiert heute im Production Lab?")
        self.assertIn("Kunstformen der Natur", answer)
        self.assertIn("Spatial Audio Listening Room", answer)

    def test_room_question_for_haptic_lab_does_not_return_event_overview(self) -> None:
        answer = self.router.direct_response("Was passiert heute im Haptic Lab?")
        self.assertIn("Technik zum Anfassen", answer)

    def test_event_preview_is_not_date_fragment(self) -> None:
        answer = self.router.direct_response("Was erwartet mich heute?")
        self.assertNotIn("5. Dezember", answer)
        self.assertTrue("Labs" in answer or "Ausstellungen" in answer)

    def test_subjective_favorite_does_not_return_event_fact(self) -> None:
        answer = self.router.direct_response("Was ist dein Lieblingsprogrammpunkt?")
        self.assertIn("bewerte", answer)
        self.assertNotIn("Tag der offenen Tür", answer)

    def test_named_current_participant_is_confirmed(self) -> None:
        answer = self.router.direct_response("Ist Michel auch da?")
        self.assertIn("Ja, Michel Blümel", answer)
        self.assertIn("Erlebnis InnoLab", answer)

    def test_repeated_program_participant_is_found_by_first_name(self) -> None:
        answer = self.router.direct_response("Ist Simon da?")
        self.assertIn("Ja, Simon Linke", answer)

    def test_unknown_attendance_question_does_not_go_to_llm(self) -> None:
        answer = self.router.direct_response("Ist Andine da?")
        self.assertEqual(answer, "Das weiß ich nicht sicher. Frag bitte das Team.")

    def test_subjective_judgement_is_not_misrouted_to_knowledge(self) -> None:
        answer = self.router.direct_response("Welches ist das schlechteste Angebot heute?")
        self.assertIn("bewerte", answer)
        self.assertNotIn("5. Dezember", answer)

    def test_smell_complaint_goes_to_staff(self) -> None:
        answer = self.router.direct_response("Hier stinkt es")
        self.assertIn("Team", answer)

    def test_recommendation_question_is_not_answered_with_event_name(self) -> None:
        answer = self.router.direct_response("Welcher Programmpunkt ist empfehlenswert?")
        self.assertIn("bewerte", answer)
        self.assertNotIn("Tag der offenen Tür", answer)


if __name__ == "__main__":
    unittest.main()
