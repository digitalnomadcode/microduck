# MicroDuck

A Windows-first virtual XGO-Duck robot with MuJoCo physics, CPU walking policy, offline Russian speech, and a local language model. The robot model and walking policy come from the official XGO-Duck repositories. Physical motors are not connected.

## Quick start on Windows

Requirements: Windows 11, 64-bit Python 3.12 with the `py` launcher, Git for Windows, 16 GB RAM, and several GB of free disk space. No CUDA, WSL2, Docker, or training is required. Python 3.15 can remain installed alongside 3.12.

Open PowerShell:

```powershell
git clone https://github.com/digitalnomadcode/microduck.git
cd microduck
.\scripts\setup_windows.ps1
.\.venv312\Scripts\python.exe scripts\talk_to_duck.py --ai --voice
```

The setup script creates an isolated environment, installs Python dependencies, checks out pinned official XGO-Duck repositories, downloads the offline Vosk and Qwen models plus a Windows CPU llama.cpp build, verifies SHA-256 hashes, and runs the project tests. The Qwen file is about 1.83 GB, so the initial download may take several minutes. Run the setup script again if a download is interrupted; model downloads resume, and an incomplete upstream Git clone restarts.

Speak a phrase, then pause so speech recognition can finalize it. Examples: `иди вперёд`, `остановись`, `посмотри налево`, `как тебя зовут?`, and `сделай пару шагов прямо`. The console prints `heard>` and the response. The MuJoCo window shows the robot. Text commands also work at the `duck>` prompt. Type `выход` to close the app.

If PowerShell blocks scripts, open a PowerShell session that permits local project scripts according to your Windows policy, then rerun the setup command. Do not change system-wide execution policy just for this project.

## Other run modes

```powershell
.\.venv312\Scripts\python.exe scripts\talk_to_duck.py --viewer
.\.venv312\Scripts\python.exe scripts\talk_to_duck.py --voice
.\.venv312\Scripts\python.exe scripts\talk_to_duck.py --ai --command "Как тебя зовут?"
.\.venv312\Scripts\python.exe scripts\talk_to_duck.py --list-mics
```

`--viewer` uses the direct text command parser; `--voice` adds offline Vosk recognition; `--ai` adds local Qwen understanding for phrases outside the direct parser. For strict voice activation, add `--require-wake-word` and begin commands with `утка`. The default omits this requirement because Vosk sometimes misses the wake word. If the default microphone fails, use `--voice --mic <index>` with an input index shown by `--list-mics`.

## What works

- The official articulated XGO-Duck model loads in MuJoCo with gravity, floor contact, joint limits, and a STAND keyframe.
- The official ONNX walking policy runs on CPU and has been validated for forward motion and stopping at 0.2 m/s command speed.
- Head yaw moves left, right, and center. The robot exposes joint and position telemetry.
- Russian offline voice commands and the local Qwen model were confirmed in a live user session: the robot answered and walked from speech.
- The public `MicroDuck` Python API keeps simulation and future hardware behind separate backends.

Backward walking and body turns are disabled because their policy replay did not validate stable movement. Qwen can misunderstand speech or produce inaccurate conversational answers. Its outputs can select only the actions implemented by the simulator. The hardware adapter is a non-operational placeholder; real robot use needs servo mapping, calibration, limits, emergency stop, watchdog, battery checks, and controller adaptation.

## Verify

```powershell
.\.venv312\Scripts\python.exe scripts\check_environment.py
.\.venv312\Scripts\python.exe scripts\test_minimal_mujoco.py
.\.venv312\Scripts\python.exe scripts\check_xgoduck_model.py
.\.venv312\Scripts\python.exe -m unittest discover -s tests -v
.\.venv312\Scripts\python.exe scripts\evaluate_walk_policy.py --seconds 5 --speed 0.2
```

The setup script already runs the automated unit tests. The viewer and microphone require a Windows desktop session with working graphics and audio input.

## Physical build planning

For the 3D-printed robot, use the [verified hardware inventory](docs/hardware_bom.md) before purchasing. It separates the standard walking build from optional roller parts and records unresolved source differences for bearings, printed copies and battery details. The current project does not command real motors.
## Source and architecture

- Official XGO-Duck model: [LuwuDynamics/xgoduck_rl](https://github.com/LuwuDynamics/xgoduck_rl), pinned at `fa621fc77ad9a05d69da13270e86118bdd3603fe`.
- Official runtime and ONNX policy: [LuwuDynamics/xgoduck_runtime_arduino](https://github.com/LuwuDynamics/xgoduck_runtime_arduino), pinned at `8837d5a3bc7cf3746f6da2b55c7b9191026b9838`.
- Local language model: [Qwen3-1.7B-GGUF](https://huggingface.co/Qwen/Qwen3-1.7B-GGUF), Apache-2.0.
- Local inference runtime: [llama.cpp release b12001](https://github.com/ggml-org/llama.cpp/releases/tag/b12001).
- Speech model: [vosk-model-small-ru-0.22](https://alphacephei.com/vosk/models), Apache-2.0.

Third-party repositories and model files are downloaded by the setup script and excluded from this Git repository. Their original licenses apply. No cloud API key is needed; the llama.cpp server binds to `127.0.0.1` and stops with the app. Microphone audio is processed locally in memory and is not saved by this app.

`src/microduck/brain.py` parses direct commands; `local_brain.py` runs the local model and validates its action choices; `voice.py` transcribes speech; `robot.py` is the public API; `simulation.py` owns MuJoCo state; `locomotion.py` runs ONNX policy inference; `state.py` defines telemetry.

See [upstream findings](docs/upstream_findings.md), [walking policy validation](docs/policy_validation.md), [voice validation](docs/voice_validation.md), and [local model validation](docs/local_model_validation.md).

## License

The original MicroDuck project code in this repository is licensed under the MIT License; see [LICENSE](LICENSE). Third-party sources and model weights retain their own licenses.
