import React, { useEffect } from "react";
import { useStore } from "./store";
import { api } from "./api/rest";
import { openLiveSocket } from "./api/websocket";
import TopBar from "./components/TopBar";
import SLDCanvas from "./components/SLDCanvas";
import StoryControls from "./components/StoryControls";
import InspectPanel from "./components/InspectPanel";
import ScenarioBuilder from "./components/ScenarioBuilder";
import WelcomePanel, { welcomeDismissed } from "./components/WelcomePanel";
import AssumptionsDrawer from "./components/AssumptionsDrawer";

export default function App() {
  const setTopology = useStore((s) => s.setTopology);
  const setComponents = useStore((s) => s.setComponents);
  const setLive = useStore((s) => s.setLive);
  const setScenarios = useStore((s) => s.setScenarios);
  const showWelcome = useStore((s) => s.showWelcome);
  const setShowWelcome = useStore((s) => s.setShowWelcome);
  const showAssumptions = useStore((s) => s.showAssumptions);
  const setShowAssumptions = useStore((s) => s.setShowAssumptions);

  useEffect(() => {
    api.topology().then(setTopology).catch(console.error);
    api.components().then(setComponents).catch(console.error);
    api.scenarios().then(setScenarios).catch(console.error);
    const close = openLiveSocket(setLive);
    if (!welcomeDismissed()) setShowWelcome(true);
    return close;
  }, []);

  return (
    <div className="app">
      <TopBar />
      <div className="workspace">
        <div className="canvas-wrap">
          <SLDCanvas />
          <StoryControls />
        </div>
        <div className="side-panels">
          <InspectPanel />
          <ScenarioBuilder />
        </div>
      </div>
      {showWelcome && <WelcomePanel onClose={() => setShowWelcome(false)} />}
      {showAssumptions && <AssumptionsDrawer onClose={() => setShowAssumptions(false)} />}
    </div>
  );
}
