from __future__ import annotations

import argparse
import sys
import time

import httpx
from rich.console import Console
from rich.pretty import Pretty

from mazesnek.client import MoltMazeClient
from mazesnek.pathfinding import bfs_next_direction
from mazesnek.solver import solve_expression
from mazesnek.state import ParsedState, StateParseError, parse_state

console = Console()


def choose_direction(state: ParsedState) -> str:
    direction = bfs_next_direction(state.maze, state.position, state.goal)
    if direction and direction in state.actions:
        return direction

    for fallback in ("up", "down", "left", "right"):
        if fallback in state.actions:
            return fallback

    raise RuntimeError("No valid direction found")



def choose_answer(state: ParsedState) -> tuple[str, str, str]:
    direction = choose_direction(state)
    expr = state.actions[direction]
    answer = solve_expression(expr)
    return direction, expr, answer



def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="mazesnek",
        description="Resume or start a MoltMaze run and solve it from the command line.",
    )
    parser.add_argument("apikey", help="MoltMaze API key")
    parser.add_argument(
        "--base-url",
        default="https://moltmaze.com",
        help="MoltMaze base URL. Default: https://moltmaze.com",
    )
    parser.add_argument(
        "--poll",
        type=float,
        default=0.15,
        help="Seconds to sleep between successful turns. Default: 0.15",
    )
    parser.add_argument(
        "--force-new-run",
        action="store_true",
        help="Ask start_run.php to force a new run instead of resuming.",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Print parsed state details when possible.",
    )
    return parser



def main() -> int:
    args = build_parser().parse_args()
    client = MoltMazeClient(api_key=args.apikey, base_url=args.base_url)

    try:
        try:
            run_info = client.start_run(force_new_run=args.force_new_run)
            console.print("[bold green]start_run response[/bold green]")
            console.print(Pretty(run_info))
        except Exception as exc:
            console.print(f"[yellow]Warning:[/yellow] start_run failed: {exc}")
            console.print("[yellow]Trying current_run and state anyway...[/yellow]")

        turn_counter = 0
        while True:
            raw_state = client.get_state()
            if args.debug:
                console.print("[bold blue]raw state[/bold blue]")
                console.print(Pretty(raw_state))

            try:
                state = parse_state(raw_state)
            except StateParseError as exc:
                console.print(f"[bold red]State parse error:[/bold red] {exc}")
                if args.debug:
                    console.print(Pretty(raw_state))
                return 2

            direction, expr, answer = choose_answer(state)
            result = client.submit_move(state.run_id, answer)
            turn_counter += 1

            console.print(
                f"[cyan]turn {turn_counter}[/cyan] "
                f"dir=[bold]{direction}[/bold] "
                f"expr=[magenta]{expr}[/magenta] "
                f"answer=[green]{answer}[/green]"
            )
            console.print(Pretty(result))

            if isinstance(result, dict):
                status_text = str(result.get("status", "")).lower()
                active_text = str(result.get("run_status", "")).lower()
                if status_text in {"failed", "dead", "ended", "complete"}:
                    console.print("[bold yellow]Run ended according to submit response.[/bold yellow]")
                    return 0
                if active_text in {"failed", "dead", "ended", "complete"}:
                    console.print("[bold yellow]Run ended according to run status.[/bold yellow]")
                    return 0

            if args.poll > 0:
                time.sleep(args.poll)

    except KeyboardInterrupt:
        console.print("\n[bold yellow]MazeSnek stopped by user.[/bold yellow]")
        return 130
    except httpx.HTTPError as exc:
        console.print(f"[bold red]HTTP error:[/bold red] {exc}")
        return 1
    except Exception as exc:
        console.print(f"[bold red]Fatal error:[/bold red] {exc}")
        return 1
    finally:
        client.close()


if __name__ == "__main__":
    sys.exit(main())
