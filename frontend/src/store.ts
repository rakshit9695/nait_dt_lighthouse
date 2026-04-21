import { create } from "zustand";

type State = {
  topology: any | null;
  components: Record<string, any>;
  flows: any[];
  selectedId: string | null;
  layer: 0 | 1 | 2 | 3;
  dtConfidence: number | null;
  scenarios: any[];
  runResult: any | null;
  runBusy: boolean;
  runError: string | null;
  showWelcome: boolean;
  showAssumptions: boolean;
  showConfidence: boolean;
  storyMode: boolean;
  storyStep: number;
  storyPlaying: boolean;
  storyDone: boolean;
  setTopology: (t: any) => void;
  setLive: (frame: any) => void;
  setComponents: (cs: any[]) => void;
  setSelected: (id: string | null) => void;
  setLayer: (l: 0 | 1 | 2 | 3) => void;
  setScenarios: (s: any[]) => void;
  setRun: (r: any) => void;
  setRunBusy: (b: boolean) => void;
  setRunError: (e: string | null) => void;
  setShowWelcome: (b: boolean) => void;
  setShowAssumptions: (b: boolean) => void;
  setShowConfidence: (b: boolean) => void;
  startStory: () => void;
  stopStory: () => void;
  setStoryStep: (n: number) => void;
  advanceStory: (max: number) => void;
  setStoryPlaying: (b: boolean) => void;
  finishStory: () => void;
};

export const useStore = create<State>((set) => ({
  topology: null,
  components: {},
  flows: [],
  selectedId: null,
  layer: 0,
  dtConfidence: null,
  scenarios: [],
  runResult: null,
  runBusy: false,
  runError: null,
  showWelcome: false,
  showAssumptions: false,
  showConfidence: false,
  storyMode: false,
  storyStep: -1,
  storyPlaying: false,
  storyDone: false,
  setTopology: (t) => set({ topology: t }),
  setLive: (frame) => set((st) => {
    const next: Record<string, any> = { ...st.components };
    for (const [k, v] of Object.entries(frame.components || {})) {
      next[k] = { ...(st.components[k] || {}), state: v, type: (st.components[k] || {}).type };
    }
    return { components: next, flows: frame.flows || [] };
  }),
  setComponents: (cs) => set(() => {
    const m: Record<string, any> = {};
    for (const c of cs) m[c.component_id] = c;
    return { components: m };
  }),
  setSelected: (id) => set((st) => ({
    selectedId: id,
    layer: id ? (st.layer === 0 ? 1 : st.layer) : 0,
  })),
  setLayer: (l) => set({ layer: l }),
  setScenarios: (s) => set({ scenarios: s }),
  setRun: (r) => set({ runResult: r, dtConfidence: r?.evaluation?.dt_confidence ?? null }),
  setRunBusy: (b) => set({ runBusy: b }),
  setRunError: (e) => set({ runError: e }),
  setShowWelcome: (b) => set({ showWelcome: b }),
  setShowAssumptions: (b) => set({ showAssumptions: b }),
  setShowConfidence: (b) => set({ showConfidence: b }),
  startStory: () => set({ storyMode: true, storyStep: 0, storyPlaying: true, storyDone: false }),
  stopStory: () => set({ storyMode: false, storyPlaying: false, storyStep: -1, storyDone: false }),
  setStoryStep: (n) => set({ storyStep: n }),
  advanceStory: (max) => set((st) => {
    const next = st.storyStep + 1;
    if (next >= max) return { storyStep: max - 1, storyPlaying: false, storyDone: true };
    return { storyStep: next };
  }),
  setStoryPlaying: (b) => set({ storyPlaying: b }),
  finishStory: () => set({ storyPlaying: false, storyDone: true }),
}));
