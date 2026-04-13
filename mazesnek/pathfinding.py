from __future__ import annotations

from collections import deque
from typing import Iterable

DIRECTIONS: list[tuple[str, tuple[int, int]]] = [
    ("up", (0, -1)),
    ("down", (0, 1)),
    ("left", (-1, 0)),
    ("right", (1, 0)),
]

PASSABLE_STRINGS = {".", " ", "S", "G", "P", "B", "0", ""}
WALL_STRINGS = {"#", "X", "1", "W"}


def is_passable(cell: object) -> bool:
    if isinstance(cell, bool):
        return not cell
    if isinstance(cell, (int, float)):
        return cell == 0
    if cell is None:
        return False
    text = str(cell).strip()
    if text in WALL_STRINGS:
        return False
    if text in PASSABLE_STRINGS:
        return True
    return text.lower() not in {"wall", "blocked", "false"}


def bfs_next_direction(
    maze: list[list[object]],
    start: tuple[int, int],
    goal: tuple[int, int],
) -> str | None:
    height = len(maze)
    width = len(maze[0]) if height else 0
    if width == 0:
        return None

    queue = deque([start])
    prev: dict[tuple[int, int], tuple[int, int] | None] = {start: None}

    while queue:
        x, y = queue.popleft()
        if (x, y) == goal:
            break
        for _, (dx, dy) in DIRECTIONS:
            nx, ny = x + dx, y + dy
            if not (0 <= nx < width and 0 <= ny < height):
                continue
            if (nx, ny) in prev:
                continue
            if not is_passable(maze[ny][nx]):
                continue
            prev[(nx, ny)] = (x, y)
            queue.append((nx, ny))

    if goal not in prev:
        return None

    cur = goal
    while prev[cur] is not None and prev[cur] != start:
        cur = prev[cur]

    dx = cur[0] - start[0]
    dy = cur[1] - start[1]
    for name, (dir_dx, dir_dy) in DIRECTIONS:
        if (dx, dy) == (dir_dx, dir_dy):
            return name
    return None
