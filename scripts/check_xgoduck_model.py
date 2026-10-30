"""Load and step the unmodified official XGO-Duck walking scene."""

import argparse
from pathlib import Path
import time

import mujoco


ROOT = Path(__file__).resolve().parents[1]
SCENE = (
    ROOT
    / "vendor"
    / "xgoduck_rl"
    / "src"
    / "mjlab_microduck"
    / "robot"
    / "xgoduck"
    / "scene_walk.xml"
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--viewer", action="store_true", help="Keep the official duck viewer open until closed")
    args = parser.parse_args()

    if not SCENE.is_file():
        raise FileNotFoundError(f"Official XGO-Duck scene missing: {SCENE}")

    model = mujoco.MjModel.from_xml_path(str(SCENE))
    data = mujoco.MjData(model)
    stand_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_KEY, "STAND")
    assert stand_id >= 0, "Official STAND keyframe is missing"
    mujoco.mj_resetDataKeyframe(model, data, stand_id)
    mujoco.mj_forward(model, data)

    assert model.nu == 14, f"Expected 14 walking-scene actuators, got {model.nu}"
    assert model.njnt == 15, f"Expected 14 hinges and a freejoint, got {model.njnt}"
    assert mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_GEOM, "floor") >= 0

    initial_z = float(data.qpos[2])
    if args.viewer:
        from mujoco import viewer

        with viewer.launch_passive(model, data) as window:
            while window.is_running():
                mujoco.mj_step(model, data)
                window.sync()
                time.sleep(model.opt.timestep)
    else:
        for _ in range(500):
            mujoco.mj_step(model, data)

    assert data.time > 0
    assert all(float(x) == float(x) for x in data.qpos), "Non-finite qpos"

    print(f"PASS official XGO-Duck: joints={model.njnt}, actuators={model.nu}, timestep={model.opt.timestep}")
    print(f"STAND base z: {initial_z:.6f} -> {data.qpos[2]:.6f} m; time={data.time:.3f} s")
    print("Actuators: " + ", ".join(model.actuator(i).name for i in range(model.nu)))


if __name__ == "__main__":
    main()
