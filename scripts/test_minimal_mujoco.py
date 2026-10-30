"""Verify MuJoCo gravity, floor contact, and fixed-step dynamics."""

import argparse
import time

import mujoco


MODEL = """
<mujoco model="gravity_check">
  <option timestep="0.002" gravity="0 0 -9.81"/>
  <worldbody>
    <geom name="floor" type="plane" size="2 2 0.1"/>
    <body name="ball" pos="0 0 1">
      <freejoint/>
      <geom type="sphere" size="0.05" mass="0.1"/>
    </body>
  </worldbody>
</mujoco>
"""


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--viewer", action="store_true", help="Open a short MuJoCo viewer session")
    args = parser.parse_args()

    model = mujoco.MjModel.from_xml_string(MODEL)
    data = mujoco.MjData(model)
    start_z = float(data.qpos[2])
    first_contact = None

    if args.viewer:
        from mujoco import viewer

        with viewer.launch_passive(model, data) as viewer:
            for step in range(1000):
                mujoco.mj_step(model, data)
                if data.ncon and first_contact is None:
                    first_contact = step
                viewer.sync()
                time.sleep(model.opt.timestep)
    else:
        for step in range(1000):
            mujoco.mj_step(model, data)
            if data.ncon and first_contact is None:
                first_contact = step

    assert model.opt.timestep == 0.002
    assert start_z > float(data.qpos[2])
    assert first_contact is not None, "The ball never contacted the floor"
    assert 0.04 < float(data.qpos[2]) < 0.07, "The ball did not settle at its radius"
    print(
        f"PASS gravity/floor: z {start_z:.3f} -> {data.qpos[2]:.3f} m, "
        f"first contact at step {first_contact}, sim time {data.time:.3f} s"
    )


if __name__ == "__main__":
    main()
