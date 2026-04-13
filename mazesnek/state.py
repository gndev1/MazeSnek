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
    position: tuple[int, int]
    goal: tuple[int, int]
    actions: dict[str, dict[str, Any]]
    raw_payload: dict[str, Any]


def _parse_xy(value: Any, label: str) -> tuple[int, int]:
    if isinstance(value, dict):
        if "x" in value and "y" in value:
            return int(value["x"]), int(value["y"])

    if isinstance(value, (list, tuple)) and len(value) >= 2:
        return int(value[0]), int(value[1])

    raise ValueError(f"{label} was missing or invalid")


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

    run_id = int(payload.get("run_id", 0))
    position = _parse_xy(payload.get("position"), "position")
    goal = _parse_xy(payload.get("goal"), "goal")
    actions = _normalize_actions(payload.get("actions"))

    return ParsedState(
        run_id=run_id,
        position=position,
        goal=goal,
        actions=actions,
        raw_payload=payload,
    )


def apply_direction(position: tuple[int, int], direction: str) -> tuple[int, int]:
    dx, dy = _DIRECTION_VECTORS[direction]
    return (position[0] + dx, position[1] + dy)


def choose_direction(
    state: ParsedState,
    visited: dict[tuple[int, int], int] | None = None,
    last_direction: str | None = None,
) -> str:
    traversable = [
        direction
        for direction, info in state.actions.items()
        if info.get("traversable", False)
    ]

    if not traversable:
        raise RuntimeError("No traversable directions were available")

    visited = visited or {}

    px, py = state.position
    gx, gy = state.goal

    def score(direction: str) -> tuple[int, int, int, int]:
        nx, ny = apply_direction((px, py), direction)
        visit_count = visited.get((nx, ny), 0)
        manhattan = abs(gx - nx) + abs(gy - ny)

        reverse_penalty = 0
        if last_direction and _OPPOSITE_DIRECTION.get(last_direction) == direction:
            reverse_penalty = 1

        tie_break = ("up", "right", "down", "left").index(direction)

        return (visit_count, reverse_penalty, manhattan, tie_break)

    traversable.sort(key=score)
    return traversable[0]