import React from 'react';
import type { ScoredTransaction } from '../types';
import { RiskBandBadge } from './RiskBandBadge';
import { X, Sparkles, ShieldCheck, Cpu, DollarSign } from 'lucide-react';

interface Props {
  transaction: ScoredTransaction | null;
  onClose: () => void;
}

export const TransactionModal: React.FC<Props> = ({ transaction, onClose }) => {
  if (!transaction) return null;

  const cohort = transaction.cohort_context || {};
  const topFeatures = transaction.top_features || {};

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm animate-fade-in">
      <div className="bg-slate-900 border border-slate-800 rounded-2xl max-w-2xl w-full p-6 text-slate-100 shadow-2xl relative overflow-hidden">
        <button
          onClick={onClose}
          className="absolute top-4 right-4 p-2 text-slate-400 hover:text-white rounded-lg hover:bg-slate-800 transition"
        >
          <X className="w-5 h-5" />
        </button>

        <div className="flex items-center justify-between mb-4 pb-4 border-b border-slate-800">
          <div>
            <span className="text-xs font-mono text-blue-400 uppercase tracking-wider">Transaction Detail</span>
            <h2 className="text-xl font-bold text-white flex items-center gap-2 mt-0.5">
              <span>{transaction.transaction_id}</span>
              <span className="text-sm font-normal text-slate-400">({transaction.merchant})</span>
            </h2>
          </div>
          <RiskBandBadge action={transaction.action} band={transaction.risk_band} score={transaction.risk_score} />
        </div>

        {/* Gemini Explanation Highlight Box */}
        <div className="mb-6 p-4 rounded-xl bg-gradient-to-r from-indigo-950/70 via-slate-900 to-slate-900 border border-indigo-500/30">
          <div className="flex items-center gap-2 text-xs font-semibold text-indigo-300 uppercase tracking-wider mb-2">
            <Sparkles className="w-4 h-4 text-indigo-400 animate-pulse" />
            <span>Gemini Plain-Language Audit Reason</span>
          </div>
          <p className="text-sm text-slate-200 leading-relaxed font-normal italic">
            "{transaction.explanation || 'Transaction cleared standard automated risk boundary checks.'}"
          </p>
        </div>

        {/* Cohort Breakdown & Feature Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
          <div className="p-4 rounded-xl bg-slate-950/60 border border-slate-800">
            <h3 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-3 flex items-center gap-1.5">
              <DollarSign className="w-4 h-4 text-emerald-400" />
              <span>Cohort & Baseline Metrics</span>
            </h3>
            <ul className="space-y-2 text-xs">
              <li className="flex justify-between">
                <span className="text-slate-400">Transaction Amount:</span>
                <span className="font-semibold text-white">${transaction.amount.toLocaleString(undefined, { minimumFractionDigits: 2 })}</span>
              </li>
              <li className="flex justify-between">
                <span className="text-slate-400">Historical Merchant Mean:</span>
                <span className="text-slate-300">${(cohort.historical_mean_amount || 65.0).toFixed(2)}</span>
              </li>
              <li className="flex justify-between">
                <span className="text-slate-400">Ratio vs Baseline:</span>
                <span className={`font-semibold ${cohort.amount_ratio_vs_baseline > 5 ? 'text-amber-400' : 'text-slate-300'}`}>
                  {(cohort.amount_ratio_vs_baseline || 1.0).toFixed(1)}x
                </span>
              </li>
              <li className="flex justify-between">
                <span className="text-slate-400">Baseline Z-Score:</span>
                <span className={`font-semibold ${cohort.baseline_zscore > 3 ? 'text-red-400' : 'text-slate-300'}`}>
                  {(cohort.baseline_zscore || 0.0).toFixed(2)}
                </span>
              </li>
            </ul>
          </div>

          <div className="p-4 rounded-xl bg-slate-950/60 border border-slate-800">
            <h3 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-3 flex items-center gap-1.5">
              <Cpu className="w-4 h-4 text-blue-400" />
              <span>Top Model Feature Drivers</span>
            </h3>
            <div className="space-y-2 text-xs">
              {Object.keys(topFeatures).length > 0 ? (
                Object.entries(topFeatures).map(([k, v]) => (
                  <div key={k} className="flex justify-between py-0.5 border-b border-slate-800/60 last:border-0">
                    <span className="text-slate-400 truncate pr-2" title={k}>{k}:</span>
                    <span className="font-mono font-medium text-blue-300">
                      {typeof v === 'number' ? v.toFixed(2) : String(v)}
                    </span>
                  </div>
                ))
              ) : (
                <p className="text-slate-500 italic">No anomaly feature signals detected.</p>
              )}
            </div>
          </div>
        </div>

        {/* Cost & Guardrail Footnote */}
        <div className="flex items-center justify-between pt-4 border-t border-slate-800 text-xs text-slate-400">
          <div className="flex items-center gap-1.5">
            <ShieldCheck className="w-4 h-4 text-blue-400" />
            <span>Strict Defense-Only ({transaction.action})</span>
          </div>
          <div>
            <span>Threshold Applied: </span>
            <span className="font-mono text-slate-200">{(transaction.threshold_used || 0.35).toFixed(2)}</span>
          </div>
        </div>
      </div>
    </div>
  );
};
