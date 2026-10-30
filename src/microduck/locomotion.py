"""CPU replay of the official XGO-Duck walking ONNX policy."""

import math
from pathlib import Path

import mujoco
import numpy as np


ROOT = Path(__file__).resolve().parents[2]
WALK_ONNX = ROOT / "vendor/xgoduck_runtime_arduino/python/xgoduck_walk.onnx"
OBSERVATION_NAMES = (
    "base_ang_vel,projected_gravity,joint_pos,joint_vel,"
    "actions,command,head_command,body_command"
)


class WalkingPolicy:
    def __init__(self, model: mujoco.MjModel, data: mujoco.MjData, path: Path = WALK_ONNX) -> None:
        try:
            import onnxruntime as ort
        except ImportError as exc:
            raise RuntimeError("ONNX Runtime is unavailable; use the project's Python 3.12 environment") from exc
        if not path.is_file():
            raise FileNotFoundError(f"Official XGO-Duck walking policy not found: {path}")

        options = ort.SessionOptions()
        options.intra_op_num_threads = 1
        self.session = ort.InferenceSession(
            str(path), sess_options=options, providers=["CPUExecutionProvider"]
        )
        self.input = self.session.get_inputs()[0]
        self.output = self.session.get_outputs()[0]
        if self.session.get_providers() != ["CPUExecutionProvider"]:
            raise RuntimeError("Walking policy is not using the CPU provider")
        if self.input.shape != [1, 61] or self.output.shape != [1, 14]:
            raise RuntimeError("Walking policy shape is not [1,61] -> [1,14]")
        metadata = self.session.get_modelmeta().custom_metadata_map
        names = [model.actuator(i).name for i in range(model.nu)]
        if metadata.get("joint_names", "").split(",") != names:
            raise RuntimeError("ONNX joint order differs from the XGO-Duck MJCF")
        if metadata.get("observation_names") != OBSERVATION_NAMES:
            raise RuntimeError("ONNX observation layout is unsupported")
        self.home = np.fromstring(metadata["default_joint_pos"], sep=",", dtype=np.float32)
        if self.home.shape != (model.nu,):
            raise RuntimeError("ONNX home pose is not 14D")
        if float(metadata.get("action_scale", "nan")) != 1.0:
            raise RuntimeError("Unexpected ONNX action scale")

        self.model, self.data = model, data
        self.joint_ids = np.asarray(model.actuator_trnid[:, 0], dtype=np.int32)
        self.pos_ids = model.jnt_qposadr[self.joint_ids]
        self.vel_ids = model.jnt_dofadr[self.joint_ids]
        self.limits = model.jnt_range[self.joint_ids]
        self.body_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, "trunk_base")
        sensor_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_SENSOR, "imu_ang_vel")
        if self.body_id < 0 or sensor_id < 0:
            raise RuntimeError("Required XGO-Duck body or gyro sensor is missing")
        self.gyro_address = model.sensor_adr[sensor_id]
        self.decimation = round(1 / (50 * model.opt.timestep))
        if abs(self.decimation * model.opt.timestep - 0.02) > 1e-9:
            raise RuntimeError("Physics timestep cannot support the policy at 50 Hz")

        self.command = np.zeros(3, dtype=np.float32)
        self.head_command = np.zeros(4, dtype=np.float32)
        self.previous_action = np.zeros(model.nu, dtype=np.float32)
        self.filtered_action = np.zeros(model.nu, dtype=np.float32)
        self.step_count = 0
        self.clipped_targets = 0

    def start_from_stand(self) -> None:
        stand_id = mujoco.mj_name2id(self.model, mujoco.mjtObj.mjOBJ_KEY, "STAND")
        mujoco.mj_resetDataKeyframe(self.model, self.data, stand_id)
        self.data.qpos[self.pos_ids] = self.home
        self.data.qpos[2] = 0.139439  # Walking home height from xgoduck_constants.py.
        self.data.ctrl[:] = self.home
        mujoco.mj_forward(self.model, self.data)
        self.head_command.fill(0)
        self.previous_action.fill(0)
        self.filtered_action.fill(0)
        self.step_count = 0
        self.clipped_targets = 0

    def set_forward_speed(self, speed: float) -> None:
        if not math.isfinite(speed) or not 0 <= speed <= 0.4:
            raise ValueError("Forward speed must be in [0, 0.4] m/s")
        self.command[:] = (speed, 0, 0)

    def set_head_yaw(self, angle_rad: float) -> None:
        if not math.isfinite(angle_rad) or not -0.35 <= angle_rad <= 0.35:
            raise ValueError("Head yaw command must be within [-0.35, 0.35] rad")
        self.head_command[2] = angle_rad

    def before_step(self) -> None:
        if self.step_count % self.decimation:
            return
        data = self.data
        gyro = data.sensordata[self.gyro_address:self.gyro_address + 3].astype(np.float32)
        rotation = data.xmat[self.body_id].reshape(3, 3)
        gravity = (rotation.T @ np.array([0, 0, -1], dtype=np.float32)).astype(np.float32)
        observation = np.concatenate([
            gyro,
            gravity,
            data.qpos[self.pos_ids].astype(np.float32) - self.home,
            data.qvel[self.vel_ids].astype(np.float32),
            self.previous_action,
            self.command,
            self.head_command,
            np.zeros(6, dtype=np.float32),
        ]).reshape(1, 61)
        if not np.isfinite(observation).all():
            raise RuntimeError("Non-finite walking-policy observation")
        action = self.session.run(
            [self.output.name], {self.input.name: observation}
        )[0].reshape(self.model.nu)
        if not np.isfinite(action).all():
            raise RuntimeError("Non-finite walking-policy action")
        self.previous_action[:] = action
        for part, alpha in ((slice(0, 5), 0.45), (slice(5, 10), 0.2), (slice(10, 14), 0.45)):
            self.filtered_action[part] *= alpha
            self.filtered_action[part] += action[part] * (1 - alpha)
        raw_target = self.home + self.filtered_action
        target = np.clip(raw_target, self.limits[:, 0], self.limits[:, 1])
        self.clipped_targets += int(np.count_nonzero(np.abs(raw_target - target) > 1e-5))
        data.ctrl[:] = target

    def after_step(self) -> None:
        self.step_count += 1
