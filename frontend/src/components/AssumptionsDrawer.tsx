import React, { useEffect, useState } from "react";
import { api } from "../api/rest";

type Assumption = {
  param: string;
  default_value: any;
  unit?: string;
  question_index?: number;
  source_doc?: string;
  confidence_penalty?: number;
};

export default function AssumptionsDrawer({ onClose }: { onClose: () => void }) {
  const [items, setItems] = useState<Assumption[]>([]);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    api.assumptions().then(setItems).catch((e) => setErr(String(e)));
  }, []);

  return (
    <div className="drawer-overlay" onClick={onClose}>
      <aside className="drawer" onClick={(e) => e.stopPropagation()}>
        <div className="drawer-head">
          <h2>Assumption ledger</h2>
          <button className="btn-link" onClick={onClose}>close ✕</button>
        </div>
        <p className="muted small">
          Every parameter the model couldn't measure from the spec is listed here, tagged with
          a <b>Q-index</b> mapping to the §10 question list for follow-up with NAIT operators.
        </p>
        {err && <div className="error">{err}</div>}
        <table className="ledger">
          <thead>
            <tr><th>Parameter</th><th>Default</th><th>Unit</th><th>Q#</th><th>Source</th></tr>
          </thead>
          <tbody>
            {items.map((a, i) => (
              <tr key={i}>
                <td><span className="assumption">{a.param}</span></td>
                <td>{String(a.default_value)}</td>
                <td>{a.unit || ""}</td>
                <td>{a.question_index ?? ""}</td>
                <td className="muted small">{a.source_doc || ""}</td>
              </tr>
            ))}
          </tbody>
        </table>
        <div className="muted small" style={{ marginTop: 12 }}>
          {items.length} assumed parameters · confidence_penalty contributes to the
          assumption_density score in DT_Confidence.
        </div>
      </aside>
    </div>
  );
}
