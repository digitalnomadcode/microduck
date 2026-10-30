# CPU walking-policy validation

Checked 2026-10-30. The simulation uses [xgoduck_rl](https://github.com/LuwuDynamics/xgoduck_rl) scene_walk.xml and [xgoduck_runtime_arduino](https://github.com/LuwuDynamics/xgoduck_runtime_arduino) xgoduck_walk.onnx. The upstream clones are kept in vendor/ and excluded from this project's Git index.

ONNX Runtime 1.22.1 runs with CPUExecutionProvider under project-local Python 3.12.16. The policy metadata declares 61 input values, 14 outputs, joint names matching the MJCF actuator order, and a walking home pose with 24-degree hip and ankle bends. The MJCF STAND keyframe uses 22 degrees. The replay initializes the 24-degree walking pose and the matching 0.139439 m base height from xgoduck_constants.py.

The observation is body angular velocity, projected gravity, joint positions relative to the policy home pose, joint velocities, previous action, twist command, four head-command zeros, and six body-command zeros. Inference runs at 50 Hz over 0.002 s physics steps; joint targets are clamped to MJCF limits. This reproduces the published policy interface for a simple flat-ground replay, not the complete training actuator dynamics or hardware behavior.

| Five-second command | Result |
| --- | --- |
| 0.0 m/s forward | 0.001 m x displacement, 0.5-degree maximum tilt |
| 0.2 m/s forward | 0.423 m x displacement, 0.137 m minimum base height, 3.2-degree maximum tilt |
| -0.2 m/s backward | Approximately 0 m x displacement; not enabled |
| +0.5 rad/s yaw | +11.3-degree yaw; needs further validation |
| -0.5 rad/s yaw | -94.0-degree yaw; asymmetric, not enabled |

After five seconds of forward motion, a zero-speed command produced only 0.010 m additional x displacement over the next five seconds. The text-command viewer was also exercised with forward, stop, and exit commands. These checks justify enabling forward walking only. They do not establish robust locomotion across terrains, disturbances, or real hardware.
A two-second forward walk followed by a two-second head-yaw command kept the policy active, the base at 0.140 m, and head yaw at 0.281 rad. Head commands during walking are passed through the policy observation rather than replacing its balance targets.
