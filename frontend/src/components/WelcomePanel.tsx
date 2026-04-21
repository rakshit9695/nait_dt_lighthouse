import React from "react";

const KEY = "nait-dt-welcome-dismissed-v1";

export function welcomeDismissed(): boolean {
  try { return localStorage.getItem(KEY) === "1"; } catch { return false; }
}

export default function WelcomePanel({ onClose }: { onClose: () => void }) {
  function dismiss() {
    try { localStorage.setItem(KEY, "1"); } catch {}
    onClose();
  }
  return (
    <div className="welcome-overlay" role="dialog" aria-modal="true">
      <div className="welcome">
        <div className="welcome-head">
          <h2>NAIT CGI · Microgrid Digital Twin</h2>
          <span className="pill">CGI-DC-01 Rev 2</span>
        </div>
        <p>
          A physics-grounded simulator of NAIT's <em>Centre for Grid Innovation</em> data-center
          microgrid testbed: PV + battery + bidirectional inverter + fuel-cell generator + a
          5-rack data-center load, tied to the Alberta grid. Every component has a published
          equation set; every assumption is logged.
        </p>
        <ul>
          <li>
            <b>Single-line diagram (L0)</b> — click any component box to inspect it. Lines are
            colored AC (blue) / DC (red) / control (gray). Arrows show direction; thickness scales with power.
          </li>
          <li>
            <b>Drill-down (L1 → L3)</b> — Layer 1 summarises live state, Layer 2 visualises
            internal dynamics (SOC, thermal, …), Layer 3 surfaces the governing equations.
          </li>
          <li>
            <b>Scenarios</b> — pick a 48–72 h scenario (sunny day, grid outage, heatwave, price
            spike, …) then <kbd>Run</kbd>. The model reports a <code>DT_Confidence</code> in
            [0,1]; <code>≥ 0.80</code> meets the §9 acceptance bar.
          </li>
        </ul>
        <div className="welcome-foot">
          <button className="btn-primary" onClick={dismiss}>Got it — show the twin</button>
          <button className="btn-link" onClick={onClose}>Show again next time</button>
        </div>
      </div>
    </div>
  );
}
