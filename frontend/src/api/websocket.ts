export function openLiveSocket(onFrame: (f: any) => void): () => void {
  const apiBase = (import.meta as any).env?.VITE_API_BASE as string | undefined;
  let url: string;
  if (apiBase) {
    // strip protocol and rebuild as ws/wss
    const u = new URL(apiBase);
    const proto = u.protocol === "https:" ? "wss:" : "ws:";
    url = `${proto}//${u.host}/ws/live`;
  } else {
    const proto = location.protocol === "https:" ? "wss:" : "ws:";
    url = `${proto}//${location.host}/ws/live`;
  }
  const ws = new WebSocket(url);
  ws.onmessage = (e) => {
    try { onFrame(JSON.parse(e.data)); } catch { /* noop */ }
  };
  return () => ws.close();
}
