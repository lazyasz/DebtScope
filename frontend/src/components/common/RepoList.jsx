import React, { useEffect, useState } from 'react';
import { GitBranch, Trash2 } from 'lucide-react';
import { getRepositories, deleteRepository, isSampleMode } from '../../services/api';

// The user's scanned repositories, with a way to remove one (and all its results).
export default function RepoList() {
  const [repos, setRepos] = useState(null);
  const [busyId, setBusyId] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    getRepositories().then((r) => setRepos(Array.isArray(r) ? r : [])).catch(() => setRepos([]));
  }, []);

  if (!repos || repos.length === 0) return null;
  const readOnly = isSampleMode();

  const remove = async (repo) => {
    if (!window.confirm(`Remove ${repo.name} and all of its scan results? This can't be undone.`)) return;
    setBusyId(repo.id);
    setError(null);
    try {
      await deleteRepository(repo.id);
      window.location.reload(); // every page's numbers change, so reload them all
    } catch (e) {
      setError(e?.response?.data?.detail || 'Could not remove it.');
      setBusyId(null);
    }
  };

  return (
    <section className="p-5 bg-white rounded-xl border border-[#e2e4ea] shadow-2xs space-y-2">
      <h2 className="text-sm font-bold text-[#0f1015]">Your repositories ({repos.length})</h2>
      <ul className="divide-y divide-[#eef1ea]">
        {repos.map((r) => (
          <li key={r.id} className="flex items-center justify-between gap-3 py-2 text-xs">
            <span className="flex items-center gap-2 min-w-0">
              <GitBranch className="w-3.5 h-3.5 text-[#7048e8] shrink-0" />
              <span className="font-mono truncate text-[#0f1015]">{r.url ? r.url.replace(/^https?:\/\/github\.com\//, '').replace(/\.git$/, '') : r.name}</span>
              <span className="text-[#88909e] shrink-0">{r.file_count} file{r.file_count === 1 ? '' : 's'}</span>
            </span>
            {!readOnly && (
              <button
                onClick={() => remove(r)}
                disabled={busyId === r.id}
                className="flex items-center gap-1 text-[#ba1a1a] hover:underline cursor-pointer disabled:opacity-50 shrink-0"
                aria-label={`Remove ${r.name}`}
              >
                <Trash2 className="w-3.5 h-3.5" /> {busyId === r.id ? 'Removing…' : 'Remove'}
              </button>
            )}
          </li>
        ))}
      </ul>
      {error && <p className="text-xs text-[#ba1a1a]">{error}</p>}
    </section>
  );
}
