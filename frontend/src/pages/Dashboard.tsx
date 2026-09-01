import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { AnalyticsService } from '../services/api';
import { PieChart, Pie, Cell, ResponsiveContainer, BarChart, Bar, XAxis, Tooltip } from 'recharts';

export const Dashboard: React.FC = () => {
  const { data: summary, isLoading } = useQuery({
    queryKey: ['dashboardSummary'],
    queryFn: AnalyticsService.getSummary,
  });

  if (isLoading || !summary || !summary.riskDistribution) {
    return (
      <div className="flex items-center justify-center h-[calc(100vh-100px)]">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-[#55624d]"></div>
      </div>
    );
  }

  // Donut chart data mapping
  const pieData = [
    { name: 'Low Risk', value: summary.riskDistribution.lowRisk, color: '#55624D' }, // primary
    { name: 'Medium Volatility', value: summary.riskDistribution.medRisk, color: '#fd7e65' }, // coral-accent
    { name: 'High Risk / Flagged', value: summary.riskDistribution.highRisk, color: '#ECEFE8' } // surface-nest
  ];

  return (
    <div className="p-8 max-w-[1400px] mx-auto space-y-8">
      {/* Welcome Header */}
      <section className="mb-10">
        <div className="flex flex-col md:flex-row justify-between items-start md:items-end gap-4">
          <div>
            <h2 className="font-headline text-[48px] font-bold text-on-surface tracking-tight leading-tight">
              Good Morning, Alex
            </h2>
            <p className="font-body text-base text-on-surface-variant mt-2 max-w-2xl">
              AI Underwriter has processed <span className="font-bold text-primary">{summary.pendingReviewsCount + 6} new applications</span> overnight. Your manual review queue is currently prioritized by risk volatility.
            </p>
          </div>
          <div className="flex items-center gap-2 px-4 py-2 bg-white rounded-full shadow-soft border border-outline-variant/15 flex-shrink-0">
            <span className="w-2 h-2 rounded-full bg-primary animate-pulse"></span>
            <span className="text-[12px] font-label font-bold text-on-surface">Live Summary: Oct 24, 2023</span>
          </div>
        </div>
      </section>

      {/* KPI Cards Grid */}
      <section className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-gutter mb-12">
        {/* Card 1 */}
        <div className="bg-white p-8 rounded-xxl shadow-soft hover:scale-[1.02] transition-transform duration-300 cursor-default border border-outline-variant/10">
          <div className="flex justify-between items-start mb-4">
            <div className="p-3 bg-primary-fixed rounded-xl flex items-center justify-center text-primary">
              <span className="material-symbols-outlined text-[24px]">assignment_turned_in</span>
            </div>
            <span className="text-primary font-bold text-xs font-label">+12.5%</span>
          </div>
          <p className="font-label text-xs font-semibold text-on-surface-variant uppercase tracking-wider mb-1">Applications Processed</p>
          <h3 className="font-headline text-[32px] font-bold text-on-surface">{summary.processedCount.toLocaleString()}</h3>
        </div>

        {/* Card 2 */}
        <div className="bg-white p-8 rounded-xxl shadow-soft hover:scale-[1.02] transition-transform duration-300 cursor-default border border-outline-variant/10">
          <div className="flex justify-between items-start mb-4">
            <div className="p-3 bg-secondary-fixed rounded-xl flex items-center justify-center text-secondary">
              <span className="material-symbols-outlined text-[24px]">check_circle</span>
            </div>
            <span className="text-secondary font-bold text-xs font-label">+2.1%</span>
          </div>
          <p className="font-label text-xs font-semibold text-on-surface-variant uppercase tracking-wider mb-1">Approval Rate</p>
          <h3 className="font-headline text-[32px] font-bold text-on-surface">{summary.approvalRate}%</h3>
        </div>

        {/* Card 3 */}
        <div className="bg-white p-8 rounded-xxl shadow-soft hover:scale-[1.02] transition-transform duration-300 cursor-default border border-outline-variant/10">
          <div className="flex justify-between items-start mb-4">
            <div className="p-3 bg-tertiary-fixed rounded-xl flex items-center justify-center text-tertiary">
              <span className="material-symbols-outlined text-[24px]">speed</span>
            </div>
            <span className="text-tertiary font-bold text-xs font-label">-0.4</span>
          </div>
          <p className="font-label text-xs font-semibold text-on-surface-variant uppercase tracking-wider mb-1">Avg Risk Score</p>
          <h3 className="font-headline text-[32px] font-bold text-on-surface">{summary.avgRiskScore}</h3>
        </div>

        {/* Card 4 */}
        <div className="bg-white p-8 rounded-xxl shadow-soft hover:scale-[1.02] transition-transform duration-300 cursor-default relative overflow-hidden border border-outline-variant/10">
          <div className="flex justify-between items-start mb-4">
            <div className="p-3 bg-surface-container-highest rounded-xl flex items-center justify-center text-on-surface">
              <span className="material-symbols-outlined text-[24px]">pending_actions</span>
            </div>
            <div className="w-2.5 h-2.5 rounded-full bg-error animate-ping"></div>
          </div>
          <p className="font-label text-xs font-semibold text-on-surface-variant uppercase tracking-wider mb-1">Pending Reviews</p>
          <h3 className="font-headline text-[32px] font-bold text-on-surface">{summary.pendingReviewsCount}</h3>
        </div>
      </section>

      {/* Main Body Two Columns */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-gutter mb-12">
        {/* Left Column: Recent Applications */}
        <section className="lg:col-span-2">
          <div className="bg-white rounded-xxl p-8 shadow-soft h-full border border-outline-variant/10 flex flex-col justify-between">
            <div>
              <div className="flex justify-between items-center mb-8">
                <h4 className="font-headline text-lg font-bold text-on-surface">Recent Loan Applications</h4>
                <button className="text-primary font-label text-xs font-bold uppercase tracking-wider flex items-center gap-1 hover:underline outline-none">
                  View All <span className="material-symbols-outlined text-[14px] font-bold">arrow_forward</span>
                </button>
              </div>
              <div className="overflow-x-auto custom-scrollbar">
                <table className="w-full text-left border-collapse">
                  <thead>
                    <tr className="border-b border-surface-container-high">
                      <th className="pb-4 font-label text-xs uppercase tracking-wider font-semibold text-outline">Applicant</th>
                      <th className="pb-4 font-label text-xs uppercase tracking-wider font-semibold text-outline">Loan Amount</th>
                      <th className="pb-4 font-label text-xs uppercase tracking-wider font-semibold text-outline">Risk Score</th>
                      <th className="pb-4 font-label text-xs uppercase tracking-wider font-semibold text-outline">Recommendation</th>
                      <th className="pb-4 font-label text-xs uppercase tracking-wider font-semibold text-outline">Status</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-surface-container">
                    {summary.recentApplications.map((app, index) => (
                      <tr key={index} className="group hover:bg-surface-container-low/40 transition-colors duration-150 cursor-pointer">
                        <td className="py-5 pr-2">
                          <div className="flex items-center gap-3">
                            <div className="w-8 h-8 rounded-full bg-surface-container-low flex items-center justify-center font-bold text-primary text-xs">
                              {app.initials}
                            </div>
                            <span className="font-body text-sm font-bold text-on-surface">{app.name}</span>
                          </div>
                        </td>
                        <td className="py-5 font-headline text-sm font-bold text-on-surface">
                          ${app.amount.toLocaleString()}
                        </td>
                        <td className="py-5">
                          <span 
                            className="px-3 py-1 text-[11px] font-label font-bold rounded-full"
                            style={{ 
                              backgroundColor: app.riskScoreColor === '#059669' ? '#d1fae5' : app.riskScoreColor === '#d97706' ? '#fef3c7' : '#ffdad6', 
                              color: app.riskScoreColor 
                            }}
                          >
                            {app.riskScoreText}
                          </span>
                        </td>
                        <td className="py-5">
                          <span 
                            className="px-3 py-1 text-[11px] font-label font-bold rounded-full"
                            style={{
                              backgroundColor: app.recommendation === 'Decline' ? '#ffdad6' : app.recommendation === 'Auto-Approve' ? '#d1fae5' : '#e7e9e2',
                              color: app.recommendation === 'Decline' ? '#ba1a1a' : app.recommendation === 'Auto-Approve' ? '#55624d' : '#444841'
                            }}
                          >
                            {app.recommendation}
                          </span>
                        </td>
                        <td className="py-5">
                          <span className="flex items-center gap-2 text-xs font-body font-semibold text-on-surface-variant">
                            <span 
                              className="w-2 h-2 rounded-full"
                              style={{
                                backgroundColor: app.statusColor === '#55624d' ? '#55624d' : app.statusColor === '#fd7e65' ? '#fd7e65' : '#ba1a1a'
                              }}
                            ></span>
                            {app.status}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        </section>

        {/* Right Column: Charts & Trends */}
        <aside className="flex flex-col gap-gutter">
          {/* Donut Chart */}
          <div className="bg-white rounded-xxl p-8 shadow-soft border border-outline-variant/10">
            <h4 className="font-headline text-md font-bold text-on-surface mb-6">Risk Distribution</h4>
            <div className="relative w-48 h-48 mx-auto flex items-center justify-center">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={pieData}
                    cx="50%"
                    cy="50%"
                    innerRadius={65}
                    outerRadius={80}
                    paddingAngle={3}
                    dataKey="value"
                  >
                    {pieData.map((entry, idx) => (
                      <Cell key={`cell-${idx}`} fill={entry.color} />
                    ))}
                  </Pie>
                </PieChart>
              </ResponsiveContainer>
              <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none">
                <span className="font-headline text-3xl font-extrabold text-primary">72%</span>
                <span className="font-label text-[10px] text-outline-variant uppercase font-semibold">Low Risk</span>
              </div>
            </div>
            <div className="mt-6 space-y-3">
              {pieData.map((item, idx) => (
                <div key={idx} className="flex justify-between items-center text-xs font-body">
                  <div className="flex items-center gap-2">
                    <div className="w-3 h-3 rounded-full" style={{ backgroundColor: item.color }} />
                    <span className="text-on-surface-variant font-medium">{item.name}</span>
                  </div>
                  <span className="font-bold text-on-surface">{item.value}%</span>
                </div>
              ))}
            </div>
          </div>

          {/* Bar Chart Trend */}
          <div className="bg-white rounded-xxl p-8 shadow-soft border border-outline-variant/10 flex-1 flex flex-col justify-between">
            <div>
              <h4 className="font-headline text-md font-bold text-on-surface mb-4">Approval Trends</h4>
              <div className="h-32 w-full mt-4">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={summary.approvalTrends} margin={{ top: 0, right: 0, left: -20, bottom: 0 }}>
                    <XAxis dataKey="day" axisLine={false} tickLine={false} tick={{ fontSize: 10, fill: '#757870' }} />
                    <Tooltip cursor={{ fill: 'transparent' }} />
                    <Bar dataKey="value" radius={[4, 4, 0, 0]}>
                      {summary.approvalTrends.map((entry, index) => (
                        <Cell 
                          key={`cell-${index}`} 
                          fill={entry.active ? '#55624D' : '#ECEFE8'} 
                          className="transition-all duration-300 hover:fill-[#98a68e]"
                        />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>
            <p className="text-xs font-body text-on-surface-variant mt-4">
              Activity is <span className="text-primary font-bold">14% higher</span> than last week's average.
            </p>
          </div>
        </aside>
      </div>

      {/* Bottom: Recent AI Decisions Timeline */}
      <section>
        <h4 className="font-headline text-lg font-bold text-on-surface mb-6 flex items-center gap-2">
          <span className="material-symbols-outlined text-secondary text-[24px]">flare</span>
          Recent AI Decisions
        </h4>
        <div className="space-y-4">
          {summary.recentDecisions.map((decision) => (
            <div 
              key={decision.id} 
              className={`bg-white p-6 rounded-xxl shadow-soft flex flex-col md:flex-row gap-6 relative border border-outline-variant/10 ${
                decision.recommendation === 'FLAG' ? 'ai-insight-border' : ''
              }`}
            >
              {/* Left Column: Metadata */}
              <div className="md:w-1/4">
                <div className="flex items-center gap-2 mb-1">
                  <span className="material-symbols-outlined text-on-surface-variant text-[16px]">schedule</span>
                  <span className="font-label text-[11px] font-semibold text-on-surface-variant uppercase tracking-wider">
                    {decision.time}
                  </span>
                </div>
                <h5 className="font-body text-base font-bold text-on-surface">{decision.name}</h5>
                <p className="text-xs font-body text-on-surface-variant">{decision.loanType}</p>
              </div>

              {/* Middle Column: Recommendation & Confidence */}
              <div className="md:w-1/4 flex flex-col justify-center gap-2">
                <div className="flex items-center gap-2">
                  <span className="font-label text-[10px] text-outline-variant uppercase font-semibold">Recommendation</span>
                  <span 
                    className={`px-2 py-0.5 font-label font-bold text-[10px] rounded-full ${
                      decision.recommendation === 'APPROVE' 
                        ? 'bg-primary-fixed text-primary' 
                        : 'bg-secondary-fixed text-secondary'
                    }`}
                  >
                    {decision.recommendation}
                  </span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="font-label text-[10px] text-outline-variant uppercase font-semibold">Confidence</span>
                  <div className="flex-1 h-1.5 bg-surface-container rounded-full max-w-[120px]">
                    <div 
                      className={`h-full rounded-full ${
                        decision.recommendation === 'APPROVE' ? 'bg-primary' : 'bg-secondary'
                      }`} 
                      style={{ width: `${decision.confidence}%` }}
                    />
                  </div>
                  <span className="font-headline text-xs font-bold text-on-surface">{decision.confidence}%</span>
                </div>
              </div>

              {/* Right Column: Insight Box */}
              <div className="flex-1 bg-surface-container-low rounded-xl p-4 border border-outline-variant/5">
                <div className="flex items-center gap-1.5 mb-2">
                  <span className="material-symbols-outlined text-[16px] text-secondary">bolt</span>
                  <span className="font-label text-[11px] font-bold text-on-surface-variant uppercase tracking-wider">
                    AI Insight
                  </span>
                </div>
                <p className="text-xs font-body font-medium italic text-on-surface-variant leading-relaxed">
                  "{decision.insight}"
                </p>
              </div>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
};
