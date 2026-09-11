import React, { useState } from 'react';
import {
  Cable,
  CheckCircle2,
  Settings2,
  ExternalLink,
  Plus,
  RefreshCw,
} from 'lucide-react';
import { Integration, Workspace } from '../../types/dashboard';
import { BrandLogo } from '../ui/BrandLogos';

interface IntegrationsViewProps {
  workspace: Workspace;
  integrations: Integration[];
  onConfigureSlack: () => void;
  onOpenMobileMenu: () => void;
}

export const IntegrationsView: React.FC<IntegrationsViewProps> = ({
  workspace,
  integrations,
  onConfigureSlack,
  onOpenMobileMenu,
}) => {
  const [filter, setFilter] = useState<'all' | 'connected' | 'available'>('all');

  const filteredIntegrations = integrations.filter((item) => {
    if (filter === 'connected') return item.connected;
    if (filter === 'available') return !item.connected;
    return true;
  });

  return (
    <div className="flex-1 p-4 sm:p-6 lg:p-8 overflow-y-auto max-w-6xl mx-auto w-full">
      {/* Page Header */}
      <div className="pb-6 border-b border-neutral-200 dark:border-neutral-800">
        <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-neutral-900 dark:text-white">
          Workspace Integrations
        </h1>
        <p className="text-xs sm:text-sm text-neutral-500 dark:text-neutral-400 mt-1">
          Connect and isolate external sources, meeting providers, and alert destinations.
        </p>
      </div>

      {/* Tabs */}
      <div className="flex items-center gap-2 mt-6 mb-6">
        {(['all', 'connected', 'available'] as const).map((tab) => (
          <button
            key={tab}
            onClick={() => setFilter(tab)}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold capitalize transition-all cursor-pointer ${
              filter === tab
                ? 'bg-neutral-900 dark:bg-white text-white dark:text-neutral-900 shadow-2xs'
                : 'bg-white dark:bg-neutral-800 text-neutral-600 dark:text-neutral-300 border border-neutral-200 dark:border-neutral-700 hover:bg-neutral-50 dark:hover:bg-neutral-750'
            }`}
          >
            {tab}
          </button>
        ))}
      </div>

      {/* Integrations Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {filteredIntegrations.map((item) => (
          <div
            key={item.id}
            className="bg-white dark:bg-neutral-900 border border-neutral-200/90 dark:border-neutral-800 rounded-2xl p-5 shadow-2xs flex flex-col justify-between hover:border-neutral-300 dark:hover:border-neutral-700 transition-all"
          >
            {/* Top info */}
            <div>
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-2.5">
                  {/* Provider Real Logo Icon */}
                  <div className="w-10 h-10 rounded-xl bg-white dark:bg-neutral-800 border border-neutral-200/90 dark:border-neutral-700 flex items-center justify-center p-2 shadow-2xs shrink-0">
                    <BrandLogo provider={item.provider} className="w-6 h-6 shrink-0" />
                  </div>

                  <div>
                    <h3 className="font-bold text-sm text-neutral-900 dark:text-white">{item.name}</h3>
                    <div className="flex items-center gap-1.5 text-[11px]">
                      {item.connected ? (
                        <>
                          <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
                          <span className="text-emerald-700 dark:text-emerald-400 font-semibold">Connected</span>
                        </>
                      ) : (
                        <>
                          <span className="w-1.5 h-1.5 rounded-full bg-neutral-300 dark:bg-neutral-600" />
                          <span className="text-neutral-400 dark:text-neutral-500">Not configured</span>
                        </>
                      )}
                    </div>
                  </div>
                </div>
              </div>

              <p className="text-xs text-neutral-600 dark:text-neutral-300 leading-relaxed mb-4">{item.description}</p>

              {item.channelOrScope && (
                <div className="mb-4 px-2.5 py-1.5 rounded-lg bg-neutral-50 dark:bg-neutral-800/60 border border-neutral-200/80 dark:border-neutral-700 text-[11px] text-neutral-600 dark:text-neutral-300 flex items-center justify-between">
                  <span className="text-neutral-400 dark:text-neutral-500 font-medium">Channel / Scope:</span>
                  <span className="font-semibold text-neutral-800 dark:text-neutral-200">{item.channelOrScope}</span>
                </div>
              )}
            </div>

            {/* Bottom Actions */}
            <div className="pt-3 border-t border-neutral-100 dark:border-neutral-800 flex items-center justify-between">
              <span className="text-[10px] text-neutral-400 dark:text-neutral-500">{item.lastSync || 'Never synced'}</span>

              {item.provider === 'slack' ? (
                <button
                  onClick={onConfigureSlack}
                  className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold bg-neutral-100 dark:bg-neutral-800 text-neutral-900 dark:text-white hover:bg-neutral-200 dark:hover:bg-neutral-700 border border-neutral-200 dark:border-neutral-700 transition-colors cursor-pointer"
                >
                  <Settings2 className="w-3.5 h-3.5" />
                  <span>Configure Slack</span>
                </button>
              ) : item.connected ? (
                <button className="inline-flex items-center gap-1 text-xs font-semibold text-neutral-600 dark:text-neutral-300 hover:text-neutral-900 dark:hover:text-white cursor-pointer">
                  <span>Manage</span>
                  <ExternalLink className="w-3 h-3" />
                </button>
              ) : (
                <button className="inline-flex items-center gap-1 px-3 py-1.5 rounded-lg text-xs font-semibold bg-neutral-900 dark:bg-white text-white dark:text-neutral-900 hover:bg-neutral-800 dark:hover:bg-neutral-200 transition-colors cursor-pointer">
                  <Plus className="w-3.5 h-3.5" />
                  <span>Connect</span>
                </button>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
