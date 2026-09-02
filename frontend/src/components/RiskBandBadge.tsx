import React from 'react';
import type { DefenseAction, RiskBand } from '../types';

interface Props {
  band?: RiskBand;
  action?: DefenseAction;
  score?: number;
}

export const RiskBandBadge: React.FC<Props> = ({ band, action, score }) => {
  const getBadgeStyle = () => {
    switch (action) {
      case 'auto_decline':
        return 'bg-red-900/60 text-red-300 border-red-700/80';
      case 'hold_for_verification':
        return 'bg-amber-900/60 text-amber-300 border-amber-700/80';
      case 'flag_for_review':
        return 'bg-yellow-900/60 text-yellow-300 border-yellow-700/80';
      case 'allow':
      default:
        return 'bg-emerald-900/60 text-emerald-300 border-emerald-700/80';
    }
  };

  const label = action ? action.replace(/_/g, ' ').toUpperCase() : band ? band.toUpperCase() : 'UNKNOWN';

  return (
    <div className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full border text-xs font-semibold tracking-wider ${getBadgeStyle()}`}>
      <span className="w-1.5 h-1.5 rounded-full bg-current animate-pulse" />
      <span>{label}</span>
      {score !== undefined && (
        <span className="opacity-75 font-mono text-[10px]">({(score * 100).toFixed(0)}%)</span>
      )}
    </div>
  );
};
