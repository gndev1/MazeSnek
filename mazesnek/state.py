
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
    local_position: tuple[int, int] | None = None
    local_goal: tuple[int, int] | None = None
    world_size: tuple[int, int] | None = None
    chunk: tuple[int, int] | None = None
    goal_visible: bool = True


def _parse_xy(value: Any, label: str) -> tuple[int, int]:
    if isinstance(value, dict) and "x" in value and "y" in value:
        return int(value["x"]), int(value["y"])

    if isinstance(value, (list, tuple)) and len(value) >= 2:
        return int(value[0]), int(value[1])

    raise ValueError(f"{label} was missing or invalid")


def _parse_optional_xy(value: Any) -> tuple[int, int] | None:
    try:
        return _parse_xy(value, "xy")
    except Exception:
        return None


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
                "answer_format": str(raw.get("answer_format", "single_integer") or "single_integer").strip(),
                "answer_count": int(raw.get("answer_count", 1) or 1),
                "challenge_type": str(raw.get("challenge_type", "text") or "text").strip(),
            }
        else:
            normalized[direction] = {
                "equation": str(raw).strip(),
                "answer": None,
                "traversable": True,
                "answer_format": "single_integer",
                "answer_count": 1,
                "challenge_type": "text",
            }

    if not normalized:
        raise ValueError("actions payload was empty")

    return normalized


def parse_state(payload: dict[str, Any]) -> ParsedState:
    if not isinstance(payload, dict):
        raise ValueError("State payload was not an object")

    local_position = _parse_optional_xy(payload.get("position"))
    local_goal = _parse_optional_xy(payload.get("goal"))
    global_position = _parse_optional_xy(payload.get("position_global")) or local_position
    global_goal = _parse_optional_xy(payload.get("goal_global")) or local_goal

    if global_position is None:
        raise ValueError("position was missing or invalid")
    if global_goal is None:
        raise ValueError("goal was missing or invalid")

    chunk_meta = payload.get("chunk_meta")
    chunk = None
    if isinstance(chunk_meta, dict) and "chunk_x" in chunk_meta and "chunk_y" in chunk_meta:
        chunk = (int(chunk_meta["chunk_x"]), int(chunk_meta["chunk_y"]))

    world_size = _parse_maze_size(payload.get("world_size"))
    maze_size = world_size or _parse_maze_size(payload.get("maze_size"))

    return ParsedState(
        run_id=int(payload.get("run_id", 0)),
        level=int(payload.get("level", 1)),
        turn=int(payload.get("turn", 0)),
        position=global_position,
        goal=global_goal,
        maze_size=maze_size,
        actions=_normalize_actions(payload.get("actions")),
        raw_payload=payload,
        local_position=local_position,
        local_goal=local_goal,
        world_size=world_size,
        chunk=chunk,
        goal_visible=bool(payload.get("goal_visible", True)),
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
