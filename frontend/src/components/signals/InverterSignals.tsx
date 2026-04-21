import React, { useEffect, useRef } from "react";
import katex from "katex";

function K({ tex }: { tex: string }) {
  const ref = useRef<HTMLSpanElement>(null);
  useEffect(() => { if (ref.current) katex.render(tex, ref.current, { throwOnError: false }); }, [tex]);
  return <span ref={ref} />;
}

export default function InverterSignals({ c }: { c: any }) {
  const s = c?.state || {};
  return (
    <div>
      <p className="caption">
        Inverter efficiency follows a 3rd-root part-load curve plus a quadratic loss term.
        In off-grid mode the Quattro forms the AC bus with V/f droop: voltage and frequency
        sag linearly with delivered active power.
      </p>
      <div className="eqn">
        <K tex={`\\eta(P) = \\eta_{base} + k_1 \\sqrt[3]{P/P_{rated}} - k_2 (P/P_{rated})^2`} />
      </div>
      <div className="eqn">
        <K tex={`V_{out} = V_{nom} - k_V \\cdot P_{ac}, \\quad f_{out} = f_{nom} - k_f \\cdot P_{ac}`} />
      </div>
      <div className="kv">
        <b>P_ac (W)</b><span>{Number(s.P_ac ?? 0).toFixed(0)}</span>
        <b>P_dc (W)</b><span>{Number(s.P_dc ?? 0).toFixed(0)}</span>
        <b>η</b><span>{Number(s.efficiency ?? 0).toFixed(3)}</span>
        <b>mode</b><span>{String(s.mode ?? "")}</span>
      </div>
    </div>
  );
}
