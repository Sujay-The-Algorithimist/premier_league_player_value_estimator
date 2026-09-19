"""Phase 1 diagnostics for the fixed Premier League time split."""

from __future__ import annotations

from pathlib import Path

import duckdb
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LinearRegression, Ridge
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

PROJECT_ROOT = Path(__file__).resolve().parents[1]
FEATURES_PATH = PROJECT_ROOT / "outputs" / "premier_league_season_features.csv"
DATABASE_PATH = PROJECT_ROOT / "data" / "raw" / "transfermarkt-datasets.duckdb"
RESULTS_DIR = PROJECT_ROOT / "results"

NUMERIC_FEATURES = [
    "appearances", "minutes_played", "goals", "assists", "yellow_cards",
    "red_cards", "clubs_in_season", "height_in_cm", "age_at_season_end",
]
CATEGORICAL_FEATURES = ["position", "sub_position", "foot", "country_of_citizenship"]
TARGET = "target_log_market_value"


def make_preprocessor() -> ColumnTransformer:
    return ColumnTransformer(
        transformers=[
            ("numeric", Pipeline([
                ("impute", SimpleImputer(strategy="median")),
                ("scale", StandardScaler()),
            ]), NUMERIC_FEATURES),
            ("categorical", Pipeline([
                ("impute", SimpleImputer(strategy="most_frequent")),
                ("encode", OneHotEncoder(handle_unknown="ignore")),
            ]), CATEGORICAL_FEATURES),
        ],
        remainder="drop",
    )


def model_pipeline(regressor) -> Pipeline:
    return Pipeline([("preprocessor", make_preprocessor()), ("regressor", regressor)])


def metrics(actual: np.ndarray, predicted: np.ndarray) -> dict[str, float]:
    return {
        "rows": int(len(actual)),
        "r2_log": float(r2_score(actual, predicted)),
        "rmse_log": float(np.sqrt(mean_squared_error(actual, predicted))),
        "mae_log": float(mean_absolute_error(actual, predicted)),
    }


def load_previous_valuations(test: pd.DataFrame) -> pd.DataFrame:
    """Attach each test row's latest valuation strictly before that season ended."""
    with duckdb.connect(str(DATABASE_PATH), read_only=True) as connection:
        valuations = connection.execute(
            "SELECT player_id, date AS previous_valuation_date, market_value_in_eur AS previous_market_value_in_eur FROM player_valuations"
        ).fetchdf()
    valuations["previous_log_value"] = np.log1p(valuations["previous_market_value_in_eur"])
    test_keys = test[["player_id", "season", "season_end"]].copy()
    test_keys["season_end"] = pd.to_datetime(test_keys["season_end"])
    valuations["previous_valuation_date"] = pd.to_datetime(valuations["previous_valuation_date"])
    merged = test_keys.merge(valuations, on="player_id", how="left")
    merged = merged[merged["previous_valuation_date"] < merged["season_end"]]
    previous = (
        merged.sort_values("previous_valuation_date")
        .drop_duplicates(["player_id", "season"], keep="last")
        [["player_id", "season", "previous_valuation_date", "previous_market_value_in_eur", "previous_log_value"]]
    )
    return test_keys.merge(previous, on=["player_id", "season"], how="left")


def main() -> None:
    frame = pd.read_csv(FEATURES_PATH)
    frame["season"] = frame["season"].astype(int)
    seasons = sorted(frame["season"].unique())
    train_seasons, test_seasons = seasons[:-2], seasons[-2:]
    train = frame[frame["season"].isin(train_seasons)].copy()
    test = frame[frame["season"].isin(test_seasons)].copy()
    x_train, x_test = train[NUMERIC_FEATURES + CATEGORICAL_FEATURES], test[NUMERIC_FEATURES + CATEGORICAL_FEATURES]
    y_train, y_test = train[TARGET].to_numpy(), test[TARGET].to_numpy()

    season_levels = frame.groupby("season")[TARGET].agg(row_count="size", mean_log_value="mean", median_log_value="median").reset_index()
    season_levels["split"] = np.where(season_levels["season"].isin(test_seasons), "test", "train")
    season_levels.to_csv(RESULTS_DIR / "phase1_season_levels.csv", index=False)

    models = {
        "constant_baseline": (None, np.full(len(test), y_train.mean())),
        "linear_regression": (model_pipeline(LinearRegression()), None),
        "ridge": (model_pipeline(Ridge(alpha=10.0)), None),
        "random_forest": (model_pipeline(RandomForestRegressor(
            n_estimators=400, min_samples_leaf=2, max_features=0.7, random_state=42, n_jobs=-1,
        )), None),
    }
    predictions = {}
    model_rows = []
    for name, (model, prediction) in models.items():
        if model is not None:
            model.fit(x_train, y_train)
            prediction = model.predict(x_test)
        predictions[name] = prediction
        model_rows.append({"model": name, **metrics(y_test, prediction)})
    model_metrics = pd.DataFrame(model_rows)
    model_metrics.to_csv(RESULTS_DIR / "phase1_model_metrics.csv", index=False)

    rf_prediction = predictions["random_forest"]
    within_rows = []
    for season, group in test.assign(rf_prediction=rf_prediction).groupby("season"):
        actual = group[TARGET].to_numpy()
        predicted = group["rf_prediction"].to_numpy()
        within_rows.append({"season": season, "diagnostic": "within-season RF R2", "rows": len(group), "r2_log": r2_score(actual - actual.mean(), predicted - actual.mean())})
    within = pd.DataFrame(within_rows)
    within.to_csv(RESULTS_DIR / "phase1_within_season_rf.csv", index=False)

    persistence = load_previous_valuations(test)
    persistence_eval = test[["player_id", "season", TARGET]].merge(persistence, on=["player_id", "season"], how="left")
    persistence_eval = persistence_eval.dropna(subset=["previous_log_value"])
    persistence_metrics = pd.DataFrame([{
        "reference": "previous_valuation_before_season_end",
        "rows": len(persistence_eval),
        "coverage_pct": len(persistence_eval) * 100 / len(test),
        **metrics(persistence_eval[TARGET].to_numpy(), persistence_eval["previous_log_value"].to_numpy()),
    }])
    persistence_metrics.to_csv(RESULTS_DIR / "phase1_persistence.csv", index=False)
    persistence_eval.to_csv(RESULTS_DIR / "phase1_persistence_rows.csv", index=False)

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    print("\nPHASE 1A: SEASON LEVELS")
    print(season_levels.to_string(index=False))
    print("\nPHASE 1B: WITHIN-SEASON RF R2 (DIAGNOSTIC ONLY; TEST-SEASON MEANS USED)")
    print(within.to_string(index=False))
    print("\nPHASE 1C: PERSISTENCE REFERENCE (PREVIOUS VALUATION BEFORE SEASON END)")
    print(persistence_metrics.to_string(index=False))
    print("\nPHASE 1D: MODEL COMPARISON")
    print(model_metrics.to_string(index=False))


if __name__ == "__main__":
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    main()