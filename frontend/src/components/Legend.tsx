import React from "react";

export default function Legend() {
  return (
    <div className="legend">
      <div className="legend-title">Legend</div>
      <div className="legend-row"><span className="swatch ac" /> AC line</div>
      <div className="legend-row"><span className="swatch dc" /> DC line</div>
      <div className="legend-row"><span className="swatch ctrl" /> control / data</div>
      <div className="legend-row"><span className="swatch flow" /> active power flow (arrow → direction, width ∝ |P|)</div>
      <div className="legend-row"><span className="swatch fault" /> fault active</div>
      <div className="legend-foot">click any box to inspect</div>
    </div>
  );
}
