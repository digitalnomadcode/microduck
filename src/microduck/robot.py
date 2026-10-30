"""Public robot API with a safe, non-operational hardware boundary."""

from .simulation import SimulationBackend
from .state import RobotState


class UnsupportedActionError(RuntimeError):
    pass


class MicroDuck:
    def __init__(self, backend: str = "simulation") -> None:
        if backend == "simulation":
            self._backend = SimulationBackend()
        elif backend == "hardware":
            raise UnsupportedActionError("Physical hardware control is not implemented")
        else:
            raise ValueError(f"Unknown backend: {backend}")

    @property
    def model(self):
        return self._backend.model

    @property
    def data(self):
        return self._backend.data

    def connect(self) -> None:
        self._backend.connect()

    def disconnect(self) -> None:
        self._backend.disconnect()

    def stand(self) -> None:
        self._backend.stand()

    def reset(self) -> None:
        self._backend.reset()

    def stop(self) -> None:
        self._backend.stop()

    def move_head(self, direction: str) -> None:
        targets = {"left": 0.35, "right": -0.35, "center": 0.0}
        if direction not in targets:
            raise ValueError("Use left, right, or center")
        self._backend.set_joint("head_yaw", targets[direction])

    def step(self, steps: int = 1) -> None:
        self._backend.step(steps)

    def get_state(self) -> RobotState:
        return self._backend.get_state()

    def walk_forward(self) -> None:
        try:
            self._backend.enable_forward(0.2)
        except (FileNotFoundError, RuntimeError) as exc:
            raise UnsupportedActionError(str(exc)) from exc

    def walk_backward(self) -> None:
        raise UnsupportedActionError("Backward movement was not observed in CPU replay")

    def turn_left(self) -> None:
        raise UnsupportedActionError("Turning needs further validation")

    def turn_right(self) -> None:
        raise UnsupportedActionError("Turning needs further validation")
