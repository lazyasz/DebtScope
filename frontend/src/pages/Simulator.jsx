import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { Sliders, ArrowRight } from 'lucide-react';
import { getPriorities, getFile, runWhatIfSimulation } from '../services/api';
import LoadingState from '../components/ui/LoadingState';

const SENIORITY = ['Junior Engineer (1-2 yrs)', 'Mid-Level Engineer (3-5 yrs)', 'Senior Engineer (6-8 yrs)', 'Staff / Principal Architect (9+ yrs)'];

// One honest calculator: real file metrics in, the trained model's before/after out.
export default function Simulator() {
  const [files, setFiles] = useState(null);
  const [fileId, setFileId] = useState('');
  const [inputs, setInputs] = useState({ churn: 20, complexity: 10, debt_minutes: 60, effort: 50, coverage: 60, seniority: SENIORITY[2] });
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    getPriorities()
      .then((d) => {
        const list = (Array.isArray(d) ? d : d?.items || d?.files || []).slice(0, 25);
        setFiles(list);
        if (list.length) setFileId(String(list[0].file_id));
      })
      .catch(() => setFiles([]));
  }, []);

  // Prefill with the selected file's measured churn and complexity
  useEffect(() => {
    if (!fileId) return;
    getFile(fileId)
      .then((f) => setInputs((s) => ({
        ...s,
        churn: f.churn_commits ?? s.churn,
        complexity: f.cyclomatic_complexity != null ? Math.round(f.cyclomatic_complexity * 10) / 10 : s.complexity,
        coverage: f.test_coverage_pct != null ? Math.round(f.test_coverage_pct) : s.coverage,
      })))
      .catch(() => {});
  }, [fileId]);

  useEffect(() => {
    const t = setTimeout(() => {
      runWhatIfSimulation({
        churn: Number(inputs.churn) || 0,
        complexity: Number(inputs.complexity) || 1,
        debt_minutes: Number(inputs.debt_minutes) || 0,
        experience: 5,
        refactoring_effort_pct: Number(inputs.effort),
        developer_seniority: inputs.seniority,
        test_coverage_pct: Number(inputs.coverage),
      })
        .then((r) => { setResult(r); setError(null); })
        .catch((e) => setError(e?.response?.data?.detail || 'The simulation could not run.'));
    }, 250);
    return () => clearTimeout(t);
  }, [inputs]);

  if (files === null) return <LoadingState message="Loading your files..." />;
  const set = (k) => (e) => setInputs((s) => ({ ...s, [k]: e.target.value }));

  return (
    <div className="w-full px-4 sm:px-6 lg:px-8 py-6 space-y-6 max-w-[1000px] mx-auto animate-fade-in">
      <div className="space-y-1">
        <h1 className="text-2xl font-extrabold text-[#161e10] tracking-tight flex items-center gap-2">
          <Sliders className="w-5 h-5" /> What if we clean up this file?
        </h1>
        <p className="text-sm text-[#45483e]">
          Pick a file, choose how much cleanup you'd do, and see how the defect model's prediction changes.
        </p>
      </div>

      {files.length === 0 && (
        <p className="p-4 rounded-2xl bg-[#f8faf6] border border-[#e5ebe0] text-sm text-[#45483e]">
          No scanned files yet. <Link to="/dashboard" className="font-semibold text-[#43562b] hover:underline">Scan a repository</Link> to use your real files, or try the numbers below by hand.
        </p>
      )}

      <section className="p-6 bg-white rounded-3xl border border-[#d4dece] grid gap-4 sm:grid-cols-2 text-sm">
        {files.length > 0 && (
          <label className="sm:col-span-2 space-y-1">
            <span className="font-semibold text-[#161e10]">File</span>
            <select value={fileId} onChange={(e) => setFileId(e.target.value)} className={field}>
              {files.map((f) => <option key={f.file_id} value={f.file_id}>{f.file_path}</option>)}
            </select>
          </label>
        )}
        <Num label="Recent changes (commits)" value={inputs.churn} onChange={set('churn')} />
        <Num label="Complexity" value={inputs.complexity} onChange={set('complexity')} step="0.1" />
        <Num label="Your estimate of cleanup time needed (minutes)" value={inputs.debt_minutes} onChange={set('debt_minutes')} />
        <label className="space-y-1">
          <span className="font-semibold text-[#161e10]">Who does the work</span>
          <select value={inputs.seniority} onChange={set('seniority')} className={field}>
            {SENIORITY.map((s) => <option key={s}>{s}</option>)}
          </select>
        </label>
        <Slider label="How much of the cleanup you do" value={inputs.effort} onChange={set('effort')} />
        <Slider label="Test coverage after the work" value={inputs.coverage} onChange={set('coverage')} />
      </section>

      {error && <p className="text-sm text-[#ba1a1a]">{error}</p>}

      {result && (
        <section className="p-6 bg-white rounded-3xl border border-[#d4dece] space-y-4">
          <div className="grid gap-4 sm:grid-cols-3">
            <Stat label="Predicted defects now" value={result.baseline.predicted_faults} sub={result.baseline.risk_level} />
            <Stat label="Predicted defects after" value={result.simulated.predicted_faults} sub={result.simulated.risk_level} />
            <Stat label="Fewer defects" value={`${result.impact.fault_reduction_pct}%`} sub={`≈ ${result.impact.total_hours_saved} hours saved`} />
          </div>
          <p className="text-xs text-[#75786d]">
            {result.model_used === 'random_forest' ? 'Predicted by the trained defect model (Random Forest) that also scores your scans' : 'Estimated with a simple formula because the trained model is not available'}. A more experienced developer and higher test coverage also lower the prediction. Hours saved assumes about 16.5 hours per avoided defect plus the cleanup time removed.
          </p>
          {fileId && (
            <Link to={`/files/${fileId}`} className="inline-flex items-center gap-1 text-xs font-bold text-[#43562b] hover:underline">
              Open file details <ArrowRight className="w-3.5 h-3.5" />
            </Link>
          )}
        </section>
      )}
    </div>
  );
}

const field = 'w-full px-3 py-2 bg-[#f8faf6] border border-[#c5c8ba] rounded-xl focus:ring-2 focus:ring-[#43562b]';

function Num({ label, ...props }) {
  return (
    <label className="space-y-1">
      <span className="font-semibold text-[#161e10]">{label}</span>
      <input type="number" min="0" className={field} {...props} />
    </label>
  );
}

function Slider({ label, value, onChange }) {
  return (
    <label className="space-y-1">
      <span className="font-semibold text-[#161e10]">{label}: {value}%</span>
      <input type="range" min="0" max="100" value={value} onChange={onChange} className="w-full accent-[#43562b]" />
    </label>
  );
}

function Stat({ label, value, sub }) {
  return (
    <div className="p-4 rounded-2xl bg-[#f8faf6] border border-[#e5ebe0]">
      <p className="text-xs text-[#45483e]">{label}</p>
      <p className="text-2xl font-extrabold text-[#161e10]">{value}</p>
      <p className="text-xs text-[#75786d]">{sub}</p>
    </div>
  );
}
