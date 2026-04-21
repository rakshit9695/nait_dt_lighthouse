import React from "react";
import { useStore } from "../store";
import { STORY_ORDER, dtHoursFromRun } from "../util/storyOrder";

export default function StoryMetricsPanel({ run }: { run: any }) {
  const step = useStore((s) => s.storyStep);
  const dtH = React.useMemo(() => dtHoursFromRun(run), [run]);
  const ref = React.useRef<HTMLDivElement>(null);

  React.useEffect(() => {
    // scroll the latest card into view
    const el = ref.current?.querySelector(".story-card.current");
    if (el) (el as HTMLElement).scrollIntoView({ behavior: "smooth", block: "end" });
  }, [step]);

  const visible = STORY_ORDER.slice(0, Math.max(0, step + 1));

  return (
    <div className="story-metrics" ref={ref}>
      <div className="story-metrics-head">
        <h3>Building the digital twin</h3>
        <div className="muted small">
          Components are revealed in electrical order. Each card adds what that
          component contributed to this run; the metrics on the right are
          accumulating step-by-step.
        </div>
      </div>
      {visible.length === 0 && (
        <div className="muted small" style={{ marginTop: 12 }}>
          Waiting to begin…
        </div>
      )}
      {visible.map((s, i) => {
        const isCurrent = i === step;
        const ms = s.metrics(run, dtH);
        return (
          <div key={s.id} className={`story-card ${isCurrent ? "current" : ""}`}>
            <div className="story-card-head">
              <span className="story-num">{i + 1}</span>
              <div>
                <div className="story-title">{s.title}</div>
                <div className="story-role muted small">{s.role}</div>
              </div>
            </div>
            {isCurrent && <p className="story-blurb">{s.blurb}</p>}
            <div className="story-mlist">
              {ms.map((m, k) => (
                <div key={k} className="story-m">
                  <div className="story-m-val">{m.value}</div>
                  <div className="story-m-lab" title={m.hint || ""}>{m.label}</div>
                </div>
              ))}
            </div>
          </div>
        );
      })}
    </div>
  );
}
