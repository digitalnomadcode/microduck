"""Measure an official XGO-Duck ONNX walking policy in CPU MuJoCo.

This is a diagnostic replay, not a validated walking controller.
"""

import argparse
import math
from pathlib import Path

import mujoco
import numpy as np
import onnxruntime as ort


ROOT = Path(__file__).resolve().parents[1]
SCENE = ROOT / "vendor/xgoduck_rl/src/mjlab_microduck/robot/xgoduck/scene_walk.xml"
POLICY = ROOT / "vendor/xgoduck_runtime_arduino/python/xgoduck_walk.onnx"
CONTROL_HZ = 50


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seconds", type=float, default=5.0)
    parser.add_argument("--speed", type=float, default=0.2)
    parser.add_argument("--yaw", type=float, default=0.0)
    args = parser.parse_args()
    if not 0 < args.seconds <= 30:
        parser.error("--seconds must be in (0, 30]")
    if not -1.0 <= args.yaw <= 1.0:
        parser.error("--yaw must be in [-1.0, 1.0]")
    if not -0.2 <= args.speed <= 0.4:
        parser.error("--speed must be in [-0.2, 0.4]")

    model = mujoco.MjModel.from_xml_path(str(SCENE))
    data = mujoco.MjData(model)
    options = ort.SessionOptions()
    options.intra_op_num_threads = 1
    session = ort.InferenceSession(str(POLICY), sess_options=options, providers=["CPUExecutionProvider"])
    model_input, model_output = session.get_inputs()[0], session.get_outputs()[0]
    if model_input.shape != [1, 61] or model_output.shape != [1, 14]:
        raise RuntimeError(f"Unexpected policy shape: {model_input.shape} -> {model_output.shape}")
    metadata = session.get_modelmeta().custom_metadata_map
    policy_names = metadata["joint_names"].split(",")
    actuator_names = [model.actuator(i).name for i in range(model.nu)]
    if policy_names != actuator_names:
        raise RuntimeError(f"Policy/MJCF joint order mismatch: {policy_names} != {actuator_names}")
    home = np.fromstring(metadata["default_joint_pos"], sep=",", dtype=np.float32)
    if home.shape != (model.nu,):
        raise RuntimeError("Policy home pose is not 14D")
    if metadata.get("observation_names") != (
        "base_ang_vel,projected_gravity,joint_pos,joint_vel,"
        "actions,command,head_command,body_command"
    ):
        raise RuntimeError("Unsupported observation layout")

    joint_ids = np.asarray(model.actuator_trnid[:, 0], dtype=np.int32)
    pos_ids = model.jnt_qposadr[joint_ids]
    vel_ids = model.jnt_dofadr[joint_ids]
    limits = model.jnt_range[joint_ids]

    stand_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_KEY, "STAND")
    mujoco.mj_resetDataKeyframe(model, data, stand_id)
    data.qpos[pos_ids] = home
    data.qpos[2] = 0.139439  # XGODUCK_WALK_STAND_Z from xgoduck_constants.py
    data.ctrl[:] = home
    mujoco.mj_forward(model, data)
    initial_x = float(data.qpos[0])
    initial_z = float(data.qpos[2])

    body_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, "trunk_base")
    gyro_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_SENSOR, "imu_ang_vel")
    gyro_address = model.sensor_adr[gyro_id]
    decimation = round(1 / (CONTROL_HZ * model.opt.timestep))
    if abs(decimation * model.opt.timestep - 1 / CONTROL_HZ) > 1e-9:
        raise RuntimeError("Physics timestep does not divide 50 Hz control period")

    previous_action = np.zeros(model.nu, dtype=np.float32)
    filtered_action = np.zeros(model.nu, dtype=np.float32)
    command = np.array([args.speed, 0, args.yaw], dtype=np.float32)
    clipped = 0
    min_z = initial_z
    max_tilt_deg = 0.0
    steps = round(args.seconds / model.opt.timestep)

    for step in range(steps):
        if step % decimation == 0:
            gyro = data.sensordata[gyro_address:gyro_address + 3].astype(np.float32)
            rotation = data.xmat[body_id].reshape(3, 3)
            gravity = (rotation.T @ np.array([0, 0, -1], dtype=np.float32)).astype(np.float32)
            obs = np.concatenate([
                gyro, gravity,
                data.qpos[pos_ids].astype(np.float32) - home,
                data.qvel[vel_ids].astype(np.float32),
                previous_action, command,
                np.zeros(4, dtype=np.float32),
                np.zeros(6, dtype=np.float32),
            ]).reshape(1, 61)
            if not np.isfinite(obs).all():
                raise RuntimeError(f"Non-finite observation at step {step}")
            action = session.run([model_output.name], {model_input.name: obs})[0].reshape(14)
            if not np.isfinite(action).all():
                raise RuntimeError(f"Non-finite policy output at step {step}")
            previous_action[:] = action
            for part, alpha in ((slice(0, 5), 0.45), (slice(5, 10), 0.2), (slice(10, 14), 0.45)):
                filtered_action[part] *= alpha
                filtered_action[part] += action[part] * (1 - alpha)
            raw_target = home + filtered_action
            target = np.clip(raw_target, limits[:, 0], limits[:, 1])
            clipped += int(np.count_nonzero(np.abs(raw_target - target) > 1e-5))
            data.ctrl[:] = target
        mujoco.mj_step(model, data)
        if not np.isfinite(data.qpos).all():
            raise RuntimeError(f"Non-finite physics state at step {step}")
        min_z = min(min_z, float(data.qpos[2]))
        upright = float(data.xmat[body_id][8])
        max_tilt_deg = max(max_tilt_deg, math.degrees(math.acos(np.clip(upright, -1, 1))))

    dx = float(data.qpos[0]) - initial_x
    qw, qx, qy, qz = [float(x) for x in data.qpos[3:7]]
    yaw_deg = math.degrees(math.atan2(2 * (qw * qz + qx * qy), 1 - 2 * (qy * qy + qz * qz)))
    print(f"Python CPU policy: {session.get_providers()[0]}")
    print(f"Duration: {data.time:.2f} s, command vx={args.speed:.2f} m/s, yaw={args.yaw:.2f} rad/s")
    print(f"Base x: {initial_x:.3f} -> {data.qpos[0]:.3f} m, displacement={dx:.3f} m")
    print(f"Base z: {initial_z:.3f} -> {data.qpos[2]:.3f} m, minimum={min_z:.3f} m")
    print(f"Maximum tilt: {max_tilt_deg:.1f} deg; final yaw: {yaw_deg:.1f} deg; clipped targets: {clipped}")
    print("Replay stability only; walking quality requires visual and multi-command checks.")


if __name__ == "__main__":
    main()
