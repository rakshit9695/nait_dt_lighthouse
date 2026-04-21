import React from "react";

export default function BatteryInternals({ c }: { c: any }) {
  const s = c?.state || {};
  const soc = Math.max(0, Math.min(1, Number(s.SOC ?? 0)));
  return (
    <div>
      <p className="caption muted small">
        Pack state at this tick. The bar shows SOC; positive current = discharging.
        SOH (state of health) decays slowly with throughput cycles.
      </p>
      <div className="soc-bar">
        <div className="soc-fill" style={{ width: `${soc * 100}%` }} />
        <span className="soc-num">{(soc * 100).toFixed(1)}%</span>
      </div>
      <div className="kv">
        <b>SOC</b><span>{(soc * 100).toFixed(1)}%</span>
        <b>SOH</b><span>{Number(s.SOH ?? 1).toFixed(3)}</span>
        <b>V_term</b><span>{Number(s.V_term ?? 0).toFixed(2)} V</span>
        <b>I</b><span>{Number(s.I ?? 0).toFixed(2)} A</span>
        <b>P_dc</b><span>{Number(s.P_dc ?? 0).toFixed(0)} W</span>
        <b>T</b><span>{Number(s.T ?? 25).toFixed(1)} °C</span>
        <b>V_RC</b><span>{Number(s.V_RC ?? 0).toFixed(3)} V</span>
        <b>Cycle Ah</b><span>{Number(s.cycle_throughput_ah ?? 0).toFixed(2)}</span>
      </div>
    </div>
  );
}
