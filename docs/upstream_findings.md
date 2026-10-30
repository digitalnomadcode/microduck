# Verified upstream sources

Checked 2026-10-30. The local shallow clones in vendor/ are inspection copies and are excluded from this project's Git index.

| Repository | Role | Findings |
| --- | --- | --- |
| [pollen-robotics/microduck](https://github.com/pollen-robotics/microduck) | Original robot runtime and hardware project | Apache-2.0; its robot and policy conventions are not interchangeable with XGO-Duck geometry or Feetech motors. |
| [pollen-robotics/microduck_rl](https://github.com/pollen-robotics/microduck_rl) | Original simulation and training | Apache-2.0; mjlab/MuJoCo Warp training targets CUDA. |
| [LuwuDynamics/xgoduck_hardware](https://github.com/LuwuDynamics/xgoduck_hardware) | Intended physical build | Fifteen Feetech 1910 servos, UNO Q, expansion board, QMI8658A IMU, printable parts. See [LICENSING.md](https://github.com/LuwuDynamics/xgoduck_hardware/blob/master/LICENSING.md): no finalized top-level license for all material. |
| [LuwuDynamics/xgoduck_runtime_arduino](https://github.com/LuwuDynamics/xgoduck_runtime_arduino) | Board runtime and browser UI | Local clone at 8837d5a3bc7cf3746f6da2b55c7b9191026b9838. Contains five ONNX policies under python/. No top-level LICENSE file was present in this revision. |
| [LuwuDynamics/xgoduck_rl](https://github.com/LuwuDynamics/xgoduck_rl) | Actual XGO-Duck simulation model | Local clone at fa621fc77ad9a05d69da13270e86118bdd3603fe. Apache-2.0. scene_walk.xml includes robot_walk.xml and STL assets. MJCF has a free base, 14 hinge joints and position actuators, floor collision, and STAND keyframe. The URDF and conversion script are also present. |

The XGO-Duck training README requires CUDA and Python 3.12 for training. This project directly loads its MJCF with MuJoCo 3.17.0 on Python 3.15 and does not install mjlab. The official runtime ships xgoduck_walk.onnx, xgoduck_roller.onnx, xgoduck_getup.onnx, xgoduck_pick.onnx, and xgoduck_roulade.onnx. Its policy loader selects ONNX Runtime CPUExecutionProvider and checks a 61-element observation and 14-element action. Those dimensions alone do not prove compatibility with a simulator controller.

## Runtime request and authentication boundary

[python/main.py](https://github.com/LuwuDynamics/xgoduck_runtime_arduino/blob/master/python/main.py) creates an Arduino WebUI on port 9527 and exposes status, mode, motion, filter, calibration, and servo routes. [assets/app.js](https://github.com/LuwuDynamics/xgoduck_runtime_arduino/blob/master/assets/app.js) sends same-origin JSON fetch requests and polls status. The controller validates command bounds and mode, runs the local policy, and sends encoded commands through Arduino Bridge to the sketch.

This revision has no application-level login, password check, bearer-token check, API key, or cookie/session authentication in its published code. The word "session" in policy.py is an ONNX inference session. ONNX files are local model assets, not credentials. The README directs users to an HTTP URL at http://<board-ip>:9527. The repository does not document transport encryption or a per-user token. Whether Arduino App Lab or a separate network layer adds access control is outside this repository and has not been verified.
