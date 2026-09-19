"""Profile the raw snapshot with explicit coverage and join diagnostics."""

from __future__ import annotations

import json
from pathlib import Path

import duckdb

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATABASE_PATH = PROJECT_ROOT / "data" / "raw" / "transfermarkt-datasets.duckdb"
OUTPUT_DIR = PROJECT_ROOT / "outputs"

TABLES = [
    "players",
    "appearances",
    "games",
    "competitions",
    "player_valuations",
]
DATE_COLUMNS = {
    "players": ["date_of_birth", "contract_expiration_date"],
    "appearances": ["date"],
    "games": ["date"],
    "player_valuations": ["date"],
}


def fetch_rows(connection: duckdb.DuckDBPyConnection, query: str) -> list[dict]:
    result = connection.execute(query)
    columns = [column[0] for column in result.description]
    return [dict(zip(columns, row)) for row in result.fetchall()]


def scalar(connection: duckdb.DuckDBPyConnection, query: str):
    return connection.execute(query).fetchone()[0]


def profile_table(connection: duckdb.DuckDBPyConnection, table: str) -> dict:
    columns = fetch_rows(connection, f"DESCRIBE {table}")
    row_count = scalar(connection, f"SELECT COUNT(*) FROM {table}")
    nulls = []
    for column in columns:
        name = column["column_name"]
        null_count = scalar(connection, f'SELECT COUNT(*) FROM {table} WHERE "{name}" IS NULL')
        nulls.append(
            {
                "column": name,
                "type": column["column_type"],
                "null_count": null_count,
                "null_pct": round(null_count * 100 / row_count, 4) if row_count else 0.0,
            }
        )

    dates = []
    for column in DATE_COLUMNS.get(table, []):
        minimum, maximum = connection.execute(
            f'SELECT MIN("{column}"), MAX("{column}") FROM {table}'
        ).fetchone()
        dates.append({"column": column, "min": str(minimum) if minimum else None, "max": str(maximum) if maximum else None})
    return {"row_count": row_count, "nulls": nulls, "date_ranges": dates}


def build_audit() -> dict:
    with duckdb.connect(str(DATABASE_PATH), read_only=True) as connection:
        tables = {table: profile_table(connection, table) for table in TABLES}
        join_queries = {
            "appearances_player": """SELECT COUNT(*) AS source_rows, COUNT(*) FILTER (WHERE p.player_id IS NOT NULL) AS matched_rows
                FROM appearances a LEFT JOIN players p ON a.player_id = p.player_id""",
            "appearances_game": """SELECT COUNT(*) AS source_rows, COUNT(*) FILTER (WHERE g.game_id IS NOT NULL) AS matched_rows
                FROM appearances a LEFT JOIN games g ON CAST(a.game_id AS VARCHAR) = g.game_id""",
            "appearances_competition": """SELECT COUNT(*) AS source_rows, COUNT(*) FILTER (WHERE c.competition_id IS NOT NULL) AS matched_rows
                FROM appearances a LEFT JOIN competitions c ON a.competition_id = c.competition_id""",
            "valuations_player": """SELECT COUNT(*) AS source_rows, COUNT(*) FILTER (WHERE p.player_id IS NOT NULL) AS matched_rows
                FROM player_valuations v LEFT JOIN players p ON v.player_id = p.player_id""",
            "valuations_positive_value": """SELECT COUNT(*) AS source_rows, COUNT(*) FILTER (WHERE market_value_in_eur > 0) AS matched_rows
                FROM player_valuations""",
        }
        joins = {}
        for name, query in join_queries.items():
            result = fetch_rows(connection, query)[0]
            joins[name] = {
                "source_rows": result["source_rows"],
                "matched_rows": result["matched_rows"],
                "unmatched_rows": result["source_rows"] - result["matched_rows"],
                "match_pct": round(result["matched_rows"] * 100 / result["source_rows"], 4),
            }
        duplicates = {
            "players_duplicate_player_ids": scalar(
                connection,
                "SELECT COUNT(*) FROM (SELECT player_id FROM players GROUP BY player_id HAVING COUNT(*) > 1)",
            ),
            "games_duplicate_game_ids": scalar(
                connection,
                "SELECT COUNT(*) FROM (SELECT game_id FROM games GROUP BY game_id HAVING COUNT(*) > 1)",
            ),
            "valuations_duplicate_player_date": scalar(
                connection,
                """SELECT COUNT(*) FROM (
                    SELECT player_id, date FROM player_valuations
                    GROUP BY player_id, date HAVING COUNT(*) > 1
                )""",
            ),
        }
        valuation_distribution = fetch_rows(
            connection,
            """SELECT
                COUNT(*) AS rows,
                COUNT(*) FILTER (WHERE market_value_in_eur IS NULL) AS null_values,
                MIN(market_value_in_eur) AS minimum_eur,
                MAX(market_value_in_eur) AS maximum_eur,
                QUANTILE_CONT(market_value_in_eur, 0.01) AS p01_eur,
                QUANTILE_CONT(market_value_in_eur, 0.25) AS p25_eur,
                QUANTILE_CONT(market_value_in_eur, 0.50) AS p50_eur,
                QUANTILE_CONT(market_value_in_eur, 0.75) AS p75_eur,
                QUANTILE_CONT(market_value_in_eur, 0.99) AS p99_eur,
                AVG(market_value_in_eur) AS mean_eur
            FROM player_valuations""",
        )[0]
        season_counts = fetch_rows(
            connection,
            "SELECT season, COUNT(*) AS game_rows FROM games GROUP BY season ORDER BY season",
        )
        valuation_year_counts = fetch_rows(
            connection,
            "SELECT YEAR(date) AS valuation_year, COUNT(*) AS valuation_rows FROM player_valuations GROUP BY valuation_year ORDER BY valuation_year",
        )
    return {
        "database": str(DATABASE_PATH),
        "tables": tables,
        "join_coverage": joins,
        "duplicate_group_counts": duplicates,
        "valuation_distribution": valuation_distribution,
        "game_rows_by_season": season_counts,
        "valuation_rows_by_year": valuation_year_counts,
    }


