import React from 'react';
import { Settings as SettingsIcon, Lock, Server } from 'lucide-react';

export const Settings: React.FC = () => {
  return (
    <div className="space-y-6 max-w-4xl mx-auto">
      <div className="bg-slate-900 border border-slate-800 p-6 rounded-2xl shadow-xl">
        <div className="flex items-center gap-2">
          <SettingsIcon className="w-5 h-5 text-blue-400" />
          <h1 className="text-xl font-bold text-white">System Settings & Safety Guardrails</h1>
        </div>
        <p className="text-xs text-slate-400 mt-1">
          Configuration overview, defense-only scope constraints, and model pipeline environment details.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="bg-slate-900 border border-slate-800 p-6 rounded-2xl space-y-4">
          <div className="flex items-center gap-2 text-emerald-400 font-bold text-sm">
            <Lock className="w-4 h-4" />
            <span>Hackathon Scope & Defense-Only Boundary</span>
          </div>
          <p className="text-xs text-slate-300 leading-relaxed">
            This system operates exclusively as a detection, flagging, and verification hold system. 
            All actions emitted by the decision engine are strictly defense-only:
          </p>
          <ul className="space-y-2 text-xs text-slate-400 list-disc pl-4">
            <li><strong className="text-emerald-300">allow</strong>: Clear transaction automatically.</li>
            <li><strong className="text-yellow-300">flag_for_review</strong>: Flag for internal analyst review.</li>
            <li><strong className="text-amber-300">hold_for_verification</strong>: Hold pending step-up customer verification.</li>
            <li><strong className="text-red-300">auto_decline</strong>: Automated decline with plain-language reason.</li>
          </ul>
          <p className="text-[11px] text-slate-500 italic">
            Zero outbound automated retaliation, IP counter-probing, or external party actions are initiated.
          </p>
        </div>

        <div className="bg-slate-900 border border-slate-800 p-6 rounded-2xl space-y-4">
          <div className="flex items-center gap-2 text-blue-400 font-bold text-sm">
            <Server className="w-4 h-4" />
            <span>Pipeline Architecture</span>
          </div>
          <ul className="space-y-3 text-xs">
            <li className="flex justify-between border-b border-slate-800 pb-2">
              <span className="text-slate-400">ML Classifier Model:</span>
              <span className="font-mono text-white">XGBoost / GradientBoosted</span>
            </li>
            <li className="flex justify-between border-b border-slate-800 pb-2">
              <span className="text-slate-400">Explainability Engine:</span>
              <span className="font-mono text-indigo-400">Gemini 2.5 Flash Lite</span>
            </li>
            <li className="flex justify-between border-b border-slate-800 pb-2">
              <span className="text-slate-400">Cohort Lookup Cache:</span>
              <span className="font-mono text-emerald-400">&lt;1ms In-Memory Baseline</span>
            </li>
            <li className="flex justify-between">
              <span className="text-slate-400">Persistence Store:</span>
              <span className="font-mono text-amber-400">SQLite (data/risk_manager.db)</span>
            </li>
          </ul>
        </div>
      </div>
    </div>
  );
};
