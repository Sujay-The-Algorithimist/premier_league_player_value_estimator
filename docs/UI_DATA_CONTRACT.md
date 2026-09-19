# UI Data Contract

The UI reads static JSON from `web/public/data/`. Phase 1 files are intentionally mock exports and are labeled by `meta.json`. Components must consume these typed payloads through the data-loading hook instead of embedding metrics.

## `meta.json`

Top-level dataset state and provenance. `dataset_status` is `mock` until real Python exports replace the files. `source`, `generated_at`, `note`, and `schema_version` are displayed or available for the Method page.

## `players.json`

An array of player-season records. Each record has `id`, `name`, `club`, `position`, `season`, `age`, `minutes`, `goals_per90`, `assists_per90`, `actual_value_eur`, `predicted_value_eur`, `residual_log`, and `verdict`. `verdict` is one of `overvalued`, `undervalued`, or `fair`.

## `metrics.json`

Contains `models` for model comparison, `ablation` for feature-step comparison, `by_position` and `by_value_band` for segmented evaluation, and `split` with train/test season labels. Group metric rows contain `group`, `rows`, `r2_log`, `rmse_log`, `median_absolute_percentage_error`, and `mae_eur_millions`.

## `scatter.json`

An array of `{ actual_value_eur, predicted_value_eur }` points for the actual-vs-predicted chart.

## `residuals.json`

An array of histogram bins with `{ bin, count }`.

## `importance.json`

An array of `{ feature, importance }` rows for the model feature-importance chart.

## Replacing mock data

Generate the same filenames and field shapes from the Python pipeline, copy them into `web/public/data/`, and change `meta.dataset_status` to `real` only after checking the exports against the production result tables. The UI should not need component changes.
