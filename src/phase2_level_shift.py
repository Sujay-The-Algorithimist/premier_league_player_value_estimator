"""Phase 2: correct season-level target shifts without test leakage."""

from __future__ import annotations

from pathlib import Path

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
RESULTS_DIR = PROJECT_ROOT / "results"
TARGET = "target_log_market_value"
NUMERIC_FEATURES = [
    "appearances", "minutes_played", "goals", "assists", "yellow_cards",
    "red_cards", "clubs_in_season", "height_in_cm", "age_at_season_end",
]
CATEGORICAL_FEATURES = ["position", "sub_position", "foot", "country_of_citizenship"]
FEATURE_COLUMNS = NUMERIC_FEATURES + CATEGORICAL_FEATURES


def preprocessor(numeric_features: list[str] | None = None) -> ColumnTransformer:
    numeric_features = numeric_features or NUMERIC_FEATURES
    return ColumnTransformer([
        ("numeric", Pipeline([
            ("impute", SimpleImputer(strategy="median")),
            ("scale", StandardScaler()),
        ]), numeric_features),
        ("categorical", Pipeline([
            ("impute", SimpleImputer(strategy="most_frequent")),
            ("encode", OneHotEncoder(handle_unknown="ignore")),
        ]), CATEGORICAL_FEATURES),
    ])


def pipeline(regressor, numeric_features: list[str] | None = None) -> Pipeline:
    return Pipeline([("preprocessor", preprocessor(numeric_features)), ("regressor", regressor)])


def score(actual: np.ndarray, predicted: np.ndarray) -> dict[str, float]:
    return {
        "rows": len(actual),
        "r2_log": r2_score(actual, predicted),
        "rmse_log": np.sqrt(mean_squared_error(actual, predicted)),
        "mae_log": mean_absolute_error(actual, predicted),
    }


def training_median_forecast(train: pd.DataFrame, seasons: list[int], target_seasons: list[int]) -> dict[int, float]:
    """Forecast season medians using only medians from the training split."""
    medians = train.groupby("season")[TARGET].median()
    trend = np.polyfit(np.array(medians.index, dtype=float), medians.to_numpy(), 1)
    forecasts = {}
    for season in target_seasons:
        previous_season = season - 1
        if previous_season in medians.index:
            forecasts[season] = float(medians.loc[previous_season])
        else:
            forecasts[season] = float(np.polyval(trend, previous_season))
    return forecasts


def main() -> None:
    frame = pd.read_csv(FEATURES_PATH)
    frame["season"] = frame["season"].astype(int)
    seasons = sorted(frame["season"].unique())
    train_seasons, test_seasons = seasons[:-2], seasons[-2:]
    train = frame[frame["season"].isin(train_seasons)].copy()
    test = frame[frame["season"].isin(test_seasons)].copy()

    # Validation is the final training season; the test seasons remain untouched.
    validation_season = train_seasons[-1]
    fit_seasons = train_seasons[:-1]
    fit = train[train["season"].isin(fit_seasons)].copy()
    validation = train[train["season"] == validation_season].copy()
    validation_baselines = training_median_forecast(fit, fit_seasons, [validation_season])
    validation_offset = validation_baselines[validation_season]
    validation_rows = []

    rows = []
    # Option A: year trend is an input feature for linear and Ridge only.
    for name, estimator in [("linear_trend", LinearRegression()), ("ridge_trend", Ridge(alpha=10.0))]:
        trend_features = FEATURE_COLUMNS + ["season"]
        validation_model = pipeline(estimator, NUMERIC_FEATURES + ["season"])
        validation_model.fit(fit[trend_features], fit[TARGET])
        validation_prediction = validation_model.predict(validation[trend_features])
        validation_rows.append({"option": "a_season_trend", "model": name.replace("_trend", ""), "validation_season": validation_season, **score(validation[TARGET], validation_prediction)})
        final_model = pipeline(estimator, NUMERIC_FEATURES + ["season"])
        final_model.fit(train[trend_features], train[TARGET])
        prediction = final_model.predict(test[trend_features])
        rows.append({"option": "a_season_trend", "model": name.replace("_trend", ""), **score(test[TARGET], prediction)})

    # Option B: center target by a previous-season median estimated from training only.
    training_medians = train.groupby("season")[TARGET].median()
    test_offsets = training_median_forecast(train, train_seasons, test_seasons)
    centered_fit = fit.copy()
    centered_fit["previous_median_offset"] = centered_fit["season"].map(
        lambda season: training_medians.get(season - 1, np.nan)
    )
    centered_fit = centered_fit.dropna(subset=["previous_median_offset"])
    centered_fit["centered_target"] = centered_fit[TARGET] - centered_fit["previous_median_offset"]
    centered_train = train.copy()
    centered_train["previous_median_offset"] = centered_train["season"].map(
        lambda season: training_medians.get(season - 1, np.nan)
    )
    centered_train = centered_train.dropna(subset=["previous_median_offset"])
    centered_train["centered_target"] = centered_train[TARGET] - centered_train["previous_median_offset"]
    test["previous_median_offset"] = test["season"].map(test_offsets)
    for name, estimator in [
        ("linear_previous_median", LinearRegression()),
        ("ridge_previous_median", Ridge(alpha=10.0)),
        ("random_forest_previous_median", RandomForestRegressor(
            n_estimators=400, min_samples_leaf=2, max_features=0.7, random_state=42, n_jobs=-1,
        )),
    ]:
        validation_model = pipeline(estimator)
        validation_model.fit(centered_fit[FEATURE_COLUMNS], centered_fit["centered_target"])
        validation_prediction = validation_model.predict(validation[FEATURE_COLUMNS]) + validation_offset
        validation_rows.append({"option": "b_previous_season_median", "model": name.replace("_previous_median", ""), "validation_season": validation_season, **score(validation[TARGET], validation_prediction)})
        final_model = pipeline(estimator)
        final_model.fit(centered_train[FEATURE_COLUMNS], centered_train["centered_target"])
        prediction = final_model.predict(test[FEATURE_COLUMNS]) + test["previous_median_offset"].to_numpy()
        rows.append({"option": "b_previous_season_median", "model": name.replace("_previous_median", ""), **score(test[TARGET], prediction)})

    comparison = pd.DataFrame(rows)
    comparison.to_csv(RESULTS_DIR / "phase2_level_shift_comparison.csv", index=False)
    validation_metrics = pd.DataFrame(validation_rows)
    validation_metrics.to_csv(RESULTS_DIR / "phase2_validation_metrics.csv", index=False)
    validation_offsets = pd.DataFrame([{
        "validation_season": validation_season,
        "offset_log_value": validation_offset,
        "source": "median of fit seasons only",
    }])
    validation_offsets.to_csv(RESULTS_DIR / "phase2_validation_offsets.csv", index=False)
    offsets = pd.DataFrame([{"season": season, "offset_log_value": offset, "source": "training-only previous median or extrapolated training trend"} for season, offset in test_offsets.items()])
    offsets.to_csv(RESULTS_DIR / "phase2_test_offsets.csv", index=False)

    print("\nPHASE 2 VALIDATION METRICS (2023; FIT ON 2012-2022)")
    print(validation_metrics.to_string(index=False))
    print("\nPHASE 2 VALIDATION OFFSET SOURCE")
    print(validation_offsets.to_string(index=False))
    print("\nPHASE 2 TEST OFFSETS (NO TEST TARGETS USED)")
    print(offsets.to_string(index=False))
    print("\nPHASE 2 LEVEL-SHIFT COMPARISON")
    print(comparison.to_string(index=False))


if __name__ == "__main__":
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    main()