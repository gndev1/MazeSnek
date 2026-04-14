from __future__ import annotations

import argparse
import sys
import time
from typing import Any

import httpx

from .client import MoltMazeClient
from .memory import MazeMemory
from .navigation import choose_direction_from_memory
from .solver import solve_equation
from .state import ParsedState, apply_direction, parse_state


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
        default=0.10,
        help="Delay before reading the next state",
    )
    parser.add_argument(
        "--move-delay",
        type=float,
        default=0.80,
        help="Minimum delay between submitted moves",
    )
    parser.add_argument(
        "--retry-delay",
        type=float,
        default=1.0,
        help="Delay before retrying after an HTTP error",
    )
    parser.add_argument(
        "--adaptive-backoff-step",
        type=float,
        default=0.15,
        help="How much to increase move delay after a failed submit",
    )
    parser.add_argument(
        "--max-move-delay",
        type=float,
        default=1.50,
        help="Maximum adaptive move delay after repeated submit failures",
    )
    parser.add_argument(
        "--failure-decay-interval",
        type=int,
        default=10,
        help="Reduce failed-move penalties every N successful submits",
    )
    parser.add_argument(
        "--failure-decay-amount",
        type=int,
        default=1,
        help="How much to reduce failed-move penalties when decay triggers",
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
    return solve_equation(equation)


def _load_initial_state(
    client: MoltMazeClient,
    force_new_run: bool,
    debug: bool,
) -> ParsedState:
    start_payload = client.start_run(force_new_run=force_new_run)
    if debug:
        _print_debug("start_run response", start_payload)
    return parse_state(start_payload)


def _refresh_state_after_error(
    client: MoltMazeClient,
    retry_delay: float,
    debug: bool,
) -> ParsedState | None:
    time.sleep(max(retry_delay, 0.0))
    try:
        payload = client.get_state()
        if debug:
            _print_debug("get_state response after error", payload)
        return parse_state(payload)
    except Exception as refresh_exc:
        print(f"Warning: state refresh after error also failed: {refresh_exc}")
        return None


def _decay_failed_move_penalties(
    failed_move_penalties: dict[tuple[tuple[int, int], str], int],
    amount: int,
) -> None:
    if amount <= 0:
        return

    to_delete: list[tuple[tuple[int, int], str]] = []
    for key, value in failed_move_penalties.items():
        new_value = value - amount
        if new_value <= 0:
            to_delete.append(key)
        else:
            failed_move_penalties[key] = new_value

    for key in to_delete:
        failed_move_penalties.pop(key, None)


def main() -> int:
    parser = _build_parser()
    args = parser.parse_args()

    client = MoltMazeClient(api_key=args.api_key, base_url=args.base_url)
    memory = MazeMemory()

    try:
        state = _load_initial_state(
            client=client,
            force_new_run=args.force_new_run,
            debug=args.debug,
        )

        last_direction: str | None = None
        last_submit_time = 0.0
        current_move_delay = max(args.move_delay, 0.0)
        failed_move_penalties: dict[tuple[tuple[int, int], str], int] = {}
        successful_submit_count = 0

        while True:
            memory.observe_state(state)
            memory.increment_visit(state.position)

            direction = choose_direction_from_memory(
                memory=memory,
                state=state,
                last_direction=last_direction,
                move_penalties=failed_move_penalties,
            )
            answer = _extract_answer(state, direction)

            now = time.time()
            elapsed = now - last_submit_time
            if elapsed < current_move_delay:
                time.sleep(current_move_delay - elapsed)

            print(
                f"run={state.run_id} level={state.level} turn={state.turn} "
                f"pos={state.position} goal={state.goal} move={direction} answer={answer}"
            )

            predicted_next_position = apply_direction(state.position, direction)

            try:
                submit_payload = client.submit_move(state.run_id, answer)
                last_submit_time = time.time()
                successful_submit_count += 1

                if current_move_delay > args.move_delay:
                    current_move_delay = max(args.move_delay, current_move_delay - 0.05)

                failed_move_penalties[(state.position, direction)] = max(
                    0,
                    failed_move_penalties.get((state.position, direction), 0) - 1,
                )
                if failed_move_penalties.get((state.position, direction), 0) <= 0:
                    failed_move_penalties.pop((state.position, direction), None)

                if (
                    args.failure_decay_interval > 0
                    and successful_submit_count % args.failure_decay_interval == 0
                ):
                    _decay_failed_move_penalties(
                        failed_move_penalties,
                        args.failure_decay_amount,
                    )

                if args.debug:
                    _print_debug("submit_move response", submit_payload)

                status = str(submit_payload.get("status", "")).lower()
                if status in {"completed", "finished", "dead", "failed"}:
                    print(f"Run ended with status: {submit_payload.get('status')}")
                    return 0

                last_direction = direction

                time.sleep(max(args.poll_seconds, 0.0))

                try:
                    next_payload = client.get_state()
                    if args.debug:
                        _print_debug("get_state response", next_payload)
                    state = parse_state(next_payload)
                except Exception as exc:
                    print(f"Warning: get_state failed after successful submit: {exc}")
                    refreshed = _refresh_state_after_error(
                        client=client,
                        retry_delay=args.retry_delay,
                        debug=args.debug,
                    )
                    if refreshed is not None:
                        state = refreshed
                    continue

                if state.position != predicted_next_position and args.debug:
                    print(
                        f"Note: predicted next position {predicted_next_position}, "
                        f"actual position {state.position}"
                    )

            except httpx.HTTPStatusError as exc:
                status_code = exc.response.status_code if exc.response is not None else "?"
                print(
                    f"Warning: submit_move failed with HTTP {status_code}. "
                    f"Backing off for {args.retry_delay:.2f}s and refreshing state."
                )

                failed_move_penalties[(state.position, direction)] = failed_move_penalties.get(
                    (state.position, direction), 0
                ) + 1

                current_move_delay = min(
                    args.max_move_delay,
                    current_move_delay + max(args.adaptive_backoff_step, 0.0),
                )

                refreshed = _refresh_state_after_error(
                    client=client,
                    retry_delay=args.retry_delay,
                    debug=args.debug,
                )
                if refreshed is not None:
                    state = refreshed
                continue

            except httpx.HTTPError as exc:
                print(
                    f"Warning: HTTP error during submit_move: {exc}. "
                    f"Backing off for {args.retry_delay:.2f}s and refreshing state."
                )
                current_move_delay = min(
                    args.max_move_delay,
                    current_move_delay + max(args.adaptive_backoff_step, 0.0),
                )
                refreshed = _refresh_state_after_error(
                    client=client,
                    retry_delay=args.retry_delay,
                    debug=args.debug,
                )
                if refreshed is not None:
                    state = refreshed
                continue

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
