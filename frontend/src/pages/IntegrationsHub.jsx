import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { GitBranch, Layers, Database, CheckCircle2, CircleDashed, ArrowRight } from 'lucide-react';
import { getIntegrationsStatus, ingestNotionCriticality } from '../services/api';
import ScanRepoModal from '../components/common/ScanRepoModal';
import LoadingState from '../components/ui/LoadingState';
import ErrorState from '../components/ui/ErrorState';

// Jira and Notion are connected once, by whoever runs the server (Render → Environment),
// so this page shows real status and what each connection is used for.
export default function IntegrationsHub() {
  const navigate = useNavigate();
  const [status, setStatus] = useState(null);
  const [error, setError] = useState(null);
  const [scanOpen, setScanOpen] = useState(false);
  const [notionResult, setNotionResult] = useState(null);
  const [notionBusy, setNotionBusy] = useState(false);

  useEffect(() => {
    getIntegrationsStatus().then(setStatus).catch((e) => setError(e.message || 'Could not load integration status'));
  }, []);

  if (error) return <ErrorState message={error} />;
  if (!status) return <LoadingState message="Checking connections..." />;

  const jiraLive = status.jira?.mode === 'live';
  const notionLive = status.notion?.mode === 'live';
  const githubLive = !!status.github_token_configured;

  const importServiceTiers = async () => {
    setNotionBusy(true);
    try {
      setNotionResult(await ingestNotionCriticality());
    } catch (e) {
      setNotionResult({ status: 'error', message: e?.response?.data?.detail || e.message });
    } finally {
      setNotionBusy(false);
    }
  };

  return (
    <div className="w-full px-4 sm:px-6 lg:px-8 py-6 space-y-6 max-w-[1100px] mx-auto animate-fade-in">
      <div className="space-y-1">
        <h1 className="text-2xl font-extrabold text-[#161e10] tracking-tight">Integrations</h1>
        <p className="text-sm text-[#45483e]">
          Tools DebtScope reads from or sends work to. Connections are set up once for the whole app by its administrator.
        </p>
      </div>

      <Card
        icon={GitBranch}
        title="GitHub"
        live={githubLive}
        purpose="Reads public repositories to measure every file. A server token raises GitHub's limit from 60 to 5,000 requests an hour."
      >
        <button onClick={() => setScanOpen(true)} className={primary}>
          Scan a repository <ArrowRight className="w-3.5 h-3.5" />
        </button>
        {!githubLive && <Steps items={['Create a GitHub token with the public_repo scope', 'Add it as GITHUB_TOKEN in Render → Environment']} />}
      </Card>

      <Card
        icon={Database}
        title="Notion"
        live={notionLive}
        purpose="Imports your service criticality table (which services matter most) so priorities reflect business impact."
      >
        {notionLive ? (
          <>
            <button onClick={importServiceTiers} disabled={notionBusy} className={primary}>
              {notionBusy ? 'Importing...' : 'Import service tiers'}
            </button>
            {notionResult && (
              <p className="text-xs text-[#45483e]">
                {notionResult.status === 'error'
                  ? `Import failed: ${notionResult.message}`
                  : `Imported ${notionResult.rules_ingested_count} service rule${notionResult.rules_ingested_count === 1 ? '' : 's'}: ${(notionResult.rules || []).map((r) => `${r.service_name} (${r.tier})`).join(', ')}`}
              </p>
            )}
            <p className="text-[11px] text-[#75786d]">Sending the backlog to Notion needs a separate backlog database (not set up yet).</p>
          </>
        ) : (
          <Steps items={['Create an internal Notion connection and copy its token', 'Share your service table with it', 'Add NOTION_API_KEY and NOTION_DATABASE_ID in Render → Environment']} />
        )}
      </Card>

      <Card
        icon={Layers}
        title="Jira"
        live={jiraLive}
        purpose="Turns your top-priority files into Jira tasks, with priority and story points filled in."
      >
        {jiraLive ? (
          <button onClick={() => navigate('/priorities')} className={primary}>
            Export priorities to Jira <ArrowRight className="w-3.5 h-3.5" />
          </button>
        ) : (
          <Steps items={[
            'Create a free Jira Cloud site and a project with key DEBT',
            'Create an API token at id.atlassian.com → Security → API tokens',
            'Add JIRA_DOMAIN, JIRA_EMAIL and JIRA_API_TOKEN in Render → Environment',
          ]} />
        )}
      </Card>

      <ScanRepoModal isOpen={scanOpen} onClose={() => setScanOpen(false)} />
    </div>
  );
}

function Card({ icon: Icon, title, live, purpose, children }) {
  return (
    <section className="p-6 bg-white rounded-3xl border border-[#d4dece] space-y-3">
      <div className="flex items-center justify-between gap-3 flex-wrap">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-2xl bg-[#edf1e8] text-[#2d3f16] flex items-center justify-center">
            <Icon className="w-5 h-5" />
          </div>
          <h2 className="text-base font-bold text-[#161e10]">{title}</h2>
        </div>
        {live ? (
          <span className="flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-semibold bg-[#e8f1db] text-[#2d3f16]">
            <CheckCircle2 className="w-3.5 h-3.5" /> Connected
          </span>
        ) : (
          <span className="flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-semibold bg-[#f4f4f2] text-[#75786d]">
            <CircleDashed className="w-3.5 h-3.5" /> Not connected
          </span>
        )}
      </div>
      <p className="text-sm text-[#45483e]">{purpose}</p>
      <div className="space-y-2">{children}</div>
    </section>
  );
}

function Steps({ items }) {
  return (
    <div className="p-3 rounded-2xl bg-[#f8faf6] border border-[#e5ebe0]">
      <p className="text-xs font-semibold text-[#161e10] mb-1">To connect (administrator):</p>
      <ol className="list-decimal pl-5 space-y-0.5 text-xs text-[#45483e]">
        {items.map((s) => <li key={s}>{s}</li>)}
      </ol>
    </div>
  );
}

const primary =
  'inline-flex items-center gap-1.5 px-4 py-2 rounded-xl text-xs font-bold bg-[#43562b] hover:bg-[#2d3f16] text-white transition cursor-pointer disabled:opacity-50';
