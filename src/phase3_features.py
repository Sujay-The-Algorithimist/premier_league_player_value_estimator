"""Phase 3: add valuation-time features and run the requested ablation."""

from __future__ import annotations

from pathlib import Path

import duckdb
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.metrics import mean_squared_error, r2_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

PROJECT_ROOT = Path(__file__).resolve().parents[1]
FEATURES_PATH = PROJECT_ROOT / "outputs" / "premier_league_season_features.csv"
DATABASE_PATH = PROJECT_ROOT / "data" / "raw" / "transfermarkt-datasets.duckdb"
RESULTS_DIR = PROJECT_ROOT / "results"
FEATURES_OUTPUT = RESULTS_DIR / "phase3_feature_rows.csv"
ABLATION_OUTPUT = RESULTS_DIR / "phase3_ablation.csv"
LEAKAGE_OUTPUT = RESULTS_DIR / "phase3_dropped_leakage_columns.csv"
TARGET = "target_log_market_value"


def query_data() -> tuple[pd.DataFrame, ...]:
    with duckdb.connect(str(DATABASE_PATH), read_only=True) as connection:
        target_rows = pd.read_csv(FEATURES_PATH)
        connection.register("target_rows", target_rows)
        performance = connection.execute(
            """
            SELECT
                a.player_id,
                g.season::INTEGER AS season,
                a.player_club_id AS club_id,
                SUM(a.minutes_played) AS minutes_played,
                SUM(a.goals) AS goals,
                SUM(a.assists) AS assists,
                SUM(a.yellow_cards) AS yellow_cards,
                SUM(a.red_cards) AS red_cards,
                COUNT(DISTINCT a.game_id) AS appearances,
                MAX(g.date) AS last_match_date
            FROM appearances a
            INNER JOIN games g ON CAST(a.game_id AS VARCHAR) = g.game_id
            WHERE g.competition_id = 'GB1'
            GROUP BY a.player_id, g.season, a.player_club_id
            """
        ).fetchdf()
        all_performance = connection.execute(
            """
            SELECT
                a.player_id,
                g.season::INTEGER AS season,
                SUM(a.minutes_played) AS minutes_played,
                SUM(a.goals) AS goals,
                SUM(a.assists) AS assists,
                SUM(a.yellow_cards) AS yellow_cards,
                SUM(a.red_cards) AS red_cards
            FROM appearances a
            INNER JOIN games g ON CAST(a.game_id AS VARCHAR) = g.game_id
            WHERE g.competition_id = 'GB1'
            GROUP BY a.player_id, g.season
            """
        ).fetchdf()
        clubs = connection.execute(
            """
            WITH club_games AS (
                SELECT season::INTEGER AS season, home_club_id AS club_id, game_id, home_club_goals AS goals_for, away_club_goals AS goals_against,
                    CASE WHEN home_club_goals > away_club_goals THEN 3 WHEN home_club_goals = away_club_goals THEN 1 ELSE 0 END AS points
                FROM games WHERE competition_id = 'GB1'
                UNION ALL
                SELECT season::INTEGER, away_club_id, game_id, away_club_goals, home_club_goals,
                    CASE WHEN away_club_goals > home_club_goals THEN 3 WHEN away_club_goals = home_club_goals THEN 1 ELSE 0 END
                FROM games WHERE competition_id = 'GB1'
            ),
            standings AS (
                SELECT season, club_id, SUM(points) AS previous_season_points,
                    SUM(goals_for) - SUM(goals_against) AS goal_difference
                FROM club_games
                GROUP BY season, club_id
            )
            SELECT season, club_id, previous_season_points,
                RANK() OVER (PARTITION BY season ORDER BY previous_season_points DESC, goal_difference DESC) AS finishing_position,
                COUNT(*) OVER (PARTITION BY season) AS clubs_in_standings
            FROM standings
            """
        ).fetchdf()
        player_meta = connection.execute(
            "SELECT player_id, date_of_birth, position, sub_position FROM players"
        ).fetchdf()
        club_schedule = connection.execute(
            """
            SELECT season::INTEGER AS season, club_id, COUNT(DISTINCT game_id) AS club_games
            FROM (
                SELECT season, home_club_id AS club_id, game_id FROM games WHERE competition_id = 'GB1'
                UNION ALL
                SELECT season, away_club_id AS club_id, game_id FROM games WHERE competition_id = 'GB1'
            )
            GROUP BY season, club_id
            """
        ).fetchdf()
        cl_appearances = connection.execute(
            """
            SELECT a.player_id, g.season::INTEGER AS season, g.date AS cl_date
            FROM appearances a
            INNER JOIN games g ON CAST(a.game_id AS VARCHAR) = g.game_id
            WHERE g.competition_id = 'CL'
            """
        ).fetchdf()
    return target_rows, performance, all_performance, clubs, player_meta, cl_appearances, club_schedule


