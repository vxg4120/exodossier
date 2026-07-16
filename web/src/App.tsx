import { lazy, Suspense, useEffect, useState } from "react";
import { NavLink, Route, Routes } from "react-router-dom";
import { getStats, MOCK } from "./api/client";
import { useApi } from "./hooks/useApi";
import { compact } from "./lib/format";
import { SourceBadge } from "./components/SourceBadge";
import { Loading } from "./components/States";

const Overview = lazy(() => import("./views/Overview").then((m) => ({ default: m.Overview })));
const Search = lazy(() => import("./views/Search").then((m) => ({ default: m.Search })));
const Target = lazy(() => import("./views/Target").then((m) => ({ default: m.Target })));
const Conflicts = lazy(() => import("./views/Conflicts").then((m) => ({ default: m.Conflicts })));
const FollowUp = lazy(() => import("./views/FollowUp").then((m) => ({ default: m.FollowUp })));
const About = lazy(() => import("./views/About").then((m) => ({ default: m.About })));

const NAV = [
  { to: "/", idx: "00", name: "Overview", end: true },
  { to: "/search", idx: "01", name: "Search", end: false },
  { to: "/conflicts", idx: "02", name: "Conflicts", end: false },
  { to: "/followup", idx: "03", name: "Follow-up", end: false },
  { to: "/about", idx: "04", name: "About", end: false },
];

function Clock() {
  const [now, setNow] = useState(() => new Date());
  useEffect(() => {
    const id = setInterval(() => setNow(new Date()), 1000);
    return () => clearInterval(id);
  }, []);
  const p = (x: number) => String(x).padStart(2, "0");
  const stamp = `${now.getUTCFullYear()}-${p(now.getUTCMonth() + 1)}-${p(now.getUTCDate())} ${p(
    now.getUTCHours(),
  )}:${p(now.getUTCMinutes())}:${p(now.getUTCSeconds())}`;
  return (
    <div className="topbar__clock">
      <span className="tele__k">{MOCK ? "mock · utc" : "live · utc"}</span>
      <span className="tele__v num">{stamp}</span>
    </div>
  );
}

function Telemetry() {
  const stats = useApi(() => getStats(), []);
  const s = stats.data;
  const chip = (k: string, v: string, cls = "") => (
    <div className="tele">
      <span className="tele__k">{k}</span>
      <span className={`tele__v ${cls}`}>{v}</span>
    </div>
  );
  return (
    <div className="topbar__tele">
      {chip("candidates", s ? compact(s.candidates) : "····")}
      {chip("host stars", s ? compact(s.stars) : "····")}
      {chip("assertions", s ? compact(s.source_assertions) : "····", "is-signal")}
      {chip("disposition conflicts", s ? compact(s.conflicts.disposition) : "····", "is-conflict")}
    </div>
  );
}

export default function App() {
  return (
    <div className="app">
      <header className="topbar">
        <div className="topbar__brand">
          <span className="topbar__mark">
            <span className="dot" aria-hidden="true" />
            ExoDossier
          </span>
          <span className="topbar__sub">Conflict Explorer · Read-only</span>
        </div>
        <Telemetry />
        <Clock />
      </header>

      <nav className="rail" aria-label="Views">
        <div className="rail__nav">
          {NAV.map((n) => (
            <NavLink
              key={n.to}
              to={n.to}
              end={n.end}
              className={({ isActive }) => `navlink${isActive ? " is-active" : ""}`}
            >
              <span className="navlink__idx num">{n.idx}</span>
              <span className="navlink__name">{n.name}</span>
            </NavLink>
          ))}
        </div>
        <div className="rail__foot">
          <span className="label">Provenance</span>
          <div className="srckey">
            <SourceBadge source="exofop_toi" />
            <SourceBadge source="nea_toi" />
            <SourceBadge source="ps" />
            <SourceBadge source="pscomppars" />
            <SourceBadge source="koi" />
          </div>
          <span className="hint">{MOCK ? "Fixtures — API offline" : "Proxy → :8700"}</span>
        </div>
      </nav>

      <main className="main">
        <Suspense fallback={<Loading label="Loading view" />}>
          <Routes>
            <Route path="/" element={<Overview />} />
            <Route path="/search" element={<Search />} />
            <Route path="/target/:id" element={<Target />} />
            <Route path="/conflicts" element={<Conflicts />} />
            <Route path="/followup" element={<FollowUp />} />
            <Route path="/about" element={<About />} />
          </Routes>
        </Suspense>
      </main>
    </div>
  );
}
