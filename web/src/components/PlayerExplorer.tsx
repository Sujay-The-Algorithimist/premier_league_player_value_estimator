import { useMemo, useState } from "react";
import { motion } from "framer-motion";
import type { PlayerRecord } from "../types";

function formatValue(value: number): string {
  return `EUR ${(value / 1_000_000).toFixed(1)}M`;
}

function formatPredictedValue(value: number | null): string {
  return value === null ? "Unavailable" : formatValue(value);
}

export function PlayerExplorer({ players }: { players: PlayerRecord[] }) {
  const [query, setQuery] = useState("");
  const [position, setPosition] = useState("All positions");
  const [sort, setSort] = useState("value");
  const [selected, setSelected] = useState<PlayerRecord | null>(null);
  const positions = [...new Set(players.map((player) => player.position))];
  const filtered = useMemo(() => players
    .filter((player) => player.name.toLowerCase().includes(query.toLowerCase()) || player.club.toLowerCase().includes(query.toLowerCase()))
    .filter((player) => position === "All positions" || player.position === position)
    .sort((left, right) => sort === "age" ? left.age - right.age : (right.predicted_value_eur ?? -1) - (left.predicted_value_eur ?? -1)), [players, position, query, sort]);

  return <section className="explorer-page" aria-labelledby="explorer-title">
    <div className="explorer-heading"><div><p className="kicker">AI valuation room / held-out results</p><h1 id="explorer-title">Read the market, player by player.</h1><p>Search the held-out Random Forest results. Every comparison pairs a valuation with the season-level signals available before it.</p></div><div className="explorer-stamp"><strong>{filtered.length}</strong><span>records in view</span></div></div>
    <div className="explorer-toolbar"><label><span>Search</span><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Player or club" /></label><label><span>Position</span><select value={position} onChange={(event) => setPosition(event.target.value)}><option>All positions</option>{positions.map((item) => <option key={item}>{item}</option>)}</select></label><label><span>Sort</span><select value={sort} onChange={(event) => setSort(event.target.value)}><option value="value">Predicted value</option><option value="age">Age</option></select></label></div>
    <div className="explorer-list">{filtered.map((player, index) => <motion.button className="explorer-row" key={`${player.id}-${player.season}`} onClick={() => setSelected(player)} initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: index * .025 }}><span className="explorer-number">{String(index + 1).padStart(2, "0")}</span><span className="explorer-player"><strong>{player.name}</strong><small>{player.club} / {player.position}</small></span><span><small>Actual</small><strong>{formatValue(player.actual_value_eur)}</strong></span><span><small>AI estimate</small><strong className="lime-text">{formatPredictedValue(player.predicted_value_eur)}</strong></span><span className={`verdict verdict-${player.verdict}`}>{player.predicted_value_eur === null ? "raw value" : player.verdict}</span><span className="row-arrow" aria-hidden="true">↗</span></motion.button>)}</div>
    {selected && <div className="detail-backdrop" role="presentation" onClick={() => setSelected(null)}><motion.aside className="player-detail" role="dialog" aria-modal="true" aria-labelledby="detail-title" onClick={(event) => event.stopPropagation()} initial={{ opacity: 0, x: 30 }} animate={{ opacity: 1, x: 0 }}><button className="close-detail" onClick={() => setSelected(null)} aria-label="Close player details">×</button><p className="kicker">{selected.predicted_value_eur === null ? "Raw dataset record" : `Random Forest result / ${selected.season}`}</p><h2 id="detail-title">{selected.name}</h2><p className="detail-club">{selected.club} / {selected.position} / age {selected.age}</p><div className="value-reveal"><span>Estimated market value</span><strong>{formatPredictedValue(selected.predicted_value_eur)}</strong><small>{selected.predicted_value_eur === null ? "Model export not available for this record yet" : "Static contract result · not a live prediction"}</small></div><div className="value-compare"><div><span>Current raw value</span><strong>{formatValue(selected.actual_value_eur)}</strong></div><div><span>AI estimate</span><strong>{formatPredictedValue(selected.predicted_value_eur)}</strong></div></div><div className="stat-strip"><span>{selected.minutes.toLocaleString()}<small>minutes</small></span><span>{selected.goals_per90.toFixed(2)}<small>goals / 90</small></span><span>{selected.assists_per90.toFixed(2)}<small>assists / 90</small></span></div></motion.aside></div>}
  </section>;
}
