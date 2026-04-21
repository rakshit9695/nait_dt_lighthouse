import React from "react";

export default function GenericInternals({ c }: { c: any }) {
  const st = c?.state || {};
  return (
    <div>
      <p className="caption muted small">
        All internal state variables of the model. Numbers are the latest tick;
        booleans / strings show mode flags.
      </p>
      <div className="kv">
        {Object.entries(st).map(([k, v]) => (
          <React.Fragment key={k}>
            <b>{k}</b>
            <span>{typeof v === "number" ? Number(v).toFixed(3) : JSON.stringify(v).slice(0, 60)}</span>
          </React.Fragment>
        ))}
      </div>
    </div>
  );
}
