import React from 'react';
import { ArrowRight, FileText, CheckCircle2 } from 'lucide-react';
import { RecentActivityItem } from '../../types/dashboard';
import { GoogleMeetLogo, JiraLogo, SlackLogo, LinearLogo, GmailLogo } from '../ui/BrandLogos';

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
          <div className="w-6 h-6 rounded-md bg-white dark:bg-neutral-800 border border-neutral-200/90 dark:border-neutral-700 flex items-center justify-center p-1 shrink-0 shadow-2xs">
            <JiraLogo className="w-4 h-4 shrink-0" />
          </div>
        );
      case 'meet':
        return (
          <div className="w-6 h-6 rounded-md bg-white dark:bg-neutral-800 border border-neutral-200/90 dark:border-neutral-700 flex items-center justify-center p-1 shrink-0 shadow-2xs">
            <GoogleMeetLogo className="w-4 h-4 shrink-0" />
          </div>
        );
      case 'slack':
        return (
          <div className="w-6 h-6 rounded-md bg-white dark:bg-neutral-800 border border-neutral-200/90 dark:border-neutral-700 flex items-center justify-center p-1 shrink-0 shadow-2xs">
            <SlackLogo className="w-4 h-4 shrink-0" />
          </div>
        );
      case 'linear':
        return (
          <div className="w-6 h-6 rounded-md bg-white dark:bg-neutral-800 border border-neutral-200/90 dark:border-neutral-700 flex items-center justify-center p-1 shrink-0 shadow-2xs">
            <LinearLogo className="w-4 h-4 shrink-0" />
          </div>
        );
      case 'gmail':
        return (
          <div className="w-6 h-6 rounded-md bg-white dark:bg-neutral-800 border border-neutral-200/90 dark:border-neutral-700 flex items-center justify-center p-1 shrink-0 shadow-2xs">
            <GmailLogo className="w-4 h-4 shrink-0" />
          </div>
        );
      case 'confirmation':
      default:
        return (
          <div className="w-6 h-6 rounded-md bg-neutral-100 dark:bg-neutral-800 border border-neutral-200 dark:border-neutral-700 flex items-center justify-center text-neutral-600 dark:text-neutral-300 shrink-0">
            <FileText className="w-3.5 h-3.5" />
          </div>
        );
    }
  };

  return (
    <div className="bg-white dark:bg-neutral-900 border border-neutral-200/90 dark:border-neutral-800 rounded-xl p-4 sm:p-5 shadow-2xs mb-6">
      {/* Header */}
      <div className="flex items-center justify-between pb-3 mb-3 border-b border-neutral-100 dark:border-neutral-800">
        <h3 className="text-sm font-semibold text-neutral-900 dark:text-white">Recent activity</h3>
        <button
          onClick={onViewAll}
          className="inline-flex items-center gap-1 text-xs font-bold text-neutral-900 dark:text-white hover:text-neutral-700 dark:hover:text-neutral-300 underline transition-colors cursor-pointer"
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
            className="flex items-center justify-between text-xs py-1 hover:bg-neutral-50/60 dark:hover:bg-neutral-800/60 rounded-md px-1 transition-colors"
          >
            <div className="flex items-center gap-2.5 min-w-0">
              {renderActivityIcon(item.type)}
              <span className="text-neutral-800 dark:text-neutral-200 font-medium truncate">{item.title}</span>
            </div>
            <span className="text-neutral-400 dark:text-neutral-500 shrink-0 ml-3 whitespace-nowrap text-[11px]">
              {item.source}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
};
