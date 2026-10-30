"""Local CPU language model with an allowlisted robot action interface."""

import json
from pathlib import Path
import socket
import subprocess
import time
from urllib.error import URLError
from urllib.request import Request, urlopen

from .brain import Brain, BrainResult

ROOT = Path(__file__).resolve().parents[2]
MODEL_PATH = ROOT / "assets" / "models" / "Qwen3-1.7B-Q8_0.gguf"
SERVER_PATH = ROOT / "tools" / "llama.cpp" / "llama-server.exe"
SYSTEM_PROMPT = """You are MicroDuck, a virtual duck robot in MuJoCo. Speak Russian.
Return exactly one JSON object with keys action and reply. Reply must be a short
Russian sentence. Allowed actions: chat, stand, walk_forward, stop, reset, state,
head_left, head_right, head_center, unsupported.
Use state ONLY when the user asks for robot position, coordinates or status.
Use chat for greetings, identity, explanations and general conversation.
Choose movement only when clearly asked to move. The robot cannot see the user
or know where the user is. Backward walking and body turning are unsupported.
Never claim to have physical sensors or abilities outside the listed actions.
Examples:
User: Как тебя зовут?
Output: {"action":"chat","reply":"Меня зовут MicroDuck. Я виртуальная утка."}
User: Покажи координаты.
Output: {"action":"state","reply":"Показываю координаты."}
User: Посмотри в левую сторону.
Output: {"action":"head_left","reply":"Поворачиваю голову влево."}
User: Подойди ко мне.
Output: {"action":"chat","reply":"Я не вижу, где вы находитесь. Могу идти вперёд по команде."}
/no_think"""


class LocalModel:
    """Start llama.cpp on loopback and own its process."""

    def __init__(self, model_path=MODEL_PATH, server_path=SERVER_PATH):
        self.model_path = Path(model_path)
        self.server_path = Path(server_path)
        self.process = None
        self.base_url = None

    def start(self, timeout=90):
        if not self.model_path.is_file():
            raise FileNotFoundError(f"Model missing: {self.model_path}")
        if not self.server_path.is_file():
            raise FileNotFoundError(f"Server missing: {self.server_path}")
        with socket.socket() as probe:
            probe.bind(("127.0.0.1", 0))
            port = probe.getsockname()[1]
        self.base_url = f"http://127.0.0.1:{port}"
        self.process = subprocess.Popen(
            [str(self.server_path), "--model", str(self.model_path),
             "--host", "127.0.0.1", "--port", str(port),
             "--ctx-size", "2048", "--threads", "6", "--n-gpu-layers", "0"],
            cwd=str(self.server_path.parent), stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if self.process.poll() is not None:
                raise RuntimeError(f"llama.cpp exited: {self.process.returncode}")
            try:
                with urlopen(f"{self.base_url}/health", timeout=2) as response:
                    if response.status == 200:
                        return
            except (URLError, TimeoutError):
                pass
            time.sleep(0.25)
        self.close()
        raise TimeoutError("Local model startup timed out")

    def complete(self, messages):
        if self.base_url is None:
            raise RuntimeError("Local model is not running")
        body = json.dumps({
            "model": self.model_path.stem, "messages": messages,
            "temperature": 0.1, "max_tokens": 180,
            "response_format": {"type": "json_object"},
        }).encode("utf-8")
        request = Request(f"{self.base_url}/v1/chat/completions", data=body,
                          headers={"Content-Type": "application/json"})
        with urlopen(request, timeout=90) as response:
            result = json.load(response)
        return result["choices"][0]["message"]["content"]

    def close(self):
        if self.process is not None:
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait(timeout=5)
            self.process = None
        self.base_url = None


class AICommandBrain:
    """Use language understanding; run only actions implemented by Brain."""

    ACTION_COMMANDS = {
        "stand": "встань", "walk_forward": "иди вперед",
        "stop": "остановись", "reset": "сброс",
        "state": "покажи состояние",
        "head_left": "поверни голову влево",
        "head_right": "поверни голову вправо",
        "head_center": "поверни голову в центр",
    }

    def __init__(self, deterministic: Brain, model: LocalModel):
        self.deterministic = deterministic
        self.model = model
        self.history = []

    def handle(self, text: str) -> BrainResult:
        known = self.deterministic.handle(text)
        if known.accepted or known.action == "locomotion":
            return known
        try:
            messages = [{"role": "system", "content": SYSTEM_PROMPT}]
            messages.extend(self.history[-6:])
            messages.append({"role": "user", "content": text})
            decision = json.loads(self.model.complete(messages))
            action = decision.get("action")
            reply = str(decision.get("reply", "")).strip()[:300]
            self.history.extend([
                {"role": "user", "content": text},
                {"role": "assistant", "content": json.dumps(decision, ensure_ascii=False)},
            ])
            self.history = self.history[-6:]
            if action in self.ACTION_COMMANDS:
                return self.deterministic.handle(self.ACTION_COMMANDS[action])
            if action == "unsupported":
                return BrainResult("unsupported", False, "Не могу выполнить эту команду. Доступны ходьба вперёд и поворот головы.")
            if action == "chat":
                return BrainResult("chat", True, reply or "Уточните, пожалуйста, что вы хотите.")
            return BrainResult("unknown", False, "Я не уверена, что поняла. Уточните команду.")
        except (ValueError, KeyError, TypeError, AttributeError, URLError, TimeoutError) as exc:
            return BrainResult("model_error", False, f"Ошибка локальной модели: {exc}")
