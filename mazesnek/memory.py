from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field

from .state import ParsedState, cardinal_neighbors


Edge = frozenset[tuple[int, int]]


def _edge(a: tuple[int, int], b: tuple[int, int]) -> Edge:
    return frozenset((a, b))


@dataclass
class MazeMemory:
    run_id: int | None = None
    level: int | None = None
    maze_size: tuple[int, int] | None = None
    known_open: set[tuple[int, int]] = field(default_factory=set)
    adjacency: dict[tuple[int, int], set[tuple[int, int]]] = field(default_factory=lambda: defaultdict(set))
    blocked_edges: set[Edge] = field(default_factory=set)
    observed_tiles: set[tuple[int, int]] = field(default_factory=set)
    visit_counts: dict[tuple[int, int], int] = field(default_factory=lambda: defaultdict(int))

    def reset(self, run_id: int | None, level: int | None, maze_size: tuple[int, int] | None = None) -> None:
        self.run_id = run_id
        self.level = level
        self.maze_size = maze_size
        self.known_open.clear()
        self.adjacency.clear()
        self.blocked_edges.clear()
        self.observed_tiles.clear()
        self.visit_counts.clear()

    def maybe_reset_for_state(self, state: ParsedState) -> None:
        if self.run_id != state.run_id or self.level != state.level:
            self.reset(state.run_id, state.level, state.maze_size)
        elif state.maze_size is not None:
            self.maze_size = state.maze_size

    def in_bounds(self, pos: tuple[int, int]) -> bool:
        if pos[0] < 0 or pos[1] < 0:
            return False
        if self.maze_size is None:
            return True
        width, height = self.maze_size
        return pos[0] < width and pos[1] < height

    def mark_open(self, pos: tuple[int, int]) -> None:
        if self.in_bounds(pos):
            self.known_open.add(pos)
            self.adjacency.setdefault(pos, set())

    def mark_blocked(self, a: tuple[int, int], b: tuple[int, int]) -> None:
        if self.in_bounds(a) and self.in_bounds(b):
            self.blocked_edges.add(_edge(a, b))

    def connect(self, a: tuple[int, int], b: tuple[int, int]) -> None:
        if not self.in_bounds(a) or not self.in_bounds(b):
            return
        self.mark_open(a)
        self.mark_open(b)
        self.adjacency[a].add(b)
        self.adjacency[b].add(a)
        blocked = _edge(a, b)
        if blocked in self.blocked_edges:
            self.blocked_edges.remove(blocked)

    def is_blocked(self, a: tuple[int, int], b: tuple[int, int]) -> bool:
        return _edge(a, b) in self.blocked_edges

    def increment_visit(self, pos: tuple[int, int]) -> None:
        self.visit_counts[pos] += 1

    def observe_state(self, state: ParsedState) -> None:
        self.maybe_reset_for_state(state)
        current = state.position
        self.mark_open(current)
        self.observed_tiles.add(current)

        for direction, neighbor in cardinal_neighbors(current).items():
            if not self.in_bounds(neighbor):
                continue

            action = state.actions.get(direction)
            if not action:
                continue

            if action.get("traversable", False):
                self.connect(current, neighbor)
            else:
                self.mark_blocked(current, neighbor)

    def unknown_neighbor_count(self, pos: tuple[int, int]) -> int:
        count = 0
        for neighbor in cardinal_neighbors(pos).values():
            if not self.in_bounds(neighbor):
                continue
            if neighbor in self.known_open:
                continue
            if self.is_blocked(pos, neighbor):
                continue
            count += 1
        return count

    def frontier_nodes(self) -> list[tuple[int, int]]:
        frontiers: list[tuple[int, int]] = []
        for pos in self.known_open:
            if self.unknown_neighbor_count(pos) > 0:
                frontiers.append(pos)
        return frontiers

    def degree(self, pos: tuple[int, int]) -> int:
        return len(self.adjacency.get(pos, set()))
