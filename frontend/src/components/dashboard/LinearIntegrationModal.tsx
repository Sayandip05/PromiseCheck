import React, { useState, useEffect } from 'react';
import {
  X,
  CheckCircle2,
  AlertCircle,
  ExternalLink,
  Loader2,
  Trash2,
  Search,
} from 'lucide-react';
import { Workspace } from '../../types/dashboard';
import { LinearLogo } from '../ui/BrandLogos';
import { api, explainError } from '../../lib/api';

interface LinearIntegrationModalProps {
  isOpen: boolean;
  onClose: () => void;
  workspace: Workspace;
  onIntegrationUpdated?: () => void;
}

export const LinearIntegrationModal: React.FC<LinearIntegrationModalProps> = ({
  isOpen,
  onClose,
  workspace,
  onIntegrationUpdated,
}) => {
  const [apiKey, setApiKey] = useState('');
  const [teamKey, setTeamKey] = useState('ENG');

  const [isConnected, setIsConnected] = useState(false);
  const [statusText, setStatusText] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isTesting, setIsTesting] = useState(false);
  const [statusMessage, setStatusMessage] = useState<{
    type: 'success' | 'error';
    text: string;
    details?: any;
  } | null>(null);

  useEffect(() => {
    if (!isOpen) return;
    setStatusMessage(null);
    api.integrations
      .list()
      .then((items) => {
        const linear = items.find((i: any) => i.provider === 'linear');
        if (linear) {
          setIsConnected(Boolean(linear.connected));
          setStatusText(linear.statusText || '');
          if (linear.channelOrScope) {
            const clean = linear.channelOrScope.replace('Team', '').trim();
            if (clean) setTeamKey(clean);
          }
        }
      })
      .catch(() => {});
  }, [isOpen]);

  if (!isOpen) return null;

  const handleTestConnection = async () => {
    setIsTesting(true);
    setStatusMessage(null);
    try {
      const res = await api.integrations.test('linear', {
        api_key: apiKey.trim() || undefined,
        team_key: teamKey.trim() || 'ENG',
      });
      setStatusMessage({
        type: 'success',
        text: res.message || 'Linear GraphQL authentication verified!',
        details: res.details,
      });
    } catch (err: any) {
      setStatusMessage({
        type: 'error',
        text: explainError(err, 'Failed to verify Linear API key. Please verify the key in Linear Settings > Account > API.'),
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
      await api.integrations.connect('linear', {
        api_key: apiKey.trim() || undefined,
        team_key: teamKey.trim() || 'ENG',
        scope: teamKey.trim() || 'ENG',
      });
      setIsConnected(true);
      setStatusMessage({
        type: 'success',
        text: 'Linear integration connected and synchronized!',
      });
      if (onIntegrationUpdated) onIntegrationUpdated();
      setTimeout(() => {
        onClose();
      }, 1000);
    } catch (err: any) {
      setStatusMessage({
        type: 'error',
        text: explainError(err, 'Failed to save Linear configuration.'),
      });
    } finally {
      setIsLoading(false);
    }
  };

  const handleDisconnect = async () => {
    setIsLoading(true);
    setStatusMessage(null);
    try {
      await api.integrations.disconnect('linear');
      setIsConnected(false);
      setApiKey('');
      setStatusMessage({
        type: 'success',
        text: 'Linear integration disconnected.',
      });
      if (onIntegrationUpdated) onIntegrationUpdated();
    } catch (err: any) {
      setStatusMessage({
        type: 'error',
        text: explainError(err, 'Failed to disconnect Linear integration.'),
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
              <LinearLogo className="w-5 h-5 shrink-0" />
            </div>
            <div>
              <h3 className="text-base font-bold text-neutral-900 dark:text-white">Linear Integration</h3>
              <p className="text-xs text-neutral-500 dark:text-neutral-400">
                Track engineering issues, cycles, and milestone progress
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

        {/* Content Form */}
        <form onSubmit={handleSave} className="p-6 space-y-4 overflow-y-auto">
          {/* Status Alert */}
          {statusMessage && (
            <div
              className={`p-3 rounded-xl text-xs flex flex-col gap-1.5 animate-in fade-in ${
                statusMessage.type === 'success'
                  ? 'bg-emerald-50 dark:bg-emerald-950/40 border border-emerald-200 dark:border-emerald-800 text-emerald-800 dark:text-emerald-300'
                  : 'bg-rose-50 dark:bg-rose-950/40 border border-rose-200 dark:border-rose-800 text-rose-800 dark:text-rose-300'
              }`}
            >
              <div className="flex items-center gap-2">
                {statusMessage.type === 'success' ? (
                  <CheckCircle2 className="w-4 h-4 shrink-0 text-emerald-600 dark:text-emerald-400" />
                ) : (
                  <AlertCircle className="w-4 h-4 shrink-0 text-rose-600 dark:text-rose-400" />
                )}
                <span className="font-medium">{statusMessage.text}</span>
              </div>
              {statusMessage.details?.issue_preview && (
                <div className="mt-1 p-2 rounded-lg bg-white/70 dark:bg-neutral-800/80 border border-emerald-200/60 dark:border-emerald-700/60 text-[11px]">
                  <span className="font-semibold text-neutral-800 dark:text-neutral-200">
                    Sample Issue: {statusMessage.details.issue_preview.identifier}
                  </span>{' '}
                  - {statusMessage.details.issue_preview.title} (
                  {statusMessage.details.issue_preview.status})
                </div>
              )}
            </div>
          )}

          {/* Connection Status Card */}
          <div className="p-3.5 border border-neutral-200 dark:border-neutral-700 rounded-xl bg-neutral-50/50 dark:bg-neutral-800/40 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <span
                className={`w-2.5 h-2.5 rounded-full ${
                  isConnected ? 'bg-emerald-500 animate-pulse' : 'bg-neutral-400'
                }`}
              />
              <div>
                <div className="text-xs font-semibold text-neutral-800 dark:text-neutral-200">
                  {isConnected ? 'Linear Workspace Connected' : 'Not Configured'}
                </div>
                <div className="text-[10px] text-neutral-400 dark:text-neutral-500">
                  {statusText || (isConnected ? 'Syncing active cycles' : 'Enter your Linear API key')}
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

          {/* Personal API Key */}
          <div className="space-y-1.5">
            <div className="flex items-center justify-between">
              <label className="text-xs font-semibold text-neutral-700 dark:text-neutral-300">
                Linear Personal API Key
              </label>
              <a
                href="https://linear.app/settings/api"
                target="_blank"
                rel="noreferrer"
                className="text-[10px] text-blue-600 dark:text-blue-400 hover:underline flex items-center gap-0.5"
              >
                Generate Key <ExternalLink className="w-2.5 h-2.5" />
              </a>
            </div>
            <input
              type="password"
              value={apiKey}
              onChange={(e) => setApiKey(e.target.value)}
              placeholder="lin_api_..."
              className="w-full text-xs px-3 py-2 border border-neutral-200 dark:border-neutral-700 rounded-lg bg-white dark:bg-neutral-800 text-neutral-900 dark:text-white font-mono focus:outline-none focus:ring-2 focus:ring-neutral-900/10 dark:focus:ring-neutral-600"
            />
            <p className="text-[10px] text-neutral-400 dark:text-neutral-500">
              Personal API keys have scoped access to your Linear workspace issues and cycles.
            </p>
          </div>

          {/* Default Team Key */}
          <div className="space-y-1.5">
            <label className="text-xs font-semibold text-neutral-700 dark:text-neutral-300 flex items-center justify-between">
              <span>Default Team Identifier</span>
              <span className="text-[10px] text-neutral-400">e.g. ENG, DES, PROD</span>
            </label>
            <input
              type="text"
              value={teamKey}
              onChange={(e) => setTeamKey(e.target.value.toUpperCase())}
              placeholder="ENG"
              className="w-full text-xs px-3 py-2 border border-neutral-200 dark:border-neutral-700 rounded-lg bg-white dark:bg-neutral-800 text-neutral-900 dark:text-white font-mono focus:outline-none focus:ring-2 focus:ring-neutral-900/10 dark:focus:ring-neutral-600"
            />
          </div>

          {/* Footer Actions */}
          <div className="pt-4 border-t border-neutral-100 dark:border-neutral-800 flex items-center justify-between gap-3">
            <button
              type="button"
              onClick={handleTestConnection}
              disabled={isTesting}
              className="inline-flex items-center gap-1.5 px-3 py-2 text-xs font-semibold text-neutral-700 dark:text-neutral-200 bg-white dark:bg-neutral-800 border border-neutral-200 dark:border-neutral-700 rounded-lg hover:bg-neutral-50 dark:hover:bg-neutral-750 transition-colors cursor-pointer"
            >
              {isTesting ? (
                <Loader2 className="w-3.5 h-3.5 animate-spin" />
              ) : (
                <Search className="w-3.5 h-3.5 text-neutral-400" />
              )}
              <span>{isTesting ? 'Verifying...' : 'Test Connection'}</span>
            </button>

            <button
              type="submit"
              disabled={isLoading}
              className="inline-flex items-center gap-1.5 px-4 py-2 text-xs font-semibold text-white dark:text-neutral-900 bg-neutral-900 dark:bg-white hover:bg-neutral-800 dark:hover:bg-neutral-200 rounded-lg transition-colors cursor-pointer"
            >
              {isLoading && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
              <span>Save & Connect</span>
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
