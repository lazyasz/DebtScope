import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { getHotspots } from '../services/api';
import { useAuth } from '../context/AuthContext';
import LoadingState from '../components/ui/LoadingState';
import ErrorState from '../components/ui/ErrorState';
import EmptyState from '../components/ui/EmptyState';
import ScanRepoModal from '../components/common/ScanRepoModal';
import JiraExportModal from '../components/integrations/JiraExportModal';
import RemediationRecipeModal from '../components/remediation/RemediationRecipeModal';
import AnimatedCounter from '../components/ui/AnimatedCounter';
import InteractiveCard from '../components/ui/InteractiveCard';
import SpringTabs from '../components/ui/SpringTabs';
import { 
  Flame, 
  RefreshCw, 
  Sparkles, 
  Layers, 
  Code2, 
  ArrowRight, 
  GitBranch, 
  AlertTriangle, 
  SlidersHorizontal,
  ChevronRight,
  Zap,
  Bot,
  Search
} from 'lucide-react';

export default function Hotspots() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [highRiskOnly, setHighRiskOnly] = useState(false);
  const [selectedComplexityFilter, setSelectedComplexityFilter] = useState('all');
  const [scanModalOpen, setScanModalOpen] = useState(false);
  const [jiraModalOpen, setJiraModalOpen] = useState(false);
  const [recipeModalOpen, setRecipeModalOpen] = useState(false);
  const [selectedItem, setSelectedItem] = useState(null);
  const { notify } = useAuth();
  const navigate = useNavigate();

  useEffect(() => {
    let cancelled = false;
    async function fetchData() {
      try {
        setLoading(true);
        setError(null);
        const result = await getHotspots();
        if (!cancelled) setData(result);
      } catch (err) {
        if (!cancelled) setError(err.message || 'Failed to load hotspots');
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    fetchData();
    return () => { cancelled = true; };
  }, []);

  const [searchQuery, setSearchQuery] = useState('');
  const [severityFilter, setSeverityFilter] = useState('ALL');

  if (loading) return <LoadingState message="Extracting Lexical AST metrics & God-classes..." />;
  if (error) return <ErrorState message={error} />;
  if (!data || data.length === 0) {
    return <EmptyState title="No hotspots yet" message="Files become hotspots when technical risk or business impact reaches 70+. Scan a repository to find them." />;
  }

  const normalizeItem = (item, idx) => {
    const file = item.file_path || item.file_name || item.file || item.path || item.name || `module_${item.file_id || idx + 1}`;
    // Show measured values only; '—' when the scan didn't record one
    const fmt = (v, d = 0) => (v === null || v === undefined ? '—' : Number(v).toFixed(d));
    const riskScore = fmt(item.technical_risk, 1);
    const complexity = fmt(item.cyclomatic_complexity);
    const churn = fmt(item.churn_commits);
    const smells = fmt(item.code_smells_count);
    const businessImpact = fmt(item.business_impact, 1);
    const id = item.file_id;

    return { id, file, riskScore, complexity, churn, smells, businessImpact, raw: item };
  };

  const normalizedList = data.map(normalizeItem);

  const filteredData = normalizedList.filter((item) => {
    const risk = parseFloat(item.riskScore);
    if (severityFilter === 'CRITICAL' && risk < 80) return false;
    if (severityFilter === 'HIGH' && (risk < 65 || risk >= 80)) return false;
    if (severityFilter === 'MODERATE' && risk >= 65) return false;
    if (searchQuery.trim() && !item.file.toLowerCase().includes(searchQuery.toLowerCase())) return false;
    return true;
  });

  const handleOpenJira = (normItem) => {
    setSelectedItem({
      component: normItem.file,
      priority_score: normItem.riskScore,
      remediation_effort_hours: normItem.raw.cyclomatic_complexity ? normItem.raw.cyclomatic_complexity * 0.8 : 8,
      defect_probability: (normItem.riskScore / 100) * 0.8,
      technical_risk: normItem.riskScore,
      business_impact: normItem.businessImpact,
      roi_quadrant: 'Strategic Refactoring',
    });
    setJiraModalOpen(true);
  };

  const raw = data;
  const nums = (key) => raw.map((r) => r[key]).filter((v) => v !== null && v !== undefined);
  const maxComplexityItem = raw.reduce((m, r) => ((r.cyclomatic_complexity ?? -1) > (m?.cyclomatic_complexity ?? -1) ? r : m), null);
  const totalChurn = nums('churn_commits').reduce((a, b) => a + b, 0);
  const churnEstimated = raw.some((r) => r.churn_provenance && r.churn_provenance !== 'MEASURED');
  const dupVals = nums('duplication_pct');
  const avgDup = dupVals.length ? dupVals.reduce((a, b) => a + b, 0) / dupVals.length : 0;
  const criticalCount = raw.filter((r) => r.technical_risk >= 80).length;

  const severityTabs = [
    { id: 'ALL', label: 'All Hotspots', count: normalizedList.length },
    { id: 'CRITICAL', label: 'Critical (≥80)', count: normalizedList.filter(i => parseFloat(i.riskScore) >= 80).length },
    { id: 'HIGH', label: 'High (65–79)', count: normalizedList.filter(i => parseFloat(i.riskScore) >= 65 && parseFloat(i.riskScore) < 80).length },
    { id: 'MODERATE', label: 'Moderate (<65)', count: normalizedList.filter(i => parseFloat(i.riskScore) < 65).length },
  ];

  return (
    <div className="w-full px-4 sm:px-6 lg:px-8 py-6 space-y-6 max-w-[1720px] mx-auto animate-fade-in">
      
      {/* Top Header Banner */}
      <section className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 p-6 sm:p-8 bg-white/95 backdrop-blur-xl rounded-3xl border border-[#d4dece] shadow-[0_8px_30px_-6px_rgba(45,63,22,0.08)]">
        <div className="space-y-2 max-w-3xl">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-[#e8f1db] text-[#2d3f16] font-mono text-xs font-bold tracking-wide uppercase border border-[#c5c8ba]/60">
              <span className="w-2 h-2 rounded-full bg-[#43562b] animate-pulse"></span>
              Risk ≥ 70 or impact ≥ 70
            </span>
          </div>
          <h1 className="text-2xl sm:text-4xl font-extrabold text-[#161e10] tracking-tight">
            Code Hotspots
          </h1>
          <p className="text-sm text-[#45483e]">
            Files where technical risk or business impact is 70 or higher, ranked by priority score.
          </p>
        </div>

        {/* Global Action Triggers */}
        <div className="flex items-center gap-3 flex-wrap">
          <button
            onClick={() => navigate('/priorities')}
            className="flex items-center gap-2 px-5 py-2.5 rounded-2xl bg-[#43562b] hover:bg-[#2d3f16] text-white text-xs font-bold shadow-[0_4px_16px_rgba(45,63,22,0.3)] transition active:scale-95 cursor-pointer"
          >
            <span>See all priorities</span>
            <ArrowRight className="w-4 h-4" />
          </button>
        </div>
      </section>

      {/* 4 Bento KPI Metric Capsules with Specular Sheen & Animated Counters */}
      <section className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-5">
        
        <InteractiveCard
          dark={true}
          isInteractive={true}
          className="min-h-[190px] flex flex-col justify-between"
        >
          <div className="flex items-start justify-between relative z-10">
            <div>
              <span className="text-xs font-mono uppercase tracking-wider text-[#d3ebb2] font-bold">
                Hotspots
              </span>
              <div className="text-3xl font-extrabold mt-1 leading-none font-mono">
                <AnimatedCounter value={raw.length} /> <span className="text-sm text-[#d3ebb2]/80 font-normal font-sans">files</span>
              </div>
            </div>
            <span className="p-2.5 rounded-2xl bg-white/15 text-white">
              <Flame className="w-5 h-5" />
            </span>
          </div>
          <div className="pt-3 flex items-center justify-between z-10 border-t border-white/10">
            <span className="text-xs text-[#d3ebb2] font-mono">Technical risk ≥ 80</span>
            <span className="px-2.5 py-0.5 rounded-full text-xs bg-white/15 font-bold font-mono">{criticalCount} critical</span>
          </div>
        </InteractiveCard>

        <InteractiveCard
          isInteractive={true}
          className="min-h-[190px] flex flex-col justify-between"
        >
          <div className="flex items-start justify-between">
            <div>
              <span className="text-xs font-mono uppercase tracking-wider text-[#45483e] font-bold">
                Highest Complexity
              </span>
              <div className="text-3xl font-extrabold text-[#161e10] tracking-tight mt-1 font-mono">
                <AnimatedCounter value={maxComplexityItem?.cyclomatic_complexity ?? 0} decimals={1} /> <span className="text-sm font-normal text-[#45483e] font-sans">cyclomatic</span>
              </div>
            </div>
            <span className="p-2.5 rounded-2xl bg-[#ffdad6] text-[#ba1a1a]">
              <AlertTriangle className="w-5 h-5" />
            </span>
          </div>
          <span className="text-xs text-[#ba1a1a] font-semibold pt-3 border-t border-[#e5ebe0]">
            {maxComplexityItem ? maxComplexityItem.file_name : 'No complexity data'}
          </span>
        </InteractiveCard>

        <InteractiveCard
          isInteractive={true}
          className="min-h-[190px] flex flex-col justify-between"
        >
          <div className="flex items-start justify-between">
            <div>
              <span className="text-xs font-mono uppercase tracking-wider text-[#45483e] font-bold">
                Code Churn
              </span>
              <div className="text-3xl font-extrabold text-[#161e10] tracking-tight mt-1 font-mono">
                <AnimatedCounter value={totalChurn} /> <span className="text-sm font-normal text-[#45483e] font-sans">commits</span>
              </div>
            </div>
            <span className="p-2.5 rounded-2xl bg-[#d3e4ac] text-[#2d3f16]">
              <GitBranch className="w-5 h-5" />
            </span>
          </div>
          <span className="text-xs text-[#556437] font-semibold pt-3 border-t border-[#e5ebe0]">
            {churnEstimated ? 'Estimated (no git history scanned)' : 'Measured from git history'}
          </span>
        </InteractiveCard>

        <InteractiveCard
          isInteractive={true}
          className="min-h-[190px] flex flex-col justify-between"
        >
          <div className="flex items-start justify-between">
            <div>
              <span className="text-xs font-mono uppercase tracking-wider text-[#45483e] font-bold">
                Code Duplication
              </span>
              <div className="text-3xl font-extrabold text-[#161e10] tracking-tight mt-1 font-mono">
                <AnimatedCounter value={avgDup} decimals={1} />% <span className="text-sm font-normal text-[#45483e] font-sans">average</span>
              </div>
            </div>
            <span className="p-2.5 rounded-2xl bg-[#fdf2e7] text-[#855300]">
              <Code2 className="w-5 h-5" />
            </span>
          </div>
          <span className="text-xs text-[#855300] font-semibold pt-3 border-t border-[#e5ebe0]">
            Across {dupVals.length} hotspot files
          </span>
        </InteractiveCard>
      </section>

      {/* Hotspots Deep Inspection Grid */}
      <section className="p-6 bg-white rounded-3xl border border-[#d4dece] shadow-[0_4px_20px_-4px_rgba(45,63,22,0.06)] space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-2 border-b border-[#e5ebe0]">
          <div>
            <h2 className="text-lg font-bold text-[#161e10]">Code Hotspots Explorer ({filteredData.length})</h2>
            <p className="text-xs text-[#45483e]">Click any module card or row to launch deep telemetry breakdown and AI refactoring diffs</p>
          </div>
          <button
            onClick={() => setScanModalOpen(true)}
            className="flex items-center gap-1.5 px-3 py-1.5 bg-[#edf1e8] hover:bg-[#dde5d7] text-[#2d3f16] text-xs font-bold rounded-xl transition border border-[#c5c8ba] cursor-pointer self-start sm:self-auto"
          >
            <Sparkles className="w-3.5 h-3.5 text-[#43562b]" />
            <span>Scan Another Repo</span>
          </button>
        </div>

        {/* Severity Filter Pills using SpringTabs & Search Input */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <SpringTabs
            tabs={severityTabs}
            activeTab={severityFilter}
            onChange={setSeverityFilter}
            size="md"
          />

          {/* Search Input */}
          <div className="relative min-w-[240px]">
            <Search className="w-4 h-4 text-[#75786d] absolute left-3 top-1/2 -translate-y-1/2 pointer-events-none" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Filter by file path..."
              className="w-full pl-8 pr-3 py-1.5 bg-[#f8faf6] border border-[#c5c8ba] rounded-xl text-xs text-[#161e10] placeholder-[#75786d] focus:outline-none focus:ring-2 focus:ring-[#43562b]"
            />
          </div>
        </div>

        {/* Mobile Card List (< 768px) */}
        <div className="md:hidden space-y-3">
          {filteredData.map((item, idx) => {
            return (
              <div
                key={item.id || idx}
                onClick={() => navigate(`/files/${item.id}`)}
                className="p-4 bg-[#f8faf6] hover:bg-[#eef3e8] border border-[#d4dece] rounded-2xl transition cursor-pointer space-y-3"
              >
                <div className="flex items-start justify-between gap-2">
                  <div className="flex items-center gap-2 min-w-0">
                    <Code2 className="w-4 h-4 text-[#43562b] shrink-0" />
                    <span className="font-mono font-bold text-sm text-[#161e10] truncate">
                      {item.file}
                    </span>
                  </div>
                  <span className="px-2.5 py-0.5 rounded-full bg-[#fdf2e7] text-[#855300] font-mono font-bold text-xs shrink-0">
                    {item.smells} Smells
                  </span>
                </div>

                <div className="grid grid-cols-3 gap-2 pt-2 border-t border-[#e5ebe0] text-center">
                  <div className="bg-white p-2 rounded-xl border border-[#e5ebe0]">
                    <span className="text-[11px] font-mono text-[#45483e] block">Risk</span>
                    <span className="font-mono font-bold text-sm text-[#ba1a1a] whitespace-nowrap">
                      {item.riskScore}
                    </span>
                  </div>
                  <div className="bg-white p-2 rounded-xl border border-[#e5ebe0]">
                    <span className="text-[11px] font-mono text-[#45483e] block">Complexity</span>
                    <span className="font-mono font-bold text-sm text-[#161e10] whitespace-nowrap">
                      {item.complexity}
                    </span>
                  </div>
                  <div className="bg-white p-2 rounded-xl border border-[#e5ebe0]">
                    <span className="text-[11px] font-mono text-[#45483e] block">Churn</span>
                    <span className="font-mono font-bold text-sm text-[#45483e] whitespace-nowrap">
                      {item.churn} commits
                    </span>
                  </div>
                </div>

                <div className="flex items-center justify-between pt-1" onClick={(e) => e.stopPropagation()}>
                  <span className="text-xs text-[#45483e]">
                    Impact: <strong className="text-[#161e10]">{item.businessImpact}/100</strong>
                  </span>
                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => {
                        setSelectedItem(item.raw);
                        setRecipeModalOpen(true);
                      }}
                      className="px-2.5 py-1.5 bg-[#edf1e8] hover:bg-[#dde5d7] text-[#2d3f16] rounded-xl text-xs font-bold transition flex items-center gap-1 border border-[#c5c8ba]"
                    >
                      <Sparkles className="w-3.5 h-3.5" />
                      <span>Recipe</span>
                    </button>
                    <button
                      onClick={() => handleOpenJira(item)}
                      className="px-2.5 py-1.5 bg-[#edf1e8] hover:bg-[#dde5d7] text-[#2d3f16] rounded-xl text-xs font-bold transition flex items-center gap-1 border border-[#c5c8ba]"
                    >
                      <Layers className="w-3.5 h-3.5" />
                      <span>Jira</span>
                    </button>
                    <button
                      onClick={() => navigate(`/files/${item.id}`)}
                      className="px-3 py-1.5 bg-[#43562b] hover:bg-[#2d3f16] text-white rounded-xl text-xs font-bold transition flex items-center gap-1 shadow-xs cursor-pointer"
                    >
                      <span>Inspect</span>
                      <ArrowRight className="w-3.5 h-3.5" />
                    </button>
                  </div>
                </div>
              </div>
            );
          })}
        </div>

        {/* Desktop/Tablet Table (>= 768px) */}
        <div className="hidden md:block overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead>
              <tr className="border-b border-[#e5ebe0] text-[#45483e] uppercase font-mono text-xs">
                <th className="py-3 px-4 font-bold">File Path</th>
                <th className="py-3 px-4 font-bold text-center whitespace-nowrap">Complexity</th>
                <th className="py-3 px-4 font-bold text-center whitespace-nowrap">Churn (commits)</th>
                <th className="py-3 px-4 font-bold text-center whitespace-nowrap">Smells / Bugs</th>
                <th className="py-3 px-4 font-bold text-center whitespace-nowrap">Technical Risk</th>
                <th className="py-3 px-4 font-bold text-center whitespace-nowrap">Business Impact</th>
                <th className="py-3 px-4 font-bold text-right whitespace-nowrap">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#f4f6f0]">
              {filteredData.map((item, idx) => {
                return (
                  <tr
                    key={item.id || idx}
                    onClick={() => navigate(`/files/${item.id}`)}
                    className="hover:bg-[#f8faf6] transition cursor-pointer group"
                  >
                    <td className="py-3.5 px-4">
                      <div className="flex items-center gap-2">
                        <Code2 className="w-4 h-4 text-[#43562b] shrink-0" />
                        <span className="font-mono font-semibold text-[#161e10] group-hover:text-[#43562b] transition">
                          {item.file}
                        </span>
                      </div>
                    </td>
                    <td className="py-3.5 px-4 text-center font-mono font-bold text-[#161e10] whitespace-nowrap">
                      {item.complexity}
                    </td>
                    <td className="py-3.5 px-4 text-center font-mono text-[#45483e] whitespace-nowrap">
                      {item.churn}
                    </td>
                    <td className="py-3.5 px-4 text-center whitespace-nowrap">
                      <span className="px-2.5 py-0.5 rounded-full bg-[#fdf2e7] text-[#855300] font-mono font-bold text-xs">
                        {item.smells} Smells
                      </span>
                    </td>
                    <td className="py-3.5 px-4 text-center font-mono font-bold text-[#ba1a1a] whitespace-nowrap">
                      {item.riskScore} / 100
                    </td>
                    <td className="py-3.5 px-4 text-center font-mono font-semibold text-[#161e10] whitespace-nowrap">
                      {item.businessImpact} / 100
                    </td>
                    <td className="py-3.5 px-4 text-right whitespace-nowrap" onClick={(e) => e.stopPropagation()}>
                      <div className="flex items-center justify-end gap-1.5">
                        <button
                          onClick={() => {
                            setSelectedItem(item.raw);
                            setRecipeModalOpen(true);
                          }}
                          className="px-2.5 py-1.5 bg-[#edf1e8] hover:bg-[#dde5d7] text-[#2d3f16] rounded-xl text-xs font-bold transition flex items-center gap-1 border border-[#c5c8ba] cursor-pointer"
                        >
                          <Sparkles className="w-3.5 h-3.5 text-[#43562b]" />
                          <span>Recipe</span>
                        </button>
                        <button
                          onClick={() => handleOpenJira(item)}
                          className="px-2.5 py-1.5 bg-[#edf1e8] hover:bg-[#dde5d7] text-[#2d3f16] rounded-xl text-xs font-bold transition flex items-center gap-1 border border-[#c5c8ba] cursor-pointer"
                        >
                          <Layers className="w-3.5 h-3.5 text-[#384a24]" />
                          <span>Jira</span>
                        </button>
                        <button
                          onClick={() => navigate(`/files/${item.id}`)}
                          className="px-3 py-1.5 bg-[#43562b] hover:bg-[#2d3f16] text-white rounded-xl text-xs font-bold transition flex items-center gap-1 shadow-xs ml-1 cursor-pointer"
                        >
                          <span>Inspect</span>
                          <ArrowRight className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </section>

      {/* Modals */}
      <ScanRepoModal
        isOpen={scanModalOpen}
        onClose={() => setScanModalOpen(false)}
      />

      <JiraExportModal
        isOpen={jiraModalOpen}
        onClose={() => setJiraModalOpen(false)}
        item={selectedItem}
      />

      <RemediationRecipeModal
        isOpen={recipeModalOpen}
        onClose={() => setRecipeModalOpen(false)}
        targetFile={selectedItem}
      />
    </div>
  );
}
