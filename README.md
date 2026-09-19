# Premier League Transfer Value Predictor

An explainable ML project that estimates a Premier League player's **market value** from their profile and recent performance. It trains on `log(market_value)` because player values are highly right-skewed, then converts estimates back to pounds for presentation.

## Status

The complete project is included:

1. Data validation and EDA
2. Leakage-safe season-level feature engineering
3. Baseline, linear, ridge, and Random Forest comparisons
4. Time-based evaluation on the 2024–25 holdout seasons
5. Player-level error reports and model diagnostics
6. FastAPI prediction endpoint
7. React valuation interface with player explorer, insights, method, and live prediction screens

The checked-in web export contains 1,048 held-out player-season evaluations. It is historical, static data—not a live transfer market feed.

## Data choices

### Primary source: publisher-provided Transfermarkt snapshot

The project uses the public `davidcariboo/player-scores` dataset through the publisher's DuckDB snapshot, not a scraper. The data contains linked `players`, `appearances`, `games`, `competitions`, and historical `player_valuations` tables. This preserves a stable ID across the core data and avoids fragile name-only joins.

As checked on **19 September 2026**, upstream updates are paused: valuations end on **12 June 2026**, appearances on **28 June 2026**, and games on **6 July 2026**. It therefore supports completed historical seasons and early 2026/27 context only; it must not be represented as a current 2026/27 valuation source. We will select the first valuation after each season's end, subject to a documented maximum gap, rather than attaching a current value to old statistics.

### Optional club context: football-data.org

`football-data.org` can add cached Premier League standings. Put a personal key in `.env` (start from `.env.example`); no secret is stored in Git. The API client writes every response under `data/raw/football_data_cache/` and reuses it by default. Since historic standings availability can vary by plan, the linked dataset's completed-season results remain the fallback for club strength.

## Setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m src.data_fetch --download
```

## Run the completed app

After installing the Python requirements, refresh all pipeline reports and web data:

```powershell
python -m src.phase1_diagnostics
python -m src.phase2_level_shift
python -m src.phase3_features
python -m src.phase4_reporting
python -m src.export_web_data
```

Start the API in one terminal:

```powershell
uvicorn api.app:app --reload
```

Start the frontend in another:

```powershell
cd web
npm install
npm run dev
```

Open `http://localhost:5173`. The prediction screen expects the API at `http://localhost:8000`; set `VITE_API_URL` to change that address.

## Deploy the app

Deploy the two parts separately:

1. Create a Render Web Service from the repository root using `render.yaml`. Render installs `api/requirements.txt` and starts `api.app:app`.
2. Set Render's `ALLOWED_ORIGINS` environment variable to the final Vercel URL, for example `https://your-project.vercel.app`.
3. Create a Vercel project from the same repository with `web` as the project root. The checked-in `web/vercel.json` builds the Vite app and rewrites client-side routes to `index.html`.
4. In Vercel, set `VITE_API_URL` to the public Render URL, for example `https://your-api.onrender.com`, then redeploy.

The Render service rebuilds the Phase 4 Random Forest from the tracked engineered feature file at startup. The ignored raw DuckDB download is not required by the deployed API.

Raw downloads and cached API responses are intentionally excluded from Git. `--download` is idempotent; use `--force` only to replace a cached snapshot.

## Why the initial source choice matters

The model target must be known at the prediction timestamp. For every player-season row we will retain the valuation date and enforce:

```
season statistics end  <=  valuation date  <=  fixed post-season tolerance
```

Rows without a valuation in that window will be reported and excluded from supervised training rather than silently back-filled with a later value. Player IDs provide the principal match key; name, date of birth, and club will be used only for any external augmentation, with match-rate and unmatched-player reports.

## Limitations

Statistics do not observe injuries, agent negotiations, brand value, transfer clauses, or every contract detail. The result is an analytical estimate, not a fair price or a recommendation to buy/sell a player.
