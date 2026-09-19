import { useState } from "react";
import { motion, useReducedMotion } from "framer-motion";
import type { PlayerRecord } from "../types";

interface ShowcasePlayer {
  name: string;
  image: string;
  role: string;
  club: string;
  era: string;
  accent: string;
  archive: boolean;
}

const archivalPlayers: ShowcasePlayer[] = [
  { name: "Erling Haaland", image: "/players/Halland.png", role: "Striker", club: "Manchester City", era: "Current star", accent: "#a8d66b", archive: false },
  { name: "Wayne Rooney", image: "/players/Rooney.png", role: "Forward", club: "Manchester United", era: "2004 — 2017", accent: "#a9865d", archive: true },
  { name: "Rodri", image: "/players/Rodri.png", role: "Midfield", club: "Manchester City", era: "Modern era", accent: "#7895bd", archive: true },
  { name: "Cristiano Ronaldo", image: "/players/Ronaldo7.png", role: "Forward", club: "Manchester United", era: "2003 — 2009", accent: "#9f625d", archive: true },
];

function Silhouette({ accent }: { accent: string }) {
  return <svg className="player-silhouette" viewBox="0 0 240 420" aria-hidden="true">
    <defs><linearGradient id={`figure-${accent.replace("#", "")}`} x1="0" x2="1" y1="0" y2="1"><stop stopColor={accent} stopOpacity=".8" /><stop offset="1" stopColor="#08120d" stopOpacity=".95" /></linearGradient></defs>
    <circle cx="121" cy="56" r="31" fill={`url(#figure-${accent.replace("#", "")})`} />
    <path d="M83 99 Q120 78 158 99 L184 220 146 235 137 164 133 265 190 403 132 403 118 293 102 403 44 403 100 265 106 163 96 235 57 220Z" fill={`url(#figure-${accent.replace("#", "")})`} />
    <path d="M83 105 L37 197 56 208 104 142 M157 105 L207 185 190 198 136 142" fill="none" stroke={accent} strokeOpacity=".65" strokeWidth="14" />
    <path d="M69 402 L104 402 M137 402 L172 402" stroke="#b8ff3f" strokeOpacity=".6" strokeWidth="4" />
  </svg>;
}

function PlayerImage({ player }: { player: ShowcasePlayer }) {
  const [imageAvailable, setImageAvailable] = useState(true);

  if (!imageAvailable) return <Silhouette accent={player.accent} />;
  return <img className="player-photo" src={player.image} alt={`${player.name} in a football moment`} onError={() => setImageAvailable(false)} loading="lazy" />;
}

export function PlayerShowcase({ currentPlayer }: { currentPlayer: PlayerRecord | undefined }) {
  const reduceMotion = useReducedMotion();
  return <section className="showcase-section" aria-labelledby="showcase-title">
    <div className="showcase-heading"><div><p className="kicker">The players who define the league</p><h2 id="showcase-title">Greatness leaves a pattern.</h2></div><p>Archive portraits are editorial references, not model predictions. Only the labelled current dataset record is connected to the valuation contract.</p></div>
    <div className="player-rail">
      {archivalPlayers.map((player, index) => <motion.article key={player.name} className={`showcase-player ${player.archive ? "archive-player" : "dataset-player"}`} initial={reduceMotion ? false : { opacity: 0, y: 30 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true, amount: .3 }} transition={{ delay: index * .06, duration: .5 }} whileHover={reduceMotion ? undefined : { y: -8 }}>
        <div className="showcase-light" /><PlayerImage player={player} />
        <div className="player-index">0{index + 1}</div>
        <div className="player-info"><span>{player.archive ? "Archive portrait" : "Dataset player"}</span><h3>{player.name}</h3><p>{player.role} / {player.club}</p><small>{player.era}{!player.archive && currentPlayer ? ` / ${currentPlayer.goals_per90.toFixed(2)} goals per 90` : ""}</small></div>
      </motion.article>)}
    </div>
  </section>;
}
