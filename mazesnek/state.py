from __future__ import annotations

from dataclasses import dataclass
from typing import Any


_DIRECTION_VECTORS: dict[str, tuple[int, int]] = {
    "up": (0, -1),
    "right": (1, 0),
    "down": (0, 1),
    "left": (-1, 0),
}

_OPPOSITE_DIRECTION: dict[str, str] = {
    "up": "down",
    "down": "up",
    "left": "right",
    "right": "left",
}


@dataclass
class ParsedState:
    run_id: int
    level: int
    turn: int
    position: tuple[int, int]
    goal: tuple[int, int]
    maze_size: tuple[int, int] | None
    actions: dict[str, dict[str, Any]]
    raw_payload: dict[str, Any]


def _parse_xy(value: Any, label: str) -> tuple[int, int]:
    if isinstance(value, dict) and "x" in value and "y" in value:
        return int(value["x"]), int(value["y"])

    if isinstance(value, (list, tuple)) and len(value) >= 2:
        return int(value[0]), int(value[1])

    raise ValueError(f"{label} was missing or invalid")


def _parse_maze_size(value: Any) -> tuple[int, int] | None:
    if isinstance(value, dict) and "width" in value and "height" in value:
        return int(value["width"]), int(value["height"])

    if isinstance(value, (list, tuple)) and len(value) >= 2:
        return int(value[0]), int(value[1])

    return None


def _normalize_actions(actions: Any) -> dict[str, dict[str, Any]]:
    if not isinstance(actions, dict):
        raise ValueError("actions payload was missing or invalid")

    normalized: dict[str, dict[str, Any]] = {}

    for direction in ("up", "right", "down", "left"):
        raw = actions.get(direction)
        if raw is None:
            continue

        if isinstance(raw, dict):
            normalized[direction] = {
                "equation": str(raw.get("equation", "")).strip(),
                "answer": raw.get("answer"),
                "traversable": bool(raw.get("traversable", False)),
            }
        else:
            normalized[direction] = {
                "equation": str(raw).strip(),
                "answer": None,
                "traversable": True,
            }

    if not normalized:
        raise ValueError("actions payload was empty")

    return normalized


def parse_state(payload: dict[str, Any]) -> ParsedState:
    if not isinstance(payload, dict):
        raise ValueError("State payload was not an object")

    return ParsedState(
        run_id=int(payload.get("run_id", 0)),
        level=int(payload.get("level", 1)),
        turn=int(payload.get("turn", 0)),
        position=_parse_xy(payload.get("position"), "position"),
        goal=_parse_xy(payload.get("goal"), "goal"),
        maze_size=_parse_maze_size(payload.get("maze_size")),
        actions=_normalize_actions(payload.get("actions")),
        raw_payload=payload,
    )


def apply_direction(position: tuple[int, int], direction: str) -> tuple[int, int]:
    dx, dy = _DIRECTION_VECTORS[direction]
    return (position[0] + dx, position[1] + dy)


def direction_between(a: tuple[int, int], b: tuple[int, int]) -> str:
    dx = b[0] - a[0]
    dy = b[1] - a[1]

    for direction, (vx, vy) in _DIRECTION_VECTORS.items():
        if (dx, dy) == (vx, vy):
            return direction

    raise ValueError(f"Positions are not adjacent: {a!r} -> {b!r}")


def opposite_direction(direction: str) -> str:
    return _OPPOSITE_DIRECTION[direction]


def cardinal_neighbors(position: tuple[int, int]) -> dict[str, tuple[int, int]]:
    return {
        direction: (position[0] + dx, position[1] + dy)
        for direction, (dx, dy) in _DIRECTION_VECTORS.items()
    }
