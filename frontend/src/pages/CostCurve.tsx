import React, { useState, useEffect } from 'react';
import { fetchThresholdCurve } from '../services/api';
import type { ThresholdAnalysisResponse } from '../types';
import { CostCurveChart } from '../components/CostCurveChart';
import { Sliders, Target, Loader2 } from 'lucide-react';

export const CostCurve: React.FC = () => {
  const [data, setData] = useState<ThresholdAnalysisResponse | null>(null);
  const [selectedThreshold, setSelectedThreshold] = useState<number>(0.35);
  const [isLoading, setIsLoading] = useState<boolean>(true);

  useEffect(() => {
    fetchThresholdCurve()
      .then((res) => {
        setData(res);
        if (res.optimal_threshold) {
          setSelectedThreshold(res.optimal_threshold);
        }
      })
      .catch((err) => {
        console.error('[CostCurve] Failed loading threshold curve data:', err);
      })
      .finally(() => {
        setIsLoading(false);
      });
  }, []);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-slate-900 border border-slate-800 p-6 rounded-2xl shadow-xl">
        <div className="flex items-center gap-2">
          <Sliders className="w-5 h-5 text-blue-400" />
          <h1 className="text-xl font-bold text-white">Threshold & Cost Trade-Off Analyzer</h1>
        </div>
        <p className="text-xs text-slate-400 mt-1">
          Derives precision, recall, and false-positive cost curves across decision thresholds on the held-out evaluation set.
        </p>
      </div>

      {/* Main Interactive Chart */}
      {isLoading ? (
        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-12 text-center text-slate-400 flex flex-col items-center justify-center gap-3">
          <Loader2 className="w-8 h-8 text-blue-400 animate-spin" />
          <span>Loading threshold & cost curve analysis...</span>
        </div>
      ) : data ? (
        <CostCurveChart
          data={data.threshold_curve}
          selectedThreshold={selectedThreshold}
          onThresholdChange={(val) => setSelectedThreshold(val)}
        />
      ) : (
        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-8 text-center text-slate-400">
          Unable to load threshold curve data. Please check backend API server status.
        </div>
      )}

      {/* Recommended Threshold Bands Breakdown */}
      {data?.recommended_bands && (
        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-xl">
          <h3 className="text-sm font-bold text-white mb-4 flex items-center gap-2">
            <Target className="w-4 h-4 text-emerald-400" />
            <span>Derived Decision Band Mapping (Defense-Only)</span>
          </h3>

          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-4 text-xs">
            <div className="p-4 rounded-xl bg-emerald-950/40 border border-emerald-800/60">
              <span className="font-bold text-emerald-300 block mb-1">LOW RISK (ALLOW)</span>
              <p className="text-slate-400">Score &lt; {data.recommended_bands.low.max.toFixed(2)}</p>
              <p className="text-[11px] text-emerald-400/80 mt-2">Automated instant approval.</p>
            </div>

            <div className="p-4 rounded-xl bg-yellow-950/40 border border-yellow-800/60">
              <span className="font-bold text-yellow-300 block mb-1">MEDIUM RISK (FLAG FOR REVIEW)</span>
              <p className="text-slate-400">
                {data.recommended_bands.medium.min.toFixed(2)} - {data.recommended_bands.medium.max.toFixed(2)}
              </p>
              <p className="text-[11px] text-yellow-400/80 mt-2">Flagged for internal analyst audit.</p>
            </div>

            <div className="p-4 rounded-xl bg-amber-950/40 border border-amber-800/60">
              <span className="font-bold text-amber-300 block mb-1">HIGH RISK (HOLD VERIFICATION)</span>
              <p className="text-slate-400">
                {data.recommended_bands.high.min.toFixed(2)} - {data.recommended_bands.high.max.toFixed(2)}
              </p>
              <p className="text-[11px] text-amber-400/80 mt-2">Step-up authentication required.</p>
            </div>

            <div className="p-4 rounded-xl bg-red-950/40 border border-red-800/60">
              <span className="font-bold text-red-300 block mb-1">VERY HIGH RISK (AUTO DECLINE)</span>
              <p className="text-slate-400">Score &ge; {data.recommended_bands.very_high.min.toFixed(2)}</p>
              <p className="text-[11px] text-red-400/80 mt-2">Automated transaction decline.</p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
