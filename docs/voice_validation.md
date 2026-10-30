# Offline voice validation

Checked 2026-10-30. The project uses [Vosk](https://alphacephei.com/vosk/) 0.3.45 and sounddevice 0.5.6 on CPU with the official [vosk-model-small-ru-0.22](https://alphacephei.com/vosk/models), which the publisher lists as 45 MB and Apache-2.0. The model is stored under assets/speech and ignored by Git. No cloud endpoint or API token is used.

Verified locally:

- The Vosk Python package and Russian model load under project Python 3.12.16.
- sounddevice enumerates the Rapoo headset and Intel microphone array.
- The default MME input fails with PaErrorCode -9999, but automatic fallback opens the Rapoo WDM-KS microphone at device 31. The stream was opened for one second and closed without saving audio. The complete --voice application starts and exits without a microphone error.
- The user confirmed live transcription: `heard> иди вперёд` and `heard> остановись`. The earlier mandatory wake-word gate rejected these phrases because Vosk omitted `утка`.
- The wake word is now optional in simulation. Strict filtering remains available with `--require-wake-word`.
- An automated test passes the exact transcript `иди вперёд` through the command parser and verifies forward motion in MuJoCo.
- A simulated recognized phrase, `утка посмотри налево`, drives head yaw in MuJoCo.
- All 13 automated project tests pass.

The user retested `--voice` after the wake-word change and confirmed both responses, `Иду вперёд в симуляции` and `Остановила движение`, and visible robot movement in the MuJoCo window. This confirms live voice control for forward walking and stopping. Head movement by voice remains unverified. Device IDs may change between Windows sessions. `тут налево` and `травму` are Vosk recognition errors; the command parser safely rejects them.

Audio buffers remain in process memory and are discarded after recognition. The application starts microphone capture only with --voice. The default no-wake setting applies to simulation; any future physical robot needs an explicit safety design before voice commands may move motors.
