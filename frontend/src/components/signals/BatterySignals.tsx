import React, { useEffect, useRef } from "react";
import katex from "katex";

function K({ tex }: { tex: string }) {
  const ref = useRef<HTMLSpanElement>(null);
  useEffect(() => {
    if (ref.current) katex.render(tex, ref.current, { throwOnError: false });
  }, [tex]);
  return <span ref={ref} />;
}

export default function BatterySignals({ c }: { c: any }) {
  const s = c?.state || {};
  return (
    <div>
      <p className="caption">
        Pytes V5 LFP modelled as Thevenin equivalent: open-circuit voltage <em>V<sub>OCV</sub>(SOC)</em>{" "}
        from a 1-cell lookup, series resistance R<sub>0</sub>, and one RC pair (R<sub>1</sub>·C<sub>1</sub>)
        capturing diffusion. SOC is coulomb-counted; cell temperature follows a single-node
        thermal RC against ambient.
      </p>
      <div className="eqn"><K tex={`V_{term} = V_{OCV}(SOC) - I R_0 - V_{RC}`} /></div>
      <div className="eqn"><K tex={`\\dot{SOC} = -\\frac{I}{3600 \\cdot C_{Ah}}`} /></div>
      <div className="eqn"><K tex={`\\dot{T} = \\frac{I^2(R_0+R_1) - h(T - T_{amb})}{m c_p}`} /></div>
      <div className="kv">
        <b>I (A) — discharge +</b><span>{Number(s.I ?? 0).toFixed(2)}</span>
        <b>V_RC (V)</b><span>{Number(s.V_RC ?? 0).toFixed(3)}</span>
        <b>SOC</b><span>{Number(s.SOC ?? 0).toFixed(3)}</span>
        <b>T (°C)</b><span>{Number(s.T ?? 25).toFixed(1)}</span>
      </div>
    </div>
  );
}
