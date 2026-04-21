import React from "react";
import Sparkline from "../../util/sparkline";

export const SCENARIO_DESCRIPTIONS: Record<string, string> = {
  sunny_grid_stable:
    "72-hour clear-sky baseline. PV peaks at solar noon, grid stays online at flat $60/MWh. Tests steady-state energy balance and battery cycling under benign conditions.",
  cloudy_grid_stable:
    "Overcast 48 h: PV output ~30% of clear-sky. Grid carries most of the load; the model should show net import close to IT load.",
  grid_outage_noon:
    "Grid drops mid-day for several hours. MTS islands the site; battery + (eventually) generator must carry the data-center load with no shedding.",
  price_spike_evening:
    "Evening LMP spike (>$300/MWh). Economic policy should arbitrage: pre-charge battery off solar, discharge during the spike.",
  carbon_high_night:
    "Carbon-intensive grid overnight (high gCO₂/kWh). Carbon-aware policy should prefer battery + generator over grid import even at higher cost.",
  heatwave:
    "Ambient up to 40 °C. CRAC effectiveness drops; battery/inverter derating possible. Tests thermal envelope behaviour.",
  ai_training_burst:
    "Workload mix swings to ~80% training. IT load doubles for several hours; the system must keep PUE and supply firm.",
  worst_case:
    "Compounded stress: outage + heatwave + price spike + training burst overlapping. Worst expected DT_Confidence in the canned set.",
};

type Props = {
  scenario: any | null;
};

export default function ScenarioCard({ scenario }: Props) {
  if (!scenario) return null;
  const d = scenario.drivers || {};
  const desc = SCENARIO_DESCRIPTIONS[scenario.id]
    ?? "Custom scenario — drivers loaded from YAML.";
  return (
    <div className="scen-card">
      <div className="scen-card-head">
        <b>{scenario.name}</b>
        <span className="muted small">{scenario.horizon_hours} h · policy: {scenario.control_policy}</span>
      </div>
      <p className="small">{desc}</p>
      <div className="scen-sparks">
        <SparkRow label="irradiance W/m²" data={d.irradiance_W_m2 || []} />
        <SparkRow label="ambient °C" data={d.ambient_temp_C || []} />
        <SparkRow label="IT load kW" data={d.IT_load_kW || []} />
        <SparkRow label="LMP $/MWh" data={d.grid_LMP_usd_MWh || []} />
        <SparkRow label="grid online" data={(d.grid_online || []).map((x: boolean) => x ? 1 : 0)} min={0} max={1} />
      </div>
    </div>
  );
}

function SparkRow({ label, data, min, max }: { label: string; data: number[]; min?: number; max?: number }) {
  return (
    <div className="spark-row">
      <span className="spark-label">{label}</span>
      <Sparkline data={data} width={180} height={22} min={min} max={max} />
    </div>
  );
}
