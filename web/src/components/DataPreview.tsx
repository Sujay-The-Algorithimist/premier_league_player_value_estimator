import type { MetricsData, PlayerRecord } from "../types";

interface DataPreviewProps {
  players: PlayerRecord[];
  metrics: MetricsData;
}

function formatMillions(value: number): string {
  return `EUR ${(value / 1_000_000).toFixed(1)}M`;
}

function formatPredictedValue(value: number | null): string {
  return value === null ? "Unavailable" : formatMillions(value);
}

function DataCard({ label, value, tone = "" }: { label: string; value: string; tone?: string }) {
  return <article className={`data-card ${tone}`}><span>{label}</span><strong>{value}</strong></article>;
}

export function DataPreview({ players, metrics }: DataPreviewProps) {
  const topPlayer = [...players].sort((left, right) => right.actual_value_eur - left.actual_value_eur)[0];
  const randomForest = metrics.models.find((model) => model.name === "Random Forest");

  return (
    <>
      <section className="data-grid" aria-label="Dataset highlights">
        <DataCard label="Players in contract" value={players.length.toString()} />
        <DataCard label="Best actual value" value={topPlayer ? formatMillions(topPlayer.actual_value_eur) : "--"} tone="accent-card" />
        <DataCard label="Random Forest R2" value={randomForest ? randomForest.r2_log.toFixed(3) : "--"} />
        <DataCard label="Model split" value={`${metrics.split.train} / ${metrics.split.test}`} />
      </section>
      <section className="table-panel" aria-labelledby="preview-title">
        <div className="panel-heading">
          <div><p className="kicker">Static export preview</p><h2 id="preview-title">Player records</h2></div>
          <span>{players.length} rows loaded</span>
        </div>
        <div className="table-wrap">
          <table>
            <thead><tr><th>Player</th><th>Club</th><th>Position</th><th>Actual</th><th>Predicted</th><th>Verdict</th></tr></thead>
            <tbody>{players.slice(0, 8).map((player) => <tr key={player.id}>
              <td><strong>{player.name}</strong><small>{player.season} season</small></td><td>{player.club}</td><td>{player.position}</td>
              <td>{formatMillions(player.actual_value_eur)}</td><td>{formatPredictedValue(player.predicted_value_eur)}</td>
              <td><span className={`verdict verdict-${player.verdict}`}>{player.verdict}</span></td>
            </tr>)}</tbody>
          </table>
        </div>
      </section>
    </>
  );
}
