"""Build leakage-safe Premier League season-level modeling rows."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import duckdb

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATABASE_PATH = PROJECT_ROOT / "data" / "raw" / "transfermarkt-datasets.duckdb"
OUTPUT_DIR = PROJECT_ROOT / "outputs"
FEATURES_PATH = OUTPUT_DIR / "premier_league_season_features.csv"
AUDIT_PATH = OUTPUT_DIR / "feature_build_audit.json"


FEATURE_QUERY = """
WITH season_games AS (
    SELECT
        competition_id,
        season,
        MAX(date) AS season_end,
        COUNT(*) AS competition_games
    FROM games
    WHERE competition_id = 'GB1'
    GROUP BY competition_id, season
),
performance AS (
    SELECT
        a.player_id,
        g.competition_id,
        g.season,
        MAX(g.season_end) AS season_end,
        COUNT(*) AS appearances,
        SUM(a.minutes_played) AS minutes_played,
        SUM(a.goals) AS goals,
        SUM(a.assists) AS assists,
        SUM(a.yellow_cards) AS yellow_cards,
        SUM(a.red_cards) AS red_cards,
        COUNT(DISTINCT a.player_club_id) AS clubs_in_season
    FROM appearances a
    INNER JOIN (
        SELECT
            g.game_id,
            g.competition_id,
            g.season,
            g.date,
            sg.season_end
        FROM games g
        INNER JOIN season_games sg
            ON g.competition_id = sg.competition_id AND g.season = sg.season
    ) g ON CAST(a.game_id AS VARCHAR) = g.game_id
    WHERE g.competition_id = 'GB1'
    GROUP BY a.player_id, g.competition_id, g.season
),
candidate_valuations AS (
    SELECT
        p.player_id,
        p.season,
        p.season_end,
        v.date AS valuation_date,
        v.market_value_in_eur,
        ROW_NUMBER() OVER (
            PARTITION BY p.player_id, p.season
            ORDER BY v.date
        ) AS valuation_rank
    FROM performance p
    INNER JOIN player_valuations v
        ON v.player_id = p.player_id
        AND v.date > p.season_end
        AND v.date <= p.season_end + INTERVAL 120 DAY
),
selected_valuations AS (
    SELECT player_id, season, valuation_date, market_value_in_eur
    FROM candidate_valuations
    WHERE valuation_rank = 1
)
SELECT
    p.player_id,
    p.season,
    p.competition_id,
    p.season_end,
    p.appearances,
    p.minutes_played,
    p.goals,
    p.assists,
    p.yellow_cards,
    p.red_cards,
    p.clubs_in_season,
    pl.name,
    pl.position,
    pl.sub_position,
    pl.foot,
    pl.height_in_cm,
    pl.country_of_citizenship,
    pl.date_of_birth,
    ROUND(date_diff('day', pl.date_of_birth, p.season_end) / 365.25, 2) AS age_at_season_end,
    v.valuation_date,
    date_diff('day', p.season_end, v.valuation_date) AS valuation_gap_days,
    v.market_value_in_eur AS target_market_value_in_eur,
    LN(v.market_value_in_eur + 1) AS target_log_market_value
FROM performance p
INNER JOIN players pl ON p.player_id = pl.player_id
INNER JOIN selected_valuations v
    ON p.player_id = v.player_id AND p.season = v.season
ORDER BY p.season, p.player_id
"""


def build_features(database_path: Path = DATABASE_PATH, output_path: Path = FEATURES_PATH) -> dict:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with duckdb.connect(str(database_path), read_only=True) as connection:
        frame = connection.execute(FEATURE_QUERY).fetchdf()
        performance_rows = connection.execute(
            """SELECT COUNT(*) FROM (
                SELECT a.player_id, g.season
                FROM appearances a
                INNER JOIN games g ON CAST(a.game_id AS VARCHAR) = g.game_id
                WHERE g.competition_id = 'GB1'
                GROUP BY a.player_id, g.season
            )"""
        ).fetchone()[0]
        candidate_rows = connection.execute(
            """SELECT COUNT(*) FROM (
                SELECT DISTINCT a.player_id, g.season
                FROM appearances a
                INNER JOIN games g ON CAST(a.game_id AS VARCHAR) = g.game_id
                INNER JOIN (
                    SELECT season, MAX(date) AS season_end
                    FROM games
                    WHERE competition_id = 'GB1'
                    GROUP BY season
                ) sg ON g.season = sg.season
                INNER JOIN player_valuations v ON v.player_id = a.player_id
                WHERE g.competition_id = 'GB1'
                  AND v.date > sg.season_end
                  AND v.date <= sg.season_end + INTERVAL 120 DAY
            )"""
        ).fetchone()[0]
    frame.to_csv(output_path, index=False)
    audit = {
        "competition_id": "GB1",
        "valuation_window_days": 120,
        "performance_rows": performance_rows,
        "rows_with_valuation_target": len(frame),
        "performance_rows_without_target": performance_rows - len(frame),
        "candidate_rows_in_valuation_window": candidate_rows,
        "columns": list(frame.columns),
        "season_end_min": str(frame["season_end"].min()) if len(frame) else None,
        "season_end_max": str(frame["season_end"].max()) if len(frame) else None,
        "valuation_date_min": str(frame["valuation_date"].min()) if len(frame) else None,
        "valuation_date_max": str(frame["valuation_date"].max()) if len(frame) else None,
        "null_counts": frame.isna().sum().astype(int).to_dict(),
    }
    AUDIT_PATH.write_text(json.dumps(audit, indent=2), encoding="utf-8")
    return audit


def main() -> None:
    parser = argparse.ArgumentParser(description="Build leakage-safe Premier League season features.")
    parser.add_argument("--database", type=Path, default=DATABASE_PATH)
    parser.add_argument("--output", type=Path, default=FEATURES_PATH)
    args = parser.parse_args()
    audit = build_features(args.database, args.output)
    print(json.dumps(audit, indent=2))


if __name__ == "__main__":
    main()