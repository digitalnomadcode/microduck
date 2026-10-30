"""Wake-word safety checks without opening a microphone."""

from pathlib import Path
import sys
import importlib.util
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from microduck.voice import extract_wake_command, command_from_transcript  # noqa: E402


class VoiceCommandTests(unittest.TestCase):
    def test_wake_word_extracts_command(self) -> None:
        self.assertEqual(extract_wake_command("Утка, иди вперёд"), "иди вперед")
        self.assertEqual(
            extract_wake_command("Утка, пожалуйста, посмотри налево"),
            "пожалуйста посмотри налево",
        )

    def test_recognized_phrase_reaches_robot(self) -> None:
        from microduck import Brain, MicroDuck

        robot = MicroDuck()
        robot.connect()
        try:
            command = extract_wake_command("утка посмотри налево")
            result = Brain(robot).handle(command)
            self.assertTrue(result.accepted)
            robot.step(150)
            self.assertGreater(robot.get_state().joint_positions["head_yaw"], 0.02)
        finally:
            robot.disconnect()

    @unittest.skipUnless(importlib.util.find_spec("onnxruntime"), "ONNX Runtime needs Python 3.12")
    def test_user_transcript_walks_without_wake_word(self) -> None:
        from microduck import Brain, MicroDuck

        robot = MicroDuck()
        robot.connect()
        try:
            command = command_from_transcript("иди вперёд")
            result = Brain(robot).handle(command)
            self.assertTrue(result.accepted, result.message)
            robot.step(2500)
            self.assertGreater(robot.get_state().position[0], 0.25)
        finally:
            robot.disconnect()

    def test_optional_wake_word_remains_strict(self) -> None:
        self.assertIsNone(command_from_transcript("иди вперёд", require_wake_word=True))
        self.assertEqual(command_from_transcript("утка иди вперёд", require_wake_word=True), "иди вперед")

    def test_background_speech_is_ignored(self) -> None:
        self.assertIsNone(extract_wake_command("иди вперед"))
        self.assertIsNone(extract_wake_command("утка"))


if __name__ == "__main__":
    unittest.main()
