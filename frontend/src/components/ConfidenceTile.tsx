import React from "react";
import { useStore } from "../store";
import { fmtNum } from "../util/format";

export default function ConfidenceTile() {
  const c = useStore((s) => s.dtConfidence);
  const open = useStore((s) => s.showConfidence);
  const setOpen = useStore((s) => s.setShowConfidence);
  const run = useStore((s) => s.runResult);
  const cls = c == null ? "" : c >= 0.8 ? "good" : c >= 0.6 ? "warn" : "bad";
  const label = c == null ? "DT_Confidence: —" : `DT_Confidence: ${c.toFixed(3)}`;
  const comps: any[] = run?.evaluation?.components || [];
  return (
    <span className="confidence-wrap">
      <button
        className={`confidence ${cls}`}
        onClick={() => setOpen(!open)}
        title="What does this number mean?"
      >
        {label} {comps.length ? <span className="caret">{open ? "▾" : "▸"}</span> : null}
      </button>
      {open && (
        <div className="conf-pop" onMouseLeave={() => setOpen(false)}>
          <h3>How DT_Confidence is computed</h3>
          <p className="muted small">
            Per spec §4.3, the system score is the <b>harmonic mean</b> of each component's
            <code> C_i</code>, where
            <code> C_i = 0.50·physical_consistency + 0.35·empirical_match + 0.15·assumption_density</code>.
            Acceptance threshold is <b>≥ 0.80</b>.
          </p>
          {comps.length === 0 ? (
            <div className="muted small">Run a scenario to see per-component scores.</div>
          ) : (
            <table className="conf-table">
              <thead>
                <tr><th>component</th><th>C_i</th><th>phys</th><th>emp</th><th>assum</th></tr>
              </thead>
              <tbody>
                {comps.map((x) => (
                  <tr key={x.id}>
                    <td>{x.id}</td>
                    <td>
                      <div className="bar-row">
                        <div className="bar-fill" style={{ width: `${(x.C_i * 100).toFixed(0)}%` }} />
                        <span className="bar-num">{fmtNum(x.C_i, 3)}</span>
                      </div>
                    </td>
                    <td>{fmtNum(x.physical_consistency, 2)}</td>
                    <td>{fmtNum(x.empirical_match, 2)}</td>
                    <td>{fmtNum(x.assumption_density, 2)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}
    </span>
  );
}
