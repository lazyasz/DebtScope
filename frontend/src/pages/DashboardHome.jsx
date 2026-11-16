import React, { useCallback, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { GitBranch, Layers, Sparkles, ArrowRight } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { getRepositories, isSampleMode, setSampleMode } from '../services/api';
import Dashboard from './Dashboard';
import ScanRepoModal from '../components/common/ScanRepoModal';
import LoadingState from '../components/ui/LoadingState';
import ErrorState from '../components/ui/ErrorState';

// Shows the real dashboard once the workspace has a repository; until then, a first-run guide.
export default function DashboardHome() {
  const [repos, setRepos] = useState(null);
  const [error, setError] = useState(null);

  const load = useCallback(() => {
    setError(null);
    getRepositories()
      .then(setRepos)
      .catch((e) => setError(e?.response?.data?.detail || e.message || 'Could not load repositories'));
  }, []);

  useEffect(load, [load]);

  if (error) return <ErrorState message={error} />;
  if (repos === null) return <LoadingState message="Loading your workspace..." />;
  if (repos.length > 0 || isSampleMode()) return <Dashboard />;
  return <GetStarted onScanned={load} />;
}

function GetStarted({ onScanned }) {
  const { user } = useAuth();
  const [scanOpen, setScanOpen] = useState(false);
  const firstName = (user?.name || '').split(' ')[0] || 'there';

  const exploreSample = () => {
    setSampleMode(true);
    window.location.reload();
  };

  const steps = [
    {
      icon: GitBranch,
      title: 'Scan a GitHub repository',
      body: 'Paste a public repo URL. DebtScope measures every file, predicts defect risk and ranks what to fix first.',
      action: <button onClick={() => setScanOpen(true)} className={primaryBtn}>Scan a repository <ArrowRight className="w-3.5 h-3.5" /></button>,
    },
    {
      icon: Layers,
      title: 'Connect your tools (optional)',
      body: 'Link Notion for service criticality and Jira for bug history, so priorities reflect business impact.',
      action: <Link to="/integrations" className={secondaryBtn}>Open Integrations</Link>,
    },
    {
      icon: Sparkles,
      title: 'Or explore sample data',
      body: 'Look around a pre-scanned demo codebase first. You can switch back to your workspace at any time.',
      action: <button onClick={exploreSample} className={secondaryBtn}>Explore sample data</button>,
    },
  ];

  return (
    <div className="max-w-3xl mx-auto px-4 sm:px-6 py-10 space-y-8">
      <div className="space-y-2">
        <span className="text-[10px] font-mono font-bold uppercase tracking-wider text-[#5b42a5]">Get started</span>
        <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-[#0f1015]">Welcome, {firstName}</h1>
        <p className="text-sm text-[#525866]">
          Your workspace is empty. Scan a repository to see which files carry the most technical debt and where to start.
        </p>
      </div>

      <ol className="space-y-3">
        {steps.map((s, i) => (
          <li key={s.title} className="flex flex-col sm:flex-row sm:items-center gap-4 p-5 bg-white rounded-2xl border border-[#e2e4ea]">
            <div className="flex items-start gap-4 flex-1">
              <div className="shrink-0 h-10 w-10 rounded-xl bg-[#f0ecfc] text-[#5b42a5] flex items-center justify-center">
                <s.icon className="w-5 h-5" />
              </div>
              <div>
                <h2 className="text-sm font-bold text-[#0f1015]">{i + 1}. {s.title}</h2>
                <p className="text-xs text-[#525866] mt-1 leading-relaxed">{s.body}</p>
              </div>
            </div>
            <div className="sm:shrink-0">{s.action}</div>
          </li>
        ))}
      </ol>

      <ScanRepoModal
        isOpen={scanOpen}
        onClose={() => { setScanOpen(false); onScanned(); }}
        onScanComplete={onScanned}
      />
    </div>
  );
}

const primaryBtn =
  'inline-flex items-center gap-1.5 px-4 py-2 rounded-lg text-xs font-semibold bg-[#130e24] text-white hover:bg-[#261c47] transition cursor-pointer';
const secondaryBtn =
  'inline-flex items-center gap-1.5 px-4 py-2 rounded-lg text-xs font-semibold border border-[#e2e4ea] text-[#0f1015] hover:bg-[#f3f4f8] transition cursor-pointer';
