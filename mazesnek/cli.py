
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


def _print_trace(title: str, payload: Any) -> None:
    print(title)
    print(payload)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="mazesnek",
        description="MazeSnek MoltMaze bot runner",
    )
    parser.add_argument("api_key", help="Your MoltMaze bot API key")
    parser.add_argument("--base-url", default="https://moltmaze.com", help="Base URL for MoltMaze")
    parser.add_argument("--poll-seconds", type=float, default=0.10, help="Delay before reading the next state")
    parser.add_argument("--move-delay", type=float, default=0.80, help="Minimum delay between submitted moves")
    parser.add_argument("--retry-delay", type=float, default=1.0, help="Delay before retrying after an HTTP error")
    parser.add_argument("--adaptive-backoff-step", type=float, default=0.15, help="How much to increase move delay after a failed submit")
    parser.add_argument("--max-move-delay", type=float, default=1.50, help="Maximum adaptive move delay after repeated submit failures")
    parser.add_argument("--failure-decay-interval", type=int, default=10, help="Reduce failed-move penalties every N successful submits")
    parser.add_argument("--failure-decay-amount", type=int, default=1, help="How much to reduce failed-move penalties when decay triggers")
    parser.add_argument("--force-new-run", action="store_true", help="Request a new run instead of resuming")
    parser.add_argument("--debug", action="store_true", help="Show compact debug info and request include_debug=1 from get_state")
    parser.add_argument("--trace", action="store_true", help="Show full raw API payloads")
    return parser


def _debug_state_summary(state: ParsedState) -> None:
    traversable = [
        direction
        for direction, info in state.actions.items()
        if info.get("traversable", False)
    ]
    parts = [
        f"run={state.run_id}",
        f"level={state.level}",
        f"turn={state.turn}",
        f"pos={state.position}",
    ]
    if state.local_position is not None and state.local_position != state.position:
        parts.append(f"local_pos={state.local_position}")
    parts.append(f"goal={state.goal}")
    if state.local_goal is not None and state.local_goal != state.goal:
        parts.append(f"local_goal={state.local_goal}")
    if state.chunk is not None:
        parts.append(f"chunk={state.chunk}")
    parts.append(f"traversable={','.join(traversable)}")
    print(' '.join(parts))


def _debug_equation_and_answer(direction: str, equation: str, answer: str) -> None:
    print(f"chosen={direction}")
    print("equation:")
    print(equation)
    print("answer:")
    print(answer)


def _debug_validation_for_direction(payload: dict[str, Any], direction: str) -> None:
    block = payload.get("debug_validation")
    if not isinstance(block, dict):
        return

    item = block.get(direction)
    if not isinstance(item, dict):
        return

    print("debug_validation:")
    expected = item.get("expected_answer") or item.get("stored_answer")
    if expected is not None:
        print(f"  expected_answer: {expected}")

    fmt = item.get("answer_format")
    if fmt is not None:
        print(f"  answer_format: {fmt}")

    count = item.get("answer_count")
    if count is not None:
        print(f"  answer_count: {count}")

    debug = item.get("debug")
    if isinstance(debug, dict):
        if "effective_difficulty" in debug:
            print(f"  effective_difficulty: {debug['effective_difficulty']}")
        if "forced_safe_fallback" in debug:
            print(f"  forced_safe_fallback: {debug['forced_safe_fallback']}")


def _extract_answer(state: ParsedState, direction: str, debug: bool = False) -> str:
    action = state.actions[direction]
    equation = action.get("equation", "")
    if not equation:
        raise RuntimeError(f"No equation found for direction: {direction}")
    try:
        return solve_equation(equation)
    except Exception as exc:
        if debug:
            print(f"Solver failed for direction {direction}: {exc}")
            print("Equation text:")
            print(equation)
        raise


def _load_initial_state(
    client: MoltMazeClient,
    force_new_run: bool,
    debug: bool,
    trace: bool,
) -> ParsedState:
    include_debug = debug or trace

    if not force_new_run:
        try:
            current_run_payload = client.current_run()
            if trace:
                _print_trace("current_run response", current_run_payload)

            status = str(current_run_payload.get("status", "")).lower()
            run_id = int(current_run_payload.get("run_id", 0) or 0)

            if run_id > 0 and status in {"active", "running", "in_progress"}:
                state_payload = client.get_state(include_debug=include_debug, run_id=run_id)
                if trace:
                    _print_trace("get_state response (startup)", state_payload)
                state = parse_state(state_payload)
                if debug:
                    _debug_state_summary(state)
                return state
        except Exception as exc:
            if debug or trace:
                print(f"current_run startup probe failed: {exc}")

    try:
        start_payload = client.start_run(force_new_run=force_new_run)
        if trace:
            _print_trace("start_run response", start_payload)
        state = parse_state(start_payload)
        if debug:
            _debug_state_summary(state)
        return state
    except Exception as exc:
        if debug or trace:
            print(f"start_run failed during startup: {exc}")

    state_payload = client.get_state(include_debug=include_debug)
    if trace:
        _print_trace("get_state response (startup fallback)", state_payload)
    state = parse_state(state_payload)
    if debug:
        _debug_state_summary(state)
    return state


