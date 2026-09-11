import React from 'react';
import { ArrowRight } from 'lucide-react';
import { GoogleMeetLogo, JiraLogo, SlackLogo } from '../ui/BrandLogos';

interface IntegrationsStatusBarProps {
  onViewIntegrations: () => void;
}

export const IntegrationsStatusBar: React.FC<IntegrationsStatusBarProps> = ({
  onViewIntegrations,
}) => {
  return (
    <div className="bg-white dark:bg-neutral-900 border border-neutral-200/90 dark:border-neutral-800 rounded-xl p-3 sm:px-5 sm:py-3.5 shadow-2xs flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs">
      {/* Connected items */}
      <div className="flex items-center flex-wrap gap-4 sm:gap-6 text-neutral-600 dark:text-neutral-400">
        {/* Google Meet */}
        <div className="flex items-center gap-2">
          <div className="w-5 h-5 rounded-md bg-white dark:bg-neutral-800 border border-neutral-200/90 dark:border-neutral-700 flex items-center justify-center p-0.5 shrink-0 shadow-2xs">
            <GoogleMeetLogo className="w-3.5 h-3.5 shrink-0" />
          </div>
          <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
          <span className="font-medium text-neutral-800 dark:text-neutral-200">Google Meet connected</span>
        </div>

        {/* Jira */}
        <div className="flex items-center gap-2">
          <div className="w-5 h-5 rounded-md bg-white dark:bg-neutral-800 border border-neutral-200/90 dark:border-neutral-700 flex items-center justify-center p-0.5 shrink-0 shadow-2xs">
            <JiraLogo className="w-3.5 h-3.5 shrink-0" />
          </div>
          <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
          <span className="font-medium text-neutral-800 dark:text-neutral-200">Jira synced 2 min ago</span>
        </div>

        {/* Slack */}
        <div className="flex items-center gap-2">
          <div className="w-5 h-5 rounded-md bg-white dark:bg-neutral-800 border border-neutral-200/90 dark:border-neutral-700 flex items-center justify-center p-0.5 shrink-0 shadow-2xs">
            <SlackLogo className="w-3.5 h-3.5 shrink-0" />
          </div>
          <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
          <span className="font-medium text-neutral-800 dark:text-neutral-200">Slack connected</span>
        </div>
      </div>

      {/* View Integrations Link */}
      <button
        onClick={onViewIntegrations}
        className="inline-flex items-center gap-1 font-bold text-neutral-900 dark:text-white hover:text-neutral-700 dark:hover:text-neutral-300 underline transition-colors cursor-pointer self-start sm:self-auto"
      >
        <span>View integrations</span>
        <ArrowRight className="w-3 h-3" />
      </button>
    </div>
  );
};
