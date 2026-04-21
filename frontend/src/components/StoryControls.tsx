import React from "react";
import { useStore } from "../store";
import { STORY_ORDER } from "../util/storyOrder";

export default function StoryControls() {
  const storyMode = useStore((s) => s.storyMode);
  const step = useStore((s) => s.storyStep);
  const playing = useStore((s) => s.storyPlaying);
  const done = useStore((s) => s.storyDone);
  const setStep = useStore((s) => s.setStoryStep);
  const setPlaying = useStore((s) => s.setStoryPlaying);
  const advance = useStore((s) => s.advanceStory);
  const stop = useStore((s) => s.stopStory);
  const finish = useStore((s) => s.finishStory);

  React.useEffect(() => {
    if (!storyMode || !playing || done) return;
    const t = setTimeout(() => advance(STORY_ORDER.length), 1700);
    return () => clearTimeout(t);
  }, [storyMode, playing, step, done, advance]);

  if (!storyMode) return null;

  const cur = STORY_ORDER[Math.max(0, step)];
  const total = STORY_ORDER.length;

  return (
    <div className="story-controls">
      <div className="story-controls-row">
        <button
          className="btn-ghost"
          title="Restart from step 1"
          onClick={() => { setStep(0); setPlaying(true); }}
        >⟲</button>
        <button
          className="btn-ghost"
          title="Step back"
          disabled={step <= 0}
          onClick={() => { setPlaying(false); setStep(Math.max(0, step - 1)); }}
        >◀</button>
        <button
          className="btn-primary play"
          title={playing ? "Pause" : "Play"}
          onClick={() => { if (done) { setStep(0); setPlaying(true); } else setPlaying(!playing); }}
        >{done ? "↻ Replay" : playing ? "⏸ Pause" : "▶ Play"}</button>
        <button
          className="btn-ghost"
          title="Step forward"
          disabled={done}
          onClick={() => { setPlaying(false); advance(total); }}
        >▶</button>
        <button
          className="btn-ghost"
          title="Skip to end"
          disabled={done}
          onClick={() => { setPlaying(false); setStep(total - 1); finish(); }}
        >⏭ Skip</button>
        <button
          className="btn-ghost danger"
          title="Exit story mode and show full results"
          onClick={() => stop()}
        >✕ Exit</button>
        <span className="story-step-label">
          Step <b>{Math.min(step + 1, total)}</b> / {total} · {cur?.title}
        </span>
      </div>
      <div className="story-progress">
        {STORY_ORDER.map((s, i) => (
          <span
            key={s.id}
            className={`dot ${i <= step ? "on" : ""} ${i === step ? "current" : ""}`}
            title={`${i + 1}. ${s.title}`}
            onClick={() => { setPlaying(false); setStep(i); }}
          />
        ))}
      </div>
    </div>
  );
}
