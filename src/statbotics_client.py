from __future__ import annotations

from typing import Any

import requests

from src.models import TeamEPA


COMMON_EPA_PATHS = (
    ("epa", "current"),
    ("epa", "mean"),
    ("epa", "recent"),
    ("norm_epa", "current"),
    ("norm_epa", "mean"),
    ("norm_epa", "recent"),
    ("epa", "total_points", "mean"),
    ("epa", "breakdown", "total_points"),
    ("epa", "stats", "pre_champs"),
    ("epa", "stats", "max"),
    ("epa", "stats", "start"),
)


def _get_path(data: dict[str, Any], path: tuple[str, ...]) -> Any:
    current: Any = data
    for part in path:
        if not isinstance(current, dict) or part not in current:
            return None
        current = current[part]
    return current


def _coerce_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def extract_epa_with_source(statbotics_response: dict) -> tuple[float, str, bool]:
    for path in COMMON_EPA_PATHS:
        value = _coerce_float(_get_path(statbotics_response, path))
        if value is not None:
            return value, ".".join(path), False

    for key in ("epa", "norm_epa"):
        value = _coerce_float(statbotics_response.get(key))
        if value is not None:
            return value, key, False

    return 0.0, "missing", True


def extract_epa(statbotics_response: dict) -> float:
    epa, _, _ = extract_epa_with_source(statbotics_response)
    return epa


class StatboticsClient:
    """Fetches and caches Statbotics team-year EPA values."""

    BASE_URL = "https://api.statbotics.io/v3"

    def __init__(self, timeout_seconds: int = 20) -> None:
        self.timeout_seconds = timeout_seconds
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Accept": "application/json",
                "User-Agent": "frc-hot-matches/1.0",
            }
        )
        self._cache: dict[tuple[int, int], TeamEPA] = {}

    @property
    def cache(self) -> dict[tuple[int, int], TeamEPA]:
        return self._cache

    def get_team_year(self, team_number: int, year: int) -> dict:
        url = f"{self.BASE_URL}/team_year/{team_number}/{year}"
        response = self.session.get(url, timeout=self.timeout_seconds)
        response.raise_for_status()
        data = response.json()
        if not isinstance(data, dict):
            raise ValueError(f"Unexpected Statbotics response for team {team_number}: expected object")
        return data

    def get_team_years(self, year: int) -> list[dict]:
        url = f"{self.BASE_URL}/team_years"
        limit = 1000
        offset = 0
        rows: list[dict] = []
        while True:
            response = self.session.get(
                url,
                params={"year": year, "limit": limit, "offset": offset},
                timeout=self.timeout_seconds,
            )
            response.raise_for_status()
            data = response.json()
            if not isinstance(data, list):
                raise ValueError(f"Unexpected Statbotics response for year {year}: expected list")
            rows.extend(data)
            if len(data) < limit:
                return rows
            offset += limit

    def get_team_epas(self, team_numbers: list[int], year: int) -> dict[int, TeamEPA]:
        missing_numbers = [team for team in team_numbers if (team, year) not in self._cache]
        if missing_numbers:
            try:
                team_years = self.get_team_years(year)
                requested = set(missing_numbers)
                for data in team_years:
                    team_number = data.get("team")
                    if team_number not in requested:
                        continue
                    epa, source, missing = extract_epa_with_source(data)
                    self._cache[(team_number, year)] = TeamEPA(
                        team_number=team_number,
                        epa=round(epa, 3),
                        epa_source=source,
                        missing_epa=missing,
                    )
                print(f"Fetched EPA table for {year}")
            except Exception as exc:
                print(f"ERROR Statbotics bulk EPA fetch failed: {type(exc).__name__}: {exc}")

        results: dict[int, TeamEPA] = {}
        for team_number in team_numbers:
            results[team_number] = self.get_team_epa(team_number, year)
        return results

    def get_team_epa(self, team_number: int, year: int) -> TeamEPA:
        cache_key = (team_number, year)
        if cache_key in self._cache:
            return self._cache[cache_key]

        try:
            data = self.get_team_year(team_number, year)
            epa, source, missing = extract_epa_with_source(data)
        except Exception as exc:
            epa, source, missing = 0.0, f"error:{type(exc).__name__}", True

        team_epa = TeamEPA(
            team_number=team_number,
            epa=round(epa, 3),
            epa_source=source,
            missing_epa=missing,
        )
        self._cache[cache_key] = team_epa
        print(f"Fetched EPA for team {team_number}")
        return team_epa
