from __future__ import annotations

from typing import Any

import httpx


class MoltMazeClient:
    def __init__(self, api_key: str, base_url: str = "https://moltmaze.com") -> None:
        self.api_key = api_key.strip()
        self.client = httpx.Client(
            base_url=base_url.rstrip("/"),
            timeout=20.0,
            headers={
                "Accept": "application/json",
                "User-Agent": "MazeSnek/0.1.0",
                "X-API-Key": self.api_key,
            },
        )

    def close(self) -> None:
        self.client.close()

    def start_run(self, force_new_run: bool = False) -> dict[str, Any]:
        params: dict[str, Any] = {"api_key": self.api_key}
        if force_new_run:
            params["force_new"] = "1"
            params["force_new_run"] = "1"

        response = self.client.post("/api/start_run.php", params=params)
        response.raise_for_status()
        return response.json()

    def current_run(self) -> dict[str, Any]:
        response = self.client.get(
            "/api/current_run.php",
            params={"api_key": self.api_key},
        )
        response.raise_for_status()
        return response.json()

    def get_state(self, include_debug: bool = False, run_id: int | None = None) -> dict[str, Any]:
        params: dict[str, Any] = {"api_key": self.api_key}
        if run_id is not None:
            params["run_id"] = run_id
        if include_debug:
            params["include_debug"] = "1"

        response = self.client.get("/api/get_state.php", params=params)
        response.raise_for_status()
        return response.json()

    def submit_move(self, run_id: int, answer: str) -> dict[str, Any]:
        response = self.client.post(
            "/api/submit_move.php",
            params={"api_key": self.api_key},
            json={"run_id": run_id, "answer": str(answer)},
        )
        response.raise_for_status()
        return response.json()