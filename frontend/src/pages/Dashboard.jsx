import React, { useState } from 'react';
import { 
  Activity, 
  Flame, 
  TrendingDown, 
  Bolt, 
  ArrowRight, 
  RefreshCw, 
  Layers, 
  Database, 
  ExternalLink,
  ChevronRight,
  ShieldCheck,
  Zap,
  Code2,
  Cpu,
  Sliders,
  FileText,
  GitPullRequest,
  Wand2
} from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { useMetrics } from '../hooks/useMetrics';
import { useAuth } from '../context/AuthContext';
import LoadingState from '../components/ui/LoadingState';
import ErrorState from '../components/ui/ErrorState';
import ScanRepoModal from '../components/common/ScanRepoModal';
import RemediationRecipeModal from '../components/remediation/RemediationRecipeModal';
import ExecutiveReportModal from '../components/reports/ExecutiveReportModal';
import ChartTooltip from '../components/ui/ChartTooltip';
import AnimatedCounter from '../components/ui/AnimatedCounter';
import InteractiveCard from '../components/ui/InteractiveCard';
import TelemetryRadar from '../components/ui/TelemetryRadar';
import { 
  ResponsiveContainer, 
  AreaChart, 
  Area, 
  XAxis, 
  YAxis, 
  Tooltip, 
  PieChart, 
  Pie, 
  Cell 
} from 'recharts';

