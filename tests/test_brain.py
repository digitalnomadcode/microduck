"""Behavior checks for command interpretation and CPU simulation control."""

import importlib.util
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from microduck import Brain, MicroDuck  # noqa: E402
from microduck.robot import UnsupportedActionError  # noqa: E402


class BrainTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.robot = MicroDuck()
        cls.robot.connect()

    @classmethod
    def tearDownClass(cls) -> None:
        cls.robot.disconnect()

    def setUp(self) -> None:
        self.robot.stand()
        self.brain = Brain(self.robot)

    def test_head_command_and_context(self) -> None:
        self.assertTrue(self.brain.handle("Поверни голову влево").accepted)
        self.robot.step(150)
        self.assertGreater(self.robot.get_state().joint_positions["head_yaw"], 0.02)
        self.assertTrue(self.brain.handle("теперь вправо").accepted)

    def test_unknown_does_not_move(self) -> None:
        before = self.robot.data.ctrl.copy()
        result = self.brain.handle("приготовь чай")
        self.assertFalse(result.accepted)
        self.assertEqual(result.action, "unknown")
        self.assertTrue((before == self.robot.data.ctrl).all())

    def test_backward_is_explicitly_unsupported(self) -> None:
        result = self.brain.handle("иди назад")
        self.assertFalse(result.accepted)
        self.assertEqual(result.action, "locomotion")

    @unittest.skipUnless(importlib.util.find_spec("onnxruntime"), "ONNX Runtime needs Python 3.12")
    def test_forward_walks_on_cpu(self) -> None:
        result = self.brain.handle("иди вперед")
        self.assertTrue(result.accepted, result.message)
        self.robot.step(2500)
        state = self.robot.get_state()
        self.assertGreater(state.position[0], 0.25)
        self.assertGreater(state.position[2], 0.1)
        self.brain.handle("остановись")
        self.assertEqual(float(self.robot._backend.policy.command[0]), 0.0)
        self.robot.step(2500)
        self.assertLess(abs(self.robot.get_state().position[0] - state.position[0]), 0.05)

    @unittest.skipUnless(importlib.util.find_spec("onnxruntime"), "ONNX Runtime needs Python 3.12")
    def test_head_command_during_walking_keeps_balance(self) -> None:
        self.assertTrue(self.brain.handle("иди вперед").accepted)
        self.robot.step(1000)
        self.assertTrue(self.brain.handle("поверни голову влево").accepted)
        self.robot.step(1000)
        state = self.robot.get_state()
        self.assertGreater(state.position[2], 0.1)
        self.assertGreater(state.joint_positions["head_yaw"], 0.1)
        self.assertIsNotNone(self.robot._backend.policy)

    def test_state_and_reset(self) -> None:
        self.assertTrue(self.brain.handle("покажи состояние").accepted)
        self.assertTrue(self.brain.handle("сброс").accepted)
        self.assertEqual(self.robot.get_state().simulation_time, 0.0)

    def test_joint_limit_is_enforced(self) -> None:
        with self.assertRaises(ValueError):
            self.robot._backend.set_joint("head_roll", 10.0)

    def test_hardware_cannot_connect(self) -> None:
        with self.assertRaises(UnsupportedActionError):
            MicroDuck(backend="hardware")


if __name__ == "__main__":
    unittest.main()
