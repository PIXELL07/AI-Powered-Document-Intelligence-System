import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api";

export default function ProjectsView() {
  const [projects, setProjects] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");

  const load = () => api.listProjects().then(setProjects).finally(() => setLoading(false));

  useEffect(() => { load(); }, []);

  const handleCreate = async (e) => {
    e.preventDefault();
    if (!name.trim()) return;
    await api.createProject(name.trim(), description.trim());
    setName("");
    setDescription("");
    setShowForm(false);
    load();
  };

  return (
    <div>
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="font-display text-3xl font-semibold text-ink">Projects</h1>
          <p className="text-inkfaint text-sm mt-1">
            Group related documents — a contract with its invoices, a filing with its supporting statements.
          </p>
        </div>
        <button
          onClick={() => setShowForm((s) => !s)}
          className="font-mono text-xs uppercase tracking-wide px-4 py-2 rounded border border-ledger text-ledger hover:bg-ledger hover:text-white transition"
        >
          {showForm ? "Cancel" : "New project"}
        </button>
      </div>

      {showForm && (
        <form onSubmit={handleCreate} className="mb-8 border border-hairline rounded-md p-5 bg-surface">
          <div className="mb-3">
            <label className="block text-xs font-mono uppercase tracking-wide text-inkfaint mb-1">Name</label>
            <input
              autoFocus
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g. Acme Supplier Agreement — Q3"
              className="w-full border border-hairline rounded px-3 py-2 bg-paper focus:outline-none focus:ring-2 focus:ring-ledger/40"
            />
          </div>
          <div className="mb-4">
            <label className="block text-xs font-mono uppercase tracking-wide text-inkfaint mb-1">Description (optional)</label>
            <input
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="What documents belong here"
              className="w-full border border-hairline rounded px-3 py-2 bg-paper focus:outline-none focus:ring-2 focus:ring-ledger/40"
            />
          </div>
          <button type="submit" className="font-mono text-xs uppercase tracking-wide px-4 py-2 rounded bg-ledger text-white hover:bg-ledgerlight transition">
            Create project
          </button>
        </form>
      )}

      {loading ? (
        <p className="text-inkfaint text-sm">Loading…</p>
      ) : projects.length === 0 ? (
        <div className="border border-dashed border-hairline rounded-md p-10 text-center">
          <p className="text-inkfaint text-sm">No projects yet. Create one to start uploading documents.</p>
        </div>
      ) : (
        <div className="grid gap-3">
          {projects.map((p) => (
            <Link
              key={p.id}
              to={`/projects/${p.id}`}
              className="block border border-hairline rounded-md p-4 bg-surface hover:border-ledger transition"
            >
              <div className="flex items-baseline justify-between">
                <span className="font-display text-lg text-ink">{p.name}</span>
                <span className="font-mono text-xs text-inkfaint">
                  {new Date(p.created_at).toLocaleDateString()}
                </span>
              </div>
              {p.description && <p className="text-sm text-inkfaint mt-1">{p.description}</p>}
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
