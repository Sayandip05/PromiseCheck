import React, { useState, useEffect } from 'react';
import {
  X,
  CheckCircle2,
  AlertCircle,
  Bell,
  Send,
  Loader2,
  Trash2,
  ExternalLink,
  ShieldAlert,
} from 'lucide-react';
import { Workspace } from '../../types/dashboard';
import { SlackLogo } from '../ui/BrandLogos';
import { api, explainError } from '../../lib/api';

interface SlackIntegrationModalProps {
  isOpen: boolean;
  onClose: () => void;
  workspace: Workspace;
  onIntegrationUpdated?: () => void;
}

export const SlackIntegrationModal: React.FC<SlackIntegrationModalProps> = ({
  isOpen,
  onClose,
  workspace,
  onIntegrationUpdated,
}) => {
  const [authMode, setAuthMode] = useState<'webhook' | 'token'>('webhook');
  const [webhookUrl, setWebhookUrl] = useState('');
  const [botToken, setBotToken] = useState('');
  const [channel, setChannel] = useState('#customer-commitments');
  const [notifyConflicts, setNotifyConflicts] = useState(true);
  const [notifyOverdue, setNotifyOverdue] = useState(true);
  const [notifyNewPromises, setNotifyNewPromises] = useState(true);

  const [isConnected, setIsConnected] = useState(false);
  const [statusText, setStatusText] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isTesting, setIsTesting] = useState(false);
  const [statusMessage, setStatusMessage] = useState<{
    type: 'success' | 'error';
    text: string;
  } | null>(null);

  // Sync state with backend when opening
  useEffect(() => {
    if (!isOpen) return;
    setStatusMessage(null);
    api.integrations
      .list()
      .then((items) => {
        const slack = items.find((i: any) => i.provider === 'slack');
        if (slack) {
          setIsConnected(Boolean(slack.connected));
          setStatusText(slack.statusText || '');
          if (slack.channelOrScope) {
            if (slack.channelOrScope.startsWith('http')) {
              setWebhookUrl(slack.channelOrScope);
              setAuthMode('webhook');
            } else if (slack.channelOrScope.startsWith('#')) {
              setChannel(slack.channelOrScope);
            }
          }
        }
      })
      .catch(() => {});
  }, [isOpen]);

  if (!isOpen) return null;

  const handleSendTest = async () => {
    setIsTesting(true);
    setStatusMessage(null);
    try {
      const res = await api.integrations.test('slack', {
        webhook_url: webhookUrl.trim() || undefined,
        bot_token: botToken.trim() || undefined,
        channel: channel.trim() || '#customer-commitments',
        message: '🧪 PromiseCheck alert: Slack live connector test successful! Delivery confirmed.',
      });
      setStatusMessage({
        type: 'success',
        text: res.message || `Test message delivered to ${channel}!`,
      });
    } catch (err: any) {
      setStatusMessage({
        type: 'error',
        text: explainError(err, 'Failed to send test message to Slack. Please verify your webhook URL or bot token.'),
      });
    } finally {
      setIsTesting(false);
    }
  };

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setStatusMessage(null);
    try {
      await api.integrations.connect('slack', {
        webhook_url: authMode === 'webhook' ? webhookUrl.trim() || undefined : undefined,
        bot_token: authMode === 'token' ? botToken.trim() || undefined : undefined,
        channel: channel.trim() || '#customer-commitments',
        scope: channel.trim() || '#customer-commitments',
        notify_conflicts: notifyConflicts,
        notify_overdue: notifyOverdue,
        notify_new_promises: notifyNewPromises,
      });
      setIsConnected(true);
      setStatusMessage({
        type: 'success',
        text: 'Slack integration saved and activated!',
      });
      if (onIntegrationUpdated) onIntegrationUpdated();
      setTimeout(() => {
        onClose();
      }, 1000);
    } catch (err: any) {
      setStatusMessage({
        type: 'error',
        text: explainError(err, 'Failed to save Slack settings. Please verify configuration.'),
      });
    } finally {
      setIsLoading(false);
    }
  };

  const handleDisconnect = async () => {
    setIsLoading(true);
    setStatusMessage(null);
    try {
      await api.integrations.disconnect('slack');
      setIsConnected(false);
      setWebhookUrl('');
      setBotToken('');
      setStatusMessage({
        type: 'success',
        text: 'Slack integration disconnected.',
      });
      if (onIntegrationUpdated) onIntegrationUpdated();
    } catch (err: any) {
      setStatusMessage({
        type: 'error',
        text: explainError(err, 'Failed to disconnect Slack integration.'),
      });
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-neutral-900/60 backdrop-blur-xs animate-in fade-in">
      <div className="bg-white dark:bg-neutral-900 rounded-2xl max-w-lg w-full border border-neutral-200 dark:border-neutral-800 shadow-2xl overflow-hidden flex flex-col max-h-[90vh]">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-neutral-100 dark:border-neutral-800 bg-neutral-50/70 dark:bg-neutral-850/70">
          <div className="flex items-center gap-2.5">
            <div className="w-9 h-9 rounded-xl bg-white dark:bg-neutral-800 border border-neutral-200 dark:border-neutral-700 flex items-center justify-center p-1.5 shadow-2xs">
              <SlackLogo className="w-5 h-5 shrink-0" />
            </div>
            <div>
              <h3 className="text-base font-bold text-neutral-900 dark:text-white">Slack Alerts & Digests</h3>
              <p className="text-xs text-neutral-500 dark:text-neutral-400">
                Workspace: <span className="font-semibold text-neutral-700 dark:text-neutral-300">{workspace.name}</span>
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

        {/* Form Body */}
        <form onSubmit={handleSave} className="p-6 space-y-5 overflow-y-auto">
          {/* Status Message */}
          {statusMessage && (
            <div
              className={`p-3 rounded-xl text-xs flex items-center gap-2 animate-in fade-in ${
                statusMessage.type === 'success'
                  ? 'bg-emerald-50 dark:bg-emerald-950/40 border border-emerald-200 dark:border-emerald-800 text-emerald-800 dark:text-emerald-300'
                  : 'bg-rose-50 dark:bg-rose-950/40 border border-rose-200 dark:border-rose-800 text-rose-800 dark:text-rose-300'
              }`}
            >
              {statusMessage.type === 'success' ? (
                <CheckCircle2 className="w-4 h-4 shrink-0 text-emerald-600 dark:text-emerald-400" />
              ) : (
                <AlertCircle className="w-4 h-4 shrink-0 text-rose-600 dark:text-rose-400" />
              )}
              <span>{statusMessage.text}</span>
            </div>
          )}

          {/* Connection Status Badge */}
          <div className="p-3.5 border border-neutral-200 dark:border-neutral-700 rounded-xl bg-neutral-50/50 dark:bg-neutral-800/40 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <span
                className={`w-2.5 h-2.5 rounded-full ${
                  isConnected ? 'bg-emerald-500 animate-pulse' : 'bg-neutral-400'
                }`}
              />
              <div>
                <div className="text-xs font-semibold text-neutral-800 dark:text-neutral-200">
                  {isConnected ? 'Slack Integration Active' : 'Not Connected'}
                </div>
                <div className="text-[10px] text-neutral-400 dark:text-neutral-500">
                  {statusText || (isConnected ? 'Ready to deliver alerts' : 'Configure incoming webhook or bot token')}
                </div>
              </div>
            </div>

            {isConnected && (
              <button
                type="button"
                onClick={handleDisconnect}
                disabled={isLoading}
                className="text-xs text-rose-600 dark:text-rose-400 hover:text-rose-700 font-semibold cursor-pointer inline-flex items-center gap-1"
              >
                <Trash2 className="w-3.5 h-3.5" />
                <span>Disconnect</span>
              </button>
            )}
          </div>

          {/* Authentication Mode Tabs */}
          <div>
            <label className="text-xs font-semibold text-neutral-700 dark:text-neutral-300 block mb-1.5">
              Connection Method
            </label>
            <div className="grid grid-cols-2 gap-2">
              <button
                type="button"
                onClick={() => setAuthMode('webhook')}
                className={`px-3 py-2 rounded-xl text-xs font-semibold border transition-all cursor-pointer text-left ${
                  authMode === 'webhook'
                    ? 'border-neutral-900 dark:border-white bg-neutral-900 dark:bg-white text-white dark:text-neutral-900 shadow-2xs'
                    : 'border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-800 text-neutral-600 dark:text-neutral-300'
                }`}
              >
                <div>Incoming Webhook</div>
                <div className="text-[10px] opacity-80 font-normal">Recommended & simplest setup</div>
              </button>
              <button
                type="button"
                onClick={() => setAuthMode('token')}
                className={`px-3 py-2 rounded-xl text-xs font-semibold border transition-all cursor-pointer text-left ${
                  authMode === 'token'
                    ? 'border-neutral-900 dark:border-white bg-neutral-900 dark:bg-white text-white dark:text-neutral-900 shadow-2xs'
                    : 'border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-800 text-neutral-600 dark:text-neutral-300'
                }`}
              >
                <div>Bot Token (OAuth)</div>
                <div className="text-[10px] opacity-80 font-normal">xoxb-... with chat:write</div>
              </button>
            </div>
          </div>

          {/* Webhook URL Input */}
          {authMode === 'webhook' ? (
            <div className="space-y-1.5">
              <div className="flex items-center justify-between">
                <label className="text-xs font-semibold text-neutral-700 dark:text-neutral-300">
                  Slack Incoming Webhook URL
                </label>
                <a
                  href="https://api.slack.com/apps"
                  target="_blank"
                  rel="noreferrer"
                  className="text-[10px] text-blue-600 dark:text-blue-400 hover:underline flex items-center gap-0.5"
                >
                  Create in Slack <ExternalLink className="w-2.5 h-2.5" />
                </a>
              </div>
              <input
                type="url"
                value={webhookUrl}
                onChange={(e) => setWebhookUrl(e.target.value)}
                placeholder="https://hooks.slack.com/services/..."
                className="w-full text-xs px-3 py-2 border border-neutral-200 dark:border-neutral-700 rounded-lg bg-white dark:bg-neutral-800 text-neutral-900 dark:text-white placeholder:text-neutral-400 focus:outline-none focus:ring-2 focus:ring-neutral-900/10 dark:focus:ring-neutral-600"
              />
              <p className="text-[10px] text-neutral-500 dark:text-neutral-400">
                Incoming Webhooks post directly to the channel selected when creating the webhook in Slack.
              </p>
            </div>
          ) : (
            <div className="space-y-1.5">
              <label className="text-xs font-semibold text-neutral-700 dark:text-neutral-300">
                Slack Bot User OAuth Token
              </label>
              <input
                type="password"
                value={botToken}
                onChange={(e) => setBotToken(e.target.value)}
                placeholder="xoxb-1234567890-..."
                className="w-full text-xs px-3 py-2 border border-neutral-200 dark:border-neutral-700 rounded-lg bg-white dark:bg-neutral-800 text-neutral-900 dark:text-white placeholder:text-neutral-400 focus:outline-none focus:ring-2 focus:ring-neutral-900/10 dark:focus:ring-neutral-600 font-mono"
              />
            </div>
          )}

          {/* Target Channel */}
          <div className="space-y-1.5">
            <label className="text-xs font-semibold text-neutral-700 dark:text-neutral-300 flex items-center justify-between">
              <span>Alert Channel Name</span>
              <span className="text-[10px] text-neutral-400 dark:text-neutral-500 font-normal">e.g. #customer-commitments</span>
            </label>
            <input
              type="text"
              value={channel}
              onChange={(e) => setChannel(e.target.value)}
              placeholder="#customer-commitments"
              className="w-full text-xs px-3 py-2 border border-neutral-200 dark:border-neutral-700 rounded-lg bg-white dark:bg-neutral-800 text-neutral-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-neutral-900/10 dark:focus:ring-neutral-600"
            />
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
                  className="rounded accent-neutral-900 dark:accent-white w-4 h-4 cursor-pointer"
                />
              </label>

              <label className="flex items-center justify-between p-2.5 rounded-lg border border-neutral-100 dark:border-neutral-800 hover:bg-neutral-50 dark:hover:bg-neutral-800/50 cursor-pointer">
                <div className="flex items-center gap-2">
                  <Bell className="w-3.5 h-3.5 text-neutral-400 dark:text-neutral-500" />
                  <span className="text-neutral-800 dark:text-neutral-200 font-medium">Overdue commitments</span>
                </div>
                <input
                  type="checkbox"
                  checked={notifyOverdue}
                  onChange={(e) => setNotifyOverdue(e.target.checked)}
                  className="rounded accent-neutral-900 dark:accent-white w-4 h-4 cursor-pointer"
                />
              </label>

              <label className="flex items-center justify-between p-2.5 rounded-lg border border-neutral-100 dark:border-neutral-800 hover:bg-neutral-50 dark:hover:bg-neutral-800/50 cursor-pointer">
                <div className="flex items-center gap-2">
                  <Bell className="w-3.5 h-3.5 text-neutral-400 dark:text-neutral-500" />
                  <span className="text-neutral-800 dark:text-neutral-200 font-medium">New unreviewed promises</span>
                </div>
                <input
                  type="checkbox"
                  checked={notifyNewPromises}
                  onChange={(e) => setNotifyNewPromises(e.target.checked)}
                  className="rounded accent-neutral-900 dark:accent-white w-4 h-4 cursor-pointer"
                />
              </label>
            </div>
          </div>

          {/* Footer Controls inside Form */}
          <div className="pt-4 border-t border-neutral-100 dark:border-neutral-800 flex items-center justify-between gap-3">
            <button
              type="button"
              onClick={handleSendTest}
              disabled={isTesting}
              className="inline-flex items-center gap-1.5 px-3 py-2 text-xs font-semibold text-neutral-700 dark:text-neutral-200 bg-white dark:bg-neutral-800 border border-neutral-200 dark:border-neutral-700 rounded-lg hover:bg-neutral-50 dark:hover:bg-neutral-750 transition-colors cursor-pointer"
            >
              {isTesting ? (
                <Loader2 className="w-3.5 h-3.5 animate-spin" />
              ) : (
                <Send className="w-3.5 h-3.5 text-neutral-400" />
              )}
              <span>{isTesting ? 'Sending...' : 'Send Live Test'}</span>
            </button>

            <button
              type="submit"
              disabled={isLoading}
              className="inline-flex items-center gap-1.5 px-4 py-2 text-xs font-semibold text-white dark:text-neutral-900 bg-neutral-900 dark:bg-white hover:bg-neutral-800 dark:hover:bg-neutral-200 rounded-lg transition-colors cursor-pointer"
            >
              {isLoading && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
              <span>Save & Activate</span>
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
