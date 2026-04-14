from __future__ import annotations

from collections import deque

from .memory import MazeMemory
from .state import ParsedState, direction_between, opposite_direction


def bfs_path(
    adjacency: dict[tuple[int, int], set[tuple[int, int]]],
    start: tuple[int, int],
    goal: tuple[int, int],
) -> list[tuple[int, int]] | None:
    if start == goal:
        return [start]

    queue = deque([start])
    prev: dict[tuple[int, int], tuple[int, int] | None] = {start: None}

    while queue:
        node = queue.popleft()
        for neighbor in adjacency.get(node, ()):
            if neighbor in prev:
                continue
            prev[neighbor] = node
            if neighbor == goal:
                queue.clear()
                break
            queue.append(neighbor)

    if goal not in prev:
        return None

    path: list[tuple[int, int]] = []
    cur: tuple[int, int] | None = goal
    while cur is not None:
        path.append(cur)
        cur = prev[cur]
    path.reverse()
    return path


def _path_first_direction(path: list[tuple[int, int]]) -> str | None:
    if len(path) < 2:
        return None
    return direction_between(path[0], path[1])


def _manhattan(a: tuple[int, int], b: tuple[int, int]) -> int:
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def _move_penalty(
    current: tuple[int, int],
    direction: str,
    move_penalties: dict[tuple[tuple[int, int], str], int],
) -> int:
    return move_penalties.get((current, direction), 0)


def _split_available_directions(
    current: tuple[int, int],
    available_now: set[str],
    move_penalties: dict[tuple[tuple[int, int], str], int],
) -> tuple[list[str], list[str]]:
    clean: list[str] = []
    failed: list[str] = []

    for direction in sorted(available_now):
        if _move_penalty(current, direction, move_penalties) > 0:
            failed.append(direction)
        else:
            clean.append(direction)

    return clean, failed


def choose_direction_from_memory(
    memory: MazeMemory,
    state: ParsedState,
    last_direction: str | None = None,
    move_penalties: dict[tuple[tuple[int, int], str], int] | None = None,
) -> str:
    current = state.position
    goal = state.goal
    available_now = {
        direction
        for direction, info in state.actions.items()
        if info.get("traversable", False)
    }

    if not available_now:
        raise RuntimeError("No traversable directions were available")

    if current == goal:
        raise RuntimeError("Already at the goal tile")

    move_penalties = move_penalties or {}
    clean_dirs, failed_dirs = _split_available_directions(current, available_now, move_penalties)
    preferred_now = set(clean_dirs) if clean_dirs else set(available_now)

    if goal in memory.known_open:
        path = bfs_path(memory.adjacency, current, goal)
        if path:
            direction = _path_first_direction(path)
            if direction and direction in preferred_now:
                return direction

    frontier_candidates: list[tuple[float, str, tuple[int, int]]] = []
    for frontier in memory.frontier_nodes():
        if frontier == current and memory.unknown_neighbor_count(frontier) == 0:
            continue

        path = bfs_path(memory.adjacency, current, frontier)
        if not path:
            continue

        first_direction = _path_first_direction(path)
        if first_direction is None:
            local_candidates: list[tuple[float, str]] = []
            for direction, info in state.actions.items():
                if not info.get("traversable", False):
                    continue
                if clean_dirs and direction not in preferred_now:
                    continue
                neighbor = next_pos(current, direction)
                score = _move_penalty(current, direction, move_penalties) * 25
                if neighbor not in memory.known_open:
                    local_candidates.append((score, direction))
            if local_candidates:
                local_candidates.sort(key=lambda item: (item[0], item[1]))
                return local_candidates[0][1]
            continue

        if first_direction not in preferred_now:
            continue

        visit_penalty = memory.visit_counts.get(frontier, 0) * 4
        dead_end_penalty = 20 if memory.degree(frontier) <= 1 and frontier != goal else 0
        reverse_penalty = 6 if last_direction and opposite_direction(last_direction) == first_direction else 0
        failed_move_penalty = _move_penalty(current, first_direction, move_penalties) * 25
        path_distance = len(path) - 1
        frontier_goal_distance = _manhattan(frontier, goal)

        score = (
            path_distance * 3
            + frontier_goal_distance
            + visit_penalty
            + dead_end_penalty
            + reverse_penalty
            + failed_move_penalty
        )
        frontier_candidates.append((score, first_direction, frontier))

    if frontier_candidates:
        frontier_candidates.sort(key=lambda item: (item[0], item[1], item[2][1], item[2][0]))
        return frontier_candidates[0][1]

    immediate_candidates: list[tuple[float, str]] = []
    for direction in preferred_now:
        neighbor = next_pos(current, direction)
        visit_penalty = memory.visit_counts.get(neighbor, 0) * 5
        reverse_penalty = 7 if last_direction and opposite_direction(last_direction) == direction else 0
        dead_end_penalty = 10 if memory.degree(neighbor) <= 1 and neighbor in memory.known_open and neighbor != goal else 0
        unknown_bonus = -3 if neighbor not in memory.known_open else 0
        failed_move_penalty = _move_penalty(current, direction, move_penalties) * 25
        goal_distance = _manhattan(neighbor, goal)
        score = goal_distance + visit_penalty + reverse_penalty + dead_end_penalty + unknown_bonus + failed_move_penalty
        immediate_candidates.append((score, direction))

    if immediate_candidates:
        immediate_candidates.sort(key=lambda item: (item[0], item[1]))
        return immediate_candidates[0][1]

    least_bad_candidates: list[tuple[float, str]] = []
    for direction in available_now:
        neighbor = next_pos(current, direction)
        visit_penalty = memory.visit_counts.get(neighbor, 0) * 5
        reverse_penalty = 7 if last_direction and opposite_direction(last_direction) == direction else 0
        failed_move_penalty = _move_penalty(current, direction, move_penalties) * 25
        goal_distance = _manhattan(neighbor, goal)
        score = goal_distance + visit_penalty + reverse_penalty + failed_move_penalty
        least_bad_candidates.append((score, direction))

    least_bad_candidates.sort(key=lambda item: (item[0], item[1]))
    return least_bad_candidates[0][1]


def next_pos(pos: tuple[int, int], direction: str) -> tuple[int, int]:
    if direction == "up":
        return (pos[0], pos[1] - 1)
    if direction == "down":
        return (pos[0], pos[1] + 1)
    if direction == "left":
        return (pos[0] - 1, pos[1])
    if direction == "right":
        return (pos[0] + 1, pos[1])
    raise ValueError(f"Unknown direction: {direction}")
