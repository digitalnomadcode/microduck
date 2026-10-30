# Local language model validation

Checked 2026-10-30 on Windows 11 with the project Python 3.12 environment and CPU inference. The model is the official [Qwen3-1.7B-Q8_0.gguf](https://huggingface.co/Qwen/Qwen3-1.7B-GGUF/tree/main) under Apache-2.0. The runtime is the [llama.cpp Windows x64 CPU release b12001](https://github.com/ggml-org/llama.cpp/releases/tag/b12001). Both are installed under C:\MicroDuck and excluded from Git. The model is 1,834,426,016 bytes. Its SHA-256 matches the publisher's LFS object ID: 061b54daade076b5d3362dac252678d17da8c68f07560be70818cace6590cb1a.

Verified:

- llama-server.exe starts on 127.0.0.1, loads Qwen on CPU, answers local HTTP requests, and terminates after the application exits.
- With --ai --command "Как тебя зовут?", the actual model replies: "Меня зовут MicroDuck. Я виртуальная утка."
- With --ai --command "Посмотри в левую сторону", the model selects head_left and MuJoCo reports head yaw 0.332 rad after 0.50 simulation seconds.
- With --ai --command "Сделай пару шагов прямо", the actual model chooses forward walking; MuJoCo reports x=0.021 m after 0.50 simulation seconds.
- A general question about gravity produces a Russian conversation response.
- Unsupported motion and an unclear transcription are rejected without moving the robot.
- The code validates model actions against an explicit list. 16 automated tests pass, including a stub-model paraphrase-to-action test and an unlisted-action rejection test.

Limitations:

- Qwen3-1.7B is a small language model. It can misclassify phrases or give incorrect conversational answers. Prompt examples corrected an observed case where it classified "Как тебя зовут?" as a telemetry request.
- The combined --ai --voice mode starts Qwen, the MuJoCo viewer and the Rapoo microphone, then exits cleanly. The user then confirmed that spoken questions receive an answer and a spoken request for forward steps moves the virtual duck. Direct voice commands without --ai were validated earlier.
- The AI only controls the simulator. The hardware backend remains non-operational.
