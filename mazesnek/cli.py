from __future__ import annotations

import argparse
import sys
import time
from typing import Any

from .client import MoltMazeClient
from .solver import solve_equation
from .state import ParsedState, apply_direction, choose_direction, parse_state


def _print_debug(title: str, payload: Any) -> None:
    print(title)
    print(payload)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="mazesnek",
        description="MazeSnek MoltMaze bot runner",
    )
    parser.add_argument("api_key", help="Your MoltMaze bot API key")
    parser.add_argument(
        "--base-url",
        default="https://moltmaze.com",
        help="Base URL for MoltMaze",
    )
    parser.add_argument(
        "--poll-seconds",
        type=float,
        default=0.15,
        help="Delay before reading the next state",
    )
    parser.add_argument(
        "--move-delay",
        type=float,
        default=0.40,
        help="Minimum delay between submitted moves",
    )
    parser.add_argument(
        "--force-new-run",
        action="store_true",
        help="Request a new run instead of resuming",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Print debug responses",
    )
    return parser


def _extract_answer(state: ParsedState, direction: str) -> str:
    action = state.actions[direction]
    equation = action.get("equation", "")
    if not equation:
        raise RuntimeError(f"No equation found for direction: {direction}")

    solved = solve_equation(equation)
    return solved


def _load_initial_state(
    client: MoltMazeClient,
    force_new_run: bool,
    debug: bool,
) -> ParsedState:
    start_payload = client.start_run(force_new_run=force_new_run)
    if debug:
        _print_debug("start_run response", start_payload)
    return parse_state(start_payload)


def main() -> int:
    parser = _build_parser()
    args = parser.parse_args()

    client = MoltMazeClient(api_key=args.api_key, base_url=args.base_url)

    try:
        state = _load_initial_state(
            client=client,
            force_new_run=args.force_new_run,
            debug=args.debug,
        )

        visited: dict[tuple[int, int], int] = {}
        last_direction: str | None = None
        last_submit_time = 0.0

        while True:
            visited[state.position] = visited.get(state.position, 0) + 1

            direction = choose_direction(
                state,
                visited=visited,
                last_direction=last_direction,
            )
            answer = _extract_answer(state, direction)

            now = time.time()
            elapsed = now - last_submit_time
            if elapsed < args.move_delay:
                time.sleep(args.move_delay - elapsed)

            print(
                f"run={state.run_id} pos={state.position} goal={state.goal} "
                f"move={direction} answer={answer}"
            )

            submit_payload = client.submit_move(state.run_id, answer)
            last_submit_time = time.time()

            if args.debug:
                _print_debug("submit_move response", submit_payload)

            status = str(submit_payload.get("status", "")).lower()
            if status in {"completed", "finished", "dead", "failed"}:
                print(f"Run ended with status: {submit_payload.get('status')}")
                return 0

            predicted_next_position = apply_direction(state.position, direction)
            last_direction = direction

            time.sleep(max(args.poll_seconds, 0.0))

            next_payload = client.get_state()
            if args.debug:
                _print_debug("get_state response", next_payload)

            state = parse_state(next_payload)

            if state.position != predicted_next_position and args.debug:
                print(
                    f"Note: predicted next position {predicted_next_position}, "
                    f"actual position {state.position}"
                )

    except KeyboardInterrupt:
        print("\nStopped.")
        return 0
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    finally:
        client.close()


if __name__ == "__main__":
    raise SystemExit(main())