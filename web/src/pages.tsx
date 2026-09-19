import { motion, useReducedMotion } from "framer-motion";
import { Link, useLocation } from "react-router-dom";
import { DataPreview } from "./components/DataPreview";
import { PlayerShowcase } from "./components/PlayerShowcase";
import { PlayerExplorer } from "./components/PlayerExplorer";
import { PredictionRoom } from "./components/PredictionRoom";
import { Insights } from "./components/Insights";
import { Method } from "./components/Method";
import { useData } from "./hooks/useData";
import type { MetaData, MetricsData, PlayerRecord } from "./types";

function HomePage({ players, metrics, meta }: { players: PlayerRecord[]; metrics: MetricsData; meta: MetaData }) {
  const reduceMotion = useReducedMotion();
  return <>
    <section className="cinematic-hero" aria-labelledby="hero-title">
      <video className="hero-video" autoPlay={!reduceMotion} muted loop playsInline poster="/players/Halland.png" aria-hidden="true"><source src="/players/ftbl_video.mp4" type="video/mp4" /></video>
      <div className="hero-video-shade" />
      <motion.div className="hero-copy cinematic-copy" initial={reduceMotion ? false : { opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.65 }}>
        <p className="kicker"><span className="signal-dot" /> AI-powered player valuation</p>
        <h1 id="hero-title">The value of <em>greatness.</em></h1>
        <p className="hero-question">Can machine learning determine what a Premier League player is worth?</p>
        <p className="hero-lede">A cinematic, evidence-led view of market value. Explore the performance signals behind the estimate, not just the number.</p>
        <div className="hero-actions"><Link className="button button-primary" to="/players">Enter the valuation room <span aria-hidden="true">↗</span></Link><Link className="button button-quiet" to="/insights">Explore the signal</Link></div>
        <div className="hero-footnote"><span>01</span><p>Random Forest valuation<br /><strong>{meta.dataset_status} export / Premier League only</strong></p></div>
      </motion.div>
      <motion.div className="hero-data-overlay" initial={reduceMotion ? false : { opacity: 0, x: 25 }} animate={{ opacity: 1, x: 0 }} transition={{ duration: .8, delay: .25 }}><span>Featured study</span><strong>Erling Haaland</strong><small>Manchester City / Striker</small><i /><b>Live visual / 01</b></motion.div>
    </section>
    <PlayerShowcase currentPlayer={players.find((player) => player.name === "Erling Haaland")} />
    <section className="transition-section" aria-label="Transition into the valuation model"><p>We know what they achieved.</p><strong>But what are they worth?</strong><Link to="/players">Run the numbers <span aria-hidden="true">↗</span></Link></section>
    <section className="section-intro"><div><p className="kicker">A clearer read on value</p><h2>Built for the space between scouting instinct and machine intelligence.</h2></div><p>Every number in this interface is traced to a static data contract. The foundation is transparent by design, so the polished layer never hides the evidence.</p></section>
    <DataPreview players={players} metrics={metrics} />
  </>;
}

export function AppRoutes() {
  const players = useData<PlayerRecord[]>("/data/players.json");
  const metrics = useData<MetricsData>("/data/metrics.json");
  const meta = useData<MetaData>("/data/meta.json");
  const importance = useData<import("./types").FeatureImportance[]>("/data/importance.json");
  const residuals = useData<import("./types").ResidualBin[]>("/data/residuals.json");
  const scatter = useData<import("./types").ScatterPoint[]>("/data/scatter.json");
  if (players.loading || metrics.loading || meta.loading || importance.loading || residuals.loading || scatter.loading) return <main className="state-panel"><p>Loading dataset contract...</p></main>;
  if (players.error || metrics.error || meta.error || importance.error || residuals.error || scatter.error || !players.data || !metrics.data || !meta.data || !importance.data || !residuals.data || !scatter.data) return <main className="state-panel"><p>Data error: {players.error ?? metrics.error ?? meta.error ?? importance.error ?? residuals.error ?? scatter.error ?? "Missing data"}</p></main>;
  return <RoutesContent players={players.data} metrics={metrics.data} meta={meta.data} importance={importance.data} residuals={residuals.data} scatter={scatter.data} />;
}

function RoutesContent({ players, metrics, meta, importance, residuals, scatter }: { players: PlayerRecord[]; metrics: MetricsData; meta: MetaData; importance: import("./types").FeatureImportance[]; residuals: import("./types").ResidualBin[]; scatter: import("./types").ScatterPoint[] }) {
  const { pathname: path } = useLocation();
  if (path === "/players") return <PlayerExplorer players={players} />;
  if (path === "/predict") return <PredictionRoom />;
  if (path === "/insights") return <Insights metrics={metrics} importance={importance} residuals={residuals} scatter={scatter} />;
  if (path === "/method") return <Method meta={meta} metrics={metrics} />;
  return <HomePage players={players} metrics={metrics} meta={meta} />;
}
