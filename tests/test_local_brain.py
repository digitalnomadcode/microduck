"""Tests for language-model action validation without loading model weights."""

import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from microduck import Brain, MicroDuck
from microduck.local_brain import AICommandBrain


class StubModel:
    def __init__(self, action, reply=""):
        self.action = action
        self.reply = reply

    def complete(self, messages):
        return json.dumps({"action": self.action, "reply": self.reply})


class AICommandBrainTests(unittest.TestCase):
    def test_paraphrase_reaches_allowlisted_walk(self):
        robot = MicroDuck()
        robot.connect()
        try:
            brain = AICommandBrain(Brain(robot), StubModel("walk_forward"))
            result = brain.handle("Подойди ко мне")
            self.assertEqual(result.action, "walk_forward")
            robot.step(2500)
            self.assertGreater(robot.get_state().position[0], 0.25)
        finally:
            robot.disconnect()

    def test_unlisted_action_does_not_move(self):
        robot = MicroDuck()
        robot.connect()
        try:
            before = robot.get_state().position
            brain = AICommandBrain(Brain(robot), StubModel("set_all_motors"))
            result = brain.handle("Произвольная команда")
            self.assertFalse(result.accepted)
            self.assertEqual(before, robot.get_state().position)
        finally:
            robot.disconnect()

    def test_conversation_response(self):
        robot = MicroDuck()
        robot.connect()
        try:
            brain = AICommandBrain(Brain(robot), StubModel("chat", "Привет!"))
            result = brain.handle("Как тебя зовут?")
            self.assertTrue(result.accepted)
            self.assertEqual(result.message, "Привет!")
        finally:
            robot.disconnect()


if __name__ == "__main__":
    unittest.main()
