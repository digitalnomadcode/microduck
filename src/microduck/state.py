"""Telemetry values independent of the simulation engine."""

from dataclasses import dataclass


@dataclass(frozen=True)
class RobotState:
    simulation_time: float
    position: tuple[float, float, float]
    orientation_wxyz: tuple[float, float, float, float]
    joint_positions: dict[str, float]
    connected: bool
