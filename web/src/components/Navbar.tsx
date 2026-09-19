import { motion, useReducedMotion } from "framer-motion";
import { NavLink } from "react-router-dom";

const links = [
  { label: "Home", to: "/" },
  { label: "Players", to: "/players" },
  { label: "Predict", to: "/predict" },
  { label: "Insights", to: "/insights" },
  { label: "Method", to: "/method" },
];

export function Navbar() {
  const reduceMotion = useReducedMotion();

  return (
    <motion.header
      className="site-nav"
      initial={reduceMotion ? false : { opacity: 0, y: -16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.45 }}
    >
      <NavLink className="brand" to="/" aria-label="Player Value AI home">
        <span className="brand-mark">PV</span>
        <span><strong>PLAYER VALUE</strong><small>AI / PREMIER LEAGUE</small></span>
      </NavLink>
      <nav aria-label="Primary navigation">
        {links.map((link) => (
          <NavLink key={link.to} className={({ isActive }) => isActive ? "nav-link active" : "nav-link"} to={link.to}>
            {link.label}
          </NavLink>
        ))}
      </nav>
      <NavLink className="nav-cta" to="/players">Explore data <span aria-hidden="true">↗</span></NavLink>
    </motion.header>
  );
}
