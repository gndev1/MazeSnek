from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class ParsedState:
    run_id: int
    maze: list[list[object]]
    position: tuple[int, int]
    goal: tuple[int, int]
    actions: dict[str, str]
    raw: dict[str, Any]


class StateParseError(RuntimeError):
    pass


def _first_present(data: dict[str, Any], keys: list[str]) -> Any:
    for key in keys:
        if key in data:
            return data[key]
    raise StateParseError(f"None of the expected keys were present: {keys}")



def _coerce_point(value: Any, label: str) -> tuple[int, int]:
    if isinstance(value, dict):
        if "x" in value and "y" in value:
            return int(value["x"]), int(value["y"])
        if "col" in value and "row" in value:
            return int(value["col"]), int(value["row"])

    if isinstance(value, (list, tuple)) and len(value) >= 2:
        return int(value[0]), int(value[1])

    raise StateParseError(f"Could not parse {label}: {value!r}")



def _normalize_maze(maze_value: Any) -> list[list[object]]:
    if not isinstance(maze_value, list) or not maze_value:
        raise StateParseError("Maze/grid payload was missing or empty")

    first_row = maze_value[0]
    if isinstance(first_row, str):
        return [list(str(row)) for row in maze_value]

    if isinstance(first_row, list):
        return [list(row) for row in maze_value]

    raise StateParseError(f"Unsupported maze format: {type(first_row).__name__}")



def _normalize_actions(actions_value: Any) -> dict[str, str]:
    if not isinstance(actions_value, dict):
        raise StateParseError("Actions payload was not a dict")

    normalized: dict[str, str] = {}
    aliases = {
        "north": "up",
        "south": "down",
        "west": "left",
        "east": "right",
    }

    for key, value in actions_value.items():
        name = aliases.get(str(key).lower(), str(key).lower())
        if name in {"up", "down", "left", "right"}:
            normalized[name] = str(value)

    if not normalized:
        raise StateParseError("No usable direction equations were found")

    return normalized



def parse_state(payload: dict[str, Any]) -> ParsedState:
    if not isinstance(payload, dict):
        raise StateParseError("State payload was not a JSON object")

    run_value = payload.get("run_id")
    if run_value is None and isinstance(payload.get("run"), dict):
        run_value = payload["run"].get("id")
    if run_value is None and isinstance(payload.get("current_run"), dict):
        run_value = payload["current_run"].get("id")
    if run_value is None:
        raise StateParseError("Run id was not present in state payload")

    maze_value = None
    for key in ["maze", "grid", "maze_data", "cells"]:
        if key in payload:
            maze_value = payload[key]
            break
    if maze_value is None and isinstance(payload.get("state"), dict):
        maze_value = _first_present(payload["state"], ["maze", "grid", "maze_data", "cells"])
    maze = _normalize_maze(maze_value)

    position_value = None
    for key in ["position", "pos", "player_position", "bot_position"]:
        if key in payload:
            position_value = payload[key]
            break
    if position_value is None and "x" in payload and "y" in payload:
        position_value = {"x": payload["x"], "y": payload["y"]}
    if position_value is None and isinstance(payload.get("player"), dict):
        position_value = payload["player"]
    position = _coerce_point(position_value, "position")

    goal_value = None
    for key in ["goal", "goal_position", "target", "exit"]:
        if key in payload:
            goal_value = payload[key]
            break
    if goal_value is None and isinstance(payload.get("state"), dict):
        for key in ["goal", "goal_position", "target", "exit"]:
            if key in payload["state"]:
                goal_value = payload["state"][key]
                break
    goal = _coerce_point(goal_value, "goal")

    actions_value = None
    for key in ["actions", "moves", "options", "equations"]:
        if key in payload:
            actions_value = payload[key]
            break
    if actions_value is None and isinstance(payload.get("state"), dict):
        actions_value = _first_present(payload["state"], ["actions", "moves", "options", "equations"])
    actions = _normalize_actions(actions_value)

    return ParsedState(
        run_id=int(run_value),
        maze=maze,
        position=position,
        goal=goal,
        actions=actions,
        raw=payload,
    )
