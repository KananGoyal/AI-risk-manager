import React, { useState, useEffect } from 'react';
import { fetchLiveTransactions, triggerSeedBatch } from '../services/api';
import type { ScoredTransaction } from '../types';
import { RiskBandBadge } from '../components/RiskBandBadge';
import { TransactionModal } from '../components/TransactionModal';
import { Play, Pause, RefreshCw, Filter, Eye } from 'lucide-react';

export const LiveFeed: React.FC = () => {
  const [transactions, setTransactions] = useState<ScoredTransaction[]>([]);
  const [selectedTx, setSelectedTx] = useState<ScoredTransaction | null>(null);
  const [isPolling, setIsPolling] = useState<boolean>(true);
  const [filterAction, setFilterAction] = useState<string>('all');
  const [isLoading, setIsLoading] = useState<boolean>(true);

  const loadStreamData = async () => {
    try {
      const res = await fetchLiveTransactions(50);
      setTransactions(res.transactions || []);
    } catch (err) {
      console.error('Error fetching stream data:', err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadStreamData();
    let interval: any;
    if (isPolling) {
      interval = setInterval(() => {
        loadStreamData();
      }, 2000);
    }
    return () => clearInterval(interval);
  }, [isPolling]);

  const handleSeedMore = async () => {
    await triggerSeedBatch();
    await loadStreamData();
  };

  const filteredTxns = transactions.filter((tx) => {
    if (filterAction === 'all') return true;
    if (filterAction === 'flagged') return tx.action !== 'allow';
    return tx.action === filterAction;
  });

  const totalFlagged = transactions.filter((tx) => tx.action !== 'allow').length;
  const totalVolume = transactions.reduce((acc, tx) => acc + tx.amount, 0);

  return (
    <div className="space-y-6">
      {/* Header & Live Stream Controls */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 bg-slate-900 border border-slate-800 p-6 rounded-2xl shadow-xl">
        <div>
          <div className="flex items-center gap-2">
            <span className="relative flex h-3 w-3">
              {isPolling && <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>}
              <span className={`relative inline-flex rounded-full h-3 w-3 ${isPolling ? 'bg-emerald-500' : 'bg-slate-500'}`}></span>
            </span>
            <h1 className="text-xl font-bold text-white">Live Transaction Stream</h1>
          </div>
          <p className="text-xs text-slate-400 mt-1">
            Real-time transaction stream scored with XGBoost model and fast in-memory cohort baseline comparison.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={() => setIsPolling(!isPolling)}
            className={`flex items-center gap-2 px-3.5 py-2 rounded-xl text-xs font-semibold border transition ${
              isPolling
                ? 'bg-emerald-950/60 text-emerald-300 border-emerald-700/60 hover:bg-emerald-900/60'
                : 'bg-slate-800 text-slate-300 border-slate-700 hover:bg-slate-700'
            }`}
          >
            {isPolling ? <Pause className="w-3.5 h-3.5" /> : <Play className="w-3.5 h-3.5" />}
            <span>{isPolling ? 'Pause Live Stream' : 'Resume Live Stream'}</span>
          </button>

          <button
            onClick={handleSeedMore}
            className="flex items-center gap-2 px-3.5 py-2 rounded-xl text-xs font-semibold bg-blue-600 text-white hover:bg-blue-500 transition shadow-lg shadow-blue-600/20"
          >
            <RefreshCw className="w-3.5 h-3.5" />
            <span>Inject Simulation Batch</span>
          </button>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div className="bg-slate-900 border border-slate-800 p-4 rounded-xl">
          <span className="text-xs text-slate-400 font-medium">Recent Stream Count</span>
          <p className="text-2xl font-bold text-white mt-1">{transactions.length} txns</p>
        </div>
        <div className="bg-slate-900 border border-slate-800 p-4 rounded-xl">
          <span className="text-xs text-slate-400 font-medium">Flagged Anomaly Rate</span>
          <p className="text-2xl font-bold text-amber-400 mt-1">
            {transactions.length > 0 ? ((totalFlagged / transactions.length) * 100).toFixed(1) : 0}% ({totalFlagged} flagged)
          </p>
        </div>
        <div className="bg-slate-900 border border-slate-800 p-4 rounded-xl">
          <span className="text-xs text-slate-400 font-medium">Stream Volume Scored</span>
          <p className="text-2xl font-bold text-emerald-400 mt-1">${totalVolume.toLocaleString(undefined, { minimumFractionDigits: 2 })}</p>
        </div>
      </div>

      {/* Filter Bar */}
      <div className="flex items-center justify-between bg-slate-900 border border-slate-800 px-4 py-3 rounded-xl text-xs">
        <div className="flex items-center gap-2 text-slate-400">
          <Filter className="w-4 h-4 text-blue-400" />
          <span>Filter Action:</span>
        </div>
        <div className="flex flex-wrap gap-1.5">
          {['all', 'flagged', 'allow', 'flag_for_review', 'hold_for_verification', 'auto_decline'].map((act) => (
            <button
              key={act}
              onClick={() => setFilterAction(act)}
              className={`px-3 py-1.5 rounded-lg font-medium transition ${
                filterAction === act
                  ? 'bg-blue-600 text-white'
                  : 'bg-slate-800 text-slate-400 hover:text-slate-200'
              }`}
            >
              {act.replace(/_/g, ' ').toUpperCase()}
            </button>
          ))}
        </div>
      </div>

      {/* Live Feed Table */}
      <div className="bg-slate-900 border border-slate-800 rounded-2xl overflow-hidden shadow-xl">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs text-slate-300">
            <thead className="bg-slate-950 text-slate-400 uppercase tracking-wider border-b border-slate-800">
              <tr>
                <th className="py-3.5 px-4 font-semibold">Txn ID / Timestamp</th>
                <th className="py-3.5 px-4 font-semibold">Merchant / Category</th>
                <th className="py-3.5 px-4 font-semibold">Amount</th>
                <th className="py-3.5 px-4 font-semibold">Risk Score</th>
                <th className="py-3.5 px-4 font-semibold">Defense Action</th>
                <th className="py-3.5 px-4 font-semibold text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60">
              {filteredTxns.length > 0 ? (
                filteredTxns.map((tx) => (
                  <tr
                    key={tx.transaction_id}
                    className={`hover:bg-slate-800/40 transition cursor-pointer ${
                      tx.action !== 'allow' ? 'bg-amber-950/10' : ''
                    }`}
                    onClick={() => setSelectedTx(tx)}
                  >
                    <td className="py-3 px-4 font-mono">
                      <span className="font-semibold text-white block">{tx.transaction_id}</span>
                      <span className="text-[10px] text-slate-500">{new Date(tx.timestamp).toLocaleTimeString()}</span>
                    </td>
                    <td className="py-3 px-4">
                      <span className="font-medium text-slate-200 block">{tx.merchant}</span>
                      <span className="text-[10px] text-slate-400">{tx.merchant_category}</span>
                    </td>
                    <td className="py-3 px-4 font-semibold text-white">
                      ${tx.amount.toLocaleString(undefined, { minimumFractionDigits: 2 })}
                    </td>
                    <td className="py-3 px-4">
                      <div className="flex items-center gap-2">
                        <div className="w-16 bg-slate-800 rounded-full h-2 overflow-hidden">
                          <div
                            className={`h-full rounded-full ${
                              tx.risk_score > 0.75 ? 'bg-red-500' : tx.risk_score > 0.35 ? 'bg-amber-500' : 'bg-emerald-500'
                            }`}
                            style={{ width: `${Math.max(5, tx.risk_score * 100)}%` }}
                          />
                        </div>
                        <span className="font-mono text-slate-300 font-medium">{(tx.risk_score * 100).toFixed(0)}%</span>
                      </div>
                    </td>
                    <td className="py-3 px-4">
                      <RiskBandBadge action={tx.action} band={tx.risk_band} />
                    </td>
                    <td className="py-3 px-4 text-right">
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          setSelectedTx(tx);
                        }}
                        className="inline-flex items-center gap-1 px-2.5 py-1.5 rounded-lg bg-slate-800 text-blue-400 hover:bg-slate-700 transition text-[11px] font-medium"
                      >
                        <Eye className="w-3.5 h-3.5" />
                        <span>Audit Reason</span>
                      </button>
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan={6} className="text-center py-12 text-slate-500 italic">
                    {isLoading ? 'Loading live stream transactions...' : 'No transactions match selected filter.'}
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Transaction Audit Modal */}
      <TransactionModal transaction={selectedTx} onClose={() => setSelectedTx(null)} />
    </div>
  );
};
