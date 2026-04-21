import React from "react";
import Sparkline from "../util/sparkline";
import { fmtEnergy, fmtNum, fmtPct } from "../util/format";

export default function RunResultsPanel({ run }: { run: any }) {
  const ev = run?.evaluation;
  if (!ev) return null;
  const sm = ev.system_metrics || {};
  const series = run?.series || {};
  const dtSec = run.n_steps > 0
    ? (new Date(run.completed_at).getTime() - new Date(run.started_at).getTime()) / 1000 / run.n_steps
    : 3600;
  const dtH = dtSec / 3600;

  const battSeries = series["battery"] || [];
  const socTrace = battSeries.map((r: any) => Number(r.SOC ?? 0));
  const grid = series["grid"] || [];
  const pv = series["pv_sim"] || [];
  const dc = series["data_center"] || [];
  const gen = series["generator"] || [];

  const sumWhPositive = (arr: any[], key: string) =>
    arr.reduce((a, r) => a + Math.max(0, Number(r[key] ?? 0)), 0) * dtH;
  const sumWh = (arr: any[], key: string) =>
    arr.reduce((a, r) => a + Number(r[key] ?? 0), 0) * dtH;

  const energyPV = sumWh(pv, "P_dc");
  const energyDC = sumWh(dc, "P_total");
  const energyGridImport = sumWhPositive(grid, "P_exchanged");
  const energyGridExport = grid.reduce(
    (a: number, r: any) => a + Math.max(0, -Number(r.P_exchanged ?? 0)), 0) * dtH;

  const battCycles = battSeries.length > 1
    ? socTrace.reduce((a: number, v: number, i: number) =>
        i === 0 ? 0 : a + Math.abs(v - socTrace[i - 1]), 0) / 2
    : 0;

  const fuelStart = gen.length > 0 ? Number(gen[0].fuel_kg_remaining ?? 0) : 0;
  const fuelEnd = gen.length > 0 ? Number(gen[gen.length - 1].fuel_kg_remaining ?? 0) : 0;
  const fuelUsed = Math.max(0, fuelStart - fuelEnd);

  const residual = sm.energy_balance_residual ?? 0;
  const dtConf = ev.dt_confidence;
  const cls = dtConf >= 0.8 ? "good" : dtConf >= 0.6 ? "warn" : "bad";

  return (
    <div className="results">
      <h3>
        Run results
        <span className={`pill ${cls}`}>DT_Confidence {fmtNum(dtConf, 3)}</span>
      </h3>
      <p className="narrative">
        Over <b>{run.n_steps} h</b> the model simulated PV output of <b>{fmtEnergy(energyPV)}</b>,
        a data-center load of <b>{fmtEnergy(energyDC)}</b>, with grid import
        <b> {fmtEnergy(energyGridImport)}</b> and export <b>{fmtEnergy(energyGridExport)}</b>.
        The battery moved through ≈<b>{fmtNum(battCycles, 2)}</b> equivalent full cycles
        {fuelUsed > 0.01 ? <> and the generator burned <b>{fmtNum(fuelUsed, 2)} kg</b> of fuel</> : null}.
        Mean energy-balance residual: <b>{fmtPct(residual, 3)}</b> (acceptance bar &lt; 0.5%).
      </p>
      <div className="metrics-grid">
        <Metric label="Energy residual" value={fmtPct(residual, 3)}
                ok={residual < 0.005} />
        <Metric label="Safety violations" value={String(sm.safety_violations ?? 0)}
                ok={(sm.safety_violations ?? 0) === 0} />
        <Metric label="Thermal viol. (s)" value={fmtNum(sm.thermal_violations_s, 0)}
                ok={(sm.thermal_violations_s ?? 0) < 1800} />
        <Metric label="Setpoint RMS err" value={`${fmtNum(sm.setpoint_rms_error_pct, 1)}%`}
                ok={(sm.setpoint_rms_error_pct ?? 99) < 5} />
      </div>

      <div className="results-section">
        <div className="muted small">Battery SOC across horizon (0–100%)</div>
        <Sparkline data={socTrace} width={300} height={50} min={0} max={1}
                   fill="#eef7ee" stroke="#5fb96b" />
      </div>

      <div className="results-section">
        <div className="muted small">Per-component confidence (C_i)</div>
        {ev.components.map((c: any) => (
          <div key={c.id} className="bar-row labeled">
            <span className="bar-label">{c.id}</span>
            <div className="bar-container">
              <div className="bar-fill" style={{ width: `${(c.C_i * 100).toFixed(0)}%` }} />
            </div>
            <span className="bar-num">{fmtNum(c.C_i, 3)}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

function Metric({ label, value, ok }: { label: string; value: string; ok?: boolean }) {
  const cls = ok === true ? "good" : ok === false ? "warn" : "";
  return (
    <div className={`metric ${cls}`}>
      <div className="metric-val">{value}</div>
      <div className="metric-lab">{label}</div>
    </div>
  );
}
