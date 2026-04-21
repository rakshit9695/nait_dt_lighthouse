import React from "react";
import { useStore } from "../store";
import { api } from "../api/rest";
import ScenarioCard from "./scenario/ScenarioCard";
import RunResultsPanel from "./RunResultsPanel";
import StoryMetricsPanel from "./StoryMetricsPanel";

export default function ScenarioBuilder() {
  const scenarios = useStore((s) => s.scenarios);
  const setRun = useStore((s) => s.setRun);
  const busy = useStore((s) => s.runBusy);
  const setBusy = useStore((s) => s.setRunBusy);
  const error = useStore((s) => s.runError);
  const setError = useStore((s) => s.setRunError);
  const run = useStore((s) => s.runResult);
  const startStory = useStore((s) => s.startStory);
  const stopStory = useStore((s) => s.stopStory);
  const storyMode = useStore((s) => s.storyMode);
  const storyDone = useStore((s) => s.storyDone);
  const [sid, setSid] = React.useState<string>("sunny_grid_stable");
  const selected = scenarios.find((s: any) => s.id === sid) || null;

  async function go() {
    setBusy(true); setError(null);
    stopStory();
    try {
      const r = await api.runScenario(sid);
      setRun(r);
      startStory();
    } catch (e: any) {
      setError(e?.message || String(e));
    } finally { setBusy(false); }
  }

  return (
    <div className="scenario-builder">
      <h2>Scenario</h2>
      <p className="muted small no-mt">
        Pick a canned scenario to play forward 48–72 h at 1 h resolution. Each one stresses a
        different part of the model (weather, grid, load, control policy).
      </p>
      <div className="scen-controls">
        <select value={sid} onChange={(e) => { setSid(e.target.value); }}>
          {scenarios.map((s: any) => (
            <option key={s.id} value={s.id}>{s.name} ({s.horizon_hours}h)</option>
          ))}
        </select>
        <button className="btn-primary" onClick={go} disabled={busy}>
          {busy ? "Running…" : "Run scenario"}
        </button>
      </div>
      {error && <div className="error small">⚠ {error}</div>}

      {!run && <ScenarioCard scenario={selected} />}

      {run && run.scenario_id === sid && storyMode && !storyDone && (
        <StoryMetricsPanel run={run} />
      )}
      {run && run.scenario_id === sid && (!storyMode || storyDone) && (
        <>
          {storyDone && (
            <div className="story-done-banner">
              ✓ Walkthrough complete — full results below.
              <button className="btn-ghost small" onClick={startStory}>↻ Replay walkthrough</button>
            </div>
          )}
          <RunResultsPanel run={run} />
        </>
      )}
    </div>
  );
}
