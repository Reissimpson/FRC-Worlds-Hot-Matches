from __future__ import annotations

import os
from pathlib import Path

import pandas as pd

from src.models import MatchPrediction, RunSummary, TeamEPA
from src.scoring import PERCENTILES, WEIGHTS


MATCH_COLUMNS = [
    "hotness_rank",
    "watch_order",
    "hotness_score",
    "hotness_tier",
    "display_time",
    "division",
    "event_key",
    "match_key",
    "comp_level",
    "match_number",
    "red_1",
    "red_1_epa",
    "red_1_epa_percentile",
    "red_1_epa_color",
    "red_2",
    "red_2_epa",
    "red_2_epa_percentile",
    "red_2_epa_color",
    "red_3",
    "red_3_epa",
    "red_3_epa_percentile",
    "red_3_epa_color",
    "blue_1",
    "blue_1_epa",
    "blue_1_epa_percentile",
    "blue_1_epa_color",
    "blue_2",
    "blue_2_epa",
    "blue_2_epa_percentile",
    "blue_2_epa_color",
    "blue_3",
    "blue_3_epa",
    "blue_3_epa_percentile",
    "blue_3_epa_color",
    "red_teams",
    "blue_teams",
    "red_epa_sum",
    "blue_epa_sum",
    "combined_epa",
    "epa_margin",
    "alliance_peak_epa",
    "max_team_epa",
    "top_teams_count",
    "elite_teams_count",
    "super_elite_teams_count",
    "combined_epa_index",
    "alliance_peak_index",
    "closeness_index",
    "star_power_index",
    "soonness_index",
    "missing_epa_count",
    "reason_to_watch",
    "last_updated",
]

TEAM_SLOTS = (
    ("red", 1),
    ("red", 2),
    ("red", 3),
    ("blue", 1),
    ("blue", 2),
    ("blue", 3),
)

TEAM_COLUMNS = [
    "team_number",
    "epa",
    "epa_source",
    "missing_epa",
    "last_updated",
]

SETTINGS_COLUMNS = [
    "setting_name",
    "setting_value",
    "description",
]

RUN_LOG_COLUMNS = [
    "run_time",
    "year",
    "events_checked",
    "matches_fetched",
    "upcoming_matches_exported",
    "teams_fetched",
    "missing_epa_count",
    "errors",
    "duration_seconds",
]


def sort_for_watch_order(matches: list[MatchPrediction]) -> list[MatchPrediction]:
    return sorted(
        matches,
        key=lambda match: (
            match.unix_time is None,
            match.unix_time or 0,
            -match.hotness_score,
            match.match_key,
        ),
    )


def _hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    hex_color = hex_color.lstrip("#")
    return tuple(int(hex_color[index : index + 2], 16) for index in (0, 2, 4))


def _rgb_to_hex(rgb: tuple[int, int, int]) -> str:
    return f"#{rgb[0]:02X}{rgb[1]:02X}{rgb[2]:02X}"


def _blend(start: str, end: str, amount: float) -> str:
    start_rgb = _hex_to_rgb(start)
    end_rgb = _hex_to_rgb(end)
    amount = max(0.0, min(1.0, amount))
    return _rgb_to_hex(
        tuple(
            round(start_rgb[index] + (end_rgb[index] - start_rgb[index]) * amount)
            for index in range(3)
        )
    )


def epa_color(percentile: float | None) -> str:
    if percentile is None:
        return "#D9D9D9"
    if percentile >= 95:
        return "#4F81BD"
    if percentile <= 50:
        return _blend("#F8696B", "#FFEB84", percentile / 50)
    return _blend("#FFEB84", "#63BE7B", (percentile - 50) / 45)


