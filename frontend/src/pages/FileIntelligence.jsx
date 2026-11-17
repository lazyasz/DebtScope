import React, { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useFile } from '../hooks/useFile';
import { FileCode, GitBranch, Shield, Target, Layers, Database, ArrowLeft, Sparkles, Bot, AlertTriangle, Code2, Bug } from 'lucide-react';
import LoadingState from '../components/ui/LoadingState';
import ErrorState from '../components/ui/ErrorState';
import EmptyState from '../components/ui/EmptyState';
import JiraExportModal from '../components/integrations/JiraExportModal';
import NotionSyncModal from '../components/integrations/NotionSyncModal';
import { getAiRemediationRecipe } from '../services/api';

const fmt = (v, d = 1) => (v === null || v === undefined ? '—' : Number(v).toFixed(d));

// Weights of the priority formula (backend/config.py): how each factor contributes.
const FACTORS = [
  { key: 'composite_technical_risk', dim: 'technical_risk', label: 'Technical risk', weight: 0.35, hint: 'Complexity, smells, duplication, coverage + ML defect prediction' },
  { key: 'composite_business_impact', dim: 'business_impact', label: 'Business impact', weight: 0.30, hint: 'How important this part of the product is' },
  { key: 'composite_urgency', dim: 'release_urgency', label: 'Release urgency', weight: 0.15, hint: 'Upcoming releases and sprint pressure' },
  { key: 'maintenance_cost', dim: 'maintenance_cost', label: 'Maintenance cost', weight: 0.10, hint: 'How costly the file is to keep changing' },
  { key: 'normalized_debt_age', dim: 'debt_age', label: 'Debt age', weight: 0.10, hint: 'How long the debt has existed' },
];

