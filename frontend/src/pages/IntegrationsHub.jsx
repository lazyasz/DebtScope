import React, { useCallback, useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { GitBranch, Layers, Database, CheckCircle2, CircleDashed, ArrowRight, Lock } from 'lucide-react';
import {
  getIntegrationsStatus,
  getProviderAuthUrl,
  getProviderResources,
  disconnectProvider,
  scanRepository,
  ingestNotionCriticality,
} from '../services/api';
import LoadingState from '../components/ui/LoadingState';
import ErrorState from '../components/ui/ErrorState';

const PROVIDERS = {
  github: {
    title: 'GitHub',
    icon: GitBranch,
    purpose: 'Connect your GitHub account to pick one of your repositories and scan it.',
    noun: 'repositories',
  },
  notion: {
    title: 'Notion',
    icon: Database,
    purpose: 'Connect your Notion workspace so service importance (which services matter most) shapes the priorities.',
    noun: 'databases',
  },
  jira: {
    title: 'Jira',
    icon: Layers,
    purpose: 'Connect your Jira site to turn top-priority files into tasks in your own projects.',
    noun: 'projects',
  },
};

export const callbackUrl = (provider) => `${window.location.origin}/integrations/callback/${provider}`;

export default function IntegrationsHub() {
  const [status, setStatus] = useState(null);
  const [error, setError] = useState(null);

  const load = useCallback(() => {
    getIntegrationsStatus().then(setStatus).catch((e) => setError(e.message || 'Could not load connections'));
  }, []);
  useEffect(load, [load]);

  if (error) return <ErrorState message={error} />;
  if (!status) return <LoadingState message="Checking your connections..." />;

  return (
    <div className="w-full px-4 sm:px-6 lg:px-8 py-6 space-y-6 max-w-[1100px] mx-auto animate-fade-in">
      <div className="space-y-1">
        <h1 className="text-2xl font-extrabold text-[#161e10] tracking-tight">Integrations</h1>
        <p className="text-sm text-[#45483e]">Connect your own accounts. DebtScope only reads what you choose, and you can disconnect at any time.</p>
      </div>
      {Object.keys(PROVIDERS).map((key) => (
        <ProviderCard key={key} provider={key} state={status[key] || {}} onChange={load} serverNotion={key === 'notion' && status.notion?.mode === 'live'} />
      ))}
    </div>
  );
}

function ProviderCard({ provider, state, onChange, serverNotion }) {
  const cfg = PROVIDERS[provider];
  const navigate = useNavigate();
  const connected = !!state.connected;
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState(null);
  const [items, setItems] = useState(null);

  useEffect(() => {
    if (!connected) return;
    getProviderResources(provider)
      .then((r) => setItems(r.repositories || r.databases || r.projects || r.items || []))
      .catch((e) => setMessage(e?.response?.data?.detail || 'Could not load your ' + cfg.noun));
  }, [connected, provider, cfg.noun]);

  const connect = async () => {
    setBusy(true);
    setMessage(null);
    try {
      const { auth_url, state: csrf } = await getProviderAuthUrl(provider, callbackUrl(provider));
      sessionStorage.setItem(`oauth_state_${provider}`, csrf);
      window.location.assign(auth_url);
    } catch (e) {
      setMessage(e?.response?.data?.detail || `Couldn't start ${cfg.title} sign-in.`);
      setBusy(false);
    }
  };

  const disconnect = async () => {
    setBusy(true);
    try {
      await disconnectProvider(provider);
      setItems(null);
      onChange();
    } catch (e) {
      setMessage(e?.response?.data?.detail || 'Disconnect failed.');
    } finally {
      setBusy(false);
    }
  };

  return (
    <section className="p-6 bg-white rounded-3xl border border-[#d4dece] space-y-3">
      <div className="flex items-center justify-between gap-3 flex-wrap">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-2xl bg-[#edf1e8] text-[#2d3f16] flex items-center justify-center">
            <cfg.icon className="w-5 h-5" />
          </div>
          <div>
            <h2 className="text-base font-bold text-[#161e10]">{cfg.title}</h2>
            {connected && state.account?.name && <p className="text-xs text-[#45483e]">Connected as {state.account.name}</p>}
          </div>
        </div>
        {connected ? (
          <span className="flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-semibold bg-[#e8f1db] text-[#2d3f16]">
            <CheckCircle2 className="w-3.5 h-3.5" /> Connected
          </span>
        ) : (
          <span className="flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-semibold bg-[#f4f4f2] text-[#75786d]">
            <CircleDashed className="w-3.5 h-3.5" /> Not connected
          </span>
        )}
      </div>

      <p className="text-sm text-[#45483e]">{cfg.purpose}</p>

      {!connected && (
        <button onClick={connect} disabled={busy} className={primary}>
          {busy ? 'Opening sign-in...' : `Connect ${cfg.title}`} <ArrowRight className="w-3.5 h-3.5" />
        </button>
      )}

      {message && <p className="text-xs text-[#855300]">{message}</p>}

      {connected && (
        <div className="space-y-2">
          <p className="text-xs font-semibold text-[#161e10]">Your {cfg.noun}{items ? ` (${items.length})` : ''}</p>
          {items === null ? (
            <p className="text-xs text-[#75786d]">Loading…</p>
          ) : items.length === 0 ? (
            <p className="text-xs text-[#75786d]">Nothing visible to this connection yet.</p>
          ) : (
            <ul className="divide-y divide-[#eef1ea] rounded-2xl border border-[#e5ebe0] max-h-80 overflow-y-auto">
              {items.map((it) => (
                <ResourceRow key={it.id || it.full_name || it.key || it.title} provider={provider} item={it} />
              ))}
            </ul>
          )}
          <div className="flex items-center gap-3 pt-1">
            {provider === 'jira' && (
              <button onClick={() => navigate('/priorities')} className={secondary}>Export priorities to Jira</button>
            )}
            <button onClick={disconnect} disabled={busy} className="text-xs text-[#ba1a1a] hover:underline cursor-pointer">
              Disconnect
            </button>
          </div>
        </div>
      )}

      {serverNotion && <ServerNotionImport />}
    </section>
  );
}

function ResourceRow({ provider, item }) {
  const navigate = useNavigate();
  const [state, setState] = useState('idle'); // idle | scanning | done | error
  const name = item.full_name || item.title || item.name || item.key;

  const scan = async () => {
    setState('scanning');
    try {
      await scanRepository(item.url);
      setState('done');
    } catch {
      setState('error');
    }
  };

  return (
    <li className="flex items-center justify-between gap-3 px-3 py-2 text-xs">
      <span className="flex items-center gap-1.5 min-w-0">
        {item.is_private && <Lock className="w-3 h-3 text-[#75786d] shrink-0" title="Private" />}
        <span className="font-mono truncate text-[#161e10]">{name}</span>
      </span>
      {provider === 'github' && (
        state === 'done' ? (
          <button onClick={() => navigate('/priorities')} className="text-[#2d3f16] font-semibold hover:underline cursor-pointer">Scanned · view priorities</button>
        ) : (
          <button onClick={scan} disabled={state === 'scanning'} className={secondary}>
            {state === 'scanning' ? 'Scanning…' : state === 'error' ? 'Failed · retry' : 'Scan'}
          </button>
        )
      )}
    </li>
  );
}

// Workspace-wide Notion table configured on the server (kept until per-user import exists)
function ServerNotionImport() {
  const [result, setResult] = useState(null);
  const [busy, setBusy] = useState(false);
  const run = async () => {
    setBusy(true);
    try {
      setResult(await ingestNotionCriticality());
    } catch (e) {
      setResult({ status: 'error', message: e?.response?.data?.detail || e.message });
    } finally {
      setBusy(false);
    }
  };
  return (
    <div className="p-3 rounded-2xl bg-[#f8faf6] border border-[#e5ebe0] space-y-2">
      <p className="text-xs text-[#45483e]">The app also has a shared service table set up by its administrator.</p>
      <button onClick={run} disabled={busy} className={secondary}>{busy ? 'Importing…' : 'Import shared service tiers'}</button>
      {result && (
        <p className="text-xs text-[#45483e]">
          {result.status === 'error'
            ? `Import failed: ${result.message}`
            : `Imported ${result.rules_ingested_count} rule(s): ${(result.rules || []).map((r) => `${r.service_name} (${r.tier})`).join(', ')}`}
        </p>
      )}
    </div>
  );
}

const primary =
  'inline-flex items-center gap-1.5 px-4 py-2 rounded-xl text-xs font-bold bg-[#43562b] hover:bg-[#2d3f16] text-white transition cursor-pointer disabled:opacity-50';
const secondary =
  'inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold border border-[#d4dece] text-[#161e10] hover:bg-[#f4f6f0] transition cursor-pointer disabled:opacity-50';
