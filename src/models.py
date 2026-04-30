from __future__ import annotations

from pydantic import BaseModel, Field


class TeamEPA(BaseModel):
    team_number: int
    epa: float = 0.0
    epa_source: str = "missing"
    missing_epa: bool = False


class AlliancePrediction(BaseModel):
    team_numbers: list[int]
    team_epas: dict[int, float]
    epa_sum: float
    epa_avg: float
    max_epa: float
    missing_epa_count: int


class MatchPrediction(BaseModel):
    match_key: str
    event_key: str
    division: str
    comp_level: str
    set_number: int | None = None
    match_number: int
    display_time: str | None = None
    display_time_est: str | None = None
    unix_time: int | None = None
    red_teams: list[int]
    blue_teams: list[int]
    red_epa_sum: float
    blue_epa_sum: float
    red_epa_avg: float
    blue_epa_avg: float
    combined_epa: float
    epa_margin: float
    alliance_peak_epa: float
    max_team_epa: float
    top_teams_count: int = 0
    elite_teams_count: int = 0
    super_elite_teams_count: int = 0
    combined_epa_index: float = 0.0
    alliance_peak_index: float = 0.0
    closeness_index: float = 0.0
    star_power_index: float = 0.0
    soonness_index: float = 0.0
    hotness_score: float = 0.0
    hotness_tier: str = "Normal"
    reason_to_watch: str = ""
    missing_epa_count: int = 0
    team_epas: list[float] = Field(default_factory=list, exclude=True)


class RunSummary(BaseModel):
    run_time: str
    year: int
    events_checked: list[str]
    matches_fetched: int = 0
    upcoming_matches_exported: int = 0
    teams_fetched: int = 0
    missing_epa_count: int = 0
    errors: list[str] = Field(default_factory=list)
    duration_seconds: float = 0.0
