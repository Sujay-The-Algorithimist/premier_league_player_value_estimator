"""Phase 4: final evaluation reports for the fixed test seasons."""

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
FEATURES_PATH = PROJECT_ROOT / "results" / "phase3_feature_rows.csv"
RESULTS_DIR = PROJECT_ROOT / "results"
TARGET = "target_log_market_value"

NUMERIC_FEATURES = [
    "age_at_valuation", "age_squared", "minutes_share", "goals_per90_last_two",
    "assists_per90_last_two", "yellow_cards_per90_last_two", "red_cards_per90_last_two",
    "two_year_minutes", "previous_season_points", "finishing_position", "champions_league_played",
]
CATEGORICAL_FEATURES = ["position"]
FEATURE_COLUMNS = NUMERIC_FEATURES + CATEGORICAL_FEATURES


def make_model(regressor, numeric_features: list[str] | None = None) -> Pipeline:
    numeric_features = numeric_features or NUMERIC_FEATURES
    transformer = ColumnTransformer([
        ("numeric", Pipeline([
            ("impute", SimpleImputer(strategy="median")),
            ("scale", StandardScaler()),
        ]), numeric_features),
        ("categorical", Pipeline([
            ("impute", SimpleImputer(strategy="most_frequent")),
            ("encode", OneHotEncoder(handle_unknown="ignore")),
        ]), CATEGORICAL_FEATURES),
    ])
    return Pipeline([("preprocessor", transformer), ("regressor", regressor)])


def median_forecast(train: pd.DataFrame, target_seasons: list[int]) -> dict[int, float]:
    medians = train.groupby("season")[TARGET].median()
    trend = np.polyfit(medians.index.to_numpy(dtype=float), medians.to_numpy(), 1)
    return {
        season: float(medians.loc[season - 1]) if season - 1 in medians.index else float(np.polyval(trend, season - 1))
        for season in target_seasons
    }


def metric_row(actual_eur: pd.Series, predicted_eur: np.ndarray, model: str, scope: str, rows: int | None = None) -> dict:
    actual = np.log1p(actual_eur.to_numpy())
    predicted_log = np.log1p(np.maximum(0, predicted_eur))
    percentage_error = np.abs(predicted_eur - actual_eur.to_numpy()) / actual_eur.to_numpy() * 100
    return {
        "model": model,
        "scope": scope,
        "rows": rows if rows is not None else len(actual),
        "r2_log": r2_score(actual, predicted_log),
        "rmse_log": np.sqrt(mean_squared_error(actual, predicted_log)),
        "median_absolute_percentage_error": np.median(percentage_error),
        "mae_eur_millions": mean_absolute_error(actual_eur, predicted_eur) / 1_000_000,
    }


