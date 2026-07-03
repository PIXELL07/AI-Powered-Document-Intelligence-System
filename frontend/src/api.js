const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";
export const WS_URL = import.meta.env.VITE_WS_URL || "ws://localhost:8000";

async function request(path, options = {}) {
  const res = await fetch(`${API_URL}${path}`, {
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    ...options,
  });
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`${res.status}: ${body}`);
  }
  const ct = res.headers.get("content-type") || "";
  return ct.includes("application/json") ? res.json() : res.text();
}

export const api = {
  listProjects: () => request("/api/projects"),
  createProject: (name, description) =>
    request("/api/projects", { method: "POST", body: JSON.stringify({ name, description }) }),
  getProject: (id) => request(`/api/projects/${id}`),
  deleteProject: (id) => request(`/api/projects/${id}`, { method: "DELETE" }),
  listProjectDocuments: (id) => request(`/api/projects/${id}/documents`),
  listContradictions: (id) => request(`/api/projects/${id}/contradictions`),

  uploadDocument: async (projectId, file) => {
    const form = new FormData();
    form.append("file", file);
    const res = await fetch(`${API_URL}/api/documents/upload?project_id=${projectId}`, {
      method: "POST",
      body: form,
    });
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  },

  getDocument: (id) => request(`/api/documents/${id}`),
  getDocumentStages: (id) => request(`/api/documents/${id}/stages`),
  getDocumentAnomalies: (id) => request(`/api/documents/${id}/anomalies`),
  getCrmSync: (id) =>
    request(`/api/documents/${id}/crm-sync`).catch(() => null),
  retryCrmSync: (id) => request(`/api/documents/${id}/crm-sync/retry`, { method: "POST" }),
  reprocessDocument: (id) => request(`/api/documents/${id}/reprocess`, { method: "POST" }),
  deleteDocument: (id) => request(`/api/documents/${id}`, { method: "DELETE" }),
};