def _refresh_state_after_error(
    client: MoltMazeClient,
    retry_delay: float,
    debug: bool,
    trace: bool,
    run_id: int | None = None,
) -> dict[str, Any] | None:
    time.sleep(max(retry_delay, 0.0))
    try:
        payload = client.get_state(include_debug=(debug or trace), run_id=run_id)
        if trace:
            _print_trace("get_state response after error", payload)
        return payload
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
    for key, value in list(failed_move_penalties.items()):
        new_value = value - amount
        if new_value <= 0:
            to_delete.append(key)
        else:
            failed_move_penalties[key] = new_value

    for key in to_delete:
        failed_move_penalties.pop(key, None)


def _print_response_body(exc: httpx.HTTPStatusError) -> None:
    if exc.response is None:
        return
    try:
        body = exc.response.text.strip()
    except Exception:
        body = ""
    if body:
        print("response body:")
        print(body)


def _try_parse_json_from_status_error(exc: httpx.HTTPStatusError) -> dict[str, Any] | None:
    if exc.response is None:
        return None
    try:
        data = exc.response.json()
    except Exception:
        return None
    return data if isinstance(data, dict) else None


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
            trace=args.trace,
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

            equation = state.actions[direction].get("equation", "")
            try:
                answer = _extract_answer(state, direction, debug=args.debug or args.trace)
            except Exception:
                failed_move_penalties[(state.position, direction)] = failed_move_penalties.get(
                    (state.position, direction), 0
                ) + 2
                refreshed_payload = _refresh_state_after_error(
                    client=client,
                    retry_delay=args.retry_delay,
                    debug=args.debug,
                    trace=args.trace,
                    run_id=state.run_id,
                )
                if refreshed_payload is not None:
                    state = parse_state(refreshed_payload)
                    if args.debug:
                        _debug_state_summary(state)
                continue

            print(
                f"run={state.run_id} level={state.level} turn={state.turn} "
                f"pos={state.position} goal={state.goal} move={direction} answer={answer}"
            )

            if args.debug:
                _debug_equation_and_answer(direction, equation, answer)

            now = time.time()
            elapsed = now - last_submit_time
            if elapsed < current_move_delay:
                time.sleep(current_move_delay - elapsed)

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

                if args.trace:
                    _print_trace("submit_move response", submit_payload)

                status = str(submit_payload.get("status", "")).lower()
                if status in {"completed", "finished", "dead", "failed"}:
                    print(f"Run ended with status: {submit_payload.get('status')}")
                    return 0

                last_direction = direction

                time.sleep(max(args.poll_seconds, 0.0))

                try:
                    next_payload = client.get_state(include_debug=(args.debug or args.trace), run_id=state.run_id)
                    if args.trace:
                        _print_trace("get_state response", next_payload)
                    state = parse_state(next_payload)
                    if args.debug:
                        _debug_state_summary(state)
                except Exception as exc:
                    print(f"Warning: get_state failed after successful submit: {exc}")
                    refreshed_payload = _refresh_state_after_error(
                        client=client,
                        retry_delay=args.retry_delay,
                        debug=args.debug,
                        trace=args.trace,
                        run_id=state.run_id,
                    )
                    if refreshed_payload is not None:
                        state = parse_state(refreshed_payload)
                        if args.debug:
                            _debug_state_summary(state)
                    continue

                if state.position != predicted_next_position and (args.debug or args.trace):
                    print(
                        f"Note: predicted next position {predicted_next_position}, "
                        f"actual position {state.position}"
                    )

            except httpx.HTTPStatusError as exc:
                effective_retry_delay = args.retry_delay

                print(
                    f"Warning: submit_move failed with HTTP {exc.response.status_code if exc.response is not None else '?'}. "
                    f"Backing off for {effective_retry_delay:.2f}s and refreshing state."
                )
                if args.debug or args.trace:
                    _print_response_body(exc)

                error_json = _try_parse_json_from_status_error(exc)
                if isinstance(error_json, dict):
                    retry_after_ms = error_json.get("retry_after_ms")
                    if isinstance(retry_after_ms, int) and retry_after_ms > 0:
                        effective_retry_delay = max(effective_retry_delay, retry_after_ms / 1000.0)

                if (args.debug or args.trace) and error_json:
                    _debug_validation_for_direction(error_json, direction)
                    state_block = error_json.get("state")
                    if isinstance(state_block, dict):
                        _debug_validation_for_direction(state_block, direction)

                failed_move_penalties[(state.position, direction)] = failed_move_penalties.get(
                    (state.position, direction), 0
                ) + 1

                current_move_delay = min(
                    args.max_move_delay,
                    current_move_delay + max(args.adaptive_backoff_step, 0.0),
                )

                refreshed_payload = _refresh_state_after_error(
                    client=client,
                    retry_delay=effective_retry_delay,
                    debug=args.debug,
                    trace=args.trace,
                    run_id=state.run_id,
                )
                if refreshed_payload is not None:
                    if args.debug:
                        _debug_validation_for_direction(refreshed_payload, direction)
                    state = parse_state(refreshed_payload)
                    if args.debug:
                        _debug_state_summary(state)
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
                refreshed_payload = _refresh_state_after_error(
                    client=client,
                    retry_delay=args.retry_delay,
                    debug=args.debug,
                    trace=args.trace,
                    run_id=state.run_id,
                )
                if refreshed_payload is not None:
                    state = parse_state(refreshed_payload)
                    if args.debug:
                        _debug_state_summary(state)
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
