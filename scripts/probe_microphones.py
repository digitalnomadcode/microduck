"""Probe Windows input drivers without reading or saving microphone samples."""

import sounddevice as sd

candidates = [1, 2, 7, 8, 14, 15, 31]
rates = [16000, 44100, 48000]


def discard_audio(indata, frames, time_info, status) -> None:
    pass


for device in candidates:
    info = sd.query_devices(device)
    host = sd.query_hostapis(info["hostapi"])["name"]
    for rate in rates:
        try:
            with sd.RawInputStream(
                device=device, samplerate=rate, channels=1, dtype="int16",
                blocksize=8000, callback=discard_audio
            ):
                print(f"OK device={device} host={host} rate={rate} name={info['name']}")
                break
        except Exception as exc:
            print(f"FAIL device={device} host={host} rate={rate}: {str(exc).splitlines()[0]}")
