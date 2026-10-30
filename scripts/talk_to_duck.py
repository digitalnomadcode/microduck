"""Talk to the simulated XGO-Duck through text or offline Russian speech."""

import argparse
from pathlib import Path
from queue import Empty, Queue
import sys
import threading
import time

sys.stdin.reconfigure(encoding="utf-8")
sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from microduck import Brain, MicroDuck  # noqa: E402


def report_state(robot: MicroDuck) -> None:
    state = robot.get_state()
    x, y, z = state.position
    print(f"Position: ({x:.3f}, {y:.3f}, {z:.3f}) m | simulation: {state.simulation_time:.2f} s")
    print(f"Head yaw: {state.joint_positions['head_yaw']:.3f} rad")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--command", help="Execute one text command and exit")
    parser.add_argument("--viewer", action="store_true", help="Keep the MuJoCo viewer open")
    parser.add_argument("--voice", action="store_true", help="Listen for offline Russian speech")
    parser.add_argument("--ai", action="store_true", help="Use the local CPU language model")
    parser.add_argument("--require-wake-word", action="store_true", help="Require утка before voice commands")
    parser.add_argument("--mic", help="Input device index or name substring")
    parser.add_argument("--list-mics", action="store_true", help="List available microphone devices")
    args = parser.parse_args()

    if args.list_mics:
        from microduck.voice import VoiceListener

        for index, name in VoiceListener.input_devices():
            print(f"{index}: {name}")
        return
    if args.command is not None and args.voice:
        parser.error("--command and --voice cannot be used together")
    if args.voice:
        args.viewer = True

    robot = MicroDuck(backend="simulation")
    robot.connect()
    brain = Brain(robot)
    local_model = None
    print("XGO-Duck ready. Type «помощь» for commands.")

    voice_stop = threading.Event()
    voice_thread = None
    try:
        if args.ai:
            from microduck.local_brain import AICommandBrain, LocalModel
            local_model = LocalModel()
            local_model.start()
            brain = AICommandBrain(brain, local_model)
            print("Local Qwen model ready on CPU.")
        if args.command is not None:
            result = brain.handle(args.command)
            robot.step(250)
            print(result.message)
            report_state(robot)
            if not result.accepted:
                raise SystemExit(2)
        elif args.viewer:
            from mujoco import viewer

            commands: Queue[tuple[str, str]] = Queue()

            def read_commands() -> None:
                while True:
                    try:
                        commands.put(("text", input("duck> ")))
                    except EOFError:
                        commands.put(("text", "выход"))
                        return

            threading.Thread(target=read_commands, daemon=True).start()

            if args.voice:
                from microduck.voice import VoiceListener

                device = int(args.mic) if args.mic and args.mic.isdecimal() else args.mic
                listener = VoiceListener(device=device)

                def listen() -> None:
                    try:
                        listener.listen(lambda phrase: commands.put(("voice", phrase)), voice_stop)
                    except Exception as exc:
                        commands.put(("error", str(exc)))

                voice_thread = threading.Thread(target=listen, daemon=True)
                voice_thread.start()
                print("Microphone on. Say «иди вперед» or «остановись».")

            with viewer.launch_passive(robot.model, robot.data) as window:
                while window.is_running():
                    try:
                        source, command = commands.get_nowait()
                    except Empty:
                        source, command = "", ""
                    if source == "error":
                        print(f"Microphone error: {command}")
                    elif command:
                        if source == "voice":
                            from microduck.voice import command_from_transcript

                            print(f"heard> {command}")
                            command = command_from_transcript(command, args.require_wake_word)
                            if command is None:
                                print("Wake word «утка» was not detected; no action.")
                        if command is not None:
                            result = brain.handle(command)
                            print(result.message)
                            if result.action == "exit":
                                break
                    robot.step()
                    window.sync()
                    time.sleep(robot.model.opt.timestep)
        else:
            while True:
                try:
                    command = input("duck> ")
                except EOFError:
                    break
                result = brain.handle(command)
                print(result.message)
                if result.action == "exit":
                    break
                robot.step(250)
                report_state(robot)
    finally:
        voice_stop.set()
        if voice_thread is not None:
            voice_thread.join(timeout=2)
        if local_model is not None:
            local_model.close()
        robot.disconnect()


if __name__ == "__main__":
    main()