def main() -> None:
    frame = pd.read_csv(FEATURES_PATH)
    names = pd.read_csv(PROJECT_ROOT / "outputs" / "premier_league_season_features.csv", usecols=["player_id", "name"])
    frame = frame.merge(names.drop_duplicates("player_id"), on="player_id", how="left")
    frame["season"] = frame["season"].astype(int)
    seasons = sorted(frame["season"].unique())
    train_seasons, test_seasons = seasons[:-2], seasons[-2:]
    train = frame[frame["season"].isin(train_seasons)].copy()
    test = frame[frame["season"].isin(test_seasons)].copy()

    predictions = test[["player_id", "name", "season", "position", "target_market_value_in_eur"]].copy()
    predictions["actual_value_eur"] = predictions["target_market_value_in_eur"]
    trend_columns = FEATURE_COLUMNS + ["season"]
    for name, estimator in [("linear", LinearRegression()), ("ridge", Ridge(alpha=10.0))]:
        model = make_model(estimator, NUMERIC_FEATURES + ["season"])
        model.fit(train[trend_columns], train[TARGET])
        prediction_log = model.predict(test[trend_columns])
        predictions[f"{name}_predicted_value_eur"] = np.maximum(0, np.expm1(prediction_log)).round().astype(int)

    offsets = median_forecast(train, test_seasons)
    centered_train = train.copy()
    train_medians = train.groupby("season")[TARGET].median()
    centered_train["offset"] = centered_train["season"].map(lambda season: train_medians.get(season - 1, np.nan))
    centered_train = centered_train.dropna(subset=["offset"])
    centered_train["centered_target"] = centered_train[TARGET] - centered_train["offset"]
    centered_test = test.copy()
    centered_test["offset"] = centered_test["season"].map(offsets)
    forest = make_model(RandomForestRegressor(
        n_estimators=1000, min_samples_leaf=4, max_features=0.5, random_state=42, n_jobs=-1,
    ))
    forest.fit(centered_train[FEATURE_COLUMNS], centered_train["centered_target"])
    forest_log = forest.predict(centered_test[FEATURE_COLUMNS]) + centered_test["offset"].to_numpy()
    predictions["random_forest_predicted_value_eur"] = np.maximum(0, np.expm1(forest_log)).round().astype(int)
    predictions.to_csv(RESULTS_DIR / "phase4_test_predictions.csv", index=False)

    metric_rows = []
    for model in ["linear", "ridge", "random_forest"]:
        prediction = predictions[f"{model}_predicted_value_eur"].to_numpy()
        metric_rows.append(metric_row(predictions["actual_value_eur"], prediction, model, "overall"))
        for position, group in predictions.groupby("position", dropna=False):
            indexes = group.index
            metric_rows.append(metric_row(group["actual_value_eur"], prediction[predictions.index.get_indexer(indexes)], model, f"position:{position}"))
        band = pd.cut(predictions["actual_value_eur"], [-np.inf, 2_000_000, 10_000_000, 30_000_000, np.inf], labels=["<€2M", "€2-10M", "€10-30M", ">€30M"])
        for label, group in predictions.groupby(band, observed=False):
            indexes = group.index
            metric_rows.append(metric_row(group["actual_value_eur"], prediction[predictions.index.get_indexer(indexes)], model, f"value_band:{label}"))
    metrics = pd.DataFrame(metric_rows)
    metrics.to_csv(RESULTS_DIR / "phase4_metrics_by_position_and_band.csv", index=False)

    final_prediction = predictions["random_forest_predicted_value_eur"]
    errors = predictions[["player_id", "name", "season", "position", "actual_value_eur"]].copy()
    errors["predicted_value_eur"] = final_prediction
    errors["error_eur"] = errors["predicted_value_eur"] - errors["actual_value_eur"]
    errors["error_pct"] = errors["error_eur"] / errors["actual_value_eur"] * 100
    overvalued = errors.sort_values("error_pct", ascending=False).head(10).assign(direction="overvalued")
    undervalued = errors.sort_values("error_pct", ascending=True).head(10).assign(direction="undervalued")
    overvalued.to_csv(RESULTS_DIR / "phase4_top10_overvalued.csv", index=False)
    undervalued.to_csv(RESULTS_DIR / "phase4_top10_undervalued.csv", index=False)

    print("\nPHASE 4 OVERALL MODEL METRICS")
    print(metrics[metrics["scope"] == "overall"].to_string(index=False))
    print("\nPHASE 4 METRICS BY POSITION")
    print(metrics[metrics["scope"].str.startswith("position:")].to_string(index=False))
    print("\nPHASE 4 METRICS BY VALUE BAND")
    print(metrics[metrics["scope"].str.startswith("value_band:")].to_string(index=False))
    print("\nPHASE 4 TOP 10 OVERVALUED (RANDOM FOREST)")
    print(overvalued.to_string(index=False))
    print("\nPHASE 4 TOP 10 UNDERVALUED (RANDOM FOREST)")
    print(undervalued.to_string(index=False))


if __name__ == "__main__":
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    main()