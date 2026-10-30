"""Offline Russian microphone transcription and optional wake-word parsing."""

import json
from pathlib import Path
from queue import Empty, Full, Queue
import re
from threading import Event
from typing import Callable


ROOT = Path(__file__).resolve().parents[2]
VOICE_MODEL = ROOT / "assets" / "speech" / "vosk-model-small-ru-0.22"


def extract_wake_command(transcript: str, wake_word: str = "утка") -> str | None:
    normalized = re.sub(r"[^\w\s]", " ", transcript.lower().replace("ё", "е"))
    words = normalized.split()
    if len(words) < 2 or words[0] != wake_word:
        return None
    return " ".join(words[1:])


def command_from_transcript(transcript: str, require_wake_word: bool = False) -> str | None:
    with_wake = extract_wake_command(transcript)
    if require_wake_word:
        return with_wake
    return with_wake or transcript.strip() or None


class VoiceListener:
    def __init__(self, model_path: Path = VOICE_MODEL, device: int | str | None = None) -> None:
        try:
            import sounddevice as sd
            from vosk import KaldiRecognizer, Model, SetLogLevel
        except ImportError as exc:
            raise RuntimeError("Voice dependencies are missing from the Python 3.12 environment") from exc
        self.sd = sd
        self.recognizer_type = KaldiRecognizer
        self.device = device
        model_path = Path(model_path)
        if not model_path.is_dir():
            raise FileNotFoundError(f"Russian Vosk model not found: {model_path}")
        SetLogLevel(-1)
        self.model = Model(str(model_path))

    @staticmethod
    def input_devices() -> list[tuple[int, str]]:
        import sounddevice as sd

        return [
            (index, f"{info['name']} [{sd.query_hostapis(info['hostapi'])['name']}]")
            for index, info in enumerate(sd.query_devices())
            if info["max_input_channels"] > 0
        ]

    def _candidate_devices(self) -> list[int | str]:
        if self.device is not None:
            return [self.device]
        devices = self.sd.query_devices()
        default_index = int(self.sd.default.device[0])
        default_name = devices[default_index]["name"].lower() if default_index >= 0 else ""
        brand = next(
            (token for token in re.findall(r"[a-z]+", default_name)
             if token not in {"microphone", "array", "input", "the"}),
            "",
        )
        candidates = [
            index for index, info in enumerate(devices)
            if info["max_input_channels"] > 0
            and "microphone" in info["name"].lower()
            and index != default_index
        ]
        host_rank = {"Windows WDM-KS": 0, "Windows WASAPI": 1,
                     "Windows DirectSound": 2, "MME": 3}
        candidates.sort(key=lambda index: (
            bool(brand) and brand not in devices[index]["name"].lower(),
            host_rank.get(self.sd.query_hostapis(devices[index]["hostapi"])["name"], 4),
            index,
        ))
        return ([default_index] if default_index >= 0 else []) + candidates

    def listen(self, on_transcript: Callable[[str], None], stop_event: Event) -> None:
        errors = []
        for candidate in self._candidate_devices():
            info = self.sd.query_devices(candidate, "input")
            sample_rate = int(info["default_samplerate"])
            chunks: Queue[bytes] = Queue(maxsize=32)

            def callback(indata, frames, time_info, status) -> None:
                try:
                    chunks.put_nowait(bytes(indata))
                except Full:
                    pass

            try:
                with self.sd.RawInputStream(
                    samplerate=sample_rate,
                    blocksize=8000,
                    device=candidate,
                    channels=1,
                    dtype="int16",
                    callback=callback,
                ):
                    print(f"Listening on microphone {candidate}: {info['name']}")
                    recognizer = self.recognizer_type(self.model, sample_rate)
                    while not stop_event.is_set():
                        try:
                            chunk = chunks.get(timeout=0.2)
                        except Empty:
                            continue
                        if recognizer.AcceptWaveform(chunk):
                            transcript = json.loads(recognizer.Result()).get("text", "").strip()
                            if transcript:
                                on_transcript(transcript)
                    return
            except self.sd.PortAudioError as exc:
                errors.append(f"{candidate}: {str(exc).splitlines()[0]}")
                if self.device is not None:
                    break
        raise RuntimeError("No microphone stream opened. " + " | ".join(errors))
