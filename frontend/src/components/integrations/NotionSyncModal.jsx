import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { syncNotion, getProviderResources, createNotionDatabase } from '../../services/api';
import { useAuth } from '../../context/AuthContext';
import { Database, CheckCircle2, AlertCircle, ExternalLink, X } from 'lucide-react';

// Adds the chosen files as pages in a database from the user's own connected Notion.
export default function NotionSyncModal({ isOpen, onClose, items = [], components = [] }) {
  const targets = items.length > 0 ? items : components;
  const { notify } = useAuth();
  const [databases, setDatabases] = useState(null); // null = loading
  const [dbError, setDbError] = useState(null);
  const [databaseId, setDatabaseId] = useState('');
  const [pages, setPages] = useState([]);
  const [pageId, setPageId] = useState('');
  const [creating, setCreating] = useState(false);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);

  useEffect(() => {
    if (!isOpen) return;
    setResult(null);
    getProviderResources('notion')
      .then((r) => {
        const list = r.connected ? r.databases || [] : [];
        const shared = r.connected ? r.pages || [] : [];
        setPages(shared);
        if (shared.length) setPageId((p) => p || shared[0].id);
        setDbError(!r.connected || list.length || shared.length ? null : r.error || 'Nothing is shared with DebtScope yet. Disconnect Notion on the Integrations page, connect again and pick a page to share.');
        setDatabases(r.connected ? list : []);
        if (list.length) setDatabaseId((d) => d || list[0].id);
      })
      .catch(() => setDatabases([]));
  }, [isOpen]);

  if (!isOpen) return null;
  const connected = databases && databases.length > 0;

  // Notion's special databases (e.g. People) refuse new rows, so let users make a normal one in a shared page
  const createDatabase = async () => {
    setCreating(true);
    try {
      const d = await createNotionDatabase(pageId);
      setDatabases((list) => [d, ...(list || [])]);
      setDatabaseId(d.id);
      setDbError(null);
      notify('Created "DebtScope backlog" in your Notion.');
    } catch (err) {
      setDbError(err?.response?.data?.detail || "Couldn't create the database.");
    } finally {
      setCreating(false);
    }
  };

  const send = async () => {
    setLoading(true);
    try {
      const res = await syncNotion({
        database_id: databaseId || null,
        components: targets.map((c) => ({
          component_name: c.component || c.file_path || c.name || c.file || 'File',
          priority_score: c.priority_score ?? c.priority ?? 0,
          technical_risk: c.technical_risk ?? c.risk_score ?? 0,
          business_impact: c.business_impact ?? 0,
          roi_quadrant: c.roi_quadrant || c.quadrant || '—',
        })),
      });
      setResult(res);
      notify(res.mode === 'live' ? `Added ${res.synced_count} pages to Notion.` : 'Simulated only: Notion is not connected.');
    } catch (err) {
      const message = err?.response?.data?.detail || err?.message || 'Request failed';
      setResult({ status: 'error', message });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-[#161e10]/60 backdrop-blur-md animate-fade-in">
      <div className="relative w-full max-w-lg bg-white rounded-3xl shadow-2xl border border-[#d4dece] overflow-hidden">
        <div className="flex items-center justify-between px-6 py-5 bg-gradient-to-r from-[#2d3f16] via-[#43562b] to-[#1e2a0f] text-white">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-2xl bg-white/15 flex items-center justify-center border border-white/20">
              <Database className="h-5 w-5 text-[#d3ebb2]" />
            </div>
            <div>
              <h3 className="text-base font-bold tracking-tight">Send to Notion</h3>
              <p className="text-xs text-[#d3ebb2]">Adds one page per file to your Notion database</p>
            </div>
          </div>
          <button onClick={onClose} aria-label="Close" className="p-1.5 rounded-full text-white/70 hover:text-white hover:bg-white/10 transition cursor-pointer">
            <X className="h-5 w-5" />
          </button>
        </div>

        <div className="p-6 space-y-4 text-xs">
          {result ? (
            <div className="space-y-3 text-center py-2">
              <div className={`w-12 h-12 rounded-full flex items-center justify-center mx-auto ${result.status === 'error' ? 'bg-[#ffdad6] text-[#ba1a1a]' : 'bg-[#d3ebb2] text-[#2d3f16]'}`}>
                {result.status === 'error' ? <AlertCircle className="h-6 w-6" /> : <CheckCircle2 className="h-6 w-6" />}
              </div>
              <h4 className="text-base font-bold text-[#161e10]">
                {result.status === 'error' ? 'Sending to Notion failed' : result.mode === 'live' ? `Added ${result.synced_count} page${result.synced_count === 1 ? '' : 's'}` : 'Simulated — Notion not connected'}
              </h4>
              <p className="text-[#75786d]">
                {result.status === 'error' ? result.message : result.mode === 'live' ? 'Open them in Notion:' : 'Connect Notion on the Integrations page to add real pages.'}
              </p>
              {result.mode === 'live' && (
                <div className="flex flex-col items-center gap-1">
                  {(result.pages || []).slice(0, 10).map((p) => (
                    <a key={p.url} href={p.url} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 font-semibold text-[#43562b] hover:underline">
                      {p.component} <ExternalLink className="w-3 h-3" />
                    </a>
                  ))}
                  {(result.errors || []).length > 0 && <p className="text-[#855300]">{result.errors.length} failed: {result.errors[0]}</p>}
                </div>
              )}
              <button onClick={onClose} className="w-full py-2.5 bg-[#43562b] hover:bg-[#2d3f16] text-white font-bold rounded-2xl transition cursor-pointer">Done</button>
            </div>
          ) : (
            <>
              <p className="p-4 bg-[#f8faf6] rounded-2xl border border-[#d4dece] text-[#161e10]">
                <strong>{targets.length} file{targets.length === 1 ? '' : 's'}</strong>, one Notion page each.
              </p>
              <div>
                <label className="block text-[#45483e] font-semibold mb-1">Notion database</label>
                {databases === null ? (
                  <p className="text-[#75786d]">Loading your Notion databases…</p>
                ) : dbError ? (
                  <p className="text-[#855300]">{dbError}</p>
                ) : !connected && pages.length === 0 ? (
                  <p className="text-[#855300]">
                    Notion isn't connected, so this will only be simulated. <Link to="/integrations" onClick={onClose} className="font-semibold underline">Connect Notion</Link> to add real pages.
                  </p>
                ) : (
                  connected && (
                    <select value={databaseId} onChange={(e) => setDatabaseId(e.target.value)} className="w-full px-3.5 py-2 bg-[#f8faf6] border border-[#c5c8ba] rounded-xl">
                      {databases.map((d) => <option key={d.id} value={d.id}>{d.title}</option>)}
                    </select>
                  )
                )}
                {databases !== null && pages.length > 0 && (
                  <div className="mt-3 p-3 rounded-2xl border border-[#e5ebe0] bg-[#f8faf6] space-y-2">
                    <p className="text-[#45483e]">{connected ? 'Or create a new database' : 'No database yet. Create one'} in a page you shared:</p>
                    <div className="flex gap-2">
                      <select value={pageId} onChange={(e) => setPageId(e.target.value)} className="flex-1 min-w-0 px-3 py-1.5 bg-white border border-[#c5c8ba] rounded-xl">
                        {pages.map((p) => <option key={p.id} value={p.id}>{p.title}</option>)}
                      </select>
                      <button onClick={createDatabase} disabled={creating || !pageId} className="px-3 py-1.5 rounded-xl border border-[#c5c8ba] font-semibold text-[#2d3f16] hover:bg-white cursor-pointer disabled:opacity-50">
                        {creating ? 'Creating…' : 'Create "DebtScope backlog"'}
                      </button>
                    </div>
                  </div>
                )}
              </div>
              <div className="pt-2 flex items-center justify-end gap-2">
                <button onClick={onClose} className="px-4 py-2 bg-[#edf1e8] hover:bg-[#dde5d7] text-[#2d3f16] font-bold rounded-xl transition cursor-pointer">Cancel</button>
                <button
                  onClick={send}
                  disabled={loading || databases === null || !!dbError || targets.length === 0 || (!connected && pages.length > 0)}
                  className="px-5 py-2 bg-[#43562b] hover:bg-[#2d3f16] text-white font-bold rounded-xl shadow-md transition cursor-pointer disabled:opacity-50"
                >
                  {loading ? 'Sending…' : connected ? `Add ${targets.length} page${targets.length === 1 ? '' : 's'}` : 'Simulate'}
                </button>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
