export type Verdict = "overvalued" | "undervalued" | "fair";

export interface PlayerRecord {
  id: number;
  name: string;
  club: string;
  position: string;
  season: number;
  age: number;
  minutes: number;
  goals_per90: number;
  assists_per90: number;
  actual_value_eur: number;
  predicted_value_eur: number | null;
  residual_log: number | null;
  verdict: Verdict;
}

export interface ModelMetric {
  name: string;
  r2_log: number;
  rmse_log: number;
  mae_log: number | null;
}

export interface AblationMetric {
  step: string;
  r2_log: number;
  rmse_log: number;
}

export interface GroupMetric {
  group: string;
  rows: number;
  r2_log: number;
  rmse_log: number;
  median_absolute_percentage_error: number;
  mae_eur_millions: number;
}

export interface MetricsData {
  models: ModelMetric[];
  ablation: AblationMetric[];
  by_position: GroupMetric[];
  by_value_band: GroupMetric[];
  split: { train: string; test: string };
}

export interface ScatterPoint {
  actual_value_eur: number;
  predicted_value_eur: number;
}

export interface ResidualBin {
  bin: string;
  count: number;
}

export interface FeatureImportance {
  feature: string;
  importance: number;
}

export interface MetaData {
  dataset_status: "mock" | "real";
  generated_at: string;
  source: string;
  note: string;
  schema_version: string;
}
