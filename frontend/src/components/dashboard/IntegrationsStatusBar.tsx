import React from 'react';
import { ArrowRight } from 'lucide-react';

interface IntegrationsStatusBarProps {
  onViewIntegrations: () => void;
}

export const IntegrationsStatusBar: React.FC<IntegrationsStatusBarProps> = ({
  onViewIntegrations,
}) => {
  return (
    <div className="bg-white border border-neutral-200/90 rounded-xl p-3 sm:px-5 sm:py-3.5 shadow-2xs flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs">
      {/* Connected items */}
      <div className="flex items-center flex-wrap gap-4 sm:gap-6 text-neutral-600">
        {/* Google Meet */}
        <div className="flex items-center gap-2">
          {/* Google Meet icon */}
          <div className="w-4 h-4 rounded-xs bg-emerald-500 flex items-center justify-center text-white shrink-0">
            <svg viewBox="0 0 24 24" className="w-2.5 h-2.5 fill-current">
              <path d="M17 10.5V7c0-.55-.45-1-1-1H4c-.55 0-1 .45-1 1v10c0 .55.45 1 1 1h12c.55 0 1-.45 1-1v-3.5l4 4v-11l-4 4z" />
            </svg>
          </div>
          <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
          <span className="font-medium text-neutral-800">Google Meet connected</span>
        </div>

        {/* Jira */}
        <div className="flex items-center gap-2">
          {/* Jira icon */}
          <div className="w-4 h-4 rounded-xs bg-blue-500 flex items-center justify-center text-white shrink-0">
            <svg viewBox="0 0 24 24" className="w-2.5 h-2.5 fill-current">
              <path d="M11.53 2c0 2.4 1.97 4.35 4.35 4.35h1.77v1.74c0 2.4 1.97 4.35 4.35 4.35V2h-10.47zm-4.7 4.74c0 2.4 1.97 4.35 4.35 4.35h1.77v1.74c0 2.4 1.97 4.35 4.35 4.35V6.74H6.83zm-4.7 4.74c0 2.4 1.97 4.35 4.35 4.35h1.77v1.74c0 2.4 1.97 4.35 4.35 4.35V11.48H2.13z" />
            </svg>
          </div>
          <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
          <span className="font-medium text-neutral-800">Jira synced 2 min ago</span>
        </div>

        {/* Slack */}
        <div className="flex items-center gap-2">
          {/* Slack icon */}
          <div className="w-4 h-4 rounded-xs bg-emerald-600 flex items-center justify-center text-white shrink-0">
            <svg viewBox="0 0 24 24" className="w-2.5 h-2.5 fill-current">
              <path d="M6 15a2 2 0 1 1-2-2h2v2zm1 0a2 2 0 0 1 2-2 2 2 0 0 1 2 2v5a2 2 0 1 1-4 0v-5zm2-8a2 2 0 1 1-2 2V7h2zm0 1a2 2 0 0 1 2 2 2 2 0 0 1-2 2H2a2 2 0 1 1 0-4h5zm8 2a2 2 0 1 1 2 2h-2v-2zm-1 0a2 2 0 0 1-2 2 2 2 0 0 1-2-2V4a2 2 0 1 1 4 0v5zm-2 8a2 2 0 1 1 2-2v2h-2zm0-1a2 2 0 0 1-2-2 2 2 0 0 1 2-2h5a2 2 0 1 1 0 4h-5z" />
            </svg>
          </div>
          <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
          <span className="font-medium text-neutral-800">Slack connected</span>
        </div>
      </div>

      {/* View Integrations Link */}
      <button
        onClick={onViewIntegrations}
        className="inline-flex items-center gap-1 font-bold text-neutral-900 hover:text-neutral-700 underline transition-colors cursor-pointer self-start sm:self-auto"
      >
        <span>View integrations</span>
        <ArrowRight className="w-3 h-3" />
      </button>
    </div>
  );
};
