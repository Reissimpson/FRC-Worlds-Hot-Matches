from __future__ import annotations

from datetime import datetime, timezone
from statistics import mean

from src.models import MatchPrediction


WEIGHTS = {
    "combined_epa": 0.35,
    "alliance_peak": 0.25,
    "closeness": 0.20,
    "star_power": 0.15,
    "soonness": 0.05,
}

PERCENTILES = {
    "top_team": 90,
    "elite_team": 95,
    "super_elite_team": 99,
}


def division_name(event_key: str) -> str:
    mapping = {
        "arc": "Archimedes",
        "cur": "Curie",
        "dal": "Daly",
        "gal": "Galileo",
        "hop": "Hopper",
        "joh": "Johnson",
        "mil": "Milstein",
        "new": "Newton",
    }
    suffix = event_key[-3:].lower() if event_key else ""
    return mapping.get(suffix, event_key)


def closeness_index(margin: float) -> float:
    if margin <= 3:
        return 100.0
    if margin <= 6:
        return 90.0
    if margin <= 10:
        return 75.0
    if margin <= 15:
        return 55.0
    if margin <= 20:
        return 35.0
    return 15.0


def soonness_index(unix_time: int | None, now: datetime | None = None) -> float:
    if not unix_time:
        return 0.0
    now = now or datetime.now(timezone.utc)
    match_time = datetime.fromtimestamp(unix_time, tz=timezone.utc)
    minutes_until_match = (match_time - now).total_seconds() / 60

    if minutes_until_match < -5:
        return 0.0
    if minutes_until_match <= 0:
        return 100.0
    if minutes_until_match <= 15:
        return 90.0
    if minutes_until_match <= 45:
        return 70.0
    if minutes_until_match <= 90:
        return 45.0
    if minutes_until_match <= 360:
        return 20.0
    return 5.0


def hotness_tier(score: float) -> str:
    if score >= 85:
        return "Must Watch"
    if score >= 70:
        return "Great"
    if score >= 55:
        return "Good"
    return "Normal"


def percentile(values: list[float], percentile_value: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    position = (len(ordered) - 1) * (percentile_value / 100)
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    fraction = position - lower
    return ordered[lower] + (ordered[upper] - ordered[lower]) * fraction


def percentile_indexes(values: list[float]) -> list[float]:
    if not values:
        return []
    if len(values) == 1:
        return [100.0]

    ordered = sorted(values)
    indexes: list[float] = []
    denominator = len(values) - 1
    for value in values:
        matching_positions = [i for i, ordered_value in enumerate(ordered) if ordered_value == value]
        rank_position = mean(matching_positions)
        indexes.append(round(100 * rank_position / denominator, 3))
    return indexes


def star_power_index(top_count: int, elite_count: int, super_elite_count: int) -> float:
    raw = 8 * top_count + 15 * elite_count + 25 * super_elite_count
    return float(min(raw, 100))


def score_matches(matches: list[MatchPrediction], all_team_epas: list[float], now: datetime | None = None) -> list[MatchPrediction]:
    combined_indexes = percentile_indexes([match.combined_epa for match in matches])
    peak_indexes = percentile_indexes([match.alliance_peak_epa for match in matches])

    top_threshold = percentile(all_team_epas, PERCENTILES["top_team"])
    elite_threshold = percentile(all_team_epas, PERCENTILES["elite_team"])
    super_elite_threshold = percentile(all_team_epas, PERCENTILES["super_elite_team"])

    for match, combined_index, peak_index in zip(matches, combined_indexes, peak_indexes):
        match.top_teams_count = sum(1 for epa in match.team_epas if epa >= top_threshold and epa > 0)
        match.elite_teams_count = sum(1 for epa in match.team_epas if epa >= elite_threshold and epa > 0)
        match.super_elite_teams_count = sum(1 for epa in match.team_epas if epa >= super_elite_threshold and epa > 0)

        match.combined_epa_index = combined_index
        match.alliance_peak_index = peak_index
        match.closeness_index = closeness_index(match.epa_margin)
        match.star_power_index = star_power_index(
            match.top_teams_count,
            match.elite_teams_count,
            match.super_elite_teams_count,
        )
        match.soonness_index = soonness_index(match.unix_time, now)
        match.hotness_score = round(
            WEIGHTS["combined_epa"] * match.combined_epa_index
            + WEIGHTS["alliance_peak"] * match.alliance_peak_index
            + WEIGHTS["closeness"] * match.closeness_index
            + WEIGHTS["star_power"] * match.star_power_index
            + WEIGHTS["soonness"] * match.soonness_index,
            2,
        )
        match.hotness_tier = hotness_tier(match.hotness_score)
        match.reason_to_watch = reason_to_watch(match)

    return matches


def reason_to_watch(match: MatchPrediction) -> str:
    label = f"{match.hotness_tier}: {match.division} QM{match.match_number}"
    traits: list[str] = []
    if match.epa_margin <= 6:
        traits.append(f"a close {match.epa_margin:.1f} EPA margin")
    if match.combined_epa_index >= 80:
        traits.append(f"high combined EPA ({match.combined_epa:.1f})")
    if match.alliance_peak_index >= 85:
        stronger = "red" if match.red_epa_sum >= match.blue_epa_sum else "blue"
        traits.append(f"a powerhouse {stronger} alliance")
    if match.elite_teams_count >= 2:
        traits.append(f"{match.elite_teams_count} elite-EPA teams")
    soon = match.soonness_index >= 70

    if not traits and not soon:
        return f"{label} is a solid upcoming match with a combined EPA of {match.combined_epa:.1f}."

    if not traits and soon:
        reason = f"{label} is happening soon."
    elif len(traits) == 1 and soon:
        reason = f"{label} features {traits[0]} and is happening soon."
    elif len(traits) == 1:
        reason = f"{label} features {traits[0]}."
    elif soon:
        reason = f"{label} features {', '.join(traits[:-1])}, and {traits[-1]}; it is happening soon."
    else:
        reason = f"{label} features {', '.join(traits[:-1])}, and {traits[-1]}."

    if len(reason) > 240:
        reason = f"{label} projects as a strong match: {match.combined_epa:.1f} combined EPA, {match.epa_margin:.1f} EPA margin."
    return reason
