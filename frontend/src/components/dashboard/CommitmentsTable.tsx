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
          <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-amber-100/70 text-amber-800 border border-amber-200/60">
            <span className="w-1.5 h-1.5 rounded-full bg-amber-500" />
            {label}
          </span>
        );
      case 'overdue':
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-red-100/70 text-red-800 border border-red-200/60">
            <span className="w-1.5 h-1.5 rounded-full bg-red-500" />
            {label}
          </span>
        );
      case 'blocked':
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-orange-100/70 text-orange-800 border border-orange-200/60">
            <span className="w-1.5 h-1.5 rounded-full bg-orange-500" />
            {label}
          </span>
        );
      case 'awaiting-review':
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-neutral-200/80 text-neutral-900 border border-neutral-300">
            <span className="w-1.5 h-1.5 rounded-full bg-neutral-600" />
            {label}
          </span>
        );
      case 'delivered':
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-100/70 text-emerald-800 border border-emerald-200/60">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
            {label}
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-neutral-100 text-neutral-700 border border-neutral-200">
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
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-neutral-200 pb-3 mb-4">
        {/* Navigation Tabs */}
        <div className="flex items-center gap-6 overflow-x-auto no-scrollbar">
          <button
            onClick={() => onTabChange('all')}
            className={`flex items-center gap-1.5 text-xs sm:text-sm font-medium pb-2 -mb-3 transition-colors whitespace-nowrap cursor-pointer ${
              activeTab === 'all'
                ? 'text-neutral-900 border-b-2 border-neutral-900 font-bold'
                : 'text-neutral-500 hover:text-neutral-800'
            }`}
          >
            <span>All</span>
            <span className="text-xs text-neutral-400 font-normal">{allCount}</span>
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
                ? 'text-neutral-900 border-b-2 border-neutral-900 font-bold'
                : 'text-neutral-500 hover:text-neutral-800'
            }`}
          >
            <span>Needs attention</span>
            <span
              className={`text-xs px-1.5 py-0.2 rounded-full font-bold ${
                activeTab === 'needs-attention'
                  ? 'bg-neutral-200 text-neutral-900'
                  : 'text-neutral-400'
              }`}
            >
              {needsAttentionCount}
            </span>
          </button>

          <button
            onClick={() => onTabChange('awaiting-review')}
            className={`flex items-center gap-1.5 text-xs sm:text-sm font-medium pb-2 -mb-3 transition-colors whitespace-nowrap cursor-pointer ${
              activeTab === 'awaiting-review'
                ? 'text-neutral-900 border-b-2 border-neutral-900 font-bold'
                : 'text-neutral-500 hover:text-neutral-800'
            }`}
          >
            <span>Awaiting review</span>
            <span className="text-xs text-neutral-400 font-normal">{awaitingReviewCount}</span>
          </button>
        </div>

        {/* Dropdown Filters */}
        <div className="flex items-center gap-2 relative">
          {/* Owner Filter */}
          <div className="relative">
            <button
              onClick={() => setOwnerDropdownOpen(!ownerDropdownOpen)}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-neutral-700 bg-white border border-neutral-200 rounded-lg hover:bg-neutral-50 transition-colors cursor-pointer"
            >
              <span>{ownerFilter === 'all' ? 'All owners' : ownerFilter}</span>
              <ChevronDown className="w-3 h-3 text-neutral-400" />
            </button>

            {ownerDropdownOpen && (
              <div className="absolute right-0 mt-1 w-44 bg-white border border-neutral-200 rounded-lg shadow-md z-30 py-1 text-xs">
                <button
                  onClick={() => {
                    setOwnerFilter('all');
                    setOwnerDropdownOpen(false);
                  }}
                  className="w-full text-left px-3 py-1.5 hover:bg-neutral-50 text-neutral-700 font-medium"
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
                    className="w-full text-left px-3 py-1.5 hover:bg-neutral-50 text-neutral-700"
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
              className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-neutral-700 bg-white border border-neutral-200 rounded-lg hover:bg-neutral-50 transition-colors cursor-pointer"
            >
              <CalendarIcon className="w-3 h-3 text-neutral-400" />
              <span>{dateFilter === 'any' ? 'Any date' : dateFilter}</span>
              <ChevronDown className="w-3 h-3 text-neutral-400" />
            </button>

            {dateDropdownOpen && (
              <div className="absolute right-0 mt-1 w-40 bg-white border border-neutral-200 rounded-lg shadow-md z-30 py-1 text-xs">
                {['Any date', 'This week', 'This month', 'Next 30 days', 'Overdue only'].map(
                  (opt) => (
                    <button
                      key={opt}
                      onClick={() => {
                        setDateFilter(opt);
                        setDateDropdownOpen(false);
                      }}
                      className="w-full text-left px-3 py-1.5 hover:bg-neutral-50 text-neutral-700"
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
      <div className="bg-white border border-neutral-200/90 rounded-xl shadow-2xs overflow-hidden">
        {/* Table Title Bar */}
        <div
          onClick={() => {
            const firstAttention = commitments.find((c) => c.category === 'needs-attention') || commitments[0];
            if (firstAttention) {
              onSelectCommitment(firstAttention);
            }
          }}
          className="px-5 py-3.5 border-b border-neutral-100 flex items-center justify-between cursor-pointer hover:bg-neutral-50/70 transition-colors group"
          title="Click to view commitment details"
        >
          <h2 className="text-sm font-semibold text-neutral-900 group-hover:text-neutral-950 transition-colors">
            {getSectionTitle()}
          </h2>
          <span className="text-[11px] text-neutral-400 group-hover:text-neutral-600 font-normal transition-colors hidden sm:inline">
            Click any row to view details &rarr;
          </span>
        </div>

        {/* Responsive Table */}
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse min-w-[550px]">
            <thead>
              <tr className="border-b border-neutral-100 text-[11px] font-medium text-neutral-400 uppercase tracking-wider bg-neutral-50/50">
                <th className="py-2.5 px-5 font-medium">
                  <div className="flex items-center gap-1 cursor-pointer hover:text-neutral-700">
                    <span>Commitment</span>
                    <ArrowUpDown className="w-3 h-3" />
                  </div>
                </th>
                <th className="py-2.5 px-4 font-medium">Customer</th>
                <th className="py-2.5 px-4 font-medium">Owner</th>
                <th className="py-2.5 px-4 font-medium">
                  <div className="flex items-center gap-1 cursor-pointer hover:text-neutral-700">
                    <span>Promised by</span>
                    <ArrowUpDown className="w-3 h-3" />
                  </div>
                </th>
                <th className="py-2.5 px-5 font-medium text-right sm:text-left">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-neutral-100 text-xs sm:text-sm">
              {filteredCommitments.length === 0 ? (
                <tr>
                  <td colSpan={5} className="py-8 text-center text-neutral-400 text-xs">
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
                          ? 'bg-neutral-100/90 border-l-4 border-l-neutral-900'
                          : 'hover:bg-neutral-50/80'
                      }`}
                    >
                      {/* Commitment Title */}
                      <td className="py-3 px-5">
                        <div className="flex items-center gap-2.5">
                          <FileText
                            className={`w-4 h-4 shrink-0 ${
                              isSelected ? 'text-neutral-900' : 'text-neutral-400 group-hover:text-neutral-600'
                            }`}
                          />
                          <span
                            className={`font-medium ${
                              isSelected ? 'text-neutral-950 font-bold' : 'text-neutral-900'
                            }`}
                          >
                            {comm.title}
                          </span>
                        </div>
                      </td>

                      {/* Customer Name */}
                      <td className="py-3 px-4 text-neutral-600">{comm.customer}</td>

                      {/* Owner Initials Avatar & First Name */}
                      <td className="py-3 px-4">
                        <div className="flex items-center gap-2">
                          <div
                            className={`w-5 h-5 rounded-full flex items-center justify-center text-[10px] font-bold ${
                              comm.owner.avatarColor || 'bg-neutral-100 text-neutral-700'
                            }`}
                          >
                            {comm.owner.initials}
                          </div>
                          <span className="text-neutral-700">{comm.owner.name.split(' ')[0]}</span>
                        </div>
                      </td>

                      {/* Promised by Date */}
                      <td className="py-3 px-4 text-neutral-600 whitespace-nowrap">
                        {comm.promisedBy}
                      </td>

                      {/* Status Chip */}
                      <td className="py-3 px-5 text-right sm:text-left whitespace-nowrap">
                        <div className="flex items-center justify-between gap-2">
                          {renderStatusBadge(comm.status, comm.statusLabel)}
                          <ChevronRight className="w-3.5 h-3.5 text-neutral-400 opacity-0 group-hover:opacity-100 transition-opacity hidden sm:inline" />
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
