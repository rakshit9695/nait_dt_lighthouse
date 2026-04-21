import React from "react";

type Props = {
  data: number[];
  width?: number;
  height?: number;
  stroke?: string;
  fill?: string;
  min?: number;
  max?: number;
};

export default function Sparkline({
  data,
  width = 120,
  height = 28,
  stroke = "#111",
  fill = "none",
  min,
  max,
}: Props) {
  if (!data || data.length === 0) {
    return <svg width={width} height={height} />;
  }
  const lo = min ?? Math.min(...data);
  const hi = max ?? Math.max(...data);
  const range = hi - lo || 1;
  const dx = data.length > 1 ? width / (data.length - 1) : width;
  const pts = data.map((v, i) => {
    const y = height - ((v - lo) / range) * height;
    return `${i * dx},${y}`;
  });
  const path = `M ${pts.join(" L ")}`;
  const area = fill !== "none" ? `${path} L ${width},${height} L 0,${height} Z` : "";
  return (
    <svg width={width} height={height} aria-hidden="true">
      {area && <path d={area} fill={fill} stroke="none" />}
      <path d={path} fill="none" stroke={stroke} strokeWidth={1.2} />
    </svg>
  );
}
