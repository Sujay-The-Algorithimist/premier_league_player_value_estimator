import type { FeatureImportance, MetricsData, ResidualBin, ScatterPoint } from "../types";

const pct = (value: number) => `${(value * 100).toFixed(1)}%`;

export function Insights({ metrics, importance, residuals, scatter }: { metrics: MetricsData; importance: FeatureImportance[]; residuals: ResidualBin[]; scatter: ScatterPoint[] }) {
  return <section className="analysis-page" aria-labelledby="insights-title">
    <p className="kicker">Model insights / held-out seasons</p><h1 id="insights-title">See what moves the estimate.</h1>
    <p className="analysis-lede">Every result below is calculated on the 2024–25 holdout, after fitting only on earlier seasons. Values are estimates, not transfer recommendations.</p>
    <div className="metric-cards">{metrics.models.map((model) => <article key={model.name}><span>{model.name}</span><strong>{model.r2_log.toFixed(3)}</strong><small>R² on log value · RMSE {model.rmse_log.toFixed(3)}</small></article>)}</div>
    <div className="analysis-grid">
      <article className="analysis-panel"><p className="kicker">Feature signal</p><h2>What the model sees</h2>{importance.map((item) => <div className="importance-row" key={item.feature}><span>{item.feature}</span><i><b style={{ width: pct(item.importance) }} /></i><strong>{pct(item.importance)}</strong></div>)}</article>
      <article className="analysis-panel"><p className="kicker">Error distribution</p><h2>Residuals in the test set</h2><div className="histogram">{residuals.map((item) => <div key={item.bin} title={`${item.bin}: ${item.count} players`}><i style={{ height: `${Math.max(8, item.count / Math.max(...residuals.map((bin) => bin.count)) * 100)}%` }} /><span>{item.count}</span></div>)}</div><p className="panel-note">Residual = predicted log value minus actual log value. A balanced spread around zero is preferable.</p></article>
    </div>
    <article className="analysis-panel table-panel"><div className="panel-heading"><div><p className="kicker">Segment checks</p><h2>Where it generalises</h2></div><span>{scatter.length} held-out rows</span></div><div className="segment-grid">{[["By position", metrics.by_position], ["By value band", metrics.by_value_band]].map(([title, groups]) => <div key={title as string}><h3>{title as string}</h3><table><thead><tr><th>Group</th><th>Rows</th><th>RMSE</th><th>Median error</th></tr></thead><tbody>{(groups as MetricsData["by_position"]).map((group) => <tr key={group.group}><td>{group.group}</td><td>{group.rows}</td><td>{group.rmse_log.toFixed(3)}</td><td>{group.median_absolute_percentage_error.toFixed(1)}%</td></tr>)}</tbody></table></div>)}</div></article>
  </section>;
}