def build_rows() -> pd.DataFrame:
    target, performance, all_performance, clubs, player_meta, cl_appearances, club_schedule = query_data()
    target["season"] = target["season"].astype(int)
    target["valuation_date"] = pd.to_datetime(target["valuation_date"])
    target["season_end"] = pd.to_datetime(target["season_end"])
    player_meta["date_of_birth"] = pd.to_datetime(player_meta["date_of_birth"])

    rows = target[["player_id", "season", "season_end", "valuation_date", TARGET, "target_market_value_in_eur"]].copy()
    rows = rows.merge(player_meta, on="player_id", how="left")
    rows["age_at_valuation"] = (rows["valuation_date"] - rows["date_of_birth"]).dt.days / 365.25
    rows["age_squared"] = rows["age_at_valuation"] ** 2

    season_team_games = club_schedule.rename(columns={"club_games": "club_available_games"})
    current = performance.sort_values("last_match_date").drop_duplicates(["player_id", "season"], keep="last")
    current = current[["player_id", "season", "club_id"]].rename(columns={"club_id": "current_club_id"})
    rows = rows.merge(current, on=["player_id", "season"], how="left")

    target_perf = performance.groupby(["player_id", "season"], as_index=False).agg(
        minutes_played=("minutes_played", "sum"), goals=("goals", "sum"), assists=("assists", "sum"),
        yellow_cards=("yellow_cards", "sum"), red_cards=("red_cards", "sum"), appearances=("appearances", "sum"),
    )
    target_available = performance.groupby(["player_id", "season"], as_index=False).agg(
        player_club_count=("club_id", "nunique"),
    )
    target_available = target_available.merge(
        performance.groupby(["player_id", "season"], as_index=False)["club_id"].unique(),
        on=["player_id", "season"],
    )
    target_available["available_minutes"] = target_available.apply(
        lambda row: sum(
            season_team_games.loc[
                (season_team_games["season"] == row["season"])
                & season_team_games["club_id"].isin(row["club_id"]),
                "club_available_games",
            ]
        ) * 90,
        axis=1,
    )
    target_perf = target_perf.merge(target_available[["player_id", "season", "available_minutes"]], on=["player_id", "season"])
    target_perf["minutes_share"] = target_perf["minutes_played"] / target_perf["available_minutes"].replace(0, np.nan)
    rows = rows.merge(target_perf, on=["player_id", "season"], how="left")

    all_season = all_performance.set_index(["player_id", "season"])
    last_two = []
    for row in rows[["player_id", "season"]].itertuples(index=False):
        pieces = all_season.reindex([(row.player_id, row.season), (row.player_id, row.season - 1)]).dropna(subset=["minutes_played"])
        minutes = pieces["minutes_played"].sum()
        values = {"player_id": row.player_id, "season": row.season, "two_year_minutes": minutes}
        for statistic in ["goals", "assists", "yellow_cards", "red_cards"]:
            values[f"{statistic}_per90_last_two"] = pieces[statistic].sum() * 90 / minutes if minutes else np.nan
        last_two.append(values)
    rows = rows.merge(pd.DataFrame(last_two), on=["player_id", "season"], how="left")

    previous_strength = clubs.rename(columns={"season": "strength_season", "club_id": "current_club_id"}).copy()
    rows["strength_season"] = rows["season"] - 1
    rows = rows.merge(previous_strength, on=["strength_season", "current_club_id"], how="left")
    cl_appearances = cl_appearances.rename(columns={"season": "cl_season"})
    cl_appearances["cl_date"] = pd.to_datetime(cl_appearances["cl_date"])
    rows["champions_league_played"] = rows.apply(
        lambda row: int(((cl_appearances["player_id"] == row["player_id"])
                         & (cl_appearances["cl_season"] == row["season"])
                         & (cl_appearances["cl_date"] <= row["valuation_date"])).any()),
        axis=1,
    )
    return rows.drop(columns=["date_of_birth", "current_club_id", "strength_season", "club_id"], errors="ignore")


