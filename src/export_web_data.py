"""Export evaluated model results and reports for the web UI data contract."""

from __future__ import annotations

import json
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATABASE_PATH = PROJECT_ROOT / "data" / "raw" / "transfermarkt-datasets.duckdb"
WEB_DATA_DIR = PROJECT_ROOT / "web" / "public" / "data"
PREDICTIONS_PATH = PROJECT_ROOT / "results" / "phase4_test_predictions.csv"
FEATURE_ROWS_PATH = PROJECT_ROOT / "results" / "phase3_feature_rows.csv"
METRICS_PATH = PROJECT_ROOT / "results" / "phase4_metrics_by_position_and_band.csv"


def write_json(name: str, payload: object) -> None:
    (WEB_DATA_DIR / name).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> None:
    with duckdb.connect(str(DATABASE_PATH), read_only=True) as connection:
        player_names = connection.execute(
            """
            SELECT
                player_id AS id,
                name,
                COALESCE(current_club_name, 'Unknown club') AS club,
                COALESCE(position, 'Unknown') AS position,
                height_in_cm
            FROM players
            WHERE name IS NOT NULL
            ORDER BY player_id
            """
        ).df()

    if not (PREDICTIONS_PATH.exists() and FEATURE_ROWS_PATH.exists() and METRICS_PATH.exists()):
        raise FileNotFoundError("Run python -m src.phase4_reporting before exporting web data.")

    predictions = pd.read_csv(PREDICTIONS_PATH)
    features = pd.read_csv(FEATURE_ROWS_PATH)
    players = predictions.merge(features, on=["player_id", "season", "position"], how="left")
    players = players.merge(player_names.drop_duplicates("id"), left_on="player_id", right_on="id", how="left")
    players["name"] = players["name_x"].fillna(players["name_y"]).fillna("Unknown player")
    players["club"] = players["club"].fillna("Premier League")
    players["age"] = players["age_at_valuation"].round().fillna(0).astype(int)
    players["minutes"] = players["minutes_played"].fillna(0).round().astype(int)
    players["goals_per90"] = (players["goals"].fillna(0) * 90 / players["minutes"].replace(0, np.nan)).fillna(0)
    players["assists_per90"] = (players["assists"].fillna(0) * 90 / players["minutes"].replace(0, np.nan)).fillna(0)
    players["actual_value_eur"] = players["actual_value_eur"].round().astype(int)
    players["predicted_value_eur"] = players["random_forest_predicted_value_eur"].round().astype(int)
    players["residual_log"] = np.log1p(players["predicted_value_eur"]) - np.log1p(players["actual_value_eur"])
    players["verdict"] = np.select(
        [players["predicted_value_eur"] > players["actual_value_eur"] * 1.1, players["predicted_value_eur"] < players["actual_value_eur"] * 0.9],
        ["overvalued", "undervalued"], default="fair",
    )
    fields = ["id", "name", "club", "position", "season", "age", "minutes", "goals_per90", "assists_per90", "actual_value_eur", "predicted_value_eur", "residual_log", "verdict"]
    records = players[fields].sort_values("predicted_value_eur", ascending=False).replace({np.nan: None}).to_dict(orient="records")

    WEB_DATA_DIR.mkdir(parents=True, exist_ok=True)
    metrics = pd.read_csv(METRICS_PATH)
    overall = metrics[metrics["scope"] == "overall"].set_index("model")
    metric_payload = {
        "models": [
            {"name": "Linear Regression", "r2_log": float(overall.loc["linear", "r2_log"]), "rmse_log": float(overall.loc["linear", "rmse_log"]), "mae_log": None},
            {"name": "Ridge", "r2_log": float(overall.loc["ridge", "r2_log"]), "rmse_log": float(overall.loc["ridge", "rmse_log"]), "mae_log": None},
            {"name": "Random Forest", "r2_log": float(overall.loc["random_forest", "r2_log"]), "rmse_log": float(overall.loc["random_forest", "rmse_log"]), "mae_log": None},
        ],
        "ablation": [],
        "by_position": metrics[(metrics.model == "random_forest") & metrics.scope.str.startswith("position:")].assign(group=lambda x: x.scope.str.removeprefix("position:")).drop(columns=["model", "scope"]).to_dict(orient="records"),
        "by_value_band": metrics[(metrics.model == "random_forest") & metrics.scope.str.startswith("value_band:")].assign(group=lambda x: x.scope.str.removeprefix("value_band:")).drop(columns=["model", "scope"]).to_dict(orient="records"),
        "split": {"train": "2012–2023", "test": "2024–2025"},
    }
    scatter = players[["actual_value_eur", "predicted_value_eur"]].to_dict(orient="records")
    histogram = np.histogram(players["residual_log"], bins=10)
    residuals = [{"bin": f"{left:.1f} to {right:.1f}", "count": int(count)} for count, left, right in zip(histogram[0], histogram[1][:-1], histogram[1][1:])]
    write_json("players.json", records)
    write_json("metrics.json", metric_payload)
    write_json("scatter.json", scatter)
    write_json("residuals.json", residuals)
    meta = {
        "dataset_status": "real",
        "generated_at": "2026-09-19",
        "source": "Transfermarkt-based DuckDB snapshot",
        "note": f"{len(records):,} raw player profiles exported. Random Forest predictions are included only where an evaluated model result exists; other profiles show Prediction unavailable.",
        "schema_version": "1.1",
    }
    write_json("meta.json", meta)
    print(json.dumps({"player_records": len(records), "prediction_records": len(prediction_map), "output": str(WEB_DATA_DIR / "players.json")}, indent=2))


if __name__ == "__main__":
    main()
