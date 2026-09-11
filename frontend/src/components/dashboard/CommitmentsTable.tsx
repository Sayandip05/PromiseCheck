import React, { useState } from 'react';
import {
  FileText,
  ArrowUpDown,
  ChevronDown,
  ChevronRight,
  Calendar as CalendarIcon,
} from 'lucide-react';
import { Commitment } from '../../types/dashboard';

interface CommitmentsTableProps {
  commitments: Commitment[];
  selectedCommitmentId: string | null;
  onSelectCommitment: (commitment: Commitment) => void;
  activeTab: string;
  onTabChange: (tab: string) => void;
  allCount: number;
  needsAttentionCount: number;
  awaitingReviewCount: number;
}

export const CommitmentsTable: React.FC<CommitmentsTableProps> = ({
  commitments,
  selectedCommitmentId,
  onSelectCommitment,
  activeTab,
  onTabChange,
  allCount,
  needsAttentionCount,
  awaitingReviewCount,
}) => {
  const [ownerFilter, setOwnerFilter] = useState('all');
  const [ownerDropdownOpen, setOwnerDropdownOpen] = useState(false);
  const [dateDropdownOpen, setDateDropdownOpen] = useState(false);
  const [dateFilter, setDateFilter] = useState('any');

  // Filter commitments based on tab and dropdowns
  const filteredCommitments = commitments.filter((comm) => {
    // Tab filter
    if (activeTab === 'needs-attention' && comm.category !== 'needs-attention') return false;
    if (activeTab === 'awaiting-review' && comm.category !== 'awaiting-review') return false;
    if (activeTab === 'delivered' && comm.category !== 'delivered') return false;

    // Owner filter
    if (ownerFilter !== 'all' && comm.owner.name !== ownerFilter) return false;

    return true;
  });

  const ownersList = Array.from(new Set(commitments.map((c) => c.owner.name)));

  // Status Badge Component
  const renderStatusBadge = (status: string, label: string) => {
    switch (status) {
      case 'at-risk':
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-amber-100/70 dark:bg-amber-950/40 text-amber-800 dark:text-amber-300 border border-amber-200/60 dark:border-amber-800/60">
            <span className="w-1.5 h-1.5 rounded-full bg-amber-500" />
            {label}
          </span>
        );
      case 'overdue':
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-red-100/70 dark:bg-red-950/40 text-red-800 dark:text-red-300 border border-red-200/60 dark:border-red-800/60">
            <span className="w-1.5 h-1.5 rounded-full bg-red-500" />
            {label}
          </span>
        );
      case 'blocked':
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-orange-100/70 dark:bg-orange-950/40 text-orange-800 dark:text-orange-300 border border-orange-200/60 dark:border-orange-800/60">
            <span className="w-1.5 h-1.5 rounded-full bg-orange-500" />
            {label}
          </span>
        );
      case 'awaiting-review':
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-neutral-200/80 dark:bg-neutral-800 text-neutral-900 dark:text-neutral-200 border border-neutral-300 dark:border-neutral-700">
            <span className="w-1.5 h-1.5 rounded-full bg-neutral-600 dark:bg-neutral-400" />
            {label}
          </span>
        );
      case 'delivered':
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-100/70 dark:bg-emerald-950/40 text-emerald-800 dark:text-emerald-300 border border-emerald-200/60 dark:border-emerald-800/60">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
            {label}
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-neutral-100 dark:bg-neutral-800 text-neutral-700 dark:text-neutral-300 border border-neutral-200 dark:border-neutral-700">
            <span className="w-1.5 h-1.5 rounded-full bg-neutral-500" />
            {label}
          </span>
        );
    }
  };

  const getSectionTitle = () => {
    if (activeTab === 'needs-attention') return 'Promises that need attention';
    if (activeTab === 'awaiting-review') return 'Promises awaiting review';
    if (activeTab === 'delivered') return 'Delivered promises';
    return 'All customer commitments';
  };

  return (
    <div className="mb-6">
      {/* Top Filter and Tab Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-neutral-200 dark:border-neutral-800 pb-3 mb-4">
        {/* Navigation Tabs */}
        <div className="flex items-center gap-6 overflow-x-auto no-scrollbar">
          <button
            onClick={() => onTabChange('all')}
            className={`flex items-center gap-1.5 text-xs sm:text-sm font-medium pb-2 -mb-3 transition-colors whitespace-nowrap cursor-pointer ${
              activeTab === 'all'
                ? 'text-neutral-900 dark:text-white border-b-2 border-neutral-900 dark:border-white font-bold'
                : 'text-neutral-500 dark:text-neutral-400 hover:text-neutral-800 dark:hover:text-neutral-200'
            }`}
          >
            <span>All</span>
            <span className="text-xs text-neutral-400 dark:text-neutral-500 font-normal">{allCount}</span>
          </button>

          <button
            onClick={() => {
              onTabChange('needs-attention');
              const firstAttention = commitments.find((c) => c.category === 'needs-attention') || commitments[0];
              if (firstAttention) {
                onSelectCommitment(firstAttention);
              }
            }}
            className={`flex items-center gap-1.5 text-xs sm:text-sm font-medium pb-2 -mb-3 transition-colors whitespace-nowrap cursor-pointer ${
              activeTab === 'needs-attention'
                ? 'text-neutral-900 dark:text-white border-b-2 border-neutral-900 dark:border-white font-bold'
                : 'text-neutral-500 dark:text-neutral-400 hover:text-neutral-800 dark:hover:text-neutral-200'
            }`}
          >
            <span>Needs attention</span>
            <span
              className={`text-xs px-1.5 py-0.2 rounded-full font-bold ${
                activeTab === 'needs-attention'
                  ? 'bg-neutral-200 dark:bg-neutral-800 text-neutral-900 dark:text-white'
                  : 'text-neutral-400 dark:text-neutral-500'
              }`}
            >
              {needsAttentionCount}
            </span>
          </button>

          <button
            onClick={() => onTabChange('awaiting-review')}
            className={`flex items-center gap-1.5 text-xs sm:text-sm font-medium pb-2 -mb-3 transition-colors whitespace-nowrap cursor-pointer ${
              activeTab === 'awaiting-review'
                ? 'text-neutral-900 dark:text-white border-b-2 border-neutral-900 dark:border-white font-bold'
                : 'text-neutral-500 dark:text-neutral-400 hover:text-neutral-800 dark:hover:text-neutral-200'
            }`}
          >
            <span>Awaiting review</span>
            <span className="text-xs text-neutral-400 dark:text-neutral-500 font-normal">{awaitingReviewCount}</span>
          </button>
        </div>

        {/* Dropdown Filters */}
        <div className="flex items-center gap-2 relative">
          {/* Owner Filter */}
          <div className="relative">
            <button
              onClick={() => setOwnerDropdownOpen(!ownerDropdownOpen)}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-neutral-700 dark:text-neutral-200 bg-white dark:bg-neutral-800 border border-neutral-200 dark:border-neutral-700 rounded-lg hover:bg-neutral-50 dark:hover:bg-neutral-750 transition-colors cursor-pointer"
            >
              <span>{ownerFilter === 'all' ? 'All owners' : ownerFilter}</span>
              <ChevronDown className="w-3 h-3 text-neutral-400" />
            </button>

            {ownerDropdownOpen && (
              <div className="absolute right-0 mt-1 w-44 bg-white dark:bg-neutral-800 border border-neutral-200 dark:border-neutral-700 rounded-lg shadow-md z-30 py-1 text-xs">
                <button
                  onClick={() => {
                    setOwnerFilter('all');
                    setOwnerDropdownOpen(false);
                  }}
                  className="w-full text-left px-3 py-1.5 hover:bg-neutral-50 dark:hover:bg-neutral-700 text-neutral-700 dark:text-neutral-200 font-medium cursor-pointer"
                >
                  All owners
                </button>
                {ownersList.map((owner) => (
                  <button
                    key={owner}
                    onClick={() => {
                      setOwnerFilter(owner);
                      setOwnerDropdownOpen(false);
                    }}
                    className="w-full text-left px-3 py-1.5 hover:bg-neutral-50 dark:hover:bg-neutral-700 text-neutral-700 dark:text-neutral-200 cursor-pointer"
                  >
                    {owner}
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* Date Filter */}
          <div className="relative">
            <button
              onClick={() => setDateDropdownOpen(!dateDropdownOpen)}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-neutral-700 dark:text-neutral-200 bg-white dark:bg-neutral-800 border border-neutral-200 dark:border-neutral-700 rounded-lg hover:bg-neutral-50 dark:hover:bg-neutral-750 transition-colors cursor-pointer"
            >
              <CalendarIcon className="w-3 h-3 text-neutral-400" />
              <span>{dateFilter === 'any' ? 'Any date' : dateFilter}</span>
              <ChevronDown className="w-3 h-3 text-neutral-400" />
            </button>

            {dateDropdownOpen && (
              <div className="absolute right-0 mt-1 w-40 bg-white dark:bg-neutral-800 border border-neutral-200 dark:border-neutral-700 rounded-lg shadow-md z-30 py-1 text-xs">
                {['Any date', 'This week', 'This month', 'Next 30 days', 'Overdue only'].map(
                  (opt) => (
                    <button
                      key={opt}
                      onClick={() => {
                        setDateFilter(opt);
                        setDateDropdownOpen(false);
                      }}
                      className="w-full text-left px-3 py-1.5 hover:bg-neutral-50 dark:hover:bg-neutral-700 text-neutral-700 dark:text-neutral-200 cursor-pointer"
                    >
                      {opt}
                    </button>
                  )
                )}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Main Table Container */}
      <div className="bg-white dark:bg-neutral-900 border border-neutral-200/90 dark:border-neutral-800 rounded-xl shadow-2xs overflow-hidden">
        {/* Table Title Bar */}
        <div
          onClick={() => {
            const firstAttention = commitments.find((c) => c.category === 'needs-attention') || commitments[0];
            if (firstAttention) {
              onSelectCommitment(firstAttention);
            }
          }}
          className="px-5 py-3.5 border-b border-neutral-100 dark:border-neutral-800 flex items-center justify-between cursor-pointer hover:bg-neutral-50/70 dark:hover:bg-neutral-800/50 transition-colors group"
          title="Click to view commitment details"
        >
          <h2 className="text-sm font-semibold text-neutral-900 dark:text-white group-hover:text-neutral-950 dark:group-hover:text-neutral-200 transition-colors">
            {getSectionTitle()}
          </h2>
          <span className="text-[11px] text-neutral-400 dark:text-neutral-500 group-hover:text-neutral-600 dark:group-hover:text-neutral-400 font-normal transition-colors hidden sm:inline">
            Click any row to view details &rarr;
          </span>
        </div>

        {/* Responsive Table */}
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse min-w-[550px]">
            <thead>
              <tr className="border-b border-neutral-100 dark:border-neutral-800 text-[11px] font-medium text-neutral-400 dark:text-neutral-500 uppercase tracking-wider bg-neutral-50/50 dark:bg-neutral-800/40">
                <th className="py-2.5 px-5 font-medium">
                  <div className="flex items-center gap-1 cursor-pointer hover:text-neutral-700 dark:hover:text-neutral-200">
                    <span>Commitment</span>
                    <ArrowUpDown className="w-3 h-3" />
                  </div>
                </th>
                <th className="py-2.5 px-4 font-medium">Customer</th>
                <th className="py-2.5 px-4 font-medium">Owner</th>
                <th className="py-2.5 px-4 font-medium">
                  <div className="flex items-center gap-1 cursor-pointer hover:text-neutral-700 dark:hover:text-neutral-200">
                    <span>Promised by</span>
                    <ArrowUpDown className="w-3 h-3" />
                  </div>
                </th>
                <th className="py-2.5 px-5 font-medium text-right sm:text-left">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-neutral-100 dark:divide-neutral-800 text-xs sm:text-sm">
              {filteredCommitments.length === 0 ? (
                <tr>
                  <td colSpan={5} className="py-8 text-center text-neutral-400 dark:text-neutral-500 text-xs">
                    No commitments found for this filter.
                  </td>
                </tr>
              ) : (
                filteredCommitments.map((comm) => {
                  const isSelected = selectedCommitmentId === comm.id;
                  return (
                    <tr
                      key={comm.id}
                      onClick={() => onSelectCommitment(comm)}
                      className={`transition-colors cursor-pointer group ${
                        isSelected
                          ? 'bg-neutral-100/90 dark:bg-neutral-800/90 border-l-4 border-l-neutral-900 dark:border-l-white'
                          : 'hover:bg-neutral-50/80 dark:hover:bg-neutral-800/40'
                      }`}
                    >
                      {/* Commitment Title */}
                      <td className="py-3 px-5">
                        <div className="flex items-center gap-2.5">
                          <FileText
                            className={`w-4 h-4 shrink-0 ${
                              isSelected ? 'text-neutral-900 dark:text-white' : 'text-neutral-400 dark:text-neutral-500 group-hover:text-neutral-600 dark:group-hover:text-neutral-300'
                            }`}
                          />
                          <span
                            className={`font-medium ${
                              isSelected ? 'text-neutral-950 dark:text-white font-bold' : 'text-neutral-900 dark:text-neutral-100'
                            }`}
                          >
                            {comm.title}
                          </span>
                        </div>
                      </td>

                      {/* Customer Name */}
                      <td className="py-3 px-4 text-neutral-600 dark:text-neutral-400">{comm.customer}</td>

                      {/* Owner Initials Avatar & First Name */}
                      <td className="py-3 px-4">
                        <div className="flex items-center gap-2">
                          <div
                            className={`w-5 h-5 rounded-full flex items-center justify-center text-[10px] font-bold ${
                              comm.owner.avatarColor || 'bg-neutral-100 dark:bg-neutral-800 text-neutral-700 dark:text-neutral-300'
                            }`}
                          >
                            {comm.owner.initials}
                          </div>
                          <span className="text-neutral-700 dark:text-neutral-300">{comm.owner.name.split(' ')[0]}</span>
                        </div>
                      </td>

                      {/* Promised by Date */}
                      <td className="py-3 px-4 text-neutral-600 dark:text-neutral-400 whitespace-nowrap">
                        {comm.promisedBy}
                      </td>

                      {/* Status Chip */}
                      <td className="py-3 px-5 text-right sm:text-left whitespace-nowrap">
                        <div className="flex items-center justify-between gap-2">
                          {renderStatusBadge(comm.status, comm.statusLabel)}
                          <ChevronRight className="w-3.5 h-3.5 text-neutral-400 dark:text-neutral-500 opacity-0 group-hover:opacity-100 transition-opacity hidden sm:inline" />
                        </div>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