export default function Dashboard() {
  const { data, loading, error, refresh } = useMetrics();
  const { notify, setSettingsOpen } = useAuth();
  const [scanModalOpen, setScanModalOpen] = useState(false);
  const [reportModalOpen, setReportModalOpen] = useState(false);
  const [recipeModalOpen, setRecipeModalOpen] = useState(false);
  const [selectedFileForRecipe, setSelectedFileForRecipe] = useState(null);
  const navigate = useNavigate();

  if (loading) return <LoadingState message="Connecting to AST telemetry & ML prediction mesh..." />;
  if (error) return <ErrorState message={error} />;

  const PALETTE = ['#7048e8', '#5b42a5', '#d97706', '#dc2626', '#059669', '#0ea5e9'];
  const kpis = data?.kpis || {};
  const health = data?.technical_debt_health?.score ?? 0;
  const trendData = data?.risk_trend || [];
  const categoryTotal = (data?.debt_categories || []).reduce((n, c) => n + c.value, 0);
  const categoryData = (data?.debt_categories || []).map((c, i) => ({
    name: (c.name.charAt(0) + c.name.slice(1).toLowerCase()).replace(/_/g, ' '),
    value: Math.round((100 * c.value) / Math.max(1, categoryTotal)),
    color: PALETTE[i % PALETTE.length],
  }));
  const recentItems = data?.recent_high_priority || [];

  return (
    <div className="w-full px-4 sm:px-6 lg:px-8 py-6 space-y-6 max-w-[1720px] mx-auto animate-fade-in">
      
      {/* Top Hero Banner with Telemetry Radar & Quick Actions */}
      <section className="relative overflow-hidden p-6 bg-white rounded-xl border border-[#e2e4ea] shadow-2xs">
        <div className="flex flex-col xl:flex-row xl:items-center justify-between gap-6 relative z-10">
          
          <div className="space-y-2.5 max-w-3xl">
            <div className="flex items-center gap-2 flex-wrap">
              <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-md bg-[#f0ecfc] text-[#5b42a5] font-mono text-[11px] font-bold tracking-wide uppercase border border-[#d8cdfa]">
                <span className="w-1.5 h-1.5 rounded-full bg-[#7048e8] animate-pulse"></span>
                DebtScope Telemetry Engine
              </span>
              <span className="text-[11px] text-[#525866] font-mono bg-[#f3f4f8] px-2 py-0.5 rounded border border-[#e2e4ea]">
                v4.18.2 · Active Mesh
              </span>
            </div>
            
            <h1 className="text-xl sm:text-3xl font-bold text-[#0f1015] tracking-tight">
              Predictive Engineering Intelligence Overview
            </h1>
            
            <p className="text-xs sm:text-sm text-[#525866] leading-relaxed">
              Real-time algorithmic triage linking software telemetry, AST cyclomatic depth, Random Forest defect models (Relative Defect Risk), and business ROI prioritization.
            </p>

            {/* Action Button Hierarchy: 1 Primary + 3 Secondary */}
            <div className="flex items-center gap-2 flex-wrap pt-1.5">
              <button
                onClick={() => setScanModalOpen(true)}
                className="flex items-center gap-1.5 px-3.5 py-2 rounded-lg bg-[#130e24] hover:bg-[#20173d] text-white text-xs font-semibold transition cursor-pointer shadow-2xs"
              >
                <RefreshCw className="w-3.5 h-3.5" />
                <span>Scan Repository AST</span>
              </button>

              <button
                onClick={() => navigate('/simulator')}
                className="flex items-center gap-1.5 px-3.5 py-2 rounded-lg bg-white hover:bg-[#f8f9fb] text-[#0f1015] text-xs font-semibold transition border border-[#e2e4ea] cursor-pointer"
              >
                <Sliders className="w-3.5 h-3.5 text-[#7048e8]" />
                <span>What-If Simulator</span>
              </button>

              <button
                onClick={() => setReportModalOpen(true)}
                className="flex items-center gap-1.5 px-3.5 py-2 rounded-lg bg-white hover:bg-[#f8f9fb] text-[#0f1015] text-xs font-semibold transition border border-[#e2e4ea] cursor-pointer"
              >
                <FileText className="w-3.5 h-3.5 text-[#7048e8]" />
                <span>Executive PDF</span>
              </button>

              <button
                onClick={() => navigate('/integrations')}
                className="flex items-center gap-1.5 px-3 py-2 rounded-lg bg-[#f8f9fb] hover:bg-[#f0ecfc] text-[#5b42a5] text-xs font-semibold transition border border-[#e2e4ea] cursor-pointer disabled:opacity-50"
              >
                <Layers className="w-3.5 h-3.5" />
                <span>Jira Backlog</span>
              </button>

              <button
                onClick={() => navigate('/integrations')}
                className="flex items-center gap-1.5 px-3 py-2 rounded-lg bg-[#f8f9fb] hover:bg-[#f3f4f8] text-[#525866] text-xs font-semibold transition border border-[#e2e4ea] cursor-pointer disabled:opacity-50"
              >
                <Database className="w-3.5 h-3.5" />
                <span>Notion Roadmap</span>
              </button>
            </div>
          </div>

          {/* Right Hero: Live Telemetry Radar Stream */}
          <div className="shrink-0 flex items-center justify-center p-3.5 bg-[#0b0714] rounded-xl border border-[#261c47] shadow-sm">
            <TelemetryRadar 
              size={120} 
              active={true} 
              healthScore={health} 
              label="Active AST Ingestion" 
            />
          </div>

        </div>
      </section>

      {/* 4 Bento KPI Metric Capsules with Specular Sheen & Tabular Numbers */}
      <section className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
        
        {/* KPI 1: Hero Lumina Obsidian Capsule */}
        <InteractiveCard
          dark={true}
          isInteractive={true}
          className="min-h-[180px] flex flex-col justify-between"
        >
          <div className="flex items-start justify-between relative z-10">
            <div>
              <span className="text-[11px] font-mono uppercase tracking-wider text-[#b39ef2] font-bold flex items-center gap-1.5">
                <span className="w-1.5 h-1.5 rounded-full bg-[#b39ef2] animate-ping"></span>
                Debt Health
              </span>
              <div className="text-3xl font-bold font-mono tracking-tight mt-1.5 text-white leading-none">
                <AnimatedCounter value={health} /> <span className="text-sm text-[#b39ef2]/80 font-normal">/ 100</span>
              </div>
            </div>
            <span className="p-2 rounded-lg bg-white/10 border border-white/15">
              <TrendingDown className="w-4 h-4 text-white" />
            </span>
          </div>

          <div className="pt-3.5 relative z-10 flex items-center justify-between border-t border-white/10 text-xs">
            <span className="text-[#b39ef2] font-mono text-[11px]">{kpis.files_analyzed ?? 0} files analysed</span>
            <span className="px-2 py-0.5 rounded text-[11px] bg-white/10 text-white font-semibold font-mono border border-white/15 capitalize">
              {data?.technical_debt_health?.status || '—'}
            </span>
          </div>
        </InteractiveCard>

        {/* KPI 2: Quick Wins Ready */}
        <InteractiveCard
          onClick={() => navigate('/priorities')}
          isInteractive={true}
          className="min-h-[180px] flex flex-col justify-between group"
        >
          <div className="flex items-start justify-between">
            <div>
              <span className="text-[11px] font-mono uppercase tracking-wider text-[#525866] font-semibold">
                Quick Wins
              </span>
              <div className="text-3xl font-bold text-[#0f1015] tracking-tight mt-1.5 font-mono">
                <AnimatedCounter value={kpis.quick_wins ?? 0} /> <span className="text-xs font-normal text-[#525866] font-sans">files</span>
              </div>
            </div>
            <span className="p-2 rounded-lg bg-[#f0ecfc] text-[#5b42a5]">
              <Bolt className="w-4 h-4 text-[#7048e8]" />
            </span>
          </div>
          <div className="pt-3.5 flex items-center justify-between border-t border-[#e2e4ea] text-xs">
            <span className="text-[#525866] text-[11px]">High impact · low effort</span>
            <span className="text-[11px] font-semibold text-[#5b42a5] group-hover:translate-x-0.5 transition flex items-center gap-1">
              <span>View Matrix</span>
              <ArrowRight className="w-3 h-3" />
            </span>
          </div>
        </InteractiveCard>

        {/* KPI 3: ML Defect Vulnerability */}
        <InteractiveCard
          onClick={() => navigate('/predictions')}
          isInteractive={true}
          className="min-h-[180px] flex flex-col justify-between group"
        >
          <div className="flex items-start justify-between">
            <div>
              <span className="text-[11px] font-mono uppercase tracking-wider text-[#525866] font-semibold">
                Average Defect Risk
              </span>
              <div className="text-3xl font-bold text-[#0f1015] tracking-tight mt-1.5 font-mono">
                <AnimatedCounter value={kpis.avg_defect_risk_pct ?? 0} decimals={1} />% <span className="text-xs font-normal text-[#525866] font-sans">per file</span>
              </div>
            </div>
            <span className="p-2 rounded-lg bg-[#fffbeb] text-[#d97706]">
              <Cpu className="w-4 h-4" />
            </span>
          </div>
          <div className="pt-3.5 flex items-center justify-between border-t border-[#e2e4ea] text-xs">
            <span className="text-[#b45309] text-[11px] font-medium">ML estimate (uncalibrated)</span>
            <span className="text-[11px] font-mono font-semibold text-[#b45309] group-hover:translate-x-0.5 transition flex items-center gap-1">
              <span>Risk Predictions</span>
              <ChevronRight className="w-3 h-3" />
            </span>
          </div>
        </InteractiveCard>

        {/* KPI 4: Monorepo Hotspots */}
        <InteractiveCard
          onClick={() => navigate('/hotspots')}
          isInteractive={true}
          className="min-h-[180px] flex flex-col justify-between group"
        >
          <div className="flex items-start justify-between">
            <div>
              <span className="text-[11px] font-mono uppercase tracking-wider text-[#525866] font-semibold">
                Complex Files
              </span>
              <div className="text-3xl font-bold text-[#0f1015] tracking-tight mt-1.5 font-mono">
                <AnimatedCounter value={kpis.complex_files ?? 0} /> <span className="text-xs font-normal text-[#525866] font-sans">files</span>
              </div>
            </div>
            <span className="p-2 rounded-lg bg-[#fef2f2] text-[#dc2626]">
              <Flame className="w-4 h-4 text-[#dc2626]" />
            </span>
          </div>
          <div className="pt-3.5 flex items-center justify-between border-t border-[#e2e4ea] text-xs">
            <span className="text-[#dc2626] text-[11px] font-medium">Cyclomatic complexity &gt; 25</span>
            <span className="text-[11px] font-semibold text-[#dc2626] group-hover:translate-x-0.5 transition flex items-center gap-1">
              <span>Inspect Files</span>
              <ArrowRight className="w-3 h-3" />
            </span>
          </div>
        </InteractiveCard>
      </section>

      {/* Analytical Section: Velocity Trajectory (8 cols) + Debt Decomposition (4 cols) */}
      <section className="grid grid-cols-1 lg:grid-cols-12 gap-5">
        
        {/* Left Bento: Velocity Trajectory Chart (8 cols) */}
        <div className="lg:col-span-8 p-5 bg-white rounded-xl border border-[#e2e4ea] shadow-2xs space-y-3">
          <div className="flex items-center justify-between flex-wrap gap-2">
            <div>
              <h2 className="text-sm font-bold text-[#0f1015] tracking-tight">Technical Risk Trend</h2>
              <p className="text-xs text-[#525866]">How average risk changes across your scans</p>
            </div>
          </div>

          {trendData.length < 2 ? (
            <div className="h-60 w-full flex items-center justify-center text-center text-xs text-[#88909e] border border-dashed border-[#e2e4ea] rounded-lg px-6">
              Not enough history yet. The trend appears once your repositories have been scanned more than once.
            </div>
          ) : (
          <div className="h-60 w-full pt-2">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={trendData} margin={{ top: 10, right: 25, left: -15, bottom: 0 }}>
                <defs>
                  <linearGradient id="luminaGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#7048e8" stopOpacity={0.25} />
                    <stop offset="95%" stopColor="#7048e8" stopOpacity={0.0} />
                  </linearGradient>
                </defs>
                <XAxis dataKey="period" stroke="#88909e" fontSize={11} tickLine={false} fontFamily="JetBrains Mono" />
                <YAxis stroke="#88909e" fontSize={11} tickLine={false} domain={[0, 100]} fontFamily="JetBrains Mono" />
                <Tooltip content={<ChartTooltip unit=" pts" />} />
                <Area 
                  type="monotone" 
                  dataKey="risk_score" 
                  name="Risk Score"
                  stroke="#7048e8" 
                  strokeWidth={2.5} 
                  fillOpacity={1} 
                  fill="url(#luminaGrad)" 
                  isAnimationActive={false} 
                  dot={{ r: 3.5, fill: '#7048e8', stroke: '#ffffff', strokeWidth: 2 }}
                  activeDot={{ r: 5, fill: '#130e24', stroke: '#ffffff', strokeWidth: 2 }}
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
          )}
        </div>

        {/* Right Bento: Category Decomposition (4 cols) */}
        <div className="lg:col-span-4 p-5 bg-white rounded-xl border border-[#e2e4ea] shadow-2xs flex flex-col justify-between">
          <div>
            <h2 className="text-sm font-bold text-[#0f1015]">Debt Decomposition</h2>
            <p className="text-xs text-[#525866]">Categorical breakdown of codebase friction</p>
          </div>

          {categoryData.length === 0 ? (
            <p className="my-auto py-10 text-center text-xs text-[#88909e]">No debt items recorded yet.</p>
          ) : (<>
          <div className="relative h-40 w-full my-auto flex items-center justify-center">
            <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none">
              <span className="text-xl font-bold text-[#0f1015] font-mono leading-none">100%</span>
              <span className="text-[10px] text-[#88909e] uppercase font-mono font-semibold tracking-wider mt-0.5">Indexed</span>
            </div>
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={categoryData}
                  cx="50%"
                  cy="50%"
                  innerRadius={46}
                  outerRadius={64}
                  paddingAngle={3}
                  dataKey="value"
                  stroke="#ffffff"
                  strokeWidth={2}
                  isAnimationActive={false}
                >
                  {categoryData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Pie>
                <Tooltip content={<ChartTooltip unit="%" />} />
              </PieChart>
            </ResponsiveContainer>
          </div>

          <div className="space-y-1.5 pt-3 border-t border-[#e2e4ea]">
            {categoryData.map((item) => (
              <div key={item.name} className="flex items-center justify-between text-xs p-1 rounded hover:bg-[#f8f9fb] transition">
                <div className="flex items-center gap-2 min-w-0">
                  <span className="w-2 h-2 rounded-full shrink-0" style={{ backgroundColor: item.color }} />
                  <span className="text-[#0f1015] font-medium truncate text-xs">{item.name}</span>
                </div>
                <div className="flex items-center gap-2 shrink-0">
                  <div className="w-12 h-1.5 rounded-full bg-[#f3f4f8] overflow-hidden hidden sm:block">
                    <div className="h-full rounded-full" style={{ width: `${item.value}%`, backgroundColor: item.color }} />
                  </div>
                  <span className="font-mono font-bold text-[#0f1015] text-xs w-8 text-right">{item.value}%</span>
                </div>
              </div>
            ))}
          </div>
          </>)}
        </div>
      </section>

      {/* Remediation Priority Queue Table */}
      <section className="p-5 bg-white rounded-xl border border-[#e2e4ea] shadow-2xs space-y-3">
        <div className="flex items-center justify-between flex-wrap gap-2">
          <div>
            <h2 className="text-sm font-bold text-[#0f1015]">Urgent Remediation Priority Queue</h2>
            <p className="text-xs text-[#525866]">Direct AST telemetry for top friction modules requiring developer triage</p>
          </div>
          <button
            onClick={() => navigate('/priorities')}
            className="flex items-center gap-1 text-xs font-semibold text-[#5b42a5] hover:text-[#7048e8] transition cursor-pointer"
          >
            <span>Explore 5D Matrix</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </button>
        </div>

        {recentItems.length === 0 && (
          <p className="py-6 text-center text-xs text-[#88909e]">No prioritised files yet. Scan a repository to fill this list.</p>
        )}

        {/* Mobile Card List (< 768px) */}
        <div className="md:hidden space-y-2.5">
          {recentItems.map((item) => (
            <div
              key={item.id}
              onClick={() => navigate(`/files/${item.id}`)}
              className="p-3.5 bg-[#f8f9fb] hover:bg-[#f3f4f8] border border-[#e2e4ea] rounded-lg transition cursor-pointer space-y-2.5"
            >
              <div className="flex items-start justify-between gap-2">
                <div className="flex items-center gap-2 min-w-0">
                  <Code2 className="w-4 h-4 text-[#7048e8] shrink-0" />
                  <span className="font-mono font-semibold text-xs text-[#0f1015] truncate">
                    {item.file}
                  </span>
                </div>
                <span className={`px-2 py-0.2 rounded text-[10px] font-mono font-bold shrink-0 ${
                  item.priority_level === 'CRITICAL'
                    ? 'bg-[#fef2f2] text-[#dc2626] border border-[#fca5a5]'
                    : 'bg-[#fffbeb] text-[#b45309] border border-[#fcd34d]'
                }`}>
                  {item.priority_level}
                </span>
              </div>

              <div className="flex items-center justify-between pt-1 text-xs">
                <span className="text-[#525866] font-medium bg-[#f0ecfc] text-[#5b42a5] px-2 py-0.5 rounded text-[11px]">
                  {item.category}
                </span>
                <span className="font-mono font-bold text-xs text-[#dc2626]">
                  Risk: {item.risk_score} / 100
                </span>
              </div>

              <div className="flex items-center justify-end gap-2 pt-2 border-t border-[#e2e4ea]" onClick={(e) => e.stopPropagation()}>
                <button
                  onClick={() => {
                    setSelectedFileForRecipe(item);
                    setRecipeModalOpen(true);
                  }}
                  className="px-2 py-1 bg-white hover:bg-[#f0ecfc] text-[#5b42a5] rounded text-xs font-semibold transition flex items-center gap-1 border border-[#e2e4ea] cursor-pointer"
                >
                  <Wand2 className="w-3 h-3 text-[#7048e8]" />
                  <span>Recipe</span>
                </button>
                <button
                  onClick={() => navigate(`/files/${item.id}`)}
                  className="px-2.5 py-1 bg-[#130e24] hover:bg-[#20173d] text-white rounded text-xs font-semibold transition flex items-center gap-1 cursor-pointer shadow-2xs"
                >
                  <span>Inspect</span>
                  <ArrowRight className="w-3 h-3" />
                </button>
              </div>
            </div>
          ))}
        </div>

        {/* Desktop/Tablet Table (>= 768px) */}
        <div className="hidden md:block overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead>
              <tr className="border-b border-[#e2e4ea] text-[#88909e] uppercase font-mono text-[11px]">
                <th className="py-2.5 px-3 font-semibold">Module Path</th>
                <th className="py-2.5 px-3 font-semibold text-center whitespace-nowrap">Risk Score</th>
                <th className="py-2.5 px-3 font-semibold text-center whitespace-nowrap">Priority</th>
                <th className="py-2.5 px-3 font-semibold whitespace-nowrap">Category</th>
                <th className="py-2.5 px-3 font-semibold text-right whitespace-nowrap">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#f3f4f8]">
              {recentItems.map((item) => (
                <tr 
                  key={item.id}
                  onClick={() => navigate(`/files/${item.id}`)}
                  className="hover:bg-[#f8f9fb] transition cursor-pointer group"
                >
                  <td className="py-3 px-3">
                    <div className="flex items-center gap-2">
                      <Code2 className="w-3.5 h-3.5 text-[#7048e8] shrink-0" />
                      <span className="font-mono font-medium text-[#0f1015] group-hover:text-[#7048e8] transition text-xs">
                        {item.file}
                      </span>
                    </div>
                  </td>
                  <td className="py-3 px-3 text-center font-mono font-bold text-[#dc2626] whitespace-nowrap text-xs">
                    {item.risk_score} / 100
                  </td>
                  <td className="py-3 px-3 text-center whitespace-nowrap">
                    <span className={`px-2 py-0.2 rounded text-[10px] font-bold font-mono border ${
                      item.priority_level === 'CRITICAL'
                        ? 'bg-[#fef2f2] text-[#dc2626] border-[#fca5a5]'
                        : 'bg-[#fffbeb] text-[#b45309] border-[#fcd34d]'
                    }`}>
                      {item.priority_level}
                    </span>
                  </td>
                  <td className="py-3 px-3 text-[#525866] font-medium whitespace-nowrap">
                    {item.category}
                  </td>
                  <td className="py-3 px-3 text-right whitespace-nowrap">
                    <div className="flex items-center justify-end gap-1.5" onClick={(e) => e.stopPropagation()}>
                      <button
                        onClick={() => {
                          setSelectedFileForRecipe(item);
                          setRecipeModalOpen(true);
                        }}
                        className="px-2.5 py-1 bg-white hover:bg-[#f0ecfc] text-[#5b42a5] rounded text-xs font-semibold transition flex items-center gap-1 border border-[#e2e4ea] cursor-pointer"
                        title="AI Remediation Recipe"
                      >
                        <Wand2 className="w-3 h-3 text-[#7048e8]" />
                        <span>Recipe</span>
                      </button>
                      <button
                        onClick={() => navigate(`/files/${item.id}`)}
                        className="px-2.5 py-1 bg-[#130e24] hover:bg-[#20173d] text-white rounded text-xs font-semibold transition flex items-center gap-1 shadow-2xs cursor-pointer"
                      >
                        <span>Inspect</span>
                        <ArrowRight className="w-3 h-3" />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {/* Modal instances */}
      <ScanRepoModal
        isOpen={scanModalOpen}
        onClose={() => setScanModalOpen(false)}
        onScanComplete={(res) => {
          notify(`Analysis complete for ${res.repository || 'repository'}!`);
          refresh();
        }}
      />

      <RemediationRecipeModal
        isOpen={recipeModalOpen}
        onClose={() => setRecipeModalOpen(false)}
        targetFile={selectedFileForRecipe}
      />

      <ExecutiveReportModal
        isOpen={reportModalOpen}
        onClose={() => setReportModalOpen(false)}
      />
    </div>
  );
}
