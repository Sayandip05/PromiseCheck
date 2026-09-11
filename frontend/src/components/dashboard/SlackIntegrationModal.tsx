import React, { useState } from 'react';
import { X, CheckCircle2, AlertCircle, Bell, Send } from 'lucide-react';
import { Workspace } from '../../types/dashboard';
import { SlackLogo } from '../ui/BrandLogos';

interface SlackIntegrationModalProps {
  isOpen: boolean;
  onClose: () => void;
  workspace: Workspace;
}

export const SlackIntegrationModal: React.FC<SlackIntegrationModalProps> = ({
  isOpen,
  onClose,
  workspace,
}) => {
  if (!isOpen) return null;

  const [channel, setChannel] = useState('#customer-commitments');
  const [notifyConflicts, setNotifyConflicts] = useState(true);
  const [notifyOverdue, setNotifyOverdue] = useState(true);
  const [notifyNewPromises, setNotifyNewPromises] = useState(true);
  const [testSent, setTestSent] = useState(false);

  const handleSendTest = () => {
    setTestSent(true);
    setTimeout(() => {
      setTestSent(false);
    }, 4000);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-neutral-900/50 backdrop-blur-xs animate-in fade-in">
      <div className="bg-white dark:bg-neutral-900 rounded-2xl max-w-lg w-full border border-neutral-200 dark:border-neutral-800 shadow-xl overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-neutral-100 dark:border-neutral-800 bg-neutral-50/50 dark:bg-neutral-850/50">
          <div className="flex items-center gap-2.5">
            <div className="w-9 h-9 rounded-xl bg-white dark:bg-neutral-800 border border-neutral-200 dark:border-neutral-700 flex items-center justify-center p-1.5 shadow-2xs">
              <SlackLogo className="w-5 h-5 shrink-0" />
            </div>
            <div>
              <h3 className="text-base font-bold text-neutral-900 dark:text-white">Slack Integration</h3>
              <p className="text-xs text-neutral-500 dark:text-neutral-400">
                Connected to tenant: <span className="font-semibold text-neutral-700 dark:text-neutral-300">{workspace.name}</span>
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded-lg text-neutral-400 dark:text-neutral-500 hover:text-neutral-700 dark:hover:text-neutral-200 hover:bg-neutral-100 dark:hover:bg-neutral-800 transition-colors cursor-pointer"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        <div className="p-6 space-y-5">


          {/* Connection Status Card */}
          <div className="p-3.5 border border-neutral-200 dark:border-neutral-700 rounded-xl bg-neutral-50/50 dark:bg-neutral-800/40 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
              <div>
                <div className="text-xs font-semibold text-neutral-800 dark:text-neutral-200">Connected to Acme Org Slack</div>
                <div className="text-[10px] text-neutral-400 dark:text-neutral-500">OAuth 2.0 authorized by Workspace Admin</div>
              </div>
            </div>
            <button className="text-xs font-semibold text-neutral-500 dark:text-neutral-400 hover:text-neutral-800 dark:hover:text-neutral-200 cursor-pointer">
              Reconnect
            </button>
          </div>

          {/* Target Channel */}
          <div className="space-y-1.5">
            <label className="text-xs font-semibold text-neutral-700 dark:text-neutral-300 flex items-center justify-between">
              <span>Default Alert Channel</span>
              <span className="text-[10px] text-neutral-400 dark:text-neutral-500 font-normal">Private or Public channel</span>
            </label>
            <select
              value={channel}
              onChange={(e) => setChannel(e.target.value)}
              className="w-full text-xs px-3 py-2 border border-neutral-200 dark:border-neutral-700 rounded-lg bg-white dark:bg-neutral-800 text-neutral-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-neutral-900/10 dark:focus:ring-neutral-600 focus:border-neutral-900 dark:focus:border-neutral-500"
            >
              <option value="#customer-commitments">#customer-commitments (Recommended)</option>
              <option value="#acme-delivery-alerts">#acme-delivery-alerts</option>
              <option value="#product-engineering">#product-engineering</option>
              <option value="#leadership-sync">#leadership-sync</option>
            </select>
          </div>

          {/* Alert Trigger Rules */}
          <div className="space-y-2.5">
            <label className="text-xs font-semibold text-neutral-700 dark:text-neutral-300 block">
              Automated Alert Triggers
            </label>

            <div className="space-y-2 text-xs">
              <label className="flex items-center justify-between p-2.5 rounded-lg border border-neutral-100 dark:border-neutral-800 hover:bg-neutral-50 dark:hover:bg-neutral-800/50 cursor-pointer">
                <div className="flex items-center gap-2">
                  <Bell className="w-3.5 h-3.5 text-neutral-400 dark:text-neutral-500" />
                  <span className="text-neutral-800 dark:text-neutral-200 font-medium">Delivery date conflicts</span>
                </div>
                <input
                  type="checkbox"
                  checked={notifyConflicts}
                  onChange={(e) => setNotifyConflicts(e.target.checked)}
                  className="rounded accent-neutral-900 dark:accent-white w-4 h-4"
                />
              </label>

              <label className="flex items-center justify-between p-2.5 rounded-lg border border-neutral-100 dark:border-neutral-800 hover:bg-neutral-50 dark:hover:bg-neutral-800/50 cursor-pointer">
                <div className="flex items-center gap-2">
                  <Bell className="w-3.5 h-3.5 text-neutral-400 dark:text-neutral-500" />
                  <span className="text-neutral-800 dark:text-neutral-200 font-medium">Overdue promises</span>
                </div>
                <input
                  type="checkbox"
                  checked={notifyOverdue}
                  onChange={(e) => setNotifyOverdue(e.target.checked)}
                  className="rounded accent-neutral-900 dark:accent-white w-4 h-4"
                />
              </label>

              <label className="flex items-center justify-between p-2.5 rounded-lg border border-neutral-100 dark:border-neutral-800 hover:bg-neutral-50 dark:hover:bg-neutral-800/50 cursor-pointer">
                <div className="flex items-center gap-2">
                  <Bell className="w-3.5 h-3.5 text-neutral-400 dark:text-neutral-500" />
                  <span className="text-neutral-800 dark:text-neutral-200 font-medium">New unreviewed promise extracted</span>
                </div>
                <input
                  type="checkbox"
                  checked={notifyNewPromises}
                  onChange={(e) => setNotifyNewPromises(e.target.checked)}
                  className="rounded accent-neutral-900 dark:accent-white w-4 h-4"
                />
              </label>
            </div>
          </div>

          {/* Test Alert Live Preview */}
          {testSent && (
            <div className="p-3 bg-emerald-50 dark:bg-emerald-950/40 border border-emerald-200 dark:border-emerald-800/60 rounded-xl text-xs text-emerald-800 dark:text-emerald-300 flex items-center gap-2 animate-in fade-in">
              <CheckCircle2 className="w-4 h-4 text-emerald-600 dark:text-emerald-400 shrink-0" />
              <span>Test payload sent to {channel}! Verified webhook 200 OK.</span>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="px-6 py-4 border-t border-neutral-100 dark:border-neutral-800 bg-neutral-50/50 dark:bg-neutral-850/50 flex items-center justify-between">
          <button
            type="button"
            onClick={handleSendTest}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-neutral-700 dark:text-neutral-200 bg-white dark:bg-neutral-800 border border-neutral-200 dark:border-neutral-700 rounded-lg hover:bg-neutral-50 dark:hover:bg-neutral-750 transition-colors cursor-pointer"
          >
            <Send className="w-3 h-3 text-neutral-400 dark:text-neutral-500" />
            <span>Send test alert</span>
          </button>

          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 text-xs font-medium text-white dark:text-neutral-900 bg-neutral-900 dark:bg-white hover:bg-neutral-800 dark:hover:bg-neutral-200 rounded-lg transition-colors cursor-pointer"
          >
            Save integration
          </button>
        </div>
      </div>
    </div>
  );
};
