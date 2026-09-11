import React from 'react';
import {
  X,
  Calendar,
  ExternalLink,
  AlertTriangle,
  MessageSquare,
  FileText,
  Quote,
} from 'lucide-react';
import { Commitment } from '../../types/dashboard';
import { JiraLogo, LinearLogo } from '../ui/BrandLogos';

interface CommitmentDetailPanelProps {
  commitment: Commitment | null;
  onClose: () => void;
  onDraftCustomerUpdate: (commitment: Commitment) => void;
  onReviewCommitment: (commitment: Commitment) => void;
  onOpenTranscript?: (transcriptId?: string) => void;
}

export const CommitmentDetailPanel: React.FC<CommitmentDetailPanelProps> = ({
  commitment,
  onClose,
  onDraftCustomerUpdate,
  onReviewCommitment,
  onOpenTranscript,
}) => {
  if (!commitment) {
    return (
      <aside className="w-full xl:w-[380px] 2xl:w-[420px] bg-white dark:bg-neutral-900 border-l border-neutral-200 dark:border-neutral-800 p-6 flex flex-col items-center justify-center text-center text-neutral-400 dark:text-neutral-500">
        <FileText className="w-10 h-10 mb-3 text-neutral-300 dark:text-neutral-600 stroke-1" />
        <p className="text-sm font-medium">Select a commitment to view details</p>
      </aside>
    );
  }

  return (
    <aside className="w-full xl:w-[380px] 2xl:w-[420px] bg-white dark:bg-neutral-900 border-l border-neutral-200 dark:border-neutral-800 flex flex-col h-full overflow-y-auto">
      {/* Header */}
      <div className="p-5 border-b border-neutral-100 dark:border-neutral-800 flex items-center justify-between">
        <span className="text-[11px] font-bold uppercase tracking-wider text-neutral-400 dark:text-neutral-500">
          Commitment Details
        </span>
        <button
          onClick={onClose}
          className="p-1.5 rounded-lg border border-neutral-300 dark:border-neutral-700 hover:border-neutral-500 dark:hover:border-neutral-500 text-neutral-500 dark:text-neutral-400 hover:text-neutral-900 dark:hover:text-white hover:bg-neutral-100 dark:hover:bg-neutral-800 transition-all cursor-pointer"
          aria-label="Close details"
          title="Close details (Esc)"
        >
          <X className="w-4 h-4" />
        </button>
      </div>

      {/* Main Content Area */}
      <div className="p-5 space-y-5 flex-1">
        {/* Title & Badges */}
        <div>
          <h2 className="text-xl font-bold text-neutral-900 dark:text-white tracking-tight leading-snug">
            {commitment.title} for {commitment.customer}
          </h2>

          <div className="flex items-center gap-2 mt-2.5">
            {/* Status chip */}
            {commitment.status === 'at-risk' && (
              <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-amber-100/80 dark:bg-amber-950/40 text-amber-800 dark:text-amber-300 border border-amber-200/60 dark:border-amber-800/60">
                <span className="w-1.5 h-1.5 rounded-full bg-amber-500" />
                At risk
              </span>
            )}
            {commitment.status === 'overdue' && (
              <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-red-100/80 dark:bg-red-950/40 text-red-800 dark:text-red-300 border border-red-200/60 dark:border-red-800/60">
                <span className="w-1.5 h-1.5 rounded-full bg-red-500" />
                Overdue
              </span>
            )}
            {commitment.status === 'blocked' && (
              <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-orange-100/80 dark:bg-orange-950/40 text-orange-800 dark:text-orange-300 border border-orange-200/60 dark:border-orange-800/60">
                <span className="w-1.5 h-1.5 rounded-full bg-orange-500" />
                Blocked
              </span>
            )}
            {commitment.status === 'awaiting-review' && (
              <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-neutral-200/80 dark:bg-neutral-800 text-neutral-900 dark:text-neutral-200 border border-neutral-300 dark:border-neutral-700">
                <span className="w-1.5 h-1.5 rounded-full bg-neutral-600 dark:bg-neutral-400" />
                Awaiting review
              </span>
            )}

            {/* Confirmed chip */}
            {commitment.isConfirmed ? (
              <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-neutral-100 dark:bg-neutral-800 text-neutral-600 dark:text-neutral-300 border border-neutral-200/80 dark:border-neutral-700">
                Confirmed
              </span>
            ) : (
              <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-neutral-100 dark:bg-neutral-800 text-neutral-800 dark:text-neutral-200 border border-neutral-200 dark:border-neutral-700">
                Unreviewed draft
              </span>
            )}
          </div>
        </div>

        {/* Owner & Promised Date Attributes */}
        <div className="grid grid-cols-2 gap-4 py-3 border-y border-neutral-100 dark:border-neutral-800 text-xs">
          {/* Owner */}
          <div>
            <div className="text-[11px] text-neutral-400 dark:text-neutral-500 font-medium mb-1.5">Owner</div>
            <div className="flex items-center gap-2">
              <div
                className={`w-6 h-6 rounded-full flex items-center justify-center text-[10px] font-bold ${
                  commitment.owner.avatarColor ? 'bg-neutral-200 dark:bg-neutral-800 text-neutral-800 dark:text-neutral-200' : 'bg-neutral-200 dark:bg-neutral-800 text-neutral-800 dark:text-neutral-200'
                }`}
              >
                {commitment.owner.initials}
              </div>
              <span className="font-semibold text-neutral-800 dark:text-neutral-200">{commitment.owner.name}</span>
            </div>
          </div>

          {/* Promised Date */}
          <div>
            <div className="text-[11px] text-neutral-400 dark:text-neutral-500 font-medium mb-1.5">Promised date</div>
            <div className="flex items-center gap-1.5 text-neutral-800 dark:text-neutral-200 font-semibold">
              <Calendar className="w-3.5 h-3.5 text-neutral-400 dark:text-neutral-500" />
              <span>{commitment.promisedBy}</span>
            </div>
          </div>
        </div>

        {/* Original Promise Excerpt */}
        <div className="space-y-1.5">
          <div className="text-xs font-semibold text-neutral-900 dark:text-white">Original promise</div>
          <div className="bg-neutral-50/80 dark:bg-neutral-800/60 border border-neutral-200/70 dark:border-neutral-700/80 rounded-xl p-3.5 relative">
            <Quote className="w-4 h-4 text-neutral-300 dark:text-neutral-600 absolute top-3 left-3 -scale-x-100" />
            <div className="pl-5">
              <p className="text-xs text-neutral-700 dark:text-neutral-300 italic leading-relaxed">
                "{commitment.originalPromise.quote}"
              </p>
              <div className="flex items-center justify-between mt-2.5 text-[11px] text-neutral-400 dark:text-neutral-500 pt-2 border-t border-neutral-200/50 dark:border-neutral-700/50">
                <span>
                  {commitment.originalPromise.sourceTitle} · {commitment.originalPromise.timestamp}
                </span>
                <button
                  onClick={() => onOpenTranscript && onOpenTranscript(commitment.originalPromise.transcriptId)}
                  className="text-neutral-900 dark:text-white hover:text-neutral-700 dark:hover:text-neutral-300 font-bold inline-flex items-center gap-0.5 cursor-pointer underline"
                >
                  <span>Open transcript</span>
                  <ExternalLink className="w-2.5 h-2.5" />
                </button>
              </div>
            </div>
          </div>
        </div>

        {/* Engineering Evidence */}
        {commitment.engineeringEvidence && (
          <div className="space-y-1.5">
            <div className="text-xs font-semibold text-neutral-900 dark:text-white">Engineering evidence</div>
            <div className="bg-neutral-50/80 dark:bg-neutral-800/60 border border-neutral-200/70 dark:border-neutral-700/80 rounded-xl p-3.5">
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-2">
                  <div className="w-5 h-5 rounded-md bg-white dark:bg-neutral-800 border border-neutral-200/90 dark:border-neutral-700 flex items-center justify-center p-0.5 shrink-0 shadow-2xs">
                    {commitment.engineeringEvidence.provider === 'linear' ? (
                      <LinearLogo className="w-3.5 h-3.5 shrink-0" />
                    ) : (
                      <JiraLogo className="w-3.5 h-3.5 shrink-0" />
                    )}
                  </div>
                  <span className="font-bold text-xs text-neutral-800 dark:text-neutral-200">
                    {commitment.engineeringEvidence.ticketId} · {commitment.engineeringEvidence.ticketTitle}
                  </span>
                </div>
              </div>

              <div className="pl-6 space-y-1 text-xs">
                <div>
                  <span className="inline-block px-2 py-0.5 rounded-md bg-neutral-200 dark:bg-neutral-700 text-neutral-800 dark:text-neutral-200 font-semibold text-[11px]">
                    {commitment.engineeringEvidence.status}
                  </span>
                </div>
                <div className="text-[11px] text-neutral-500 dark:text-neutral-400 pt-1">
                  Target delivery: <span className="font-semibold text-neutral-700 dark:text-neutral-300">{commitment.engineeringEvidence.targetDelivery}</span>
                </div>
                <div className="flex items-center justify-between text-[11px] text-neutral-400 dark:text-neutral-500 pt-1">
                  <span>Synced {commitment.engineeringEvidence.syncedAt}</span>
                  <a
                    href={commitment.engineeringEvidence.ticketUrl || '#'}
                    target="_blank"
                    rel="noreferrer"
                    className="text-neutral-900 dark:text-white hover:text-neutral-700 dark:hover:text-neutral-300 font-bold inline-flex items-center gap-0.5 underline"
                  >
                    <span>Open ticket</span>
                    <ExternalLink className="w-2.5 h-2.5" />
                  </a>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Conflict Warning Alert Box */}
        {commitment.risk?.hasConflict && (
          <div className="bg-amber-50 dark:bg-amber-950/30 border border-amber-200/80 dark:border-amber-800/50 rounded-xl p-3.5 text-xs">
            <div className="flex items-start gap-2.5">
              <AlertTriangle className="w-4 h-4 text-amber-600 dark:text-amber-400 shrink-0 mt-0.5" />
              <div>
                <h4 className="font-bold text-amber-900 dark:text-amber-200 mb-0.5">
                  {commitment.risk.conflictTitle || 'Delivery date conflict'}
                </h4>
                <p className="text-amber-800 dark:text-amber-300/90 leading-relaxed text-[11px]">
                  {commitment.risk.conflictDescription}
                </p>
              </div>
            </div>
          </div>
        )}

        {/* Recommended Next Step */}
        {commitment.recommendedNextStep && (
          <div className="space-y-1.5">
            <div className="text-xs font-semibold text-neutral-900 dark:text-white">Recommended next step</div>
            <div className="flex items-center gap-2 p-3 bg-neutral-50/60 dark:bg-neutral-800/50 border border-neutral-200/70 dark:border-neutral-700/70 rounded-xl text-xs text-neutral-700 dark:text-neutral-300">
              <MessageSquare className="w-4 h-4 text-neutral-400 dark:text-neutral-500 shrink-0" />
              <span className="leading-snug">{commitment.recommendedNextStep.text}</span>
            </div>
          </div>
        )}
      </div>

      {/* Action Buttons Footer */}
      <div className="p-5 border-t border-neutral-100 dark:border-neutral-800 bg-white dark:bg-neutral-900 space-y-2">
        <button
          onClick={() => onDraftCustomerUpdate(commitment)}
          className="w-full py-2.5 px-4 bg-neutral-900 dark:bg-white text-white dark:text-neutral-900 font-medium text-xs rounded-lg hover:bg-neutral-800 dark:hover:bg-neutral-200 transition-all shadow-xs active:scale-99 cursor-pointer"
        >
          Draft customer update
        </button>

        <button
          onClick={() => onReviewCommitment(commitment)}
          className="w-full py-2.5 px-4 bg-white dark:bg-neutral-800 border border-neutral-300 dark:border-neutral-700 text-neutral-800 dark:text-neutral-200 font-medium text-xs rounded-lg hover:bg-neutral-50 dark:hover:bg-neutral-750 transition-all shadow-2xs active:scale-99 cursor-pointer"
        >
          Review commitment
        </button>

        <div className="text-center pt-1">
          <span className="text-[10px] text-neutral-400 dark:text-neutral-500">
            Customer messages require approval.
          </span>
        </div>
      </div>
    </aside>
  );
};
