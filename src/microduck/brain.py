"""Conservative Russian text command parser and action dispatcher."""

from dataclasses import dataclass
import re

from .robot import MicroDuck, UnsupportedActionError


@dataclass(frozen=True)
class BrainResult:
    action: str
    accepted: bool
    message: str


class Brain:
    def __init__(self, robot: MicroDuck) -> None:
        self.robot = robot
        self.last_subject: str | None = None

    def handle(self, text: str) -> BrainResult:
        phrase = re.sub(r"[^\w\s]", " ", text.lower().replace("ё", "е")).strip()
        tokens = set(phrase.split())
        if not phrase:
            return BrainResult("unknown", False, "Скажите команду. Напишите «помощь» для списка.")

        if tokens & {"выход", "quit", "exit"}:
            return BrainResult("exit", True, "Завершаю сеанс.")
        if tokens & {"помощь", "help"} or "что умеешь" in phrase or "что ты умеешь" in phrase:
            return BrainResult(
                "help", True,
                "Доступно: встань, иди вперед, поверни голову влево/вправо/в центр, "
                "остановись, сброс, покажи состояние, выход. Назад и повороты корпуса "
                "пока не прошли проверку.",
            )
        if tokens & {"стоп", "stop", "хватит"} or "останов" in phrase:
            self.robot.stop()
            return BrainResult("stop", True, "Остановила движение.")
        if tokens & {"сброс", "сбрось", "reset"} or "начни заново" in phrase:
            self.robot.reset()
            self.last_subject = None
            return BrainResult("reset", True, "Симуляция сброшена в позу STAND.")
        if tokens & {"состояние", "статус", "координаты", "status"} or "где ты" in phrase:
            state = self.robot.get_state()
            x, y, z = state.position
            return BrainResult(
                "state", True,
                f"Время {state.simulation_time:.2f} с; положение "
                f"x={x:.3f}, y={y:.3f}, z={z:.3f} м; суставов {len(state.joint_positions)}.",
            )
        if tokens & {"встань", "стой", "stand"} or "стойка" in phrase:
            self.robot.stand()
            return BrainResult("stand", True, "Перешла в исходную позу STAND.")

        left = any(word in phrase for word in ("влев", "налев", "слева"))
        right = any(word in phrase for word in ("вправ", "направ", "справа"))
        center = bool(tokens & {"центр", "прямо", "ровно"})
        head = "голов" in phrase or "смотр" in phrase or (
            self.last_subject == "head" and "теперь" in tokens and (left or right or center)
        )
        if head:
            if sum((left, right, center)) != 1:
                return BrainResult("unknown", False, "Уточните направление головы: влево, вправо или в центр.")
            direction = "left" if left else "right" if right else "center"
            self.robot.move_head(direction)
            self.last_subject = "head"
            labels = {"left": "влево", "right": "вправо", "center": "в центр"}
            return BrainResult("head", True, f"Поворачиваю голову {labels[direction]}.")

        forward = "вперед" in phrase
        backward = "назад" in tokens
        motion = any(word in phrase for word in ("иди", "идти", "пойди", "пошли", "шагай", "двигайся", "двигай", "начни", "walk"))
        turn = "повер" in phrase or "развер" in phrase
        if (motion and (forward or backward)) or (turn and (left or right)):
            try:
                if forward:
                    self.robot.walk_forward()
                    self.last_subject = "body"
                    return BrainResult("walk_forward", True, "Иду вперёд в симуляции.")
                if backward:
                    self.robot.walk_backward()
                elif left:
                    self.robot.turn_left()
                else:
                    self.robot.turn_right()
            except UnsupportedActionError as exc:
                return BrainResult("locomotion", False, f"Поняла команду, но действие пока недоступно: {exc}")

        return BrainResult(
            "unknown", False,
            "Не уверена, что поняла команду. Напишите «помощь» для доступных действий.",
        )
