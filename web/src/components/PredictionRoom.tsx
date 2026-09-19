import { useState } from "react";
import type { FormEvent } from "react";
import { motion } from "framer-motion";

interface PredictionResponse {
  predicted_value_eur: number;
  model: string;
  target: string;
}

interface PredictionForm {
  season: number;
  age_at_valuation: number;
  age_squared: number;
  minutes_share: number;
  goals_per90_last_two: number;
  assists_per90_last_two: number;
  yellow_cards_per90_last_two: number;
  red_cards_per90_last_two: number;
  two_year_minutes: number;
  previous_season_points: number;
  finishing_position: number;
  champions_league_played: number;
  position: string;
}

const numericFields = [
  { key: "age_at_valuation", label: "Age at valuation", step: "0.01" },
  { key: "age_squared", label: "Age squared", step: "0.01" },
  { key: "minutes_share", label: "Minutes share", step: "0.0001" },
  { key: "goals_per90_last_two", label: "Goals / 90 (last 2 seasons)", step: "0.0001" },
  { key: "assists_per90_last_two", label: "Assists / 90 (last 2 seasons)", step: "0.0001" },
  { key: "yellow_cards_per90_last_two", label: "Yellow cards / 90 (last 2 seasons)", step: "0.0001" },
  { key: "red_cards_per90_last_two", label: "Red cards / 90 (last 2 seasons)", step: "0.0001" },
  { key: "two_year_minutes", label: "Two-year minutes", step: "1" },
  { key: "previous_season_points", label: "Previous season points", step: "1" },
  { key: "finishing_position", label: "Finishing position", step: "1" },
  { key: "champions_league_played", label: "Champions League played", step: "1" },
] as const satisfies ReadonlyArray<{ key: keyof Omit<PredictionForm, "season" | "position">; label: string; step: string }>;

const initialForm: PredictionForm = {
  season: 2025,
  age_at_valuation: 24.26,
  age_squared: 588.55,
  minutes_share: 0.7152,
  goals_per90_last_two: 0.2859,
  assists_per90_last_two: 0.2691,
  yellow_cards_per90_last_two: 0.2354,
  red_cards_per90_last_two: 0.0,
  two_year_minutes: 5352,
  previous_season_points: 60,
  finishing_position: 7,
  champions_league_played: 0,
  position: "Attack",
};

const apiUrl = import.meta.env.VITE_API_URL ?? "http://localhost:8000";
const positions = ["Attack", "Defender", "Goalkeeper", "Midfield"];

function money(value: number): string {
  return `EUR ${(value / 1_000_000).toFixed(1)}M`;
}

export function PredictionRoom() {
  const [form, setForm] = useState<PredictionForm>(initialForm);
  const [result, setResult] = useState<PredictionResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const updateNumber = (key: keyof Omit<PredictionForm, "season" | "position">, value: string) =>
    setForm((current) => ({ ...current, [key]: Number(value) }));

  const updateText = (key: "position", value: string) =>
    setForm((current) => ({ ...current, [key]: value }));

  async function submit(event: FormEvent) {
    event.preventDefault();
    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const response = await fetch(`${apiUrl}/predict`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(form),
      });

      if (!response.ok) {
        throw new Error(`Prediction service returned ${response.status}`);
      }

      setResult((await response.json()) as PredictionResponse);
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? `${requestError.message}. Start the API with: uvicorn api.app:app --reload`
          : "Prediction service unavailable.",
      );
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="prediction-room" aria-labelledby="prediction-title">
      <div className="prediction-intro">
        <p className="kicker">AI valuation room / live model endpoint</p>
        <h1 id="prediction-title">What is this player worth?</h1>
        <p>Send the same Phase 4 engineered inputs used by the Random Forest pipeline to the Python API.</p>
        <span className="api-status">Endpoint: {apiUrl}/predict</span>
      </div>

      <div className="prediction-layout">
        <form className="prediction-form" onSubmit={submit}>
          <div className="form-section">
            <span>Phase 4 model inputs</span>
            <div className="form-grid">
              <label>
                Season
                <input
                  type="number"
                  min={2012}
                  max={2030}
                  value={form.season}
                  onChange={(event) => setForm((current) => ({ ...current, season: Number(event.target.value) }))}
                />
              </label>

              {numericFields.map(({ key, label, step }) => (
                <label key={key}>
                  {label}
                  <input
                    type="number"
                    min="0"
                    step={step}
                    value={form[key]}
                    onChange={(event) => updateNumber(key, event.target.value)}
                  />
                </label>
              ))}

              <label>
                Position
                <select value={form.position} onChange={(event) => updateText("position", event.target.value)}>
                  {positions.map((item) => (
                    <option key={item} value={item}>
                      {item}
                    </option>
                  ))}
                </select>
              </label>
            </div>
          </div>

          <button className="button button-primary predict-button" disabled={loading}>
            {loading ? "Analysing model signal..." : "Run valuation →"}
          </button>

          {error && <p className="api-error" role="alert">{error}</p>}
        </form>

        <motion.aside className="prediction-result" animate={{ opacity: result ? 1 : 0.55 }}>
          <span>Phase 4 Random Forest</span>
          {result ? (
            <>
              <strong>{money(result.predicted_value_eur)}</strong>
              <p>Estimated market value</p>
              <small>Generated by the live Python prediction service.</small>
            </>
          ) : (
            <>
              <strong>--</strong>
              <p>Awaiting player inputs</p>
              <small>Submit the inputs to reveal the model estimate.</small>
            </>
          )}
        </motion.aside>
      </div>
    </section>
  );
}
