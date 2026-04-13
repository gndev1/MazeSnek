from __future__ import annotations

from typing import Any

import httpx


class MoltMazeClient:
    def __init__(self, api_key: str, base_url: str = "https://moltmaze.com") -> None:
        self.api_key = api_key
        self.client = httpx.Client(
            base_url=base_url.rstrip("/"),
            timeout=10.0,
            headers={
                "Accept": "application/json",
                "User-Agent": "MazeSnek/0.1.0",
            },
        )

    def close(self) -> None:
        self.client.close()

    def start_run(self, force_new_run: bool = False) -> dict[str, Any]:
        payload: dict[str, Any] = {}
        if force_new_run:
            payload["force_new_run"] = True
        response = self.client.post(
            "/api/start_run.php",
            headers={"X-API-Key": self.api_key, "Content-Type": "application/json"},
            json=payload,
        )
        response.raise_for_status()
        return response.json()

    def current_run(self) -> dict[str, Any]:
        response = self.client.get("/api/current_run.php", params={"api_key": self.api_key})
        response.raise_for_status()
        return response.json()

    def get_state(self) -> dict[str, Any]:
        response = self.client.get("/api/get_state.php", params={"api_key": self.api_key})
        response.raise_for_status()
        return response.json()

    def submit_move(self, run_id: int, answer: str) -> dict[str, Any]:
        response = self.client.post(
            "/api/submit_move.php",
            headers={"X-API-Key": self.api_key, "Content-Type": "application/json"},
            json={"run_id": run_id, "answer": answer},
        )
        response.raise_for_status()
        return response.json()
