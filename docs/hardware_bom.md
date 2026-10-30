# Physical XGO-Duck build inventory

Checked 2026-10-30 against [LuwuDynamics/xgoduck_hardware](https://github.com/LuwuDynamics/xgoduck_hardware/tree/e62467ac8aa7ccac763555c61a554d9c32de5f35) at commit `e62467ac8aa7ccac763555c61a554d9c32de5f35`. This is a planning list for the standard walking robot; nothing has been purchased or physically validated.

## Parts for one standard walking robot

| Item | Planning quantity | Specification and check |
| --- | ---: | --- |
| Arduino UNO Q | 1 | Official build accepts 2 GB or 4 GB variant. Record the exact SKU. |
| Assembled XGO-Duck expansion board | 1 | Match the UNO Q and current V1.1 board revision. The board includes the QMI8658A IMU; do not buy a second IMU for the reference build. |
| Feetech 1910 serial servos | 15 | Confirm the HD-1910-C001 / HD1910M variant and AMP2.0-3P TTL bus connector. Ordinary PWM servos are not substitutes. |
| AMP 3-pin servo cables | 15 | Verify they are included with the servos or kit. |
| 18650 battery pack labelled 8.4 V | 1 | Current root BOM specifies XH2.54 connector, capacity >3,500 mAh and discharge rating >3C. Confirm actual cell configuration, pack dimensions, connector polarity and board compatibility before buying or connecting. |
| 8.4 V Li-ion charger | 1 | DC5521 (5.5 x 2.1 mm) plug in the official BOM. Match it to the verified pack. |
| M2 x 6 countersunk, flat-end self-tapping screws | 200 | Base walking build. The official 204 purchasing total includes 4 optional roller screws. |
| M2.3 x 8 flat-top round-head, flat-end self-tapping screws | 6 | Do not replace with the servo output-shaft M2.5 x 6 screw. |
| M3 x 16 round-head machine screws | 4 | Confirm head and drive against the assembly guide. |
| 10 x 15 x 3 mm bearings | 2 or 3 | The current root BOM says 2 for the base robot; the current hardware README says 3. Resolve this discrepancy against the assembly PDF or maintainer before ordering. |
| 16 x 22 x 4 mm bearings | 11 | Verify the supplier's actual dimensions. |

Sources: [robot BOM](https://github.com/LuwuDynamics/xgoduck_hardware/blob/e62467ac8aa7ccac763555c61a554d9c32de5f35/BOM.md), [hardware README](https://github.com/LuwuDynamics/xgoduck_hardware/blob/e62467ac8aa7ccac763555c61a554d9c32de5f35/readme.md), and [component details](https://github.com/LuwuDynamics/xgoduck_hardware/blob/e62467ac8aa7ccac763555c61a554d9c32de5f35/docs/BOM.md). The detailed component notes still quote an older >2,500 mAh battery threshold; this list uses the current root BOM's >3,500 mAh threshold. The BOM's board-level PCBA components are needed only when manufacturing a board; they are already part of a finished expansion board.

The official electronics kit is described as containing the BOM items other than UNO Q, but verify its actual contents, battery/charger match and V1.1 board revision before ordering. A separate board-store battery option has not been matched to the BOM pack.

## 3D printing

The current [structure directory](https://github.com/LuwuDynamics/xgoduck_hardware/tree/e62467ac8aa7ccac763555c61a554d9c32de5f35/structure) contains 27 base STL files. Their filename prefixes imply 35 planned printed pieces: `2x_` means two copies; unprefixed files mean one for planning. The [official printing inventory](https://github.com/LuwuDynamics/xgoduck_hardware/blob/e62467ac8aa7ccac763555c61a554d9c32de5f35/docs/PRINTING.md) lists the body, legs, feet, neck, head, mouth and shells. Keep left and right parts distinct.

The actual file `2x_hip_yaw2rol.STL` has a `2x_` prefix, while the printing inventory names `hip_yaw2rol.STL` without it. This is a source discrepancy. Check the required quantity in the [assembly guide](https://github.com/LuwuDynamics/xgoduck_hardware/blob/e62467ac8aa7ccac763555c61a554d9c32de5f35/Assembly_Guide.pdf) before printing the full set.

Use a rigid material for structural test prints and TPU for files explicitly ending in `_tpu.stl` (two foot bottoms and two mouth pieces by filename count). No complete validated print profile, TPU hardness, filament mass or print duration is published. Print one servo mount and one bearing seat first; verify fit, cable clearance, and part orientation before a full batch. If the printer cannot handle TPU, outsource those pieces rather than substituting rigid plastic without a fit test.

Optional roller skates add three STL files and ten printed pieces: `2x_tire_support.STL` x2, `4x_tire.STL` x4 and `4x_tire_axis.STL` x4. They also add 4 M2 x 6 screws and 8 bearings sized 10 x 15 x 3 mm. The bearing discrepancy above still needs resolution.

## Tools and preparation

Have a suitable USB data cable for UNO Q, screwdrivers matching the actual fastener drives, a multimeter, servo ID labels, a stable robot support, and material-compatible adhesive for the assembly step shown in the guide. These are workshop items, not quantified BOM entries. Check whether the servo kit includes output-shaft M2.5 x 6 screws, which are shown in the assembly guide but are distinct from the six M2.3 x 8 fasteners.

Before assembly, install the [official runtime](https://github.com/LuwuDynamics/xgoduck_runtime_arduino), configure one servo at a time, assign IDs 10–14, 20–24 and 30–34, and label them. Follow the illustrated assembly guide for shaft preparation and cable routing. Before power-up, verify the battery polarity and power limits on the actual board revision. V1.1 board files are under [PCBA](https://github.com/LuwuDynamics/xgoduck_hardware/blob/e62467ac8aa7ccac763555c61a554d9c32de5f35/PCBA/README.md); archived wiring notes for older boards do not automatically apply to V1.1.

## Software boundary

The official UNO Q runtime provides the physical servo and IMU loop. Our current Python Qwen/Vosk brain and MuJoCo control run on the Windows PC. Connecting that brain to the real robot needs a separately designed network/hardware adapter and safety tests. A microphone, speaker and standalone speech hardware are not part of the official robot BOM; choose them only after deciding whether speech stays on the PC or moves onto the robot. No commands from this project currently drive physical motors.

The hardware repository [does not provide a finalized project-wide reuse license](https://github.com/LuwuDynamics/xgoduck_hardware/blob/e62467ac8aa7ccac763555c61a554d9c32de5f35/LICENSING.md). Link to the official STL and board files; do not assume this repository's MIT license covers them.
