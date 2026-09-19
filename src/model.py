"""Train time-split baseline and linear market-value models."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.pipeline import Pipeline
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import OneHotEncoder, StandardScaler

PROJECT_ROOT = Path(__file__).resolve().parents[1]
FEATURES_PATH = PROJECT_ROOT / "outputs" / "premier_league_season_features.csv"
OUTPUT_DIR = PROJECT_ROOT / "outputs"
METRICS_PATH = OUTPUT_DIR / "model_metrics.json"
PREDICTIONS_PATH = OUTPUT_DIR / "model_predictions.csv"

NUMERIC_FEATURES = [
    "appearances",
    "minutes_played",
    "goals",
    "assists",
    "yellow_cards",
    "red_cards",
    "clubs_in_season",
    "height_in_cm",
    "age_at_season_end",
]
CATEGORICAL_FEATURES = ["position", "sub_position", "foot", "country_of_citizenship"]
TARGET = "target_log_market_value"


def regression_metrics(actual: np.ndarray, predicted: np.ndarray) -> dict[str, float]:
    actual_eur = np.expm1(actual)
    predicted_eur = np.maximum(0, np.expm1(predicted))
    return {
        "rows": int(len(actual)),
        "rmse_log_eur": float(np.sqrt(mean_squared_error(actual, predicted))),
        "mae_log_eur": float(mean_absolute_error(actual, predicted)),
        "r2_log_eur": float(r2_score(actual, predicted)),
        "mae_eur": float(mean_absolute_error(actual_eur, predicted_eur)),
        "median_absolute_error_eur": float(np.median(np.abs(actual_eur - predicted_eur))),
    }


def train_models(features_path: Path = FEATURES_PATH) -> dict:
    frame = pd.read_csv(features_path)
    seasons = [int(season) for season in sorted(frame["season"].astype(int).unique())]
    if len(seasons) < 3:
        raise ValueError("At least three seasons are required for a time split.")
    test_seasons = seasons[-2:]
    train_seasons = seasons[:-2]
    train = frame[frame["season"].isin(train_seasons)].copy()
    test = frame[frame["season"].isin(test_seasons)].copy()

    feature_columns = NUMERIC_FEATURES + CATEGORICAL_FEATURES
    x_train = train[feature_columns]
    x_test = test[feature_columns]
    y_train = train[TARGET].to_numpy()
    y_test = test[TARGET].to_numpy()

    baseline_prediction = np.full(len(test), y_train.mean())
    preprocessor = ColumnTransformer(
        transformers=[
            (
                "numeric",
                Pipeline(
                    [
                        ("impute", SimpleImputer(strategy="median")),
                        ("scale", StandardScaler()),
                    ]
                ),
                NUMERIC_FEATURES,
            ),
            (
                "categorical",
                Pipeline(
                    [
                        ("impute", SimpleImputer(strategy="most_frequent")),
                        ("encode", OneHotEncoder(handle_unknown="ignore")),
                    ]
                ),
                CATEGORICAL_FEATURES,
            ),
        ],
        remainder="drop",
    )
    model = Pipeline(
        steps=[
            ("preprocessor", preprocessor),
            ("regressor", Ridge(alpha=10.0)),
        ]
    )
    model.fit(x_train, y_train)
    linear_prediction = model.predict(x_test)
    random_forest = Pipeline(
        steps=[
            ("preprocessor", preprocessor),
            (
                "regressor",
                RandomForestRegressor(
                    n_estimators=400,
                    min_samples_leaf=2,
                    max_features=0.7,
                    random_state=42,
                    n_jobs=-1,
                ),
            ),
        ]
    )
    random_forest.fit(x_train, y_train)
    forest_prediction = random_forest.predict(x_test)

    predictions = test[["player_id", "season", "name", "target_market_value_in_eur"]].copy()
    predictions["baseline_predicted_market_value_in_eur"] = np.maximum(0, np.expm1(baseline_prediction)).round().astype("int64")
    predictions["linear_predicted_market_value_in_eur"] = np.maximum(0, np.expm1(linear_prediction)).round().astype("int64")
    predictions["random_forest_predicted_market_value_in_eur"] = np.maximum(0, np.expm1(forest_prediction)).round().astype("int64")
    predictions.to_csv(PREDICTIONS_PATH, index=False)

    metrics = {
        "selected_model": "random_forest",
        "train_seasons": train_seasons,
        "test_seasons": test_seasons,
        "train_rows": len(train),
        "test_rows": len(test),
        "features": feature_columns,
        "baseline": regression_metrics(y_test, baseline_prediction),
        "ridge_linear": regression_metrics(y_test, linear_prediction),
        "random_forest": regression_metrics(y_test, forest_prediction),
    }
    METRICS_PATH.write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    return metrics


def main() -> None:
    metrics = train_models()
    print(json.dumps(metrics, indent=2))


if __name__ == "__main__":
    main()