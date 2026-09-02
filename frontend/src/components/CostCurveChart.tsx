import React from 'react';
import type { ThresholdCurvePoint } from '../types';
import {
  ResponsiveContainer,
  ComposedChart,
  Line,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  Legend,
  CartesianGrid,
  ReferenceLine,
} from 'recharts';

interface Props {
  data: ThresholdCurvePoint[];
  selectedThreshold: number;
  onThresholdChange: (newThreshold: number) => void;
}

export const CostCurveChart: React.FC<Props> = ({ data, selectedThreshold, onThresholdChange }) => {
  if (!data || data.length === 0) {
    return <div className="text-slate-400 p-8 text-center">Loading threshold curve data...</div>;
  }

  const activePoint = data.find((d) => Math.abs(d.threshold - selectedThreshold) < 0.03) || data[0];

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 text-slate-100 shadow-xl">
      <div className="flex flex-col md:flex-row items-start md:items-center justify-between mb-6 gap-4">
        <div>
          <h2 className="text-lg font-bold text-white">Precision / Recall / False-Positive Cost Trade-Off</h2>
          <p className="text-xs text-slate-400">
            Drag the slider to adjust the decision boundary threshold and observe FP revenue cost vs fraud caught.
          </p>
        </div>

        {/* Threshold Slider Control */}
        <div className="flex items-center gap-4 bg-slate-950 px-4 py-2 rounded-xl border border-slate-800 w-full md:w-auto">
          <div className="text-xs">
            <span className="text-slate-400 block">Threshold</span>
            <span className="font-mono text-base font-bold text-blue-400">{selectedThreshold.toFixed(2)}</span>
          </div>
          <input
            type="range"
            min="0.05"
            max="0.95"
            step="0.05"
            value={selectedThreshold}
            onChange={(e) => onThresholdChange(parseFloat(e.target.value))}
            className="w-36 accent-blue-500 cursor-pointer"
          />
        </div>
      </div>

      {/* KPI Cards for active threshold */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-6">
        <div className="p-3.5 rounded-xl bg-slate-950/80 border border-slate-800">
          <span className="text-[11px] text-slate-400 font-medium block">Precision</span>
          <span className="text-xl font-bold text-emerald-400">{((activePoint?.precision || 0) * 100).toFixed(1)}%</span>
        </div>
        <div className="p-3.5 rounded-xl bg-slate-950/80 border border-slate-800">
          <span className="text-[11px] text-slate-400 font-medium block">Recall (Fraud Catch Rate)</span>
          <span className="text-xl font-bold text-blue-400">{((activePoint?.recall || 0) * 100).toFixed(1)}%</span>
        </div>
        <div className="p-3.5 rounded-xl bg-slate-950/80 border border-slate-800">
          <span className="text-[11px] text-slate-400 font-medium block">Est. False-Positive Cost</span>
          <span className="text-xl font-bold text-amber-400">${(activePoint?.estimated_fp_cost || 0).toLocaleString()}</span>
        </div>
        <div className="p-3.5 rounded-xl bg-slate-950/80 border border-slate-800">
          <span className="text-[11px] text-slate-400 font-medium block">Est. Fraud Loss Prevented</span>
          <span className="text-xl font-bold text-indigo-400">${(activePoint?.estimated_fraud_caught || 0).toLocaleString()}</span>
        </div>
      </div>

      {/* Interactive Recharts Chart */}
      <div className="h-72 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <ComposedChart data={data} margin={{ top: 10, right: 20, left: 10, bottom: 20 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
            <XAxis dataKey="threshold" stroke="#64748b" tickFormatter={(v) => v.toFixed(2)} label={{ value: 'Decision Threshold', position: 'bottom', offset: 0, fill: '#94a3b8', fontSize: 12 }} />
            <YAxis yAxisId="left" stroke="#64748b" domain={[0, 1]} tickFormatter={(v) => `${(v * 100).toFixed(0)}%`} />
            <YAxis yAxisId="right" orientation="right" stroke="#64748b" tickFormatter={(v) => `$${v}`} />
            <Tooltip
              contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', borderRadius: '0.75rem', fontSize: '0.75rem' }}
            formatter={(val, name) => {
                const n = String(name ?? '');
                const v = Number(val ?? 0);
                if (n === 'Precision' || n === 'Recall') return [`${(v * 100).toFixed(1)}%`, n];
                return [`$${v.toLocaleString()}`, n];
              }}
            />
            <Legend wrapperStyle={{ fontSize: '0.75rem', paddingTop: '10px' }} />
            <ReferenceLine x={selectedThreshold} stroke="#3b82f6" strokeDasharray="4 4" label={{ value: 'Selected', fill: '#60a5fa', fontSize: 11 }} />
            <Bar yAxisId="right" dataKey="estimated_fp_cost" name="FP Revenue Cost ($)" fill="#f59e0b" opacity={0.4} radius={[4, 4, 0, 0]} />
            <Line yAxisId="left" type="monotone" dataKey="precision" name="Precision" stroke="#10b981" strokeWidth={2.5} dot={false} />
            <Line yAxisId="left" type="monotone" dataKey="recall" name="Recall" stroke="#3b82f6" strokeWidth={2.5} dot={false} />
          </ComposedChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
};
