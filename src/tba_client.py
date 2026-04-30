from __future__ import annotations

import requests


class TBAClient:
    """Small wrapper for The Blue Alliance API v3."""

    BASE_URL = "https://www.thebluealliance.com/api/v3"

    def __init__(self, auth_key: str, timeout_seconds: int = 20) -> None:
        if not auth_key:
            raise ValueError("TBA_AUTH_KEY is required")
        self.timeout_seconds = timeout_seconds
        self.session = requests.Session()
        self.session.headers.update(
            {
                "X-TBA-Auth-Key": auth_key,
                "Accept": "application/json",
                "User-Agent": "frc-hot-matches/1.0",
            }
        )

    def get_event_matches(self, event_key: str) -> list[dict]:
        url = f"{self.BASE_URL}/event/{event_key}/matches"
        response = self.session.get(url, timeout=self.timeout_seconds)
        response.raise_for_status()
        data = response.json()
        if not isinstance(data, list):
            raise ValueError(f"Unexpected TBA response for {event_key}: expected list")
        return data
