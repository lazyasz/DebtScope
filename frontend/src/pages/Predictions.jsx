import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { usePredictions } from '../hooks/usePredictions';
import { getModelInfo, getPriorities } from '../services/api';
import LoadingState from '../components/ui/LoadingState';
import ErrorState from '../components/ui/ErrorState';
import EmptyState from '../components/ui/EmptyState';
import AnimatedCounter from '../components/ui/AnimatedCounter';
import InteractiveCard from '../components/ui/InteractiveCard';
import { 
  Activity, 
  Cpu, 
  Sparkles, 
  TrendingUp, 
  Sliders, 
  CheckCircle2, 
  ArrowRight, 
  Layers, 
  Code2, 
  BarChart3,
  Flame,
  ShieldAlert,
  BrainCircuit
} from 'lucide-react';
import ChartTooltip from '../components/ui/ChartTooltip';
import { 
  ResponsiveContainer, 
  BarChart, 
  Bar, 
  XAxis, 
  YAxis, 
  Tooltip, 
  Cell
} from 'recharts';

export default function Predictions() {
  const { data, loading, error } = usePredictions();
  const navigate = useNavigate();
  const [model, setModel] = useState(null);
  const [ranked, setRanked] = useState([]);

  useEffect(() => {
    getModelInfo().then(setModel).catch(() => setModel(null));
    getPriorities('source').then((r) => setRanked(r || [])).catch(() => setRanked([]));
  }, []);

  if (loading) return <LoadingState message="Loading predictions..." />;
  if (error) return <ErrorState message={error} />;
  if (!data || data.length === 0) {
    return <EmptyState title="No predictions yet" message="Scan a repository and the defect model will score each of its files." />;
  }

  const pretty = (f) => f.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
  const GREENS = ['#384a24', '#4d6332', '#687e45', '#889d62', '#a3b57f', '#bccb9c'];
  const featureImportanceData = (model?.features || []).slice(0, 6).map((f, i) => ({
    feature: pretty(f.feature),
    weight: Math.round(f.importance * 1000) / 10,
    color: GREENS[i],
  }));
  const topFeature = model?.features?.[0];
  const probs = data.map((p) => p.defect_probability).filter((v) => typeof v === 'number');
  const avgDefectPct = probs.length ? (100 * probs.reduce((a, b) => a + b, 0)) / probs.length : 0;
  const highRiskCount = probs.filter((v) => v >= 0.5).length;
  const trainedOn = model?.trained_at ? new Date(model.trained_at).toLocaleDateString(undefined, { day: 'numeric', month: 'short', year: 'numeric' }) : '—';
  const fmt = (v, d = 2) => (typeof v === 'number' ? v.toFixed(d) : '—');

  const atRiskFiles = [...ranked]
    .sort((a, b) => (b.predicted_risk ?? 0) - (a.predicted_risk ?? 0))
    .slice(0, 8)
    .map((r) => ({
      id: r.file_id,
      file: r.file_path,
      current_risk: (r.technical_risk ?? 0).toFixed(1),
      predicted_risk: (r.predicted_risk ?? 0).toFixed(1),
      risk_delta: ((r.predicted_risk ?? 0) - (r.technical_risk ?? 0)).toFixed(1),
      confidence: r.confidence_score ?? 0,
      level: r.priority_level || '—',
    }));

  return (
    <div className="w-full px-4 sm:px-6 lg:px-8 py-6 space-y-6 max-w-[1720px] mx-auto animate-fade-in">
      
      {/* Sub-Header & Controls */}
      <section className="flex flex-col xl:flex-row xl:items-end justify-between gap-4 p-6 sm:p-8 bg-white/95 backdrop-blur-xl rounded-3xl border border-[#d4dece] shadow-[0_8px_30px_-6px_rgba(45,63,22,0.08)]">
        <div className="space-y-2 max-w-4xl">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-[#e8f1db] text-[#2d3f16] font-mono text-xs font-bold tracking-wider uppercase border border-[#c5c8ba]/60">
              <span className="w-2 h-2 rounded-full bg-[#43562b] animate-pulse"></span>
              {model ? `${pretty(model.algorithm.replace('Regressor', ' regressor'))} · ${model.n_estimators} trees` : 'Defect model'}
            </span>
            <span className="text-xs text-[#45483e] font-mono px-2.5 py-0.5 rounded-full bg-[#edf1e8] border border-[#d4dece]">
              Trained {trainedOn}
            </span>
          </div>
          <h1 className="text-2xl sm:text-4xl font-extrabold text-[#161e10] tracking-tight">
            Defect Risk Predictions
          </h1>
          <p className="text-sm text-[#45483e] max-w-3xl">
            A machine-learning model estimates how many faults each file is likely to contain, from its size, change history and author activity. Scores are relative (uncalibrated): use them to compare files, not as exact bug counts.
          </p>
        </div>

        <div className="flex items-center gap-2.5 flex-wrap">
          <button
            onClick={() => navigate('/simulator')}
            className="flex items-center gap-2 px-4 py-2.5 rounded-2xl bg-[#edf1e8] hover:bg-[#dde5d7] text-[#2d3f16] text-xs font-bold transition border border-[#c5c8ba] shadow-xs cursor-pointer active:scale-95"
          >
            <Sliders className="w-4 h-4 text-[#43562b]" />
            <span>Try the What-If Simulator</span>
          </button>

        </div>
      </section>

      {/* 4 Model Performance Capsule Badges */}
      <section className="flex items-center gap-3 overflow-x-auto pb-1 text-xs font-mono">
        <div className="flex items-center gap-2 px-3.5 py-2 bg-white rounded-2xl border border-[#d4dece] shadow-2xs whitespace-nowrap">
          <Activity className="w-3.5 h-3.5 text-[#43562b]" />
          <span className="text-[#45483e]">Trained:</span>
          <strong className="text-[#161e10]">{trainedOn}</strong>
        </div>

        <div className="flex items-center gap-2 px-3.5 py-2 bg-white rounded-2xl border border-[#d4dece] shadow-2xs whitespace-nowrap">
          <BrainCircuit className="w-3.5 h-3.5 text-[#43562b]" />
          <span className="text-[#45483e]">Cross-validated R²:</span>
          <strong className="text-[#161e10]">{fmt(model?.cv_r2_mean)}</strong>
        </div>

        <div className="flex items-center gap-2 px-3.5 py-2 bg-white rounded-2xl border border-[#d4dece] shadow-2xs whitespace-nowrap">
          <Code2 className="w-3.5 h-3.5 text-[#43562b]" />
          <span className="text-[#45483e]">Predicts:</span>
          <strong className="text-[#161e10]">{model?.target ? pretty(model.target) : '—'}</strong>
        </div>

        <div className="flex items-center gap-2 px-3.5 py-2 bg-[#e8f1db] rounded-2xl border border-[#c5c8ba] shadow-2xs whitespace-nowrap ml-auto">
          <CheckCircle2 className="w-3.5 h-3.5 text-[#43562b]" />
          <span className="text-[#2d3f16] font-bold">Relative Defect Risk (Uncalibrated)</span>
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
                Average Defect Risk
              </span>
              <div className="text-3xl font-extrabold tracking-tight mt-1 text-white leading-none font-mono">
                <AnimatedCounter value={avgDefectPct} decimals={1} />% <span className="text-base text-[#d3ebb2]/80 font-normal font-sans">per file</span>
              </div>
            </div>
          </div>
          <div className="pt-3 flex items-center justify-between z-10 text-xs border-t border-white/10">
            <span className="text-[#d3ebb2] font-mono">{highRiskCount} of {probs.length} files ≥ 50%</span>
            <span className="font-mono font-bold text-white">Relative risk</span>
          </div>
        </InteractiveCard>

        <InteractiveCard
          isInteractive={true}
          className="min-h-[190px] flex flex-col justify-between"
        >
          <div className="flex items-start justify-between">
            <div>
              <span className="text-xs font-mono uppercase tracking-wider text-[#45483e] font-bold">Mean Absolute Error</span>
              <div className="text-3xl font-extrabold text-[#161e10] mt-1 font-mono">
                <AnimatedCounter value={model?.mae ?? 0} decimals={2} /> <span className="text-sm font-normal text-[#45483e] font-sans">faults</span>
              </div>
            </div>
            <span className="p-2.5 rounded-2xl bg-[#d3e4ac] text-[#2d3f16]">
              <BarChart3 className="w-5 h-5" />
            </span>
          </div>
          <div className="flex items-center justify-between text-xs text-[#45483e] font-mono pt-3 border-t border-[#e5ebe0]">
            <span>{fmt(model?.mae_improvement_pct, 0)}% better than baseline</span>
            <strong className="text-[#161e10]">RMSE: {fmt(model?.rmse)}</strong>
          </div>
        </InteractiveCard>

        <InteractiveCard
          isInteractive={true}
          className="min-h-[190px] flex flex-col justify-between"
        >
          <div className="flex items-start justify-between">
            <div>
              <span className="text-xs font-mono uppercase tracking-wider text-[#45483e] font-bold">Model Size</span>
              <div className="text-3xl font-extrabold text-[#161e10] mt-1 font-mono">
                <AnimatedCounter value={model?.n_estimators ?? 0} /> <span className="text-sm font-normal text-[#45483e] font-sans">trees</span>
              </div>
            </div>
            <span className="p-2.5 rounded-2xl bg-[#ffddb8] text-[#855300]">
              <Cpu className="w-5 h-5" />
            </span>
          </div>
          <div className="flex items-center justify-between text-xs text-[#45483e] font-mono pt-3 border-t border-[#e5ebe0]">
            <span>{model?.features?.length ?? 0} input features</span>
            <span>Test R² {fmt(model?.r2)}</span>
          </div>
        </InteractiveCard>

        <InteractiveCard
          isInteractive={true}
          className="min-h-[190px] flex flex-col justify-between"
        >
          <div className="flex items-start justify-between">
            <div>
              <span className="text-xs font-mono uppercase tracking-wider text-[#45483e] font-bold">Strongest Factor</span>
              <div className="text-3xl font-extrabold text-[#161e10] mt-1 font-mono">
                <AnimatedCounter value={(topFeature?.importance ?? 0) * 100} decimals={1} />% <span className="text-sm font-normal text-[#45483e] font-sans">importance</span>
              </div>
            </div>
            <span className="p-2.5 rounded-2xl bg-[#ffdad6] text-[#ba1a1a]">
              <Flame className="w-5 h-5" />
            </span>
          </div>
          <span className="text-xs text-[#ba1a1a] font-semibold pt-3 border-t border-[#e5ebe0]">{topFeature ? pretty(topFeature.feature) : '—'}</span>
        </InteractiveCard>
      </section>

      {/* Feature Importance & Interactive Live Simulator Bento Grid */}
      <section id="defect-simulator" className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        
        {/* Left Bento: Feature Importance SHAP (5 cols) */}
        <div className="lg:col-span-5 p-6 bg-white rounded-3xl border border-[#d4dece] shadow-[0_4px_20px_-4px_rgba(45,63,22,0.06)] flex flex-col justify-between space-y-4">
          <div>
            <h2 className="text-lg font-bold text-[#161e10]">What drives the prediction</h2>
            <p className="text-xs text-[#45483e]">Top features by importance in the trained model</p>
          </div>

          <div className="h-56 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart layout="vertical" data={featureImportanceData} margin={{ top: 5, right: 30, left: 10, bottom: 5 }}>
                <XAxis type="number" stroke="#75786d" fontSize={11} domain={[0, 'dataMax']} />
                <YAxis dataKey="feature" type="category" stroke="#45483e" fontSize={11} width={140} tickLine={false} />
                <Tooltip content={<ChartTooltip unit="%" />} />
                <Bar dataKey="weight" fill="#43562b" radius={[0, 8, 8, 0]} isAnimationActive={false}>
                  {featureImportanceData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>

          <div className="p-3 bg-[#f8faf6] rounded-2xl border border-[#e5ebe0] text-xs text-[#45483e]">
            <span className="font-bold text-[#161e10]">Reading this: </span>
            <span>
              {featureImportanceData.length >= 2
                ? `${featureImportanceData[0].feature} and ${featureImportanceData[1].feature} account for ${(featureImportanceData[0].weight + featureImportanceData[1].weight).toFixed(0)}% of the model's decisions.`
                : 'Model details unavailable.'}
            </span>
          </div>
        </div>

        <div className="lg:col-span-7 p-6 bg-white rounded-3xl border border-[#d4dece] space-y-3 flex flex-col justify-center">
          <h2 className="text-lg font-bold text-[#161e10]">What if you clean up a file?</h2>
          <p className="text-sm text-[#45483e]">
            The What-If Simulator runs this same trained model on one of your files and shows how its predicted defects change as you clean it up or add tests.
          </p>
          <button
            onClick={() => navigate('/simulator')}
            className="self-start px-4 py-2 rounded-xl bg-[#43562b] hover:bg-[#2d3f16] text-white text-xs font-bold transition cursor-pointer"
          >
            Open the What-If Simulator
          </button>
        </div>
      </section>

      {/* At-Risk Files Forecast Table */}
      <section className="p-6 bg-white rounded-3xl border border-[#d4dece] shadow-[0_4px_20px_-4px_rgba(45,63,22,0.06)] space-y-4">
        <div className="flex items-center justify-between flex-wrap gap-2">
          <div>
            <h2 className="text-lg font-bold text-[#161e10]">Highest predicted risk ({atRiskFiles.length})</h2>
            <p className="text-xs text-[#45483e]">Files the model expects to be riskiest, compared with their current technical risk</p>
          </div>
          <button
            onClick={() => navigate('/priorities')}
            className="flex items-center gap-1.5 text-xs font-bold text-[#43562b] hover:text-[#2d3f16] transition cursor-pointer"
          >
            <span>See all priorities</span>
            <ArrowRight className="w-4 h-4" />
          </button>
        </div>

        {/* Mobile Card List (< 768px) */}
        <div className="md:hidden space-y-3">
          {atRiskFiles.map((file) => (
            <div
              key={file.id}
              onClick={() => navigate(`/files/${file.id}`)}
              className="p-4 bg-[#f8faf6] hover:bg-[#eef3e8] border border-[#d4dece] rounded-2xl transition cursor-pointer space-y-3"
            >
              <div className="flex items-start justify-between gap-2">
                <div className="flex items-center gap-2 min-w-0">
                  <Code2 className="w-4 h-4 text-[#43562b] shrink-0" />
                  <span className="font-mono font-bold text-sm text-[#161e10] truncate">
                    {file.file}
                  </span>
                </div>
                <span className="font-mono font-bold text-xs text-[#2d3f16] bg-[#d3ebb2] px-2 py-0.5 rounded-full shrink-0">
                  {(file.confidence * 100).toFixed(0)}% Conf
                </span>
              </div>

              <div className="grid grid-cols-2 gap-2 pt-2 border-t border-[#e5ebe0] text-center">
                <div className="bg-white p-2 rounded-xl border border-[#e5ebe0]">
                  <span className="text-[11px] font-mono text-[#45483e] block">Current</span>
                  <span className="font-mono font-bold text-sm text-[#45483e] whitespace-nowrap">
                    {file.current_risk}
                  </span>
                </div>
                <div className="bg-white p-2 rounded-xl border border-[#e5ebe0]">
                  <span className="text-[11px] font-mono text-[#45483e] block">Predicted</span>
                  <span className="font-mono font-bold text-sm text-[#ba1a1a] whitespace-nowrap">
                    {file.predicted_risk} ({file.risk_delta >= 0 ? '+' : ''}{file.risk_delta})
                  </span>
                </div>
              </div>

              <div className="flex flex-wrap gap-1.5 pt-1">
                <span className="px-2 py-0.5 rounded-full bg-[#edf1e8] text-[#2d3f16] font-mono text-[10px] font-semibold border border-[#d4dece]">
                  Priority {file.level}
                </span>
              </div>

              <div className="flex justify-end pt-1" onClick={(e) => e.stopPropagation()}>
                <button
                  onClick={() => navigate(`/files/${file.id}`)}
                  className="px-3 py-1.5 bg-[#43562b] hover:bg-[#2d3f16] text-white rounded-xl text-xs font-bold transition flex items-center gap-1 shadow-xs"
                >
                  <span>Inspect</span>
                  <ArrowRight className="w-3.5 h-3.5" />
                </button>
              </div>
            </div>
          ))}
        </div>

        {/* Desktop/Tablet Table (>= 768px) */}
        <div className="hidden md:block overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead>
              <tr className="border-b border-[#e5ebe0] text-[#45483e] uppercase font-mono text-xs">
                <th className="py-3 px-4 font-bold">Module Path</th>
                <th className="py-3 px-4 font-bold text-center whitespace-nowrap">Current Risk</th>
                <th className="py-3 px-4 font-bold text-center whitespace-nowrap">Predicted Risk</th>
                <th className="py-3 px-4 font-bold text-center whitespace-nowrap">Confidence</th>
                <th className="py-3 px-4 font-bold">Priority</th>
                <th className="py-3 px-4 font-bold text-right whitespace-nowrap">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#f4f6f0]">
              {atRiskFiles.map((file) => (
                <tr 
                  key={file.id}
                  onClick={() => navigate(`/files/${file.id}`)}
                  className="hover:bg-[#f8faf6] transition cursor-pointer group"
                >
                  <td className="py-3.5 px-4">
                    <div className="flex items-center gap-2">
                      <Code2 className="w-4 h-4 text-[#43562b] shrink-0" />
                      <span className="font-mono font-semibold text-[#161e10] group-hover:text-[#43562b] transition">
                        {file.file}
                      </span>
                    </div>
                  </td>
                  <td className="py-3.5 px-4 text-center font-mono text-[#45483e] whitespace-nowrap">
                    {file.current_risk}
                  </td>
                  <td className="py-3.5 px-4 text-center font-mono font-bold text-[#ba1a1a] whitespace-nowrap">
                    {file.predicted_risk}
                    <span className="text-xs text-[#ba1a1a] ml-1 font-semibold">
                      ({file.risk_delta >= 0 ? '+' : ''}{file.risk_delta})
                    </span>
                  </td>
                  <td className="py-3.5 px-4 text-center font-mono font-semibold text-[#2d3f16] whitespace-nowrap">
                    {(file.confidence * 100).toFixed(0)}%
                  </td>
                  <td className="py-3.5 px-4">
                    <span className="px-2 py-0.5 rounded-full bg-[#edf1e8] text-[#2d3f16] font-mono text-xs font-semibold border border-[#d4dece] whitespace-nowrap">
                      {file.level}
                    </span>
                  </td>
                  <td className="py-3.5 px-4 text-right whitespace-nowrap" onClick={(e) => e.stopPropagation()}>
                    <button
                      onClick={() => navigate(`/files/${file.id}`)}
                      className="px-3 py-1.5 bg-[#43562b] hover:bg-[#2d3f16] text-white rounded-xl text-xs font-bold transition flex items-center gap-1.5 shadow-xs ml-auto cursor-pointer"
                    >
                      <span>Inspect</span>
                      <ArrowRight className="w-3.5 h-3.5" />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}
