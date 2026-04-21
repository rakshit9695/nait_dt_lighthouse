const TOKEN = (import.meta as any).env?.VITE_DT_TOKEN || "dev-token";
const API_BASE = (import.meta as any).env?.VITE_API_BASE || "";
const BASE = `${API_BASE}/api/v1`;

async function req<T>(path: string, init?: RequestInit): Promise<T> {
  const r = await fetch(BASE + path, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      "Authorization": `Bearer ${TOKEN}`,
      ...(init?.headers || {}),
    },
  });
  if (!r.ok) throw new Error(`${r.status} ${r.statusText}`);
  return r.json();
}

export const api = {
  topology: () => req<any>("/topology"),
  components: () => req<any[]>("/components"),
  scenarios: () => req<any[]>("/scenarios"),
  runScenario: (id: string) => req<any>(`/scenarios/${id}/run`, { method: "POST" }),
  evaluation: (runId: string) => req<any>(`/evaluation/${runId}`),
  command: (cid: string, body: any) =>
    req<any>(`/components/${cid}/command`, {
      method: "POST",
      body: JSON.stringify({ component_id: cid, command: body }),
    }),
  assumptions: () => req<any[]>("/assumptions"),
};
