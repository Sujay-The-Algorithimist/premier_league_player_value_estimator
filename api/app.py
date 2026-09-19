from __future__ import annotations

import os
from pathlib import Path

import numpy as np
import pandas as pd
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

PROJECT_ROOT = Path(__file__).resolve().parents[1]
FEATURES_PATH = PROJECT_ROOT / "results" / "phase3_feature_rows.csv"
TARGET = "target_log_market_value"
NUMERIC_FEATURES = [
    "age_at_valuation",
    "age_squared",
    "minutes_share",
    "goals_per90_last_two",
    "assists_per90_last_two",
    "yellow_cards_per90_last_two",
    "red_cards_per90_last_two",
    "two_year_minutes",
    "previous_season_points",
    "finishing_position",
    "champions_league_played",
]
CATEGORICAL_FEATURES = ["position"]
FEATURE_COLUMNS = NUMERIC_FEATURES + CATEGORICAL_FEATURES


def median_forecast(train: pd.DataFrame, target_seasons: list[int]) -> dict[int, float]:
    medians = train.groupby("season")[TARGET].median()
    trend = np.polyfit(medians.index.to_numpy(dtype=float), medians.to_numpy(), 1)
    return {
        season: float(medians.loc[season - 1]) if season - 1 in medians.index else float(np.polyval(trend, season - 1))
        for season in target_seasons
    }


class PredictionRequest(BaseModel):
    season: int = Field(ge=2012, le=2030)
    age_at_valuation: float = Field(ge=15.0, le=45.0)
    age_squared: float = Field(ge=225.0, le=2025.0)
    minutes_share: float = Field(ge=0.0, le=1.5)
    goals_per90_last_two: float = Field(ge=0.0, le=3.0)
    assists_per90_last_two: float = Field(ge=0.0, le=3.0)
    yellow_cards_per90_last_two: float = Field(ge=0.0, le=2.0)
    red_cards_per90_last_two: float = Field(ge=0.0, le=1.0)
    two_year_minutes: float = Field(ge=0.0, le=7000.0)
    previous_season_points: float | None = Field(default=None, ge=0.0, le=120.0)
    finishing_position: int | None = Field(default=None, ge=1, le=20)
    champions_league_played: int = Field(ge=0, le=10)
    position: str


def build_model() -> tuple[Pipeline, dict[int, float]]:
    frame = pd.read_csv(FEATURES_PATH)
    if TARGET not in frame.columns:
        raise ValueError(f"Expected {TARGET} in {FEATURES_PATH}")
    seasons = sorted(frame["season"].astype(int).unique())
    train_seasons, test_seasons = seasons[:-2], seasons[-2:]
    train = frame[frame["season"].isin(train_seasons)].copy()
    offsets = median_forecast(train, test_seasons)

    centered_train = train.copy()
    train_medians = train.groupby("season")[TARGET].median()
    centered_train["offset"] = centered_train["season"].map(lambda season: train_medians.get(season - 1, np.nan))
    centered_train = centered_train.dropna(subset=["offset"])
    centered_train["centered_target"] = centered_train[TARGET] - centered_train["offset"]

    preprocessor = ColumnTransformer([
        (
            "numeric",
            Pipeline([("impute", SimpleImputer(strategy="median")), ("scale", StandardScaler())]),
            NUMERIC_FEATURES,
        ),
        (
            "categorical",
            Pipeline([("impute", SimpleImputer(strategy="most_frequent")), ("encode", OneHotEncoder(handle_unknown="ignore"))]),
            CATEGORICAL_FEATURES,
        ),
    ])
    model = Pipeline([
        ("preprocessor", preprocessor),
        (
            "regressor",
            RandomForestRegressor(
                n_estimators=1000,
                min_samples_leaf=4,
                max_features=0.5,
                random_state=42,
                n_jobs=-1,
            ),
        ),
    ])
    model.fit(centered_train[FEATURE_COLUMNS], centered_train["centered_target"])
    return model, offsets


model, season_offsets = build_model()
app = FastAPI(title="Player Value AI API", version="1.0.0")
allowed_origins = [origin.strip() for origin in os.getenv("ALLOWED_ORIGINS", "http://localhost:5173").split(",") if origin.strip()]
app.add_middleware(CORSMiddleware, allow_origins=allowed_origins, allow_credentials=False, allow_methods=["GET", "POST"], allow_headers=["*"])


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "model": "Phase 4 Random Forest"}


@app.post("/predict")
def predict(payload: PredictionRequest) -> dict[str, float | str]:
    row = payload.model_dump()
    offset = season_offsets.get(int(row["season"]), float(np.median(list(season_offsets.values()))))
    values = pd.DataFrame([row])[FEATURE_COLUMNS]
    predicted_centered_log = float(model.predict(values)[0])
    predicted_log = predicted_centered_log + offset
    predicted_value = max(0.0, float(np.expm1(predicted_log)))
    return {
        "predicted_value_eur": round(predicted_value),
        "model": "Phase 4 Random Forest",
        "target": "market value in euros",
    }