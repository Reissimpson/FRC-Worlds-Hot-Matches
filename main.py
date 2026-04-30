from __future__ import annotations

import argparse
import os
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

from src.export import write_google_sheet, write_matches_csv, write_support_csvs
from src.pipeline import run_pipeline
from src.statbotics_client import StatboticsClient
from src.tba_client import TBAClient


DEFAULT_OUTPUT_DIR = Path("output")
DEFAULT_MATCHES_CSV = DEFAULT_OUTPUT_DIR / "worlds_hot_matches.csv"


def current_year() -> int:
    return datetime.now().year


def parse_events(value: str | None) -> list[str]:
    if not value:
        return []
    return [event.strip() for event in value.split(",") if event.strip()]


def read_events_file(path: str | None) -> list[str]:
    if not path:
        return []
    events: list[str] = []
    with open(path, "r", encoding="utf-8") as handle:
        for line in handle:
            event = line.strip()
            if event and not event.startswith("#"):
                events.append(event)
    return events


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Rank upcoming FRC Worlds matches by hotness.")
    parser.add_argument("--year", type=int, default=None, help="FRC season year. Defaults to SEASON_YEAR or current year.")
    parser.add_argument("--events", default=None, help="Comma-separated TBA event keys.")
    parser.add_argument("--events-file", default=None, help="File with one TBA event key per line.")
    parser.add_argument("--output", default=str(DEFAULT_MATCHES_CSV), help="Path for the main matches CSV.")
    parser.add_argument("--google-sheet-id", default=None, help="Optional Google Sheet ID to update the Matches worksheet.")
    return parser.parse_args()


def main() -> int:
    load_dotenv()
    args = parse_args()

    year = args.year or int(os.getenv("SEASON_YEAR") or current_year())
    events = parse_events(args.events) + read_events_file(args.events_file)
    events = list(dict.fromkeys(events))
    if not events:
        raise SystemExit("Provide --events or --events-file.")

    tba_auth_key = os.getenv("TBA_AUTH_KEY", "")
    tba_client = TBAClient(tba_auth_key)
    statbotics_client = StatboticsClient()

    predictions, teams, summary = run_pipeline(year, events, tba_client, statbotics_client)
    last_updated = datetime.now(timezone.utc).isoformat()
    rows = write_matches_csv(predictions, args.output, last_updated, teams)
    write_support_csvs(teams, summary, DEFAULT_OUTPUT_DIR, last_updated)

    if args.google_sheet_id:
        write_google_sheet(rows, args.google_sheet_id)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
