import React from 'react';
import { ListTodo, CheckCircle2, XCircle, FileEdit, Quote, ExternalLink } from 'lucide-react';
import { Commitment } from '../../types/dashboard';

interface ReviewQueueViewProps {
  commitments: Commitment[];
  onConfirm: (id: string) => void;
  onReject: (id: string) => void;
  onSelectCommitment: (comm: Commitment) => void;
}

export const ReviewQueueView: React.FC<ReviewQueueViewProps> = ({
  commitments,
  onConfirm,
  onReject,
  onSelectCommitment,
}) => {
  const unreviewed = commitments.filter((c) => c.category === 'awaiting-review');

  return (
    <div className="flex-1 p-4 sm:p-6 lg:p-8 overflow-y-auto max-w-6xl mx-auto w-full">
      <div className="pb-6 border-b border-neutral-200">
        <div className="flex items-center gap-3">
          <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-neutral-900">
            Commitment Review Queue
          </h1>
          <span className="px-2.5 py-0.5 rounded-full bg-neutral-900 text-white font-bold text-xs">
            {unreviewed.length} pending
          </span>
        </div>
        <p className="text-xs sm:text-sm text-neutral-500 mt-1">
          Verify AI-extracted candidate promises from customer conversations before confirming.
        </p>
      </div>

      {unreviewed.length === 0 ? (
        <div className="text-center py-16 bg-white border border-neutral-200 rounded-2xl mt-6">
          <CheckCircle2 className="w-12 h-12 text-emerald-500 mx-auto mb-3" />
          <h3 className="font-bold text-neutral-900 text-base">Review Queue is Clear</h3>
          <p className="text-xs text-neutral-500 max-w-md mx-auto mt-1">
            All extracted candidate promises have been reviewed and verified. New candidate promises
            will automatically appear here when meetings or emails are processed.
          </p>
        </div>
      ) : (
        <div className="space-y-4 mt-6">
          {unreviewed.map((comm) => (
            <div
              key={comm.id}
              className="bg-white border border-neutral-200/90 rounded-2xl p-5 shadow-2xs hover:border-neutral-300 transition-all flex flex-col md:flex-row md:items-center justify-between gap-5"
            >
              {/* Left Details */}
              <div className="space-y-2 flex-1">
                <div className="flex items-center gap-2">
                  <span className="text-xs font-semibold px-2 py-0.5 rounded-md bg-neutral-200 text-neutral-800">
                    Candidate Promise
                  </span>
                  <span className="text-xs text-neutral-400 font-medium">
                    Customer: <strong className="text-neutral-700">{comm.customer}</strong>
                  </span>
                  <span className="text-xs text-neutral-400 font-medium">
                    Owner: <strong className="text-neutral-700">{comm.owner.name}</strong>
                  </span>
                  <span className="text-xs text-neutral-400 font-medium">
                    Target: <strong className="text-neutral-700">{comm.promisedBy}</strong>
                  </span>
                </div>

                <h3 className="font-bold text-base text-neutral-900">{comm.title}</h3>

                <div className="p-3 bg-neutral-50 rounded-xl border border-neutral-200/70 text-xs text-neutral-700 italic flex items-start gap-2">
                  <Quote className="w-4 h-4 text-neutral-400 shrink-0 mt-0.5" />
                  <span>"{comm.originalPromise.quote}"</span>
                </div>

                <div className="text-[11px] text-neutral-400">
                  Source: {comm.originalPromise.sourceTitle} · {comm.originalPromise.timestamp}
                </div>
              </div>

              {/* Action Buttons */}
              <div className="flex items-center gap-2 shrink-0 self-end md:self-center">
                <button
                  onClick={() => onReject(comm.id)}
                  className="inline-flex items-center gap-1.5 px-3 py-2 text-xs font-medium text-neutral-600 bg-white border border-neutral-200 rounded-lg hover:bg-neutral-50 transition-colors cursor-pointer"
                >
                  <XCircle className="w-4 h-4 text-neutral-400" />
                  <span>Dismiss</span>
                </button>

                <button
                  onClick={() => onSelectCommitment(comm)}
                  className="inline-flex items-center gap-1.5 px-3 py-2 text-xs font-medium text-neutral-900 bg-neutral-100 border border-neutral-300 rounded-lg hover:bg-neutral-200 transition-colors cursor-pointer"
                >
                  <FileEdit className="w-4 h-4" />
                  <span>Inspect terms</span>
                </button>

                <button
                  onClick={() => onConfirm(comm.id)}
                  className="inline-flex items-center gap-1.5 px-3.5 py-2 text-xs font-semibold text-white bg-neutral-900 rounded-lg hover:bg-neutral-800 transition-colors shadow-xs cursor-pointer"
                >
                  <CheckCircle2 className="w-4 h-4" />
                  <span>Confirm commitment</span>
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
