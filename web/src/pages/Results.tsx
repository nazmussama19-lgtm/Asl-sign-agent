// Test-set report of notebook 01 (71,762 test samples).
const F1: Record<string, number> = {
  A: 1.0, B: 1.0, C: 0.99, D: 0.99, E: 0.99, F: 1.0, G: 1.0, H: 1.0, I: 0.98, J: 0.98, K: 1.0, L: 1.0, M: 0.97, N: 0.96,
  O: 0.99, P: 0.99, Q: 0.99, R: 0.99, S: 0.99, T: 1.0, U: 0.99, V: 0.99, W: 0.99, X: 0.99, Y: 1.0, Z: 0.99, del: 0.99, space: 0.99,
};

export default function Results() {
  const rows = Object.entries(F1).sort((a, b) => a[1] - b[1] || a[0].localeCompare(b[0]));
  const W = 900, H = 260, pad = { l: 44, r: 12, t: 12, b: 46 }, lo = 0.9, hi = 1.005;
  const x = (i: number) => pad.l + (i + 0.5) * ((W - pad.l - pad.r) / rows.length);
  const y = (v: number) => pad.t + (1 - (v - lo) / (hi - lo)) * (H - pad.t - pad.b);
  const lowest = rows[0];

  return (
    <>
      <h1 className="page-title">Results</h1>
      <p className="page-sub">How well the models recognize signs.</p>

      <h2 className="section-title" style={{ marginTop: 20 }}>Letters (static signs)</h2>
      <div className="metrics" style={{ marginTop: 16 }}>
        <div className="panel metric"><b>99.23%</b><span>test accuracy</span></div>
        <div className="panel metric"><b>28</b><span>classes: A to Z, space and delete</span></div>
        <div className="panel metric"><b>{lowest[1].toFixed(2)}</b><span>lowest F1-score (letter {lowest[0]})</span></div>
      </div>

      <div className="panel" style={{ marginTop: 18, overflowX: "auto" }}>
        <p className="panel-label">F1-score by sign</p>
        <svg viewBox={`0 0 ${W} ${H}`} style={{ width: "100%", minWidth: 640 }} role="img" aria-label="F1-score of each sign, all above 0.95">
          {[0.9, 0.95, 1].map((v) => (
            <g key={v}>
              <line x1={pad.l} x2={W - pad.r} y1={y(v)} y2={y(v)} stroke="#D8DBE6" />
              <text x={pad.l - 8} y={y(v) + 4} textAnchor="end" fontSize="11" fill="#6A6F8C">{v.toFixed(2)}</text>
            </g>
          ))}
          {rows.map(([k, v], i) => (
            <g key={k}>
              <line x1={x(i)} x2={x(i)} y1={y(lo)} y2={y(v)} stroke="#D3D6E3" strokeWidth={3} strokeLinecap="round" />
              <circle cx={x(i)} cy={y(v)} r={5.5} fill="#0E1330"><title>{`${k}: ${v.toFixed(2)}`}</title></circle>
              <text x={x(i)} y={H - pad.b + 18} textAnchor="middle" fontSize="11" fill="#4E5373" fontFamily="Unbounded, sans-serif">{k === "space" ? "sp" : k}</text>
            </g>
          ))}
        </svg>
        <p className="muted">The axis starts at 0.90 to make the differences visible: every sign scores above 0.95. Scores from the evaluation in notebook 01 (71,762 test samples).</p>
      </div>

      <h2 className="section-title">Word signs</h2>
      <p className="section-sub">Trained on the Google ASL Signs dataset, which covers up to 250 signs. Evaluated on 24 signs, the Conv1D + GRU model reaches 86% accuracy. This demo ships a lighter 9-sign model to keep it small and fast.</p>
      <p className="muted">Letter scores are measured on images from the same dataset as training. Accuracy on new signers, lighting and cameras is usually lower: the Practice mode collects your own labeled samples to measure it.</p>
    </>
  );
}