def format_value(value) -> str:
    if value is None:
        return "NULL"
    if isinstance(value, float):
        return f"{value:,.4f}"
    return f"{value:,}" if isinstance(value, int) else str(value)


def render_markdown(audit: dict) -> str:
    lines = ["# Exploratory Data Audit", "", f"Source: `{audit['database']}`", ""]
    lines += ["## Table row counts and date ranges", "", "| Table | Rows | Date column | Minimum | Maximum |", "|---|---:|---|---|---|"]
    for table, profile in audit["tables"].items():
        ranges = profile["date_ranges"] or [{"column": "-", "min": "-", "max": "-"}]
        for index, date_range in enumerate(ranges):
            lines.append(
                f"| {table if index == 0 else ''} | {profile['row_count'] if index == 0 else ''} | "
                f"{date_range['column']} | {date_range['min']} | {date_range['max']} |"
            )
    lines += ["", "## Null percentages", "", "| Table | Column | Type | Null rows | Null % |", "|---|---|---|---:|---:|"]
    for table, profile in audit["tables"].items():
        for null in profile["nulls"]:
            lines.append(f"| {table} | {null['column']} | {null['type']} | {null['null_count']:,} | {null['null_pct']:.4f}% |")
    lines += ["", "## Join coverage", "", "| Check | Source rows | Matched rows | Unmatched rows | Match % |", "|---|---:|---:|---:|---:|"]
    for check, values in audit["join_coverage"].items():
        lines.append(f"| {check} | {values['source_rows']:,} | {values['matched_rows']:,} | {values['unmatched_rows']:,} | {values['match_pct']:.4f}% |")
    lines += ["", "## Duplicate key groups", "", "| Check | Groups |", "|---|---:|"]
    for check, value in audit["duplicate_group_counts"].items():
        lines.append(f"| {check} | {value:,} |")
    lines += ["", "## Valuation distribution (EUR)", "", "| Rows | Null values | Minimum | P01 | P25 | Median | P75 | P99 | Maximum | Mean |", "|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
    distribution = audit["valuation_distribution"]
    lines.append("| " + " | ".join(format_value(distribution[key]) for key in ["rows", "null_values", "minimum_eur", "p01_eur", "p25_eur", "p50_eur", "p75_eur", "p99_eur", "maximum_eur", "mean_eur"]) + " |")
    lines += ["", "## Game rows by season", "", "| Season | Game rows |", "|---|---:|"]
    lines.extend(f"| {row['season']} | {row['game_rows']:,} |" for row in audit["game_rows_by_season"])
    lines += ["", "## Valuation rows by year", "", "| Year | Valuation rows |", "|---:|---:|"]
    lines.extend(f"| {row['valuation_year']} | {row['valuation_rows']:,} |" for row in audit["valuation_rows_by_year"])
    return "\n".join(lines) + "\n"


def main() -> None:
    audit = build_audit()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUTPUT_DIR / "eda_audit.json").write_text(json.dumps(audit, indent=2, default=str), encoding="utf-8")
    (OUTPUT_DIR / "eda_audit.md").write_text(render_markdown(audit), encoding="utf-8")
    print(render_markdown(audit))


if __name__ == "__main__":
    main()