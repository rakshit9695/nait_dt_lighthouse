export function fmtPower(w: number | null | undefined): string {
  if (w == null || !isFinite(w as number)) return "—";
  const v = Number(w);
  const a = Math.abs(v);
  if (a >= 1000) return `${(v / 1000).toFixed(2)} kW`;
  return `${v.toFixed(0)} W`;
}

export function fmtEnergy(wh: number | null | undefined): string {
  if (wh == null || !isFinite(wh as number)) return "—";
  const v = Number(wh);
  const a = Math.abs(v);
  if (a >= 1000) return `${(v / 1000).toFixed(2)} kWh`;
  return `${v.toFixed(0)} Wh`;
}

export function fmtPct(x: number | null | undefined, digits = 1): string {
  if (x == null || !isFinite(x as number)) return "—";
  return `${(Number(x) * 100).toFixed(digits)}%`;
}

export function fmtNum(x: number | null | undefined, digits = 2): string {
  if (x == null || !isFinite(x as number)) return "—";
  return Number(x).toFixed(digits);
}

export function clamp(x: number, lo: number, hi: number): number {
  return Math.max(lo, Math.min(hi, x));
}
