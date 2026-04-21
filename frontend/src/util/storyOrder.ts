// Story-mode reveal sequence + per-step explanatory text and cumulative
// metric extractors. Order follows electrical hierarchy: utility boundary →
// renewable source → conversion → AC bus → loads → storage → backup → control.

export type StepMetric = {
  label: string;
  value: string;
  hint?: string;
};

export type StoryStep = {
  id: string;
  title: string;
  role: string;
  blurb: string; // one-paragraph plain-language explanation
  metrics: (run: any, dtH: number) => StepMetric[];
};

const sumWh = (arr: any[], key: string, dtH: number) =>
  arr.reduce((a, r) => a + Number(r[key] ?? 0), 0) * dtH;
const sumWhPos = (arr: any[], key: string, dtH: number) =>
  arr.reduce((a, r) => a + Math.max(0, Number(r[key] ?? 0)), 0) * dtH;
const sumWhNeg = (arr: any[], key: string, dtH: number) =>
  arr.reduce((a, r) => a + Math.max(0, -Number(r[key] ?? 0)), 0) * dtH;
const fmtE = (wh: number) => (Math.abs(wh) >= 1000 ? `${(wh / 1000).toFixed(2)} kWh` : `${wh.toFixed(0)} Wh`);
const fmtN = (n: number, d = 2) => (Number.isFinite(n) ? n.toFixed(d) : "—");

