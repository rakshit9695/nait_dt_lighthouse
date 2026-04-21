export function openLiveSocket(onFrame: (f: any) => void): () => void {
  const proto = location.protocol === "https:" ? "wss:" : "ws:";
  const ws = new WebSocket(`${proto}//${location.host}/ws/live`);
  ws.onmessage = (e) => {
    try { onFrame(JSON.parse(e.data)); } catch { /* noop */ }
  };
  return () => ws.close();
}
