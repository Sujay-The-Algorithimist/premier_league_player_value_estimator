"""Download and cache the source data used by this project.

We use the publisher's public DuckDB snapshot rather than scraping Transfermarkt.
That makes runs reproducible and avoids making requests to a site whose terms may
not permit automated collection.  The optional football-data.org client caches
each response, so the free API limit is not consumed on repeated runs.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

import duckdb
import requests
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = PROJECT_ROOT / "data" / "raw"
CACHE_DIR = RAW_DIR / "football_data_cache"

# Documented by the dataset publisher. The source is a point-in-time snapshot,
# not a claim that it contains live 2026/27 data.
TRANSFERMARKT_DUCKDB_URL = (
    "https://pub-e682421888d945d684bcae8890b0ec20.r2.dev/data/"
    "transfermarkt-datasets.duckdb"
)
TRANSFERMARKT_DB = RAW_DIR / "transfermarkt-datasets.duckdb"
REQUIRED_TABLES = {"players", "appearances", "games", "competitions", "player_valuations"}


def download_file(url: str, destination: Path, *, force: bool = False) -> Path:
    """Stream a large download to disk and retain it for reproducible reruns."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists() and not force:
        return destination

    temporary = destination.with_suffix(destination.suffix + ".part")
    with requests.get(url, stream=True, timeout=60) as response:
        response.raise_for_status()
        with temporary.open("wb") as file:
            for chunk in response.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    file.write(chunk)
    temporary.replace(destination)
    return destination


def validate_transfermarkt_snapshot(database_path: Path = TRANSFERMARKT_DB) -> dict[str, int]:
    """Fail early if a partial/wrong download would make later analysis misleading."""
    if not database_path.exists():
        raise FileNotFoundError(f"Dataset not found: {database_path}. Run this module with --download.")

    with duckdb.connect(str(database_path), read_only=True) as connection:
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT table_name FROM information_schema.tables WHERE table_schema = 'main'"
            ).fetchall()
        }
        missing = REQUIRED_TABLES - tables
        if missing:
            raise ValueError(f"Dataset is missing expected tables: {sorted(missing)}")
        return {
            table: connection.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0]
            for table in sorted(REQUIRED_TABLES)
        }


def fetch_standings(season_start_year: int, *, force: bool = False) -> dict:
    """Fetch one PL standings response and cache the exact JSON used downstream.

    `season_start_year` is football-data.org's season convention, e.g. 2024 for
    the 2024/25 season.  The API key is deliberately read only from `.env` or the
    process environment, never committed in source code.
    """
    load_dotenv(PROJECT_ROOT / ".env")
    api_key = os.getenv("FOOTBALL_DATA_API_KEY")
    if not api_key:
        raise RuntimeError("Set FOOTBALL_DATA_API_KEY in .env before fetching standings.")

    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_path = CACHE_DIR / f"pl_standings_{season_start_year}.json"
    if cache_path.exists() and not force:
        return json.loads(cache_path.read_text(encoding="utf-8"))

    response = requests.get(
        "https://api.football-data.org/v4/competitions/PL/standings",
        headers={"X-Auth-Token": api_key},
        params={"season": season_start_year},
        timeout=30,
    )
    response.raise_for_status()
    payload = response.json()
    cache_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch/certify raw project data.")
    parser.add_argument("--download", action="store_true", help="Download the published DuckDB snapshot.")
    parser.add_argument("--force", action="store_true", help="Replace a cached file or API response.")
    parser.add_argument("--standings-season", type=int, help="Optionally cache PL standings for this start year.")
    arguments = parser.parse_args()

    if arguments.download:
        path = download_file(TRANSFERMARKT_DUCKDB_URL, TRANSFERMARKT_DB, force=arguments.force)
        print(f"Cached dataset: {path}")
        print(f"Validated rows: {validate_transfermarkt_snapshot(path)}")
    if arguments.standings_season:
        fetch_standings(arguments.standings_season, force=arguments.force)
        print(f"Cached PL standings for {arguments.standings_season}/{str(arguments.standings_season + 1)[-2:]}")


if __name__ == "__main__":
    main()