def team_epa_percentiles(teams: list[TeamEPA]) -> dict[int, float]:
    available = [team for team in teams if not team.missing_epa]
    if not available:
        return {}
    if len(available) == 1:
        return {available[0].team_number: 100.0}

    sorted_epas = sorted(team.epa for team in available)
    denominator = len(sorted_epas) - 1
    percentiles: dict[int, float] = {}
    for team in available:
        positions = [index for index, epa in enumerate(sorted_epas) if epa == team.epa]
        average_position = sum(positions) / len(positions)
        percentiles[team.team_number] = round(100 * average_position / denominator, 2)
    return percentiles


def _team_slot_rows(match: MatchPrediction, team_lookup: dict[int, TeamEPA], percentile_lookup: dict[int, float]) -> dict:
    values: dict = {}
    for color, slot_number in TEAM_SLOTS:
        teams = match.red_teams if color == "red" else match.blue_teams
        team_number = teams[slot_number - 1] if len(teams) >= slot_number else None
        prefix = f"{color}_{slot_number}"
        team = team_lookup.get(team_number) if team_number is not None else None
        percentile = percentile_lookup.get(team_number) if team_number is not None else None

        values[prefix] = team_number or ""
        values[f"{prefix}_epa"] = round(team.epa, 2) if team else ""
        values[f"{prefix}_epa_percentile"] = percentile if percentile is not None else ""
        values[f"{prefix}_epa_color"] = epa_color(percentile)
    return values


def build_match_rows(matches: list[MatchPrediction], last_updated: str, teams: list[TeamEPA] | None = None) -> list[dict]:
    hotness_sorted = sorted(matches, key=lambda match: (-match.hotness_score, match.match_key))
    hotness_rank = {match.match_key: index + 1 for index, match in enumerate(hotness_sorted)}
    watch_sorted = sort_for_watch_order(matches)
    watch_order = {match.match_key: index + 1 for index, match in enumerate(watch_sorted)}
    teams = teams or []
    team_lookup = {team.team_number: team for team in teams}
    percentile_lookup = team_epa_percentiles(teams)

    rows: list[dict] = []
    for match in watch_sorted:
        row = {
            "hotness_rank": hotness_rank[match.match_key],
            "watch_order": watch_order[match.match_key],
            "hotness_score": match.hotness_score,
            "hotness_tier": match.hotness_tier,
            "display_time": match.display_time or "",
            "division": match.division,
            "event_key": match.event_key,
            "match_key": match.match_key,
            "comp_level": match.comp_level,
            "match_number": match.match_number,
            "red_teams": ",".join(str(team) for team in match.red_teams),
            "blue_teams": ",".join(str(team) for team in match.blue_teams),
            "red_epa_sum": round(match.red_epa_sum, 2),
            "blue_epa_sum": round(match.blue_epa_sum, 2),
            "combined_epa": round(match.combined_epa, 2),
            "epa_margin": round(match.epa_margin, 2),
            "alliance_peak_epa": round(match.alliance_peak_epa, 2),
            "max_team_epa": round(match.max_team_epa, 2),
            "top_teams_count": match.top_teams_count,
            "elite_teams_count": match.elite_teams_count,
            "super_elite_teams_count": match.super_elite_teams_count,
            "combined_epa_index": round(match.combined_epa_index, 2),
            "alliance_peak_index": round(match.alliance_peak_index, 2),
            "closeness_index": round(match.closeness_index, 2),
            "star_power_index": round(match.star_power_index, 2),
            "soonness_index": round(match.soonness_index, 2),
            "missing_epa_count": match.missing_epa_count,
            "reason_to_watch": match.reason_to_watch,
            "last_updated": last_updated,
        }
        row.update(_team_slot_rows(match, team_lookup, percentile_lookup))
        rows.append(row)
    return rows


def write_matches_csv(
    matches: list[MatchPrediction],
    output_path: str | Path,
    last_updated: str,
    teams: list[TeamEPA] | None = None,
) -> list[dict]:
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    rows = build_match_rows(matches, last_updated, teams)
    pd.DataFrame(rows, columns=MATCH_COLUMNS).to_csv(output_path, index=False)
    print(f"Exported {output_path.as_posix()}")
    return rows


def write_teams_csv(teams: list[TeamEPA], output_path: str | Path, last_updated: str) -> None:
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    rows = [
        {
            "team_number": team.team_number,
            "epa": round(team.epa, 3),
            "epa_source": team.epa_source,
            "missing_epa": team.missing_epa,
            "last_updated": last_updated,
        }
        for team in sorted(teams, key=lambda team: team.team_number)
    ]
    pd.DataFrame(rows, columns=TEAM_COLUMNS).to_csv(output_path, index=False)
    print(f"Exported {output_path.as_posix()}")


def write_settings_csv(output_path: str | Path) -> None:
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    rows = [
        ("weight_combined_epa", WEIGHTS["combined_epa"], "Final score weight for combined match EPA percentile."),
        ("weight_alliance_peak", WEIGHTS["alliance_peak"], "Final score weight for stronger alliance EPA percentile."),
        ("weight_closeness", WEIGHTS["closeness"], "Final score weight for projected EPA margin closeness."),
        ("weight_star_power", WEIGHTS["star_power"], "Final score weight for elite team presence."),
        ("weight_soonness", WEIGHTS["soonness"], "Final score weight for matches happening soon."),
        ("top_team_percentile", PERCENTILES["top_team"], "EPA percentile threshold for top teams in this run."),
        ("elite_team_percentile", PERCENTILES["elite_team"], "EPA percentile threshold for elite teams in this run."),
        ("super_elite_team_percentile", PERCENTILES["super_elite_team"], "EPA percentile threshold for super elite teams in this run."),
    ]
    pd.DataFrame(rows, columns=SETTINGS_COLUMNS).to_csv(output_path, index=False)
    print(f"Exported {output_path.as_posix()}")


def append_run_log(summary: RunSummary, output_path: str | Path) -> None:
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    row = {
        "run_time": summary.run_time,
        "year": summary.year,
        "events_checked": ",".join(summary.events_checked),
        "matches_fetched": summary.matches_fetched,
        "upcoming_matches_exported": summary.upcoming_matches_exported,
        "teams_fetched": summary.teams_fetched,
        "missing_epa_count": summary.missing_epa_count,
        "errors": " | ".join(summary.errors),
        "duration_seconds": summary.duration_seconds,
    }
    existing = pd.read_csv(output_path) if output_path.exists() else pd.DataFrame(columns=RUN_LOG_COLUMNS)
    pd.concat([existing, pd.DataFrame([row], columns=RUN_LOG_COLUMNS)], ignore_index=True).to_csv(output_path, index=False)
    print(f"Exported {output_path.as_posix()}")


def write_support_csvs(teams: list[TeamEPA], summary: RunSummary, output_dir: str | Path, last_updated: str) -> None:
    output_dir = Path(output_dir)
    write_teams_csv(teams, output_dir / "teams.csv", last_updated)
    write_settings_csv(output_dir / "settings.csv")
    append_run_log(summary, output_dir / "run_log.csv")


def write_google_sheet(rows: list[dict], sheet_id: str, worksheet_name: str = "Matches") -> None:
    credentials_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    if not credentials_path:
        raise ValueError("GOOGLE_APPLICATION_CREDENTIALS must point to a service account JSON file")

    import gspread

    client = gspread.service_account(filename=credentials_path)
    spreadsheet = client.open_by_key(sheet_id)

    try:
        worksheet = spreadsheet.worksheet(worksheet_name)
    except gspread.WorksheetNotFound:
        worksheet = spreadsheet.add_worksheet(title=worksheet_name, rows=max(len(rows) + 1, 100), cols=len(MATCH_COLUMNS))

    values = [MATCH_COLUMNS]
    values.extend([[row.get(column, "") for column in MATCH_COLUMNS] for row in rows])
    worksheet.clear()
    if values:
        worksheet.update(values, value_input_option="RAW")
    print(f"Exported Google Sheet worksheet '{worksheet_name}'")