export const STORY_ORDER: StoryStep[] = [
  {
    id: "grid",
    title: "Main Grid Tie",
    role: "Utility boundary",
    blurb:
      "The site connects to the local utility through a 240/120 V single-phase service. Positive power means the microgrid is importing from the grid; negative means the site is exporting back. This boundary tells us the net dependency on the utility over the run.",
    metrics: (run, dtH) => {
      const g = run?.series?.grid || [];
      const imp = sumWhPos(g, "P_exchanged", dtH);
      const exp = sumWhNeg(g, "P_exchanged", dtH);
      return [
        { label: "Energy imported", value: fmtE(imp), hint: "Σ P>0 over horizon" },
        { label: "Energy exported", value: fmtE(exp), hint: "Σ P<0 over horizon" },
      ];
    },
  },
  {
    id: "pv_sim",
    title: "PV Array (Keysight N8937APV)",
    role: "Renewable source",
    blurb:
      "The PV simulator drives the array based on irradiance and ambient temperature for each scenario step. Output is DC power. This step quantifies how much solar energy was generated across the horizon.",
    metrics: (run, dtH) => {
      const pv = run?.series?.pv_sim || [];
      const e = sumWh(pv, "P_dc", dtH);
      const peak = pv.reduce((a: number, r: any) => Math.max(a, Number(r.P_dc ?? 0)), 0);
      return [
        { label: "PV energy", value: fmtE(e), hint: "DC, before inverter loss" },
        { label: "Peak DC power", value: `${(peak / 1000).toFixed(2)} kW` },
      ];
    },
  },
  {
    id: "fronius",
    title: "Fronius Primo Inverter",
    role: "DC→AC conversion",
    blurb:
      "The Fronius converts the PV DC output to grid-quality AC and feeds it onto the panel. Conversion efficiency varies with load and temperature. Losses here are part of the energy-balance residual scored later.",
    metrics: (run, dtH) => {
      const f = run?.series?.fronius || [];
      const eAC = sumWhPos(f, "P_ac", dtH);
      const meanEff =
        f.length > 0
          ? f.reduce((a: number, r: any) => a + Number(r.efficiency ?? 0), 0) / f.length
          : 0;
      return [
        { label: "AC energy delivered", value: fmtE(eAC) },
        { label: "Mean η", value: `${(meanEff * 100).toFixed(1)}%` },
      ];
    },
  },
  {
    id: "panel",
    title: "240/120 V Panel",
    role: "AC bus",
    blurb:
      "The main panel is the AC junction: PV-AC, battery-AC (via the Quattro), and grid all meet here, and loads tap off it. Flows on this bus determine the moment-to-moment energy balance of the site.",
    metrics: (run) => {
      const flows = (run?.flows || []) as any[][];
      // count distinct (from,to) pairs touching panel
      const seen = new Set<string>();
      for (const step of flows) for (const f of step) {
        if (f.from === "panel" || f.to === "panel") seen.add(`${f.from}→${f.to}`);
      }
      return [
        { label: "Connected paths", value: String(seen.size) },
        { label: "Steps simulated", value: String(flows.length) },
      ];
    },
  },
  {
    id: "data_center",
    title: "Data-Center Load",
    role: "Primary load",
    blurb:
      "The data center is the IT load plus its cooling (PUE = (P_IT + P_cool) / P_IT). It draws AC from the panel. Inlet temperature drives cooling power; cooling power drives PUE; PUE drives total kWh.",
    metrics: (run, dtH) => {
      const d = run?.series?.data_center || [];
      const e = sumWh(d, "P_total", dtH);
      const meanT =
        d.length > 0 ? d.reduce((a: number, r: any) => a + Number(r.T_inlet ?? 0), 0) / d.length : 0;
      return [
        { label: "DC energy served", value: fmtE(e) },
        { label: "Mean T_inlet", value: `${meanT.toFixed(1)} °C` },
      ];
    },
  },
  {
    id: "chroma",
    title: "Chroma Load Sim",
    role: "Variable load",
    blurb:
      "The Chroma 61809 is a programmable AC load that emulates other facility loads driven by the scenario. It lets us stress the panel with realistic, time-varying demand independent of the data-center model.",
    metrics: (run, dtH) => {
      const c = run?.series?.chroma || [];
      const e = sumWh(c, "P_load_W", dtH) || sumWh(c, "P_load", dtH);
      return [{ label: "Load energy", value: fmtE(Math.abs(e)) }];
    },
  },
  {
    id: "battery",
    title: "Pytes V5 Battery",
    role: "Storage",
    blurb:
      "The 5.12 kWh LFP battery is modelled with a thermal-coupled equivalent-circuit (V_oc(SOC), R_int, RC). SOC tracks state-of-charge; cycles count equivalent full charge/discharge equivalents. Charge fills it; discharge supports loads when PV/grid drop.",
    metrics: (run) => {
      const b = run?.series?.battery || [];
      const soc = b.map((r: any) => Number(r.SOC ?? 0));
      const cycles =
        soc.length > 1
          ? soc.reduce((a: number, v: number, i: number) =>
              i === 0 ? 0 : a + Math.abs(v - soc[i - 1]), 0) / 2
          : 0;
      const lo = soc.length ? Math.min(...soc) : 0;
      const hi = soc.length ? Math.max(...soc) : 0;
      return [
        { label: "Equivalent cycles", value: fmtN(cycles, 2) },
        { label: "SOC range", value: `${(lo * 100).toFixed(0)}–${(hi * 100).toFixed(0)}%` },
      ];
    },
  },
  {
    id: "quattro",
    title: "Victron Quattro",
    role: "Battery interface (AC↔DC)",
    blurb:
      "The Quattro is a bidirectional inverter sitting between the battery DC bus and the AC panel (via the MTS). It handles charging from AC sources and discharging to AC loads. Its mode is set by the Cerbo controller.",
    metrics: (run, dtH) => {
      const q = run?.series?.quattro || [];
      const eIn = sumWhPos(q, "P_ac", dtH);
      const eOut = sumWhNeg(q, "P_ac", dtH);
      return [
        { label: "AC out (discharge)", value: fmtE(eIn) },
        { label: "AC in (charge)", value: fmtE(eOut) },
      ];
    },
  },
  {
    id: "generator",
    title: "AlumaPower Generator",
    role: "Backup source",
    blurb:
      "The fuel-burning generator is a backup DC source routed through a DC-DC converter into the battery bus. Fuel consumption is integrated from its fuel curve. State 'on' indicates it was running at that step.",
    metrics: (run) => {
      const g = run?.series?.generator || [];
      const fuelStart = g.length ? Number(g[0].fuel_kg_remaining ?? 0) : 0;
      const fuelEnd = g.length ? Number(g[g.length - 1].fuel_kg_remaining ?? 0) : 0;
      const used = Math.max(0, fuelStart - fuelEnd);
      const onSteps = g.filter((r: any) => r.state === "on" || Number(r.P_dc ?? 0) > 50).length;
      return [
        { label: "Fuel used", value: `${used.toFixed(2)} kg` },
        { label: "Steps running", value: `${onSteps} / ${g.length}` },
      ];
    },
  },
  {
    id: "dcdc",
    title: "DC-DC Converter",
    role: "Generator → battery DC",
    blurb:
      "The DC-DC bridges the generator output to the battery DC bus at the right voltage. Throughput here equals charge energy injected into the battery from the generator path.",
    metrics: (run, dtH) => {
      const d = run?.series?.dcdc || [];
      const e = sumWhPos(d, "P_out", dtH);
      return [{ label: "Energy throughput", value: fmtE(e) }];
    },
  },
  {
    id: "mts",
    title: "Manual Transfer Switch",
    role: "Source selector",
    blurb:
      "The MTS routes either the Quattro AC output or the grid path into the panel. In the model it tracks state changes; each toggle is one switching event the operator must approve.",
    metrics: (run) => {
      const m = run?.series?.mts || [];
      let switches = 0;
      for (let i = 1; i < m.length; i++) {
        if (m[i].state !== m[i - 1].state) switches += 1;
      }
      return [{ label: "Switching events", value: String(switches) }];
    },
  },
  {
    id: "cerbo",
    title: "Cerbo GX Controller",
    role: "Battery / Quattro supervisor",
    blurb:
      "The Cerbo coordinates the Quattro and battery: choosing charge vs discharge modes and limits based on SOC and AC presence. It is part of the modelled control surface; its decisions show up in Quattro's mode.",
    metrics: (run) => {
      const q = run?.series?.quattro || [];
      const modes = new Set<string>();
      for (const r of q) if (r.mode) modes.add(String(r.mode));
      return [{ label: "Modes used", value: Array.from(modes).join(", ") || "—" }];
    },
  },
  {
    id: "plc",
    title: "Site PLC (Supervisor)",
    role: "Top-level control + acceptance",
    blurb:
      "The PLC supervises every device: dispatch setpoints, generator start, MTS transfer, load shed. Its quality is judged by safety violations, thermal violations, setpoint RMS error and the energy-balance residual — which together drive DT_Confidence.",
    metrics: (run) => {
      const sm = run?.evaluation?.system_metrics || {};
      const conf = run?.evaluation?.dt_confidence ?? 0;
      return [
        { label: "Safety violations", value: String(sm.safety_violations ?? 0) },
        { label: "Energy residual", value: `${((sm.energy_balance_residual ?? 0) * 100).toFixed(3)}%` },
        { label: "DT_Confidence", value: conf.toFixed(3), hint: "≥ 0.80 = acceptable" },
      ];
    },
  },
];

export function dtHoursFromRun(run: any): number {
  if (!run?.n_steps) return 1;
  const dur = (new Date(run.completed_at).getTime() - new Date(run.started_at).getTime()) / 1000;
  return dur / run.n_steps / 3600;
}

export function revealedIdsAt(step: number): Set<string> {
  return new Set(STORY_ORDER.slice(0, Math.max(0, step + 1)).map((s) => s.id));
}
