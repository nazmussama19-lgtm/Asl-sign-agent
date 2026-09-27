import { lazy, Suspense, useEffect } from "react";
import { BrowserRouter, Link, NavLink, Route, Routes, useLocation } from "react-router-dom";
import { ResourcesProvider } from "./resources";
import Home from "./pages/Home";
import { ThemeToggle } from "./components/ThemeToggle";

const SignToText = lazy(() => import("./pages/SignToText"));
const Practice = lazy(() => import("./pages/Practice"));
const TextToSign = lazy(() => import("./pages/TextToSign"));
const Chart = lazy(() => import("./pages/Chart"));
const Results = lazy(() => import("./pages/Results"));

const PAGES = [
  { to: "/sign", label: "Sign to text" },
  { to: "/practice", label: "Practice" },
  { to: "/text", label: "Text to sign" },
  { to: "/chart", label: "ASL chart" },
  { to: "/results", label: "Results" },
];

/** Soft light behind the glass; it only drifts on the home page, so camera pages keep the GPU for hand tracking. */
function Aurora() {
  const { pathname } = useLocation();
  return <div className={`aurora${pathname === "/" ? " live" : ""}`} aria-hidden="true"><i /><i /><i /></div>;
}

function ScrollTop() {
  const { pathname } = useLocation();
  useEffect(() => { window.scrollTo(0, 0); }, [pathname]);
  return null;
}

export default function App() {
  return (
    <BrowserRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
      <ResourcesProvider>
        <ScrollTop />
        <Aurora />
        <header className="topbar">
          <div className="topbar-inner">
            <Link to="/" className="brand" aria-label="Sign Agent, home">
              <span className="brand-mark" aria-hidden="true">
                <svg viewBox="0 0 16 16"><path fill="currentColor" d="M8 0l1.6 6.4L16 8l-6.4 1.6L8 16l-1.6-6.4L0 8l6.4-1.6z" /></svg>
              </span>
              <span className="brand-name">Sign Agent</span>
            </Link>
            <nav className="nav" aria-label="Pages">
              {PAGES.map((p) => <NavLink key={p.to} to={p.to}>{p.label}</NavLink>)}
            </nav>
            <ThemeToggle />
          </div>
        </header>
        <main>
          <Suspense fallback={<p className="muted">Loading…</p>}>
            <Routes>
              <Route path="/" element={<Home />} />
              <Route path="/sign" element={<SignToText />} />
              <Route path="/practice" element={<Practice />} />
              <Route path="/text" element={<TextToSign />} />
              <Route path="/chart" element={<Chart />} />
              <Route path="/results" element={<Results />} />
              <Route path="*" element={<Home />} />
            </Routes>
          </Suspense>
        </main>
      </ResourcesProvider>
    </BrowserRouter>
  );
}
