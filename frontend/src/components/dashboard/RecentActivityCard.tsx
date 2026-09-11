import React from 'react';
import { ArrowRight, FileText, CheckCircle2 } from 'lucide-react';
import { RecentActivityItem } from '../../types/dashboard';

interface RecentActivityCardProps {
  activities: RecentActivityItem[];
  onViewAll?: () => void;
}

export const RecentActivityCard: React.FC<RecentActivityCardProps> = ({
  activities,
  onViewAll,
}) => {
  // Render icon based on activity type
  const renderActivityIcon = (type: string) => {
    switch (type) {
      case 'jira':
        return (
          <div className="w-6 h-6 rounded-md bg-blue-500 flex items-center justify-center text-white shrink-0 shadow-2xs">
            {/* Jira blue diamond polygon */}
            <svg viewBox="0 0 24 24" className="w-3.5 h-3.5 fill-current">
              <path d="M11.53 2c0 2.4 1.97 4.35 4.35 4.35h1.77v1.74c0 2.4 1.97 4.35 4.35 4.35V2h-10.47zm-4.7 4.74c0 2.4 1.97 4.35 4.35 4.35h1.77v1.74c0 2.4 1.97 4.35 4.35 4.35V6.74H6.83zm-4.7 4.74c0 2.4 1.97 4.35 4.35 4.35h1.77v1.74c0 2.4 1.97 4.35 4.35 4.35V11.48H2.13z" />
            </svg>
          </div>
        );
      case 'meet':
        return (
          <div className="w-6 h-6 rounded-md bg-emerald-500 flex items-center justify-center text-white shrink-0 shadow-2xs">
            {/* Google Meet camera icon */}
            <svg viewBox="0 0 24 24" className="w-3.5 h-3.5 fill-current">
              <path d="M17 10.5V7c0-.55-.45-1-1-1H4c-.55 0-1 .45-1 1v10c0 .55.45 1 1 1h12c.55 0 1-.45 1-1v-3.5l4 4v-11l-4 4z" />
            </svg>
          </div>
        );
      case 'slack':
        return (
          <div className="w-6 h-6 rounded-md bg-emerald-600 flex items-center justify-center text-white shrink-0 shadow-2xs">
            <svg viewBox="0 0 24 24" className="w-3.5 h-3.5 fill-current">
              <path d="M6 15a2 2 0 1 1-2-2h2v2zm1 0a2 2 0 0 1 2-2 2 2 0 0 1 2 2v5a2 2 0 1 1-4 0v-5zm2-8a2 2 0 1 1-2 2V7h2zm0 1a2 2 0 0 1 2 2 2 2 0 0 1-2 2H2a2 2 0 1 1 0-4h5zm8 2a2 2 0 1 1 2 2h-2v-2zm-1 0a2 2 0 0 1-2 2 2 2 0 0 1-2-2V4a2 2 0 1 1 4 0v5zm-2 8a2 2 0 1 1 2-2v2h-2zm0-1a2 2 0 0 1-2-2 2 2 0 0 1 2-2h5a2 2 0 1 1 0 4h-5z" />
            </svg>
          </div>
        );
      case 'confirmation':
      default:
        return (
          <div className="w-6 h-6 rounded-md bg-neutral-100 border border-neutral-200 flex items-center justify-center text-neutral-600 shrink-0">
            <FileText className="w-3.5 h-3.5" />
          </div>
        );
    }
  };

  return (
    <div className="bg-white border border-neutral-200/90 rounded-xl p-4 sm:p-5 shadow-2xs mb-6">
      {/* Header */}
      <div className="flex items-center justify-between pb-3 mb-3 border-b border-neutral-100">
        <h3 className="text-sm font-semibold text-neutral-900">Recent activity</h3>
        <button
          onClick={onViewAll}
          className="inline-flex items-center gap-1 text-xs font-bold text-neutral-900 hover:text-neutral-700 underline transition-colors cursor-pointer"
        >
          <span>View all activity</span>
          <ArrowRight className="w-3 h-3" />
        </button>
      </div>

      {/* Activity List */}
      <div className="space-y-3">
        {activities.map((item) => (
          <div
            key={item.id}
            className="flex items-center justify-between text-xs py-1 hover:bg-neutral-50/60 rounded-md px-1 transition-colors"
          >
            <div className="flex items-center gap-2.5 min-w-0">
              {renderActivityIcon(item.type)}
              <span className="text-neutral-800 font-medium truncate">{item.title}</span>
            </div>
            <span className="text-neutral-400 shrink-0 ml-3 whitespace-nowrap text-[11px]">
              {item.source}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
};
