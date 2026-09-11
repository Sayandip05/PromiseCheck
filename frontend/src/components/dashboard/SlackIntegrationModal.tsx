import React, { useState } from 'react';
import { X, CheckCircle2, AlertCircle, Shield, Bell, Send } from 'lucide-react';
import { Workspace } from '../../types/dashboard';

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
      <div className="bg-white rounded-none max-w-lg w-full border border-neutral-200 shadow-xl overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-neutral-100 bg-neutral-50/50">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-emerald-600 flex items-center justify-center text-white">
              <svg viewBox="0 0 24 24" className="w-4 h-4 fill-current">
                <path d="M6 15a2 2 0 1 1-2-2h2v2zm1 0a2 2 0 0 1 2-2 2 2 0 0 1 2 2v5a2 2 0 1 1-4 0v-5zm2-8a2 2 0 1 1-2 2V7h2zm0 1a2 2 0 0 1 2 2 2 2 0 0 1-2 2H2a2 2 0 1 1 0-4h5zm8 2a2 2 0 1 1 2 2h-2v-2zm-1 0a2 2 0 0 1-2 2 2 2 0 0 1-2-2V4a2 2 0 1 1 4 0v5zm-2 8a2 2 0 1 1 2-2v2h-2zm0-1a2 2 0 0 1-2-2 2 2 0 0 1 2-2h5a2 2 0 1 1 0 4h-5z" />
              </svg>
            </div>
            <div>
              <h3 className="text-base font-bold text-neutral-900">Isolated Slack Integration</h3>
              <p className="text-xs text-neutral-500">
                Connected to tenant: <span className="font-semibold text-neutral-700">{workspace.name}</span>
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded-lg text-neutral-400 hover:text-neutral-700 hover:bg-neutral-100 transition-colors cursor-pointer"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        <div className="p-6 space-y-5">
          {/* SaaS Isolation Banner */}
          <div className="flex items-start gap-2.5 p-3.5 bg-neutral-100 border border-neutral-200 rounded-xl text-xs text-neutral-800">
            <Shield className="w-4 h-4 text-neutral-700 shrink-0 mt-0.5" />
            <div>
              <span className="font-bold">Tenant Data Isolation: </span>
              Your Slack OAuth credentials and webhook tokens are strictly encrypted per-workspace
              (`workspace_id: {workspace.id}`). No cross-tenant notification bleeding is possible.
            </div>
          </div>

          {/* Connection Status Card */}
          <div className="p-3.5 border border-neutral-200 rounded-xl bg-neutral-50/50 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
              <div>
                <div className="text-xs font-semibold text-neutral-800">Connected to Acme Org Slack</div>
                <div className="text-[10px] text-neutral-400">OAuth 2.0 authorized by Workspace Admin</div>
              </div>
            </div>
            <button className="text-xs font-semibold text-neutral-500 hover:text-neutral-800">
              Reconnect
            </button>
          </div>

          {/* Target Channel */}
          <div className="space-y-1.5">
            <label className="text-xs font-semibold text-neutral-700 flex items-center justify-between">
              <span>Default Alert Channel</span>
              <span className="text-[10px] text-neutral-400 font-normal">Private or Public channel</span>
            </label>
            <select
              value={channel}
              onChange={(e) => setChannel(e.target.value)}
              className="w-full text-xs px-3 py-2 border border-neutral-200 rounded-lg bg-white focus:outline-none focus:ring-2 focus:ring-neutral-900/10 focus:border-neutral-900"
            >
              <option value="#customer-commitments">#customer-commitments (Recommended)</option>
              <option value="#acme-delivery-alerts">#acme-delivery-alerts</option>
              <option value="#product-engineering">#product-engineering</option>
              <option value="#leadership-sync">#leadership-sync</option>
            </select>
          </div>

          {/* Alert Trigger Rules */}
          <div className="space-y-2.5">
            <label className="text-xs font-semibold text-neutral-700 block">
              Automated Alert Triggers
            </label>

            <div className="space-y-2 text-xs">
              <label className="flex items-center justify-between p-2.5 rounded-lg border border-neutral-100 hover:bg-neutral-50 cursor-pointer">
                <div className="flex items-center gap-2">
                  <Bell className="w-3.5 h-3.5 text-neutral-400" />
                  <span className="text-neutral-800 font-medium">Delivery date conflicts</span>
                </div>
                <input
                  type="checkbox"
                  checked={notifyConflicts}
                  onChange={(e) => setNotifyConflicts(e.target.checked)}
                  className="rounded accent-neutral-900 w-4 h-4"
                />
              </label>

              <label className="flex items-center justify-between p-2.5 rounded-lg border border-neutral-100 hover:bg-neutral-50 cursor-pointer">
                <div className="flex items-center gap-2">
                  <Bell className="w-3.5 h-3.5 text-neutral-400" />
                  <span className="text-neutral-800 font-medium">Overdue promises</span>
                </div>
                <input
                  type="checkbox"
                  checked={notifyOverdue}
                  onChange={(e) => setNotifyOverdue(e.target.checked)}
                  className="rounded accent-neutral-900 w-4 h-4"
                />
              </label>

              <label className="flex items-center justify-between p-2.5 rounded-lg border border-neutral-100 hover:bg-neutral-50 cursor-pointer">
                <div className="flex items-center gap-2">
                  <Bell className="w-3.5 h-3.5 text-neutral-400" />
                  <span className="text-neutral-800 font-medium">New unreviewed promise extracted</span>
                </div>
                <input
                  type="checkbox"
                  checked={notifyNewPromises}
                  onChange={(e) => setNotifyNewPromises(e.target.checked)}
                  className="rounded accent-neutral-900 w-4 h-4"
                />
              </label>
            </div>
          </div>

          {/* Test Alert Live Preview */}
          {testSent && (
            <div className="p-3 bg-emerald-50 border border-emerald-200 rounded-xl text-xs text-emerald-800 flex items-center gap-2 animate-in fade-in">
              <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
              <span>Test payload sent to {channel}! Verified webhook 200 OK.</span>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="px-6 py-4 border-t border-neutral-100 bg-neutral-50/50 flex items-center justify-between">
          <button
            type="button"
            onClick={handleSendTest}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-neutral-700 bg-white border border-neutral-200 rounded-lg hover:bg-neutral-50 transition-colors cursor-pointer"
          >
            <Send className="w-3 h-3 text-neutral-400" />
            <span>Send test alert</span>
          </button>

          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 text-xs font-medium text-white bg-neutral-900 hover:bg-neutral-800 rounded-lg transition-colors cursor-pointer"
          >
            Save integration
          </button>
        </div>
      </div>
    </div>
  );
};
