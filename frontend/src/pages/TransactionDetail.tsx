import React, { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { fetchTransactionDetail } from '../services/api';
import type { ScoredTransaction } from '../types';
import { RiskBandBadge } from '../components/RiskBandBadge';
import { ArrowLeft, Sparkles, ShieldCheck, Cpu, DollarSign } from 'lucide-react';

export const TransactionDetail: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const [transaction, setTransaction] = useState<ScoredTransaction | null>(null);

  useEffect(() => {
    if (id) {
      fetchTransactionDetail(id).then(setTransaction);
    }
  }, [id]);

  if (!transaction) {
    return <div className="p-8 text-center text-slate-400">Loading transaction detail...</div>;
  }

  const cohort = transaction.cohort_context || {};
  const topFeatures = transaction.top_features || {};

  return (
    <div className="space-y-6 max-w-4xl mx-auto">
      <Link to="/" className="inline-flex items-center gap-2 text-xs font-semibold text-blue-400 hover:text-blue-300">
        <ArrowLeft className="w-4 h-4" />
        <span>Back to Live Stream Feed</span>
      </Link>

      <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-xl text-slate-100 space-y-6">
        <div className="flex items-center justify-between pb-4 border-b border-slate-800">
          <div>
            <h1 className="text-2xl font-bold text-white">{transaction.transaction_id}</h1>
            <p className="text-xs text-slate-400 mt-1">{transaction.merchant} ({transaction.merchant_category})</p>
          </div>
          <RiskBandBadge action={transaction.action} band={transaction.risk_band} score={transaction.risk_score} />
        </div>

        {/* Gemini Explanation */}
        <div className="p-5 rounded-xl bg-gradient-to-r from-indigo-950/70 via-slate-900 to-slate-900 border border-indigo-500/40 space-y-2">
          <div className="flex items-center gap-2 text-xs font-semibold text-indigo-300 uppercase tracking-wider">
            <Sparkles className="w-4 h-4 text-indigo-400 animate-pulse" />
            <span>Gemini Plain-Language Audit Reason</span>
          </div>
          <p className="text-sm text-slate-100 italic">
            "{transaction.explanation || 'Transaction cleared standard automated risk boundary checks.'}"
          </p>
        </div>

        {/* Cohort & Features Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="p-4 rounded-xl bg-slate-950 border border-slate-800 space-y-3">
            <h3 className="text-xs font-semibold text-slate-400 uppercase tracking-wider flex items-center gap-1.5">
              <DollarSign className="w-4 h-4 text-emerald-400" />
              <span>Merchant Cohort Baseline Comparison</span>
            </h3>
            <div className="space-y-2 text-xs">
              <div className="flex justify-between py-1 border-b border-slate-800">
                <span className="text-slate-400">Transaction Amount:</span>
                <span className="font-bold text-white">${transaction.amount.toFixed(2)}</span>
              </div>
              <div className="flex justify-between py-1 border-b border-slate-800">
                <span className="text-slate-400">Merchant Mean:</span>
                <span className="text-slate-300">${(cohort.historical_mean_amount || 65.0).toFixed(2)}</span>
              </div>
              <div className="flex justify-between py-1 border-b border-slate-800">
                <span className="text-slate-400">Ratio vs Baseline:</span>
                <span className="font-bold text-amber-400">{(cohort.amount_ratio_vs_baseline || 1.0).toFixed(1)}x</span>
              </div>
              <div className="flex justify-between py-1">
                <span className="text-slate-400">Baseline Z-Score:</span>
                <span className="font-bold text-red-400">{(cohort.baseline_zscore || 0.0).toFixed(2)}</span>
              </div>
            </div>
          </div>

          <div className="p-4 rounded-xl bg-slate-950 border border-slate-800 space-y-3">
            <h3 className="text-xs font-semibold text-slate-400 uppercase tracking-wider flex items-center gap-1.5">
              <Cpu className="w-4 h-4 text-blue-400" />
              <span>Top Model Feature Signals</span>
            </h3>
            <div className="space-y-2 text-xs">
              {Object.entries(topFeatures).map(([k, v]) => (
                <div key={k} className="flex justify-between py-1 border-b border-slate-800 last:border-0">
                  <span className="text-slate-400 truncate pr-2">{k}:</span>
                  <span className="font-mono text-blue-300 font-medium">{typeof v === 'number' ? v.toFixed(2) : String(v)}</span>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Guardrail Footer */}
        <div className="flex items-center justify-between pt-4 border-t border-slate-800 text-xs text-slate-400">
          <div className="flex items-center gap-1.5">
            <ShieldCheck className="w-4 h-4 text-blue-400" />
            <span>Strictly Defense-Only ({transaction.action})</span>
          </div>
          <span>Threshold: {(transaction.threshold_used || 0.35).toFixed(2)}</span>
        </div>
      </div>
    </div>
  );
};
