import React from "react";

// Compact monochrome glyphs sized to fit inside a 24px circle on the SLD node.
// All icons render in current text color; size is controlled by the parent <g>.
type IconProps = { size?: number };

const wrap = (size: number, children: React.ReactNode) => (
  <g
    transform={`translate(${-size / 2},${-size / 2})`}
    fill="none"
    stroke="currentColor"
    strokeWidth={1.4}
    strokeLinecap="round"
    strokeLinejoin="round"
  >
    {children}
  </g>
);

export function PVIcon({ size = 18 }: IconProps) {
  return wrap(
    size,
    <>
      <circle cx={size / 2} cy={size / 2} r={3} />
      {Array.from({ length: 8 }).map((_, i) => {
        const a = (i * Math.PI) / 4;
        const x1 = size / 2 + Math.cos(a) * 5;
        const y1 = size / 2 + Math.sin(a) * 5;
        const x2 = size / 2 + Math.cos(a) * 8;
        const y2 = size / 2 + Math.sin(a) * 8;
        return <line key={i} x1={x1} y1={y1} x2={x2} y2={y2} />;
      })}
    </>
  );
}

export function InverterIcon({ size = 18 }: IconProps) {
  // a square with ~~ inside (sine wave) → AC
  return wrap(
    size,
    <>
      <rect x={2} y={3} width={size - 4} height={size - 6} />
      <path d={`M ${4} ${size / 2} q ${(size - 8) / 4} -3 ${(size - 8) / 2} 0 t ${(size - 8) / 2} 0`} />
    </>
  );
}

export function BatteryIcon({ size = 18 }: IconProps) {
  return wrap(
    size,
    <>
      <rect x={2} y={5} width={size - 6} height={size - 10} />
      <rect x={size - 4} y={size / 2 - 2} width={2} height={4} />
      <line x1={5} y1={size / 2} x2={size - 7} y2={size / 2} />
    </>
  );
}

export function GeneratorIcon({ size = 18 }: IconProps) {
  return wrap(
    size,
    <>
      <circle cx={size / 2} cy={size / 2} r={6} />
      <text x={size / 2} y={size / 2 + 3} textAnchor="middle" fontSize={7} fill="currentColor" stroke="none">
        G
      </text>
    </>
  );
}

export function ControllerIcon({ size = 18 }: IconProps) {
  return wrap(
    size,
    <>
      <circle cx={size / 2} cy={size / 2} r={6} />
      <circle cx={size / 2} cy={size / 2} r={2} fill="currentColor" />
    </>
  );
}

export function PanelIcon({ size = 18 }: IconProps) {
  return wrap(
    size,
    <>
      <rect x={2} y={3} width={size - 4} height={size - 6} />
      <line x1={2} y1={size / 2} x2={size - 2} y2={size / 2} />
      <line x1={size / 2} y1={3} x2={size / 2} y2={size - 3} />
    </>
  );
}

export function DCDCIcon({ size = 18 }: IconProps) {
  return wrap(
    size,
    <>
      <rect x={2} y={3} width={size - 4} height={size - 6} />
      <text x={size / 2} y={size / 2 + 3} textAnchor="middle" fontSize={6} fill="currentColor" stroke="none">
        DC
      </text>
    </>
  );
}

export function MTSIcon({ size = 18 }: IconProps) {
  return wrap(
    size,
    <>
      <line x1={2} y1={size - 4} x2={size / 2} y2={4} />
      <circle cx={2} cy={size - 4} r={1.5} fill="currentColor" />
      <circle cx={size / 2} cy={4} r={1.5} fill="currentColor" />
      <circle cx={size - 2} cy={4} r={1.5} fill="currentColor" />
    </>
  );
}

export function DataCenterIcon({ size = 18 }: IconProps) {
  return wrap(
    size,
    <>
      <rect x={2} y={3} width={size - 4} height={4} />
      <rect x={2} y={9} width={size - 4} height={4} />
      <circle cx={5} cy={5} r={0.8} fill="currentColor" />
      <circle cx={5} cy={11} r={0.8} fill="currentColor" />
    </>
  );
}

export function LoadSimIcon({ size = 18 }: IconProps) {
  return wrap(
    size,
    <>
      <circle cx={size / 2} cy={size / 2} r={6} />
      <text x={size / 2} y={size / 2 + 3} textAnchor="middle" fontSize={7} fill="currentColor" stroke="none">
        Z
      </text>
    </>
  );
}

export function GridIcon({ size = 18 }: IconProps) {
  return wrap(
    size,
    <>
      <line x1={size / 2} y1={2} x2={size / 2} y2={6} />
      <line x1={3} y1={6} x2={size - 3} y2={6} />
      <line x1={5} y1={6} x2={3} y2={size - 3} />
      <line x1={size / 2} y1={6} x2={size / 2} y2={size - 3} />
      <line x1={size - 5} y1={6} x2={size - 3} y2={size - 3} />
    </>
  );
}

export function PLCIcon({ size = 18 }: IconProps) {
  return wrap(
    size,
    <>
      <rect x={3} y={3} width={size - 6} height={size - 6} />
      <line x1={5} y1={6} x2={size - 5} y2={6} />
      <line x1={5} y1={9} x2={size - 5} y2={9} />
      <line x1={5} y1={12} x2={size - 8} y2={12} />
    </>
  );
}

export function iconForType(type: string): React.FC<IconProps> {
  switch (type) {
    case "pv_sim": return PVIcon;
    case "inverter":
    case "bidir_inverter": return InverterIcon;
    case "battery": return BatteryIcon;
    case "generator": return GeneratorIcon;
    case "system_controller": return ControllerIcon;
    case "panel": return PanelIcon;
    case "dcdc": return DCDCIcon;
    case "mts": return MTSIcon;
    case "data_center": return DataCenterIcon;
    case "load_sim": return LoadSimIcon;
    case "grid_tie": return GridIcon;
    case "plc": return PLCIcon;
    default: return PanelIcon;
  }
}

export const TYPE_DESCRIPTIONS: Record<string, string> = {
  pv_sim: "Keysight N8937APV solar-array simulator. Models PV I-V curve from irradiance + cell temperature.",
  inverter: "Fronius Primo 3.8-1 string inverter. DC PV → AC; MPPT and grid-tie.",
  bidir_inverter: "Victron Quattro 48/5000 bidirectional. AC↔DC for battery; supports off-grid islanding.",
  battery: "Pytes V5 5.12 kWh LFP. Modelled as OCV(SOC) + R₀ + 1RC + thermal RC.",
  generator: "AlumaPower fuel-cell generator. Polarization curve, fuel mass, hot/cold startup.",
  system_controller: "Victron Cerbo GX. Coordinates Quattro / battery / Fronius via VE-bus.",
  dcdc: "DC-DC converter linking generator DC output to the 48 V battery bus.",
  mts: "Manual transfer switch — selects grid vs island AC source.",
  panel: "240/120 V distribution panel — single AC bus that combines all sources.",
  data_center: "5-rack datacenter load. Workload mix → IT power; CRAC + ASHRAE thermal envelope.",
  load_sim: "Chroma 61809 programmable AC load — synthesizes arbitrary load profiles.",
  grid_tie: "Main utility tie. Import/export at LMP price; subject to outage events.",
  plc: "Site PLC. Top-level command bus for inverters / generator / DC-DC / MTS.",
};
