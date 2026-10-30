"""CPU-only MuJoCo backend for the official XGO-Duck walking scene."""

from pathlib import Path
import math

import mujoco

from .locomotion import WalkingPolicy
from .state import RobotState


ROOT = Path(__file__).resolve().parents[2]
SCENE = (
    ROOT / "vendor" / "xgoduck_rl" / "src" / "mjlab_microduck"
    / "robot" / "xgoduck" / "scene_walk.xml"
)


class SimulationBackend:
    def __init__(self, scene: Path = SCENE) -> None:
        self.scene = Path(scene)
        self.model: mujoco.MjModel | None = None
        self.data: mujoco.MjData | None = None
        self.policy: WalkingPolicy | None = None

    def connect(self) -> None:
        if not self.scene.is_file():
            raise FileNotFoundError(f"Official XGO-Duck MJCF not found: {self.scene}")
        self.model = mujoco.MjModel.from_xml_path(str(self.scene))
        self.data = mujoco.MjData(self.model)
        if self.model.nu != 14:
            raise RuntimeError(f"Expected 14 XGO-Duck actuators, got {self.model.nu}")
        self.stand()

    def disconnect(self) -> None:
        self.policy = None
        self.model = None
        self.data = None

    def _ready(self) -> tuple[mujoco.MjModel, mujoco.MjData]:
        if self.model is None or self.data is None:
            raise RuntimeError("Simulation is not connected")
        return self.model, self.data

    def stand(self) -> None:
        model, data = self._ready()
        self.policy = None
        key_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_KEY, "STAND")
        if key_id < 0:
            raise RuntimeError("Official STAND keyframe is missing")
        mujoco.mj_resetDataKeyframe(model, data, key_id)
        mujoco.mj_forward(model, data)

    def reset(self) -> None:
        self.stand()

    def stop(self) -> None:
        model, data = self._ready()
        if self.policy is not None:
            self.policy.set_forward_speed(0.0)
            return
        for index in range(model.nu):
            joint_name = model.actuator(index).name
            joint_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, joint_name)
            qpos_address = model.jnt_qposadr[joint_id]
            value = float(data.qpos[qpos_address])
            lower, upper = model.jnt_range[joint_id]
            data.ctrl[index] = min(max(value, lower), upper)

    def set_joint(self, name: str, position_rad: float) -> None:
        model, data = self._ready()
        if not math.isfinite(position_rad):
            raise ValueError("Joint target must be finite")
        actuator_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_ACTUATOR, name)
        joint_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, name)
        if actuator_id < 0 or joint_id < 0:
            raise ValueError(f"Unknown actuated joint: {name}")
        lower, upper = model.jnt_range[joint_id]
        if not lower <= position_rad <= upper:
            raise ValueError(f"{name} target outside [{lower:.3f}, {upper:.3f}] rad")
        if self.policy is not None:
            if name == "head_yaw":
                self.policy.set_head_yaw(position_rad)
                return
            raise RuntimeError("Direct joint commands are unavailable while walking")
        data.ctrl[actuator_id] = position_rad

    def enable_forward(self, speed: float = 0.2) -> None:
        model, data = self._ready()
        if self.policy is None:
            policy = WalkingPolicy(model, data)
            policy.start_from_stand()
            self.policy = policy
        self.policy.set_forward_speed(speed)

    def step(self, steps: int = 1) -> None:
        model, data = self._ready()
        if steps < 0:
            raise ValueError("steps must be non-negative")
        for _ in range(steps):
            if self.policy is not None:
                try:
                    self.policy.before_step()
                except Exception:
                    self.policy = None
                    self.stop()
                    raise
            mujoco.mj_step(model, data)
            if self.policy is not None:
                self.policy.after_step()

    def get_state(self) -> RobotState:
        model, data = self._ready()
        joints = {}
        for index in range(model.nu):
            name = model.actuator(index).name
            joint_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, name)
            joints[name] = float(data.qpos[model.jnt_qposadr[joint_id]])
        return RobotState(
            simulation_time=float(data.time),
            position=tuple(float(x) for x in data.qpos[:3]),
            orientation_wxyz=tuple(float(x) for x in data.qpos[3:7]),
            joint_positions=joints,
            connected=True,
        )
