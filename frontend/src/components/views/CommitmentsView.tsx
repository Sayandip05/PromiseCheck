import React from 'react';
import { Header } from '../dashboard/Header';
import { MetricCards } from '../dashboard/MetricCards';
import { CommitmentsTable } from '../dashboard/CommitmentsTable';
import { RecentActivityCard } from '../dashboard/RecentActivityCard';
import { IntegrationsStatusBar } from '../dashboard/IntegrationsStatusBar';
import { CommitmentDetailPanel } from '../dashboard/CommitmentDetailPanel';
import { Commitment, RecentActivityItem } from '../../types/dashboard';

interface CommitmentsViewProps {
  commitments: Commitment[];
  selectedCommitment: Commitment | null;
  onSelectCommitment: (comm: Commitment) => void;
  activeTab: string;
  onTabChange: (tab: string) => void;
  activities: RecentActivityItem[];
  onOpenUpload: () => void;
  onOpenAddCommitment: () => void;
  onOpenMobileMenu: () => void;
  onViewIntegrations: () => void;
  onDraftCustomerUpdate: (comm: Commitment) => void;
  onReviewCommitment: (comm: Commitment) => void;
  isDetailOpen: boolean;
  onCloseDetail: () => void;
  onOpenDetail: () => void;
}

export const CommitmentsView: React.FC<CommitmentsViewProps> = ({
  commitments,
  selectedCommitment,
  onSelectCommitment,
  activeTab,
  onTabChange,
  activities,
  onOpenUpload,
  onOpenAddCommitment,
  onOpenMobileMenu,
  onViewIntegrations,
  onDraftCustomerUpdate,
  onReviewCommitment,
  isDetailOpen,
  onCloseDetail,
  onOpenDetail,
}) => {
  const needsAttentionCount = commitments.filter((c) => c.category === 'needs-attention').length;
  const awaitingReviewCount = commitments.filter((c) => c.category === 'awaiting-review').length;
  const deliveredCount = commitments.filter((c) => c.category === 'delivered').length;

  React.useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isDetailOpen) {
        onCloseDetail();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isDetailOpen, onCloseDetail]);

  return (
    <div className="flex-1 flex flex-col xl:flex-row min-h-0 relative">
      {/* Customer Commitments Main Content (Centered / Approx Middle) */}
      <div className="flex-1 min-w-0 p-4 sm:p-6 lg:p-8 overflow-y-auto max-w-6xl w-full mx-auto">
        {/* Top Header */}
        <Header
          title="Customer commitments"
          subtitle="Track every promise from conversation to delivery."
          dateStr="As of Sep 24, 2026"
          onOpenUpload={onOpenUpload}
          onOpenAddCommitment={onOpenAddCommitment}
          onOpenMobileMenu={onOpenMobileMenu}
        />

        {/* 4 Metric KPI Cards */}
        <MetricCards
          activeCount={commitments.length}
          needsAttentionCount={needsAttentionCount}
          awaitingReviewCount={awaitingReviewCount}
          deliveredCount={deliveredCount}
          selectedCategory={activeTab}
          onSelectCategory={(cat) => {
            onTabChange(cat);
            if (cat === 'needs-attention') {
              const firstAttention =
                commitments.find((c) => c.category === 'needs-attention') || commitments[0];
              if (firstAttention) {
                onSelectCommitment(firstAttention);
                onOpenDetail();
              }
            }
          }}
        />

        {/* Commitments Table */}
        <CommitmentsTable
          commitments={commitments}
          selectedCommitmentId={isDetailOpen ? selectedCommitment?.id || null : null}
          onSelectCommitment={(comm) => {
            onSelectCommitment(comm);
            onOpenDetail();
          }}
          activeTab={activeTab}
          onTabChange={onTabChange}
          allCount={commitments.length}
          needsAttentionCount={needsAttentionCount}
          awaitingReviewCount={awaitingReviewCount}
        />

        {/* Recent Activity Card */}
        <RecentActivityCard
          activities={activities}
          onViewAll={() => console.log('View all activity')}
        />

        {/* Bottom Connected Integrations Status Bar */}
        <IntegrationsStatusBar onViewIntegrations={onViewIntegrations} />
      </div>

      {/* Desktop Right Inspector Panel (Pops up from the right side) */}
      {isDetailOpen && selectedCommitment && (
        <div className="hidden xl:block shrink-0 sticky top-16 h-[calc(100vh-4rem)] animate-slide-in-right self-start z-20">
          <CommitmentDetailPanel
            commitment={selectedCommitment}
            onClose={onCloseDetail}
            onDraftCustomerUpdate={onDraftCustomerUpdate}
            onReviewCommitment={onReviewCommitment}
          />
        </div>
      )}

      {/* Mobile / Tablet Drawer Inspector (Pops up from the right side) */}
      {isDetailOpen && selectedCommitment && (
        <div className="fixed inset-0 z-50 xl:hidden">
          {/* Backdrop */}
          <div
            className="fixed inset-0 bg-neutral-900/50 backdrop-blur-xs transition-opacity"
            onClick={onCloseDetail}
          />
          {/* Drawer Container on the right */}
          <div className="fixed inset-y-0 right-0 max-w-full sm:max-w-md w-full bg-white shadow-2xl z-50 flex flex-col animate-slide-in-right duration-300 border-l border-neutral-200">
            <CommitmentDetailPanel
              commitment={selectedCommitment}
              onClose={onCloseDetail}
              onDraftCustomerUpdate={(comm) => {
                onCloseDetail();
                onDraftCustomerUpdate(comm);
              }}
              onReviewCommitment={(comm) => {
                onCloseDetail();
                onReviewCommitment(comm);
              }}
            />
          </div>
        </div>
      )}
    </div>
  );
};
