import React from "react";
import { useStore } from "../store";
import BatteryInternals from "./internals/BatteryInternals";
import GenericInternals from "./internals/GenericInternals";
import BatterySignals from "./signals/BatterySignals";
import InverterSignals from "./signals/InverterSignals";
import PVSignals from "./signals/PVSignals";
import { TYPE_DESCRIPTIONS, iconForType } from "../util/icons";
import { fmtPower } from "../util/format";

const LAYER_CAPTIONS: Record<number, string> = {
  1: "Live snapshot — all state variables for this component as of the latest tick.",
  2: "Internal model state — the dynamics implemented inside this component.",
  3: "Governing equations — the physics being integrated, with current signal values.",
};

export default function InspectPanel() {
  const id = useStore((s) => s.selectedId);
  const layer = useStore((s) => s.layer);
  const setLayer = useStore((s) => s.setLayer);
  const components = useStore((s) => s.components);
  const flows = useStore((s) => s.flows);
  const dtConf = useStore((s) => s.dtConfidence);
  const topology = useStore((s) => s.topology);

  if (!id) {
    return (
      <div className="inspect">
        <h2>System overview</h2>
        <p className="muted small no-mt">
          Click any box on the diagram to inspect that component.
        </p>
        <div className="kv">
          <b>DT_Confidence</b><span>{dtConf?.toFixed(3) ?? "—"}</span>
          <b>Components</b><span>{Object.keys(components).length}</span>
          <b>Live flows ({">"}50W)</b><span>{flows.filter((f) => Math.abs(f.P_W) > 50).length}</span>
        </div>
        <h2>Components</h2>
        <ul className="comp-list">
          {topology?.nodes.map((n: any) => {
            const Icon = iconForType(n.type);
            return (
              <li key={n.id} onClick={() => useStore.getState().setSelected(n.id)}>
                <svg width={18} height={18} viewBox="0 0 18 18">
                  <g transform="translate(9,9)" stroke="#111" fill="none">
                    <Icon size={16} />
                  </g>
                </svg>
                <span className="comp-label">{n.label}</span>
                <span className="muted small">{n.type}</span>
              </li>
            );
          })}
        </ul>
        <h2>Active power flows</h2>
        <table className="flows">
          <thead><tr><th>from</th><th>to</th><th>P</th></tr></thead>
          <tbody>
            {flows.filter((f) => Math.abs(f.P_W) > 50).map((f, i) => (
              <tr key={i}><td>{f.from}</td><td>{f.to}</td><td>{fmtPower(f.P_W)}</td></tr>
            ))}
            {flows.filter((f) => Math.abs(f.P_W) > 50).length === 0 && (
              <tr><td colSpan={3} className="muted small">No live flows yet — run a scenario or wait for the live tick.</td></tr>
            )}
          </tbody>
        </table>
      </div>
    );
  }

  const c = components[id];
  const node = topology?.nodes.find((n: any) => n.id === id);
  const desc = node ? TYPE_DESCRIPTIONS[node.type] : "";
  return (
    <div className="inspect">
      <div className="inspect-head">
        <h2 className="no-border">{node?.label || id}</h2>
        <button className="btn-link" onClick={() => useStore.getState().setSelected(null)}>← back</button>
      </div>
      <p className="muted small no-mt">{desc}</p>
      <div className="layer-tabs">
        {[1, 2, 3].map((l) => (
          <button key={l} className={layer === l ? "active" : ""}
                  onClick={() => setLayer(l as 1 | 2 | 3)}>
            L{l}
          </button>
        ))}
      </div>
      <p className="muted small no-mt">{LAYER_CAPTIONS[layer]}</p>
      {layer === 1 && <Layer1Summary c={c} />}
      {layer === 2 && <Layer2Internals id={id} c={c} />}
      {layer === 3 && <Layer3Signals id={id} c={c} />}
    </div>
  );
}

function Layer1Summary({ c }: { c: any }) {
  if (!c) return <div className="muted small">No data yet — run a scenario or wait for the live tick.</div>;
  const st = c.state || {};
  return (
    <>
      <h2>State</h2>
      <div className="kv">
        {Object.entries(st).slice(0, 16).map(([k, v]) => (
          <React.Fragment key={k}>
            <b>{k}</b>
            <span>{typeof v === "number" ? Number(v).toFixed(3) : String(v).slice(0, 60)}</span>
          </React.Fragment>
        ))}
      </div>
      {c.faults?.length ? (
        <>
          <h2>Faults</h2>
          <ul className="faults">{c.faults.map((f: string) => <li key={f}>⚠ {f}</li>)}</ul>
        </>
      ) : null}
      {c.assumptions?.length ? (
        <>
          <h2>Assumed parameters</h2>
          <ul className="assumptions">
            {c.assumptions.map((a: any) => (
              <li key={a.param}>
                <span className="assumption">{a.param}</span> ={" "}
                {String(a.default_value)} {a.unit}
                <small> · Q{a.question_index}</small>
              </li>
            ))}
          </ul>
        </>
      ) : null}
    </>
  );
}

function Layer2Internals({ id, c }: { id: string; c: any }) {
  if (!c) return <div className="muted small">No data yet.</div>;
  if (id === "battery") return <BatteryInternals c={c} />;
  return <GenericInternals c={c} />;
}

function Layer3Signals({ id, c }: { id: string; c: any }) {
  if (!c) return <div className="muted small">No data yet.</div>;
  if (id === "battery") return <BatterySignals c={c} />;
  if (id === "quattro" || id === "fronius") return <InverterSignals c={c} />;
  if (id === "pv_sim") return <PVSignals c={c} />;
  return (
    <div className="muted small">
      No bespoke signal-level view yet for this component. The L1 / L2 panels show all
      relevant variables from the underlying physics model.
    </div>
  );
}
