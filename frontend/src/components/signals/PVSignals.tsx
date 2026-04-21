import React, { useEffect, useRef } from "react";
import katex from "katex";

function K({ tex }: { tex: string }) {
  const ref = useRef<HTMLSpanElement>(null);
  useEffect(() => { if (ref.current) katex.render(tex, ref.current, { throwOnError: false }); }, [tex]);
  return <span ref={ref} />;
}

export default function PVSignals({ c }: { c: any }) {
  const s = c?.state || {};
  return (
    <div>
      <p className="caption">
        Single-diode model with series + shunt resistance. Photo-current scales linearly with
        irradiance G; the diode saturation term gives the characteristic I-V knee. Cell
        temperature shifts the curve via the temperature coefficient α.
      </p>
      <div className="eqn">
        <K tex={`I = I_{ph} - I_0 \\left(e^{(V + I R_s)/(n V_T)} - 1\\right) - \\frac{V + I R_s}{R_{sh}}`} />
      </div>
      <div className="eqn">
        <K tex={`I_{ph}(G,T) = I_{sc,ref} \\frac{G}{G_{ref}} (1 + \\alpha (T - T_{ref}))`} />
      </div>
      <div className="kv">
        <b>P_dc (W)</b><span>{Number(s.P_dc ?? 0).toFixed(0)}</span>
        <b>V_dc (V)</b><span>{Number(s.V_dc ?? 0).toFixed(1)}</span>
        <b>I_dc (A)</b><span>{Number(s.I_dc ?? 0).toFixed(2)}</span>
      </div>
    </div>
  );
}
