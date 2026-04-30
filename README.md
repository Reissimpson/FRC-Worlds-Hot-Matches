# FRC Worlds Hot Matches

A small Python data pipeline that ranks upcoming FRC World Championship matches by "hotness" across multiple divisions.

The script fetches upcoming match schedules from The Blue Alliance, fetches team EPA values from Statbotics, calculates a deterministic hotness score, and exports AppSheet-friendly data files.

## What It Produces

Default output:

```text
output/worlds_hot_matches.csv
```

AppSheet support tables:

```text
output/teams.csv
output/settings.csv
output/run_log.csv
```

Optional Google Sheets export writes the main match table to a worksheet named `Matches`.

## Setup

Create and activate a virtual environment:

```bash
python -m venv .venv
.venv\Scripts\activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Copy the example environment file:

```bash
copy .env.example .env
```

## The Blue Alliance API Key

1. Sign in at [thebluealliance.com](https://www.thebluealliance.com/).
2. Open your account page.
3. Create a TBA API v3 key.
4. Put it in `.env`:

```env
TBA_AUTH_KEY=your_tba_key_here
SEASON_YEAR=2026
```

`SEASON_YEAR` is optional. If it is not set, the script uses the current year.

## Run With Inline Events

```bash
python main.py --year 2026 --events 2026arc,2026cur,2026dal,2026gal,2026hop,2026joh,2026mil,2026new
```

## Run With an Events File

```bash
python main.py --year 2026 --events-file config/worlds_events_2026.txt
```

The events file contains one TBA event key per line.

## Google Sheets Export

CSV export remains the default and is always written. To also update Google Sheets:

```bash
python main.py --year 2026 --events-file config/worlds_events_2026.txt --google-sheet-id SHEET_ID
```

Google Sheets setup:

1. Create a Google Cloud service account.
2. Enable the Google Sheets API for the project.
3. Create and download a service account JSON key.
4. Share the target Google Sheet with the service account email address.
5. Add the credential path to `.env`:

```env
GOOGLE_APPLICATION_CREDENTIALS=path/to/service-account.json
```

The script clears and rewrites a worksheet named `Matches` using the same columns as `output/worlds_hot_matches.csv`.

## Import CSV Into Google Sheets

1. Open Google Sheets.
2. Create or open a spreadsheet.
3. Choose **File > Import**.
4. Upload `output/worlds_hot_matches.csv`.
5. Choose replace current sheet or insert new sheet.

For AppSheet, keep the header row unchanged.

The match CSV includes readable alliance slots:

```text
red_1, red_2, red_3, blue_1, blue_2, blue_3
```

Each slot also has helper columns for formatting:

```text
red_1_epa, red_1_epa_percentile, red_1_epa_color
```

The same pattern exists for all six team slots. Teams at or above the 95th EPA percentile in the current run get a blue color value. Other teams get a red-to-yellow-to-green color value based on EPA percentile.

## Connect to AppSheet

1. Create an AppSheet app from the Google Sheet.
2. Use `Matches` or the imported `worlds_hot_matches.csv` sheet as the main table.
3. Add `teams`, `settings`, and `run_log` as additional tables if you want team metadata, scoring settings, and run history.
4. Suggested views:
   - Live watch list sorted by `watch_order`.
   - Hottest overall sorted by `hotness_rank`.
   - Team lookup from `teams.csv`.
   - Run diagnostics from `run_log.csv`.

## AppSheet Team Highlighting

Use the separated team slot columns in the `Matches` table:

```text
red_1, red_2, red_3, blue_1, blue_2, blue_3
```

For a simple top-team highlight, create AppSheet format rules like:

```text
[red_1_epa_percentile] >= 95
```

Apply that rule to the `red_1` column and choose a blue highlight. Repeat for `red_2`, `red_3`, `blue_1`, `blue_2`, and `blue_3`.

For a red-to-green effect in AppSheet, create several percentile bucket rules for each team slot. For example, for `red_1`:

```text
[red_1_epa_percentile] < 20
[red_1_epa_percentile] >= 20 AND [red_1_epa_percentile] < 40
[red_1_epa_percentile] >= 40 AND [red_1_epa_percentile] < 60
[red_1_epa_percentile] >= 60 AND [red_1_epa_percentile] < 80
[red_1_epa_percentile] >= 80 AND [red_1_epa_percentile] < 95
[red_1_epa_percentile] >= 95
```

Use red, orange, yellow, light green, green, and blue respectively. The CSV also includes `red_1_epa_color` and matching color columns for each slot if you want to use the generated hex colors in Google Sheets or another visualization layer.

## Hotness Formula

Each match receives five component indexes from 0 to 100:

```text
hotness_score =
  0.35 * combined_epa_index
+ 0.25 * alliance_peak_index
+ 0.20 * closeness_index
+ 0.15 * star_power_index
+ 0.05 * soonness_index
```

Components:

- `combined_epa_index`: percentile rank of total red plus blue EPA across upcoming matches in the run.
- `alliance_peak_index`: percentile rank of the stronger alliance EPA sum.
- `closeness_index`: fixed score from the projected EPA margin.
- `star_power_index`: counts teams above the run's 90th, 95th, and 99th percentile EPA thresholds.
- `soonness_index`: favors matches happening now or soon.

Tiers:

```text
85+ = Must Watch
70+ = Great
55+ = Good
else = Normal
```

The `reason_to_watch` text is deterministic and does not use an LLM.

## AppSheet Support Tables

`output/teams.csv` contains one row per team seen in the current run:

```text
team_number, epa, epa_source, missing_epa, last_updated
```

`output/settings.csv` documents the scoring weights and percentile thresholds.

`output/run_log.csv` appends one row per run with timing, event count, exported match count, missing EPA count, and errors.

## Known Limitations

- v1 only exports upcoming qualification matches.
- EPA availability depends on the Statbotics team-year endpoint.
- Match timing depends on TBA `predicted_time`, `actual_time`, or `time`.
- Google Sheets export only writes the `Matches` worksheet; support tables are currently CSV-only.
- The pipeline is designed for local/manual runs, not scheduled hosting yet.
