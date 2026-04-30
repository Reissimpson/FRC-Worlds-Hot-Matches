from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Iterable
from zoneinfo import ZoneInfo

from src.models import AlliancePrediction, MatchPrediction, RunSummary, TeamEPA
from src.scoring import division_name, score_matches
from src.statbotics_client import StatboticsClient
from src.tba_client import TBAClient


DEFAULT_DISPLAY_TIME_ZONE = "America/New_York"


def display_time_zone() -> ZoneInfo:
    timezone_name = os.getenv("DISPLAY_TIMEZONE", DEFAULT_DISPLAY_TIME_ZONE)
    try:
        return ZoneInfo(timezone_name)
    except Exception:
        print(f"ERROR Unknown DISPLAY_TIMEZONE '{timezone_name}', using {DEFAULT_DISPLAY_TIME_ZONE}")
        return ZoneInfo(DEFAULT_DISPLAY_TIME_ZONE)


def parse_team_number(team_key: str) -> int | None:
    if not team_key:
        return None
    value = str(team_key).lower().replace("frc", "", 1)
    try:
        return int(value)
    except ValueError:
        return None


def best_match_time(match: dict) -> int | None:
    for key in ("predicted_time", "actual_time", "time"):
        value = match.get(key)
        if value:
            return int(value)
    return None


def iso_time(unix_time: int | None) -> str | None:
    if not unix_time:
        return None
    return datetime.fromtimestamp(unix_time, tz=display_time_zone()).isoformat()


def eastern_display_time(unix_time: int | None) -> str | None:
    if not unix_time:
        return None
    local_time = datetime.fromtimestamp(unix_time, tz=display_time_zone())
    hour = local_time.strftime("%I").lstrip("0") or "0"
    return f"{hour}:{local_time:%M %p}"


def is_upcoming_match(match: dict, comp_levels: Iterable[str] = ("qm",)) -> bool:
    if match.get("comp_level") not in set(comp_levels):
        return False
    if match.get("actual_time") is not None:
        return False
    if match.get("winning_alliance"):
        return False

    alliances = match.get("alliances") or {}
    for color in ("red", "blue"):
        alliance = alliances.get(color) or {}
        if alliance.get("score") not in (None, -1):
            return False
        if not alliance.get("team_keys"):
            return False
    return True


def get_alliance_team_numbers(match: dict, color: str) -> list[int]:
    alliances = match.get("alliances") or {}
    alliance = alliances.get(color) or {}
    team_keys = alliance.get("team_keys") or []
    team_numbers = [parse_team_number(team_key) for team_key in team_keys]
    return [team_number for team_number in team_numbers if team_number is not None]


def build_alliance(team_numbers: list[int], team_epas: dict[int, TeamEPA]) -> AlliancePrediction:
    epa_values = {team: team_epas[team].epa for team in team_numbers}
    total = sum(epa_values.values())
    return AlliancePrediction(
        team_numbers=team_numbers,
        team_epas=epa_values,
        epa_sum=round(total, 3),
        epa_avg=round(total / len(team_numbers), 3) if team_numbers else 0.0,
        max_epa=round(max(epa_values.values()), 3) if epa_values else 0.0,
        missing_epa_count=sum(1 for team in team_numbers if team_epas[team].missing_epa),
    )


def collect_team_numbers(matches: list[dict]) -> list[int]:
    teams: set[int] = set()
    for match in matches:
        teams.update(get_alliance_team_numbers(match, "red"))
        teams.update(get_alliance_team_numbers(match, "blue"))
    return sorted(teams)


def build_match_prediction(match: dict, team_epas: dict[int, TeamEPA]) -> MatchPrediction:
    red_teams = get_alliance_team_numbers(match, "red")
    blue_teams = get_alliance_team_numbers(match, "blue")
    red = build_alliance(red_teams, team_epas)
    blue = build_alliance(blue_teams, team_epas)
    unix_time = best_match_time(match)
    all_epas = list(red.team_epas.values()) + list(blue.team_epas.values())

    red_sum = red.epa_sum
    blue_sum = blue.epa_sum
    combined_epa = red_sum + blue_sum

    return MatchPrediction(
        match_key=match.get("key", ""),
        event_key=match.get("event_key", ""),
        division=division_name(match.get("event_key", "")),
        comp_level=match.get("comp_level", ""),
        set_number=match.get("set_number"),
        match_number=int(match.get("match_number") or 0),
        display_time=iso_time(unix_time),
        display_time_est=eastern_display_time(unix_time),
        unix_time=unix_time,
        red_teams=red_teams,
        blue_teams=blue_teams,
        red_epa_sum=round(red_sum, 3),
        blue_epa_sum=round(blue_sum, 3),
        red_epa_avg=red.epa_avg,
        blue_epa_avg=blue.epa_avg,
        combined_epa=round(combined_epa, 3),
        epa_margin=round(abs(red_sum - blue_sum), 3),
        alliance_peak_epa=round(max(red_sum, blue_sum), 3),
        max_team_epa=round(max(all_epas), 3) if all_epas else 0.0,
        missing_epa_count=red.missing_epa_count + blue.missing_epa_count,
        team_epas=all_epas,
    )


def run_pipeline(
    year: int,
    event_keys: list[str],
    tba_client: TBAClient,
    statbotics_client: StatboticsClient,
) -> tuple[list[MatchPrediction], list[TeamEPA], RunSummary]:
    started = datetime.now(timezone.utc)
    errors: list[str] = []
    all_matches: list[dict] = []

    print("Loading events...")
    for event_key in event_keys:
        try:
            event_matches = tba_client.get_event_matches(event_key)
            all_matches.extend(event_matches)
            print(f"Fetched {len(event_matches)} matches from {event_key}")
        except Exception as exc:
            message = f"{event_key}: {type(exc).__name__}: {exc}"
            errors.append(message)
            print(f"ERROR {message}")

    upcoming_matches = [match for match in all_matches if is_upcoming_match(match)]
    team_numbers = collect_team_numbers(upcoming_matches)

    team_epas = statbotics_client.get_team_epas(team_numbers, year)

    predictions = [build_match_prediction(match, team_epas) for match in upcoming_matches]
    unique_team_epas = [team_epa.epa for team_epa in team_epas.values()]
    score_matches(predictions, unique_team_epas, now=started)

    duration = (datetime.now(timezone.utc) - started).total_seconds()
    missing_epa_count = sum(team_epa.missing_epa for team_epa in team_epas.values())
    summary = RunSummary(
        run_time=started.isoformat(),
        year=year,
        events_checked=event_keys,
        matches_fetched=len(all_matches),
        upcoming_matches_exported=len(predictions),
        teams_fetched=len(team_epas),
        missing_epa_count=missing_epa_count,
        errors=errors,
        duration_seconds=round(duration, 3),
    )

    print(f"Calculated hotness for {len(predictions)} upcoming matches")
    return predictions, list(team_epas.values()), summary