def make_model(numeric: list[str], categorical: list[str]) -> Pipeline:
    transformer = ColumnTransformer([
        ("numeric", Pipeline([("impute", SimpleImputer(strategy="median")), ("scale", StandardScaler())]), numeric),
        ("categorical", Pipeline([("impute", SimpleImputer(strategy="most_frequent")), ("encode", OneHotEncoder(handle_unknown="ignore"))]), categorical),
    ])
    return Pipeline([("preprocessor", transformer), ("regressor", RandomForestRegressor(n_estimators=400, min_samples_leaf=2, max_features=0.7, random_state=42, n_jobs=-1))])


def main() -> None:
    rows = build_rows()
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    rows.to_csv(FEATURES_OUTPUT, index=False)
    dropped = pd.DataFrame({"dropped_column": [
        "highest_market_value_in_eur", "market_value_in_eur", "international_caps", "international_goals",
        "current_club_name", "contract_expiration_date", "previous_market_value", "previous_valuation",
    ], "reason": ["leakage rule"] * 8})
    dropped.to_csv(LEAKAGE_OUTPUT, index=False)

    seasons = sorted(rows["season"].astype(int).unique())
    train_seasons, test_seasons = seasons[:-2], seasons[-2:]
    train = rows[rows["season"].isin(train_seasons)].copy()
    test = rows[rows["season"].isin(test_seasons)].copy()
    validation_season = train_seasons[-1]
    fit = train[train["season"] < validation_season]
    validation = train[train["season"] == validation_season]

    ablations = [
        ("1_age_position_minutes", ["age_at_valuation", "age_squared", "minutes_share"], ["position"]),
        ("2_plus_performance", ["age_at_valuation", "age_squared", "minutes_share", "goals_per90_last_two", "assists_per90_last_two", "yellow_cards_per90_last_two", "red_cards_per90_last_two", "two_year_minutes"], ["position"]),
        ("3_plus_club_strength", ["age_at_valuation", "age_squared", "minutes_share", "goals_per90_last_two", "assists_per90_last_two", "yellow_cards_per90_last_two", "red_cards_per90_last_two", "two_year_minutes", "previous_season_points", "finishing_position", "champions_league_played"], ["position"]),
    ]
    results = []
    for name, numeric, categorical in ablations:
        model = make_model(numeric, categorical)
        model.fit(fit[numeric + categorical], fit[TARGET])
        validation_prediction = model.predict(validation[numeric + categorical])
        final_model = make_model(numeric, categorical)
        final_model.fit(train[numeric + categorical], train[TARGET])
        test_prediction = final_model.predict(test[numeric + categorical])
        results.append({"ablation": name, "validation_season": validation_season, "validation_rows": len(validation), "validation_r2_log": r2_score(validation[TARGET], validation_prediction), "validation_rmse_log": np.sqrt(mean_squared_error(validation[TARGET], validation_prediction)), "test_rows": len(test), "test_r2_log": r2_score(test[TARGET], test_prediction), "test_rmse_log": np.sqrt(mean_squared_error(test[TARGET], test_prediction))})
    ablation_results = pd.DataFrame(results)
    ablation_results.to_csv(ABLATION_OUTPUT, index=False)

    print("\nPHASE 3 LEAKAGE DROPS")
    print(dropped.to_string(index=False))
    print("\nPHASE 3 FEATURE COVERAGE")
    print(pd.DataFrame({"rows": [len(rows)], "columns": [len(rows.columns)], "train_rows": [len(train)], "validation_rows": [len(validation)], "test_rows": [len(test)], "null_age_pct": [rows["age_at_valuation"].isna().mean() * 100], "null_club_points_pct": [rows["previous_season_points"].isna().mean() * 100]}).to_string(index=False))
    print("\nPHASE 3 ABLATION RESULTS")
    print(ablation_results.to_string(index=False))


if __name__ == "__main__":
    main()