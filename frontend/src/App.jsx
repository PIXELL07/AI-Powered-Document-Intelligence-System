import { Routes, Route, Link, useLocation } from "react-router-dom";
import ProjectsView from "./pages/ProjectsView.jsx";
import ProjectDetail from "./pages/ProjectDetail.jsx";
import DocumentProcessing from "./pages/DocumentProcessing.jsx";
import DocumentDetail from "./pages/DocumentDetail.jsx";

export default function App() {
  const location = useLocation();

  return (
    <div className="min-h-screen bg-paper">
      <header className="border-b border-hairline bg-surface">
        <div className="max-w-6xl mx-auto px-6 py-4 flex items-baseline justify-between">
          <Link to="/" className="flex items-baseline gap-3">
            <span className="font-display text-2xl font-semibold text-ledger tracking-tight">
              Ledgerline
            </span>
            <span className="font-mono text-xs text-inkfaint uppercase tracking-widest">
              Document Intelligence
            </span>
          </Link>
          <nav className="font-mono text-xs uppercase tracking-widest text-inkfaint">
            <span className={location.pathname === "/" ? "text-ledger" : ""}>Projects</span>
          </nav>
        </div>
      </header>

      <main className="max-w-6xl mx-auto px-6 py-8">
        <Routes>
          <Route path="/" element={<ProjectsView />} />
          <Route path="/projects/:projectId" element={<ProjectDetail />} />
          <Route path="/documents/:documentId/processing" element={<DocumentProcessing />} />
          <Route path="/documents/:documentId" element={<DocumentDetail />} />
        </Routes>
      </main>
    </div>
  );
}
