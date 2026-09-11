import React from 'react';
import { TrendingUp, ShieldAlert, CheckCircle2, Clock, FileText, AlertTriangle } from 'lucide-react';
import { Commitment } from '../../types/dashboard';

interface OverviewViewProps {
  commitments: Commitment[];
  onNavigateToCommitments: () => void;
}

export const OverviewView: React.FC<OverviewViewProps> = ({
  commitments,
  onNavigateToCommitments,
}) => {
  const needsAttention = commitments.filter((c) => c.category === 'needs-attention').length;
  const awaitingReview = commitments.filter((c) => c.category === 'awaiting-review').length;
  const delivered = commitments.filter((c) => c.category === 'delivered').length;

  return (
    <div className="flex-1 p-6 sm:p-8 lg:p-10 xl:p-12 overflow-y-auto max-w-[1380px] mx-auto w-full">
      {/* Overview Top Header */}
      <div className="pb-8 border-b border-neutral-200/90">
        <h1 className="text-3xl sm:text-4xl lg:text-[40px] font-extrabold tracking-tight text-neutral-900 leading-tight">
          Executive Overview
        </h1>
        <p className="text-sm sm:text-base text-neutral-500 mt-2">
          High-level delivery health, risk velocity, and commitment fulfillment metrics.
        </p>
      </div>

      {/* 4 Metric KPI Cards (Scaled Up for Overview with Colorful Icons) */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 sm:gap-6 mt-8 mb-8">
        {/* Active Commitments */}
        <div className="p-6 sm:p-7 rounded-2xl border border-neutral-200/90 bg-white shadow-2xs hover:border-neutral-300 hover:shadow-xs transition-all flex flex-col justify-between">
          <div className="flex items-center justify-between text-sm font-semibold text-neutral-500 mb-3">
            <span>Active commitments</span>
            <div className="w-9 h-9 rounded-xl bg-blue-50 dark:bg-blue-950/60 text-blue-600 dark:text-blue-400 flex items-center justify-center border border-blue-100 dark:border-blue-900/50 shadow-2xs">
              <FileText className="w-5 h-5" />
            </div>
          </div>
          <div className="text-3xl sm:text-4xl lg:text-5xl font-extrabold tracking-tight text-neutral-900">
            {commitments.length}
          </div>
        </div>

        {/* Needs Attention */}
        <div className="p-6 sm:p-7 rounded-2xl border-2 border-neutral-900 bg-white shadow-xs flex flex-col justify-between">
          <div className="flex items-center justify-between text-sm font-semibold text-neutral-900 mb-3">
            <span className="flex items-center gap-2">
              <span className="w-2.5 h-2.5 rounded-full bg-amber-400" />
              <span>Needs attention</span>
            </span>
            <div className="w-9 h-9 rounded-xl bg-amber-50 dark:bg-amber-950/60 text-amber-600 dark:text-amber-400 flex items-center justify-center border border-amber-200/70 dark:border-amber-900/50 shadow-2xs">
              <AlertTriangle className="w-5 h-5" />
            </div>
          </div>
          <div className="text-3xl sm:text-4xl lg:text-5xl font-extrabold tracking-tight text-neutral-900">
            {needsAttention}
          </div>
        </div>

        {/* Awaiting Review */}
        <div className="p-6 sm:p-7 rounded-2xl border border-neutral-200/90 bg-white shadow-2xs hover:border-neutral-300 hover:shadow-xs transition-all flex flex-col justify-between">
          <div className="flex items-center justify-between text-sm font-semibold text-neutral-500 mb-3">
            <span>Awaiting review</span>
            <div className="w-9 h-9 rounded-xl bg-purple-50 dark:bg-purple-950/60 text-purple-600 dark:text-purple-400 flex items-center justify-center border border-purple-100 dark:border-purple-900/50 shadow-2xs">
              <Clock className="w-5 h-5" />
            </div>
          </div>
          <div className="text-3xl sm:text-4xl lg:text-5xl font-extrabold tracking-tight text-neutral-900">
            {awaitingReview}
          </div>
        </div>

        {/* Delivered This Month */}
        <div className="p-6 sm:p-7 rounded-2xl border border-neutral-200/90 bg-white shadow-2xs hover:border-neutral-300 hover:shadow-xs transition-all flex flex-col justify-between">
          <div className="flex items-center justify-between text-sm font-semibold text-neutral-500 mb-3">
            <span>Delivered this month</span>
            <div className="w-9 h-9 rounded-xl bg-emerald-50 dark:bg-emerald-950/60 text-emerald-600 dark:text-emerald-400 flex items-center justify-center border border-emerald-100 dark:border-emerald-900/50 shadow-2xs">
              <CheckCircle2 className="w-5 h-5" />
            </div>
          </div>
          <div className="text-3xl sm:text-4xl lg:text-5xl font-extrabold tracking-tight text-neutral-900">
            {delivered}
          </div>
        </div>
      </div>

      {/* Analytics Breakdown Grid (Scaled Up) */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 sm:gap-8 mt-4">
        {/* Delivery Reliability Index */}
        <div className="bg-white border border-neutral-200/90 rounded-2xl p-6 sm:p-8 shadow-xs flex flex-col justify-between">
          <div>
            <h3 className="font-bold text-base sm:text-lg text-neutral-900 mb-1.5 flex items-center gap-2.5">
              <TrendingUp className="w-5 h-5 text-neutral-900" />
              <span>Fulfillment Velocity & Adherence</span>
            </h3>
            <p className="text-xs sm:text-sm text-neutral-500 mb-6">
              Percentage of customer promises fulfilled within original agreed target dates.
            </p>
          </div>

          <div className="flex flex-col sm:flex-row items-center gap-6 sm:gap-8 pt-2">
            {/* 84.0 Target Met Radial Gauge (Bigger) */}
            <div className="shrink-0 flex flex-col items-center justify-center">
              <svg viewBox="0 0 200 155" className="w-48 h-36 sm:w-52 sm:h-40">
                {/* Background Track */}
                <path
                  d="M 52.5 129.8 A 62 62 0 1 1 147.5 129.8"
                  fill="none"
                  stroke="#E5E7EB"
                  strokeWidth="18"
                  strokeLinecap="round"
                />
                {/* Active Filled Arc (84%) */}
                <path
                  d="M 52.5 129.8 A 62 62 0 1 1 147.5 129.8"
                  fill="none"
                  stroke="#000000"
                  strokeWidth="18"
                  strokeLinecap="round"
                  strokeDasharray="236.3 281.3"
                />
                {/* Center Value */}
                <text
                  x="100"
                  y="86"
                  textAnchor="middle"
                  className="text-[34px] font-extrabold fill-neutral-950 select-none tracking-tight"
                >
                  84.0
                </text>
                {/* Center Label */}
                <text
                  x="100"
                  y="108"
                  textAnchor="middle"
                  className="text-[12px] font-semibold fill-neutral-400 select-none tracking-normal"
                >
                  Target Met
                </text>
              </svg>
            </div>

            {/* Customer Breakdown Progress Bars */}
            <div className="flex-1 w-full space-y-4">
              <div>
                <div className="flex justify-between text-xs sm:text-sm font-semibold mb-1.5">
                  <span className="text-neutral-900">Acme Corp</span>
                  <span className="text-emerald-700">92% on-time</span>
                </div>
                <div className="w-full h-2.5 sm:h-3 bg-neutral-100 rounded-full overflow-hidden">
                  <div className="h-full bg-emerald-500 rounded-full" style={{ width: '92%' }} />
                </div>
              </div>

              <div>
                <div className="flex justify-between text-xs sm:text-sm font-semibold mb-1.5">
                  <span className="text-neutral-900">Northstar Labs</span>
                  <span className="text-amber-700">76% on-time</span>
                </div>
                <div className="w-full h-2.5 sm:h-3 bg-neutral-100 rounded-full overflow-hidden">
                  <div className="h-full bg-amber-500 rounded-full" style={{ width: '76%' }} />
                </div>
              </div>

              <div>
                <div className="flex justify-between text-xs sm:text-sm font-semibold mb-1.5">
                  <span className="text-neutral-900">Orbit HQ</span>
                  <span className="text-emerald-700">88% on-time</span>
                </div>
                <div className="w-full h-2.5 sm:h-3 bg-neutral-100 rounded-full overflow-hidden">
                  <div className="h-full bg-emerald-500 rounded-full" style={{ width: '88%' }} />
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Risk Distribution Card */}
        <div className="bg-white border border-neutral-200/90 rounded-2xl p-6 sm:p-8 shadow-xs flex flex-col justify-between">
          <div>
            <h3 className="font-bold text-base sm:text-lg text-neutral-900 mb-1.5 flex items-center gap-2.5">
              <ShieldAlert className="w-5 h-5 text-amber-600" />
              <span>Active Risk Analysis</span>
            </h3>
            <p className="text-xs sm:text-sm text-neutral-500 mb-6">
              Current blocker distribution detected via Jira and Linear webhooks.
            </p>
          </div>

          <div className="space-y-3.5 text-xs sm:text-sm">
            <div className="p-4 sm:p-4.5 bg-amber-50/70 border border-amber-200/80 rounded-2xl flex items-center justify-between gap-3">
              <div>
                <span className="font-bold text-amber-900 block text-sm">Delivery Date Conflicts (2)</span>
                <span className="text-xs text-amber-700 mt-0.5 block">
                  Engineering target date later than promised date.
                </span>
              </div>
              <button
                onClick={onNavigateToCommitments}
                className="text-xs font-semibold text-amber-900 underline hover:text-amber-950 shrink-0 cursor-pointer"
              >
                Inspect
              </button>
            </div>

            <div className="p-4 sm:p-4.5 bg-red-50/70 border border-red-200/80 rounded-2xl flex items-center justify-between gap-3">
              <div>
                <span className="font-bold text-red-900 block text-sm">Overdue Commitments (1)</span>
                <span className="text-xs text-red-700 mt-0.5 block">
                  Passed deadline without verified delivery evidence.
                </span>
              </div>
              <button
                onClick={onNavigateToCommitments}
                className="text-xs font-semibold text-red-900 underline hover:text-red-950 shrink-0 cursor-pointer"
              >
                Inspect
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
