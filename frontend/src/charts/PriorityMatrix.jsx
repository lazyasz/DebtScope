import React from 'react';
import {
  ScatterChart,
  Scatter,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ZAxis,
  ReferenceLine,
} from 'recharts';

export function formatQuadrant(quadrant) {
  if (!quadrant) return 'Deprioritized';
  const q = String(quadrant).toUpperCase();
  if (q.includes('QUICK') || q === 'QUICK_WIN') return 'Quick Win';
  if (q.includes('STRATEGIC') || q === 'STRATEGIC_REFACTOR') return 'Strategic Refactor';
  if (q.includes('OPPORTUNISTIC')) return 'Opportunistic';
  if (q.includes('DEPRIORITIZED')) return 'Deprioritized';
  return quadrant;
}

export function getQuadrantStyle(quadrant) {
  const q = String(quadrant || '').toUpperCase();
  if (q.includes('QUICK')) {
    return { text: '#5b42a5', bg: '#f0ecfc', border: '#d8cdfa', dot: '#7048e8' };
  }
  if (q.includes('STRATEGIC')) {
    return { text: '#b45309', bg: '#fffbeb', border: '#fcd34d', dot: '#f59e0b' };
  }
  if (q.includes('OPPORTUNISTIC')) {
    return { text: '#0284c7', bg: '#f0f9ff', border: '#bae6fd', dot: '#0ea5e9' };
  }
  return { text: '#64748b', bg: '#f8fafc', border: '#cbd5e1', dot: '#94a3b8' };
}

export default function PriorityMatrix({ data, onSelectPoint }) {
  if (!data || data.length === 0) return null;

  const CustomTooltip = ({ active, payload }) => {
    if (active && payload && payload.length) {
      const item = payload[0].payload;
      const qStyle = getQuadrantStyle(item.quadrant);
      return (
        <div className="p-3 bg-[#130e24] border border-[#261c47] rounded-lg shadow-xl text-white text-xs space-y-2 min-w-[220px]">
          <div className="flex items-center justify-between gap-2 border-b border-white/10 pb-1.5">
            <p className="font-mono font-bold text-[#d8cdfa] truncate max-w-[150px]">
              {item.file_name || item.file_path || item.file || item.name || 'Component'}
            </p>
            <span
              className="text-[10px] font-mono font-bold px-1.5 py-0.5 rounded border"
              style={{ color: qStyle.text, backgroundColor: qStyle.bg, borderColor: qStyle.border }}
            >
              {formatQuadrant(item.quadrant)}
            </span>
          </div>
          <div className="grid grid-cols-2 gap-2 text-[11px]">
            <div>
              <span className="text-[#88909e] block">Priority Score:</span>
              <span className="font-bold text-[#b39ef2] font-mono">
                {(item.priority_score ?? item.final_priority_score ?? 0).toFixed(1)} / 100
              </span>
            </div>
            <div>
              <span className="text-[#88909e] block">Remediation Effort:</span>
              <span className="font-bold text-white font-mono">
                {(item.remediation_effort ?? 0).toFixed(1)} / 100
              </span>
            </div>
            <div>
              <span className="text-[#88909e] block">Business Impact:</span>
              <span className="font-bold text-white font-mono">
                {(item.business_impact ?? 0).toFixed(1)} / 100
              </span>
            </div>
            <div>
              <span className="text-[#88909e] block">Technical Risk:</span>
              <span className="font-bold text-[#dc2626] font-mono">
                {(item.technical_risk ?? item.risk_score ?? 0).toFixed(1)} / 100
              </span>
            </div>
          </div>
          <div className="pt-1.5 border-t border-white/10 flex items-center justify-between text-[10px] text-[#88909e]">
            <span>Dimension Coverage:</span>
            <span className="font-mono text-emerald-400 font-semibold">
              {item.dimension_coverage || `${item.scored_dimensions_count || 5} of 5 dimensions`}
            </span>
          </div>
        </div>
      );
    }
    return null;
  };

  return (
    <div className="relative w-full h-[380px]">
      {/* 4 Quadrants Background Labels (Threshold: Priority >= 60, Effort <= 40) */}
      <div className="absolute top-2 left-10 text-[10px] font-mono font-bold uppercase tracking-wider text-[#5b42a5]/70 pointer-events-none">
        Quick Wins (Priority ≥ 60, Effort ≤ 40)
      </div>
      <div className="absolute top-2 right-4 text-[10px] font-mono font-bold uppercase tracking-wider text-[#b45309]/70 pointer-events-none">
        Strategic Refactor (Priority ≥ 60, Effort &gt; 40)
      </div>
      <div className="absolute bottom-9 left-10 text-[10px] font-mono font-bold uppercase tracking-wider text-[#0284c7]/70 pointer-events-none">
        Opportunistic (Priority &lt; 60, Effort ≤ 40)
      </div>
      <div className="absolute bottom-9 right-4 text-[10px] font-mono font-bold uppercase tracking-wider text-[#88909e]/70 pointer-events-none">
        Deprioritized (Priority &lt; 60, Effort &gt; 40)
      </div>

      <ResponsiveContainer width="100%" height="100%">
        <ScatterChart margin={{ top: 25, right: 25, bottom: 25, left: 10 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#e2e4ea" />
          <XAxis
            type="number"
            dataKey="remediation_effort"
            name="Remediation Effort"
            stroke="#88909e"
            fontSize={11}
            fontFamily="JetBrains Mono"
            domain={[0, 100]}
            label={{
              value: 'Remediation Effort (0-100) ->',
              position: 'insideBottom',
              offset: -14,
              fill: '#525866',
              fontSize: 11,
            }}
          />
          <YAxis
            type="number"
            dataKey="priority_score"
            name="Priority Score"
            stroke="#88909e"
            fontSize={11}
            fontFamily="JetBrains Mono"
            domain={[0, 100]}
            label={{
              value: 'Priority Score (0-100) ->',
              angle: -90,
              position: 'insideLeft',
              fill: '#525866',
              fontSize: 11,
              offset: 10,
            }}
          />
          <ZAxis
            type="number"
            dataKey="technical_risk"
            range={[60, 260]}
            name="Technical Risk"
          />
          <Tooltip content={<CustomTooltip />} cursor={{ strokeDasharray: '3 3', stroke: '#7048e8' }} />

          {/* Dividing Threshold Lines: Effort = 40, Priority = 60 */}
          <ReferenceLine
            x={40}
            stroke="#d0d4de"
            strokeDasharray="4 4"
            strokeWidth={1.5}
            label={{ value: 'Effort: 40', position: 'top', fill: '#88909e', fontSize: 10 }}
          />
          <ReferenceLine
            y={60}
            stroke="#d0d4de"
            strokeDasharray="4 4"
            strokeWidth={1.5}
            label={{ value: 'Priority: 60', position: 'right', fill: '#88909e', fontSize: 10 }}
          />

          <Scatter
            name="Ranked Components"
            data={data}
            fill="#7048e8"
            onClick={(node) => onSelectPoint && onSelectPoint(node)}
            className="cursor-pointer"
          />
        </ScatterChart>
      </ResponsiveContainer>
    </div>
  );
}
