import React from "react";
import { useStore } from "../store";
import ConfidenceTile from "./ConfidenceTile";
import Tooltip from "../util/Tooltip";

const LAYERS: { id: 0 | 1 | 2 | 3; label: string; help: string }[] = [
  { id: 0, label: "L0 · SLD", help: "Single-line diagram of the whole site." },
  { id: 1, label: "L1 · Summary", help: "Live state of the selected component." },
  { id: 2, label: "L2 · Internals", help: "Internal dynamics (SOC, thermal, droop, …)." },
  { id: 3, label: "L3 · Signals", help: "Governing equations and raw signal values." },
];

export default function TopBar() {
  const layer = useStore((s) => s.layer);
  const setLayer = useStore((s) => s.setLayer);
  const selectedId = useStore((s) => s.selectedId);
  const setShowWelcome = useStore((s) => s.setShowWelcome);
  const setShowAssumptions = useStore((s) => s.setShowAssumptions);
  return (
    <header className="topbar">
      <h1>NAIT CGI · Microgrid Digital Twin</h1>
      <span className="pill">CGI-DC-01 Rev 2</span>
      <div className="layer-tabs">
        {LAYERS.map((l) => {
          const disabled = l.id !== 0 && !selectedId;
          return (
            <Tooltip key={l.id} text={l.help}>
              <button
                className={layer === l.id ? "active" : ""}
                disabled={disabled}
                title={disabled ? "Select a component first" : l.help}
                onClick={() => setLayer(l.id)}
              >
                {l.label}
              </button>
            </Tooltip>
          );
        })}
      </div>
      <div className="topbar-actions">
        <button className="btn-ghost" onClick={() => setShowAssumptions(true)}>
          Assumptions
        </button>
        <button className="btn-ghost" onClick={() => setShowWelcome(true)}>
          About
        </button>
      </div>
      <ConfidenceTile />
    </header>
  );
}
