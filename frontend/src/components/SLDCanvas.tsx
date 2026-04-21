import React, { useMemo, useState } from "react";
import { useStore } from "../store";
import { iconForType, TYPE_DESCRIPTIONS } from "../util/icons";
import Legend from "./Legend";
import { fmtPower } from "../util/format";
import { STORY_ORDER, revealedIdsAt } from "../util/storyOrder";

const W = 920;
const H = 620;

// Choose a representative active-power scalar for each component type.
function nodePowerW(type: string, state: any): number | null {
  if (!state) return null;
  switch (type) {
    case "pv_sim": return Number(state.P_dc ?? 0);
    case "battery": return Number(state.P_dc ?? 0);
    case "inverter": return Number(state.P_ac ?? 0);
    case "bidir_inverter": return Number(state.P_ac ?? 0);
    case "generator": return Number(state.P_dc ?? 0);
    case "data_center": return Number(state.P_total ?? 0);
    case "load_sim": return Number(state.P_load_W ?? state.P_load ?? 0);
    case "grid_tie": return Number(state.P_exchanged ?? 0);
    case "dcdc": return Number(state.P_out ?? state.P_in ?? 0);
    default: return null;
  }
}

export default function SLDCanvas() {
  const topology = useStore((s) => s.topology);
  const components = useStore((s) => s.components);
  const flows = useStore((s) => s.flows);
  const selectedId = useStore((s) => s.selectedId);
  const setSelected = useStore((s) => s.setSelected);
  const storyMode = useStore((s) => s.storyMode);
  const storyStep = useStore((s) => s.storyStep);
  const [hoverId, setHoverId] = useState<string | null>(null);

  const revealed = useMemo(
    () => (storyMode ? revealedIdsAt(storyStep) : null),
    [storyMode, storyStep]
  );
  const currentStoryId = storyMode && storyStep >= 0 ? STORY_ORDER[storyStep]?.id : null;

  const nodeMap = useMemo(() => {
    const m: Record<string, { x: number; y: number; label: string; type: string }> = {};
    if (!topology) return m;
    for (const n of topology.nodes) {
      m[n.id] = { x: n.x * W, y: n.y * H, label: n.label || n.id, type: n.type };
    }
    return m;
  }, [topology]);

  const flowMaxAbs = useMemo(() => {
    let m = 1;
    for (const f of flows) m = Math.max(m, Math.abs(Number(f.P_W) || 0));
    return m;
  }, [flows]);

  if (!topology) return <div style={{ padding: 18 }}>Loading topology…</div>;

  const hover = hoverId ? components[hoverId] : null;
  const hoverNode = hoverId ? nodeMap[hoverId] : null;

  return (
    <div className="sld-host">
      <svg width="100%" height="100%" viewBox={`0 0 ${W} ${H}`}
           preserveAspectRatio="xMidYMid meet">
        <defs>
          <marker id="arrow-flow" viewBox="0 0 10 10" refX="9" refY="5"
                  markerWidth="6" markerHeight="6" orient="auto-start-reverse">
            <path d="M 0 0 L 10 5 L 0 10 z" fill="#111" />
          </marker>
        </defs>

        {/* topology edges */}
        {topology.edges.map((e: any, i: number) => {
          const a = nodeMap[e.from], b = nodeMap[e.to];
          if (!a || !b) return null;
          if (revealed && (!revealed.has(e.from) || !revealed.has(e.to))) return null;
          return (
            <line key={`e${i}`} className={`edge ${e.kind || "ac"}`}
                  x1={a.x} y1={a.y} x2={b.x} y2={b.y} />
          );
        })}

        {/* live power flows */}
        {flows.filter((f: any) => Math.abs(f.P_W) > 50).map((f: any, i: number) => {
          const a = nodeMap[f.from], b = nodeMap[f.to];
          if (!a || !b) return null;
          if (revealed && (!revealed.has(f.from) || !revealed.has(f.to))) return null;
          const mag = Math.abs(Number(f.P_W));
          const w = 1.2 + 4.5 * (mag / flowMaxAbs);
          const fwd = Number(f.P_W) >= 0;
          const x1 = fwd ? a.x : b.x; const y1 = fwd ? a.y : b.y;
          const x2 = fwd ? b.x : a.x; const y2 = fwd ? b.y : a.y;
          // shorten endpoints so arrow doesn't overlap node rect
          const dx = x2 - x1, dy = y2 - y1; const L = Math.hypot(dx, dy) || 1;
          const ux = dx / L, uy = dy / L;
          const sx = x1 + ux * 24, sy = y1 + uy * 18;
          const ex = x2 - ux * 24, ey = y2 - uy * 18;
          return (
            <line key={`f${i}`} className="flow"
                  x1={sx} y1={sy} x2={ex} y2={ey}
                  strokeWidth={w}
                  markerEnd="url(#arrow-flow)" />
          );
        })}

        {/* nodes */}
        {topology.nodes.map((n: any) => {
          const p = nodeMap[n.id];
          const sel = n.id === selectedId;
          const c = components[n.id];
          const fault = (c?.faults || []).length > 0;
          const Icon = iconForType(n.type);
          const pw = nodePowerW(n.type, c?.state);
          if (revealed && !revealed.has(n.id)) return null;
          const cur = currentStoryId === n.id;
          return (
            <g key={n.id}
               className={`node ${sel ? "selected" : ""} ${fault ? "fault" : ""} ${cur ? "story-current" : ""}`}
               transform={`translate(${p.x},${p.y})`}
               onClick={() => setSelected(n.id)}
               onMouseEnter={() => setHoverId(n.id)}
               onMouseLeave={() => setHoverId((id) => (id === n.id ? null : id))}>
              {cur && <rect x={-60} y={-28} width={120} height={56} rx={4} ry={4} className="story-pulse" />}
              <rect x={-54} y={-22} width={108} height={44} rx={2} ry={2} />
              <g transform="translate(-38,0)" className="node-icon">
                <Icon size={20} />
              </g>
              <text x={6} y={-4} className="node-label">{n.label || n.id}</text>
              <text x={6} y={9} className="node-sub">
                {pw == null ? n.type : fmtPower(pw)}
              </text>
              {fault && (
                <g transform="translate(46,-18)">
                  <circle r={5} fill="#e15554" />
                  <text x={0} y={3} textAnchor="middle"
                        fontSize={8} fill="#fff" stroke="none">!</text>
                </g>
              )}
            </g>
          );
        })}
      </svg>

      {hover && hoverNode && (
        <div className="sld-tip"
             style={{
               left: Math.min(hoverNode.x + 60, W - 250),
               top: Math.max(hoverNode.y - 30, 8),
             }}>
          <div className="tip-head">
            <b>{hoverNode.label}</b>
            <span className="muted small"> · {hoverNode.type}</span>
          </div>
          <div className="tip-desc">
            {TYPE_DESCRIPTIONS[hoverNode.type] || ""}
          </div>
          {hover.faults?.length ? (
            <div className="tip-fault">⚠ {hover.faults.join(", ")}</div>
          ) : null}
          <div className="tip-foot muted small">click to inspect →</div>
        </div>
      )}

      <Legend />
    </div>
  );
}
