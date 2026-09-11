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
      <div className="pb-6 border-b border-neutral-200">
        <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-neutral-900">
          Workspace Integrations
        </h1>
        <p className="text-xs sm:text-sm text-neutral-500 mt-1">
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
                ? 'bg-neutral-900 text-white shadow-2xs'
                : 'bg-white text-neutral-600 border border-neutral-200 hover:bg-neutral-50'
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
            className="bg-white border border-neutral-200/90 rounded-2xl p-5 shadow-2xs flex flex-col justify-between hover:border-neutral-300 transition-all"
          >
            {/* Top info */}
            <div>
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-2.5">
                  {/* Provider Logo Icon */}
                  {item.provider === 'slack' && (
                    <div className="w-9 h-9 rounded-xl bg-emerald-600 flex items-center justify-center text-white shadow-2xs">
                      <svg viewBox="0 0 24 24" className="w-5 h-5 fill-current">
                        <path d="M6 15a2 2 0 1 1-2-2h2v2zm1 0a2 2 0 0 1 2-2 2 2 0 0 1 2 2v5a2 2 0 1 1-4 0v-5zm2-8a2 2 0 1 1-2 2V7h2zm0 1a2 2 0 0 1 2 2 2 2 0 0 1-2 2H2a2 2 0 1 1 0-4h5zm8 2a2 2 0 1 1 2 2h-2v-2zm-1 0a2 2 0 0 1-2 2 2 2 0 0 1-2-2V4a2 2 0 1 1 4 0v5zm-2 8a2 2 0 1 1 2-2v2h-2zm0-1a2 2 0 0 1-2-2 2 2 0 0 1 2-2h5a2 2 0 1 1 0 4h-5z" />
                      </svg>
                    </div>
                  )}
                  {item.provider === 'google_meet' && (
                    <div className="w-9 h-9 rounded-xl bg-emerald-500 flex items-center justify-center text-white shadow-2xs">
                      <svg viewBox="0 0 24 24" className="w-5 h-5 fill-current">
                        <path d="M17 10.5V7c0-.55-.45-1-1-1H4c-.55 0-1 .45-1 1v10c0 .55.45 1 1 1h12c.55 0 1-.45 1-1v-3.5l4 4v-11l-4 4z" />
                      </svg>
                    </div>
                  )}
                  {item.provider === 'jira' && (
                    <div className="w-9 h-9 rounded-xl bg-blue-500 flex items-center justify-center text-white shadow-2xs">
                      <svg viewBox="0 0 24 24" className="w-5 h-5 fill-current">
                        <path d="M11.53 2c0 2.4 1.97 4.35 4.35 4.35h1.77v1.74c0 2.4 1.97 4.35 4.35 4.35V2h-10.47zm-4.7 4.74c0 2.4 1.97 4.35 4.35 4.35h1.77v1.74c0 2.4 1.97 4.35 4.35 4.35V6.74H6.83zm-4.7 4.74c0 2.4 1.97 4.35 4.35 4.35h1.77v1.74c0 2.4 1.97 4.35 4.35 4.35V11.48H2.13z" />
                      </svg>
                    </div>
                  )}
                  {item.provider === 'linear' && (
                    <div className="w-9 h-9 rounded-xl bg-neutral-800 flex items-center justify-center text-white shadow-2xs font-bold text-sm">
                      L
                    </div>
                  )}
                  {item.provider === 'gmail' && (
                    <div className="w-9 h-9 rounded-xl bg-neutral-700 flex items-center justify-center text-white shadow-2xs font-bold text-sm">
                      M
                    </div>
                  )}
                  {item.provider === 'recall' && (
                    <div className="w-9 h-9 rounded-xl bg-neutral-900 flex items-center justify-center text-white shadow-2xs font-bold text-sm">
                      R
                    </div>
                  )}

                  <div>
                    <h3 className="font-bold text-sm text-neutral-900">{item.name}</h3>
                    <div className="flex items-center gap-1.5 text-[11px]">
                      {item.connected ? (
                        <>
                          <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
                          <span className="text-emerald-700 font-semibold">Connected</span>
                        </>
                      ) : (
                        <>
                          <span className="w-1.5 h-1.5 rounded-full bg-neutral-300" />
                          <span className="text-neutral-400">Not configured</span>
                        </>
                      )}
                    </div>
                  </div>
                </div>
              </div>

              <p className="text-xs text-neutral-600 leading-relaxed mb-4">{item.description}</p>

              {item.channelOrScope && (
                <div className="mb-4 px-2.5 py-1.5 rounded-lg bg-neutral-50 border border-neutral-200/80 text-[11px] text-neutral-600 flex items-center justify-between">
                  <span className="text-neutral-400 font-medium">Channel / Scope:</span>
                  <span className="font-semibold text-neutral-800">{item.channelOrScope}</span>
                </div>
              )}
            </div>

            {/* Bottom Actions */}
            <div className="pt-3 border-t border-neutral-100 flex items-center justify-between">
              <span className="text-[10px] text-neutral-400">{item.lastSync || 'Never synced'}</span>

              {item.provider === 'slack' ? (
                <button
                  onClick={onConfigureSlack}
                  className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold bg-neutral-100 text-neutral-900 hover:bg-neutral-200 border border-neutral-200 transition-colors cursor-pointer"
                >
                  <Settings2 className="w-3.5 h-3.5" />
                  <span>Configure Slack</span>
                </button>
              ) : item.connected ? (
                <button className="inline-flex items-center gap-1 text-xs font-semibold text-neutral-600 hover:text-neutral-900 cursor-pointer">
                  <span>Manage</span>
                  <ExternalLink className="w-3 h-3" />
                </button>
              ) : (
                <button className="inline-flex items-center gap-1 px-3 py-1.5 rounded-lg text-xs font-semibold bg-neutral-900 text-white hover:bg-neutral-800 transition-colors cursor-pointer">
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