export default function FileIntelligence() {
  const { id } = useParams();
  const { data, loading, error } = useFile(id);
  const navigate = useNavigate();

  const [jiraOpen, setJiraOpen] = useState(false);
  const [notionOpen, setNotionOpen] = useState(false);
  const [recipe, setRecipe] = useState(null);
  const [recipeState, setRecipeState] = useState('idle'); // idle | loading | error

  if (loading) return <LoadingState message="Loading file details..." />;
  if (error) return <ErrorState message={error} />;
  if (!data) return <EmptyState title="File not found" message="It may belong to another workspace or was removed by a newer scan." />;

  const b = data.breakdown || {};
  const level = (data.priority_level || '').toUpperCase();
  const levelStyle = level === 'CRITICAL' ? 'bg-[#ffdad6] text-[#ba1a1a]' : level === 'HIGH' ? 'bg-[#ffddb8] text-[#855300]' : 'bg-[#edf1e8] text-[#2d3f16]';

  const componentData = {
    component: data.file_path,
    priority_score: data.priority_score,
    remediation_effort_hours: data.remediation_effort,
    technical_risk: data.technical_risk,
    business_impact: data.business_impact,
    roi_quadrant: data.quadrant,
  };

  const loadRecipe = async () => {
    setRecipeState('loading');
    try {
      const res = await getAiRemediationRecipe({
        file_path: data.file_path,
        risk_score: data.priority_score,
        debt_minutes: Math.max(30, (data.remediation_effort || 0) * 6),
        complexity: data.cyclomatic_complexity ?? 1,
      });
      setRecipe(res);
      setRecipeState('idle');
    } catch {
      setRecipeState('error');
    }
  };

  const metrics = [
    { label: 'Technical risk', value: `${fmt(data.technical_risk)} / 100`, icon: Shield },
    { label: 'Predicted risk', value: `${fmt(data.predicted_risk)} / 100`, icon: Target },
    { label: 'Cyclomatic complexity', value: fmt(data.cyclomatic_complexity, 0), icon: GitBranch },
    { label: 'Lines of code', value: data.lines_of_code != null ? data.lines_of_code.toLocaleString() : '—', icon: FileCode },
    { label: 'Code smells', value: fmt(data.code_smells_count, 0), icon: Bug },
    {
      label: 'Churn (commits)',
      value: fmt(data.churn_commits, 0),
      note: data.churn_provenance && data.churn_provenance !== 'MEASURED' ? 'estimated' : null,
      icon: Code2,
    },
  ];

  return (
    <div className="w-full px-4 sm:px-6 lg:px-8 py-6 space-y-6 max-w-[1400px] mx-auto animate-fade-in">
      {/* Top bar */}
      <div className="flex items-center justify-between flex-wrap gap-3">
        <button
          onClick={() => navigate(-1)}
          className="flex items-center gap-2 px-3.5 py-2 rounded-full bg-white hover:bg-[#edf1e8] text-[#2d3f16] text-xs font-bold border border-[#d4dece] transition cursor-pointer"
        >
          <ArrowLeft className="w-4 h-4" /> Back
        </button>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setNotionOpen(true)}
            className="flex items-center gap-1.5 px-4 py-2 bg-white hover:bg-[#f8faf6] text-[#161e10] text-xs font-bold rounded-2xl border border-[#d4dece] transition cursor-pointer"
          >
            <Database className="w-4 h-4 text-[#384a24]" /> Send to Notion
          </button>
          <button
            onClick={() => setJiraOpen(true)}
            className="flex items-center gap-2 px-5 py-2 bg-[#43562b] hover:bg-[#2d3f16] text-white text-xs font-bold rounded-2xl transition cursor-pointer"
          >
            <Layers className="w-4 h-4" /> Create Jira task
          </button>
        </div>
      </div>

      {/* Header */}
      <section className="p-6 bg-white rounded-3xl border border-[#d4dece] space-y-2">
        <div className="flex items-center gap-2 flex-wrap">
          <h1 className="text-xl sm:text-2xl font-extrabold font-mono text-[#161e10] break-all">{data.file_path}</h1>
          {level && <span className={`px-2.5 py-0.5 rounded-full font-mono text-[10px] font-bold ${levelStyle}`}>{level}</span>}
          {data.is_experimental && (
            <span className="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-amber-50 text-amber-700 border border-amber-200">
              Experimental prediction for this language
            </span>
          )}
        </div>
        <p className="text-xs text-[#45483e]">
          {data.repository_name} · priority score <strong>{fmt(data.priority_score)}</strong> · {(data.quadrant || '').replace(/_/g, ' ').toLowerCase()}
        </p>
        {data.recommendation && <p className="text-sm text-[#161e10]">{data.recommendation}</p>}
      </section>

      {/* Why it ranks here */}
      <section className="p-6 bg-white rounded-3xl border border-[#d4dece] space-y-4">
        <div>
          <h2 className="text-base font-bold text-[#161e10]">Why it ranks here</h2>
          <p className="text-xs text-[#75786d]">Each factor's score (0–100) times its weight adds up to the base priority score.</p>
        </div>
        <div className="space-y-3">
          {FACTORS.map((f) => {
            const score = b[f.key];
            const points = typeof score === 'number' ? score * f.weight : null;
            const isDefault = (data.missing_dimensions || []).includes(f.dim);
            return (
              <div key={f.key} className="grid grid-cols-12 items-center gap-3 text-xs">
                <div className="col-span-12 sm:col-span-4">
                  <p className="font-semibold text-[#161e10]">{f.label} <span className="text-[#75786d] font-normal">({f.weight * 100}%)</span></p>
                  <p className="text-[11px] text-[#75786d]">
                    {isDefault ? <span className="text-[#855300]">Default value — connect Notion/Jira to measure this</span> : f.hint}
                  </p>
                </div>
                <div className="col-span-9 sm:col-span-6 h-2 rounded-full bg-[#edf1e8] overflow-hidden">
                  <div className={`h-full ${isDefault ? 'bg-[#d9c8a9]' : 'bg-[#43562b]'}`} style={{ width: `${Math.min(100, score || 0)}%` }} />
                </div>
                <div className="col-span-3 sm:col-span-2 text-right font-mono">
                  {fmt(score, 0)} → <strong>{points === null ? '—' : points.toFixed(1)}</strong>
                </div>
              </div>
            );
          })}
        </div>
        <div className="flex flex-wrap gap-x-6 gap-y-1 pt-3 border-t border-[#e5ebe0] text-xs text-[#45483e] font-mono">
          <span>Base score: <strong className="text-[#161e10]">{fmt(b.baseline_priority_score)}</strong></span>
          <span>Effort adjustment: <strong className="text-[#161e10]">{b.effort_deduction_or_boost >= 0 ? '+' : ''}{fmt(b.effort_deduction_or_boost)}</strong></span>
          <span>Final priority: <strong className="text-[#161e10]">{fmt(data.priority_score)}</strong></span>

        </div>
      </section>

      {/* Measured metrics */}
      <section className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-4">
        {metrics.map((m) => (
          <div key={m.label} className="p-4 bg-white rounded-3xl border border-[#d4dece] space-y-1">
            <m.icon className="w-4 h-4 text-[#43562b]" />
            <p className="text-lg font-mono font-extrabold text-[#161e10] pt-1">{m.value}</p>
            <p className="text-[10px] font-bold uppercase tracking-wider text-[#556437]">
              {m.label}{m.note && <span className="normal-case font-normal text-[#855300]"> · {m.note}</span>}
            </p>
          </div>
        ))}
      </section>

      <section className="grid grid-cols-1 lg:grid-cols-12 gap-5">
        {/* Debt items */}
        <div className="lg:col-span-6 p-6 bg-white rounded-3xl border border-[#d4dece] space-y-3">
          <h2 className="text-base font-bold text-[#161e10]">Debt found in this file ({data.technical_debt_items?.length || 0})</h2>
          {(data.technical_debt_items || []).length === 0 ? (
            <p className="text-xs text-[#75786d] py-6 text-center">No individual debt items were recorded for this file.</p>
          ) : (
            <ul className="space-y-2">
              {data.technical_debt_items.map((d) => (
                <li key={d.id} className="p-3 rounded-2xl bg-[#f8faf6] border border-[#e5ebe0] text-xs space-y-1">
                  <div className="flex items-center gap-2 flex-wrap">
                    <AlertTriangle className="w-3.5 h-3.5 text-[#855300]" />
                    <strong className="text-[#161e10]">{(d.category || '').replace(/_/g, ' ').toLowerCase()}</strong>
                    <span className="font-mono text-[10px] px-1.5 rounded bg-white border border-[#d4dece]">{d.severity}</span>
                    {d.line_number && <span className="text-[#75786d]">line {d.line_number}</span>}
                    <span className="text-[#75786d]">{d.debt_age_days} days old</span>
                  </div>
                  <p className="text-[#45483e]">{d.description}</p>
                  {d.remediation_guidance && <p className="text-[#2d3f16]">Fix: {d.remediation_guidance}</p>}
                </li>
              ))}
            </ul>
          )}
        </div>

        {/* Fix recipe */}
        <div className="lg:col-span-6 p-6 bg-white rounded-3xl border border-[#d4dece] space-y-4">
          <div className="flex items-center justify-between gap-2 flex-wrap">
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 rounded-xl bg-[#43562b] text-white flex items-center justify-center"><Bot className="w-4 h-4" /></div>
              <div>
                <h2 className="text-base font-bold text-[#161e10]">How to fix it</h2>
                <p className="text-xs text-[#75786d]">Rule-based recipe from this file's complexity and path</p>
              </div>
            </div>
            <button
              onClick={loadRecipe}
              disabled={recipeState === 'loading'}
              className="px-3 py-1.5 bg-[#43562b] hover:bg-[#2d3f16] text-white rounded-xl text-xs font-bold transition flex items-center gap-1.5 disabled:opacity-50 cursor-pointer"
            >
              <Sparkles className="w-3.5 h-3.5" />
              {recipeState === 'loading' ? 'Building...' : recipe ? 'Refresh' : 'Get recipe'}
            </button>
          </div>

          {recipeState === 'error' && <p className="text-xs text-[#ba1a1a]">Couldn't build a recipe right now. Try again.</p>}

          {recipe ? (
            <div className="space-y-3 text-xs">
              <p><strong className="text-[#161e10]">Likely problem:</strong> {recipe.identified_smell}</p>
              <p className="text-[#45483e]">{recipe.impact_analysis}</p>
              <ol className="space-y-1 text-[#161e10]">
                {(recipe.recipe_steps || []).map((s) => <li key={s}>{s}</li>)}
              </ol>
              {recipe.code_diff && (
                <details className="rounded-2xl border border-[#d4dece]">
                  <summary className="cursor-pointer px-3 py-2 font-semibold text-[#2d3f16]">Example of this pattern (generic code, not your file)</summary>
                  <div className="grid sm:grid-cols-2 gap-2 p-3">
                    <pre className="bg-[#fff5f4] p-2 rounded-lg overflow-x-auto text-[10px]">{recipe.code_diff.before}</pre>
                    <pre className="bg-[#f2f8ea] p-2 rounded-lg overflow-x-auto text-[10px]">{recipe.code_diff.after}</pre>
                  </div>
                </details>
              )}
            </div>
          ) : (
            recipeState !== 'error' && <p className="text-xs text-[#75786d] py-6 text-center">Click "Get recipe" for step-by-step refactoring guidance.</p>
          )}

          <button onClick={() => navigate('/copilot')} className="text-xs text-[#43562b] font-bold hover:underline">
            Ask the AI Copilot about this file →
          </button>
        </div>
      </section>

      <JiraExportModal isOpen={jiraOpen} onClose={() => setJiraOpen(false)} component={componentData} />
      <NotionSyncModal isOpen={notionOpen} onClose={() => setNotionOpen(false)} items={[componentData]} />
    </div>
  );
}
