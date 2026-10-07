import React, { useState, useEffect } from 'react';
import {
  X,
  CheckCircle2,
  AlertCircle,
  Calendar,
  Mail,
  ExternalLink,
  ShieldCheck,
  Send,
  RefreshCw,
  Terminal,
} from 'lucide-react';
import { Workspace } from '../../types/dashboard';
import { api, explainError } from '../../lib/api';

interface GoogleIntegrationModalProps {
  isOpen: boolean;
  onClose: () => void;
  workspace: Workspace;
  onIntegrationUpdated?: () => void;
}

export const GoogleIntegrationModal: React.FC<GoogleIntegrationModalProps> = ({
  isOpen,
  onClose,
  workspace,
  onIntegrationUpdated,
}) => {
  const [isConnected, setIsConnected] = useState(false);
  const [connectedEmail, setConnectedEmail] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [statusMessage, setStatusMessage] = useState<{ type: 'success' | 'error'; text: string; link?: string } | null>(null);
  const [showManualToken, setShowManualToken] = useState(false);
  const [manualToken, setManualToken] = useState('');
  const [manualEmail, setManualEmail] = useState('');
  const [isSyncingCalendar, setIsSyncingCalendar] = useState(false);

  // Check integration status whenever modal opens
  useEffect(() => {
    if (!isOpen) return;

    api.integrations
      .list()
      .then((list) => {
        const gmailInt = list.find((i: any) => i.provider === 'gmail');
        if (gmailInt && gmailInt.connected) {
          setIsConnected(true);
          setConnectedEmail(gmailInt.channelOrScope || 'Authorized Google Account');
        } else {
          setIsConnected(false);
          setConnectedEmail(null);
        }
      })
      .catch(() => {});
  }, [isOpen]);

  // Listen for popup message on OAuth completion
  useEffect(() => {
    const handleAuthMessage = (e: MessageEvent) => {
      if (e.data?.type === 'GOOGLE_AUTH_SUCCESS') {
        setIsConnected(true);
        setConnectedEmail(e.data.email || 'Authorized Google Account');
        setStatusMessage({
          type: 'success',
          text: `Successfully connected Google account (${e.data.email || 'Authorized'})!`,
        });
        if (onIntegrationUpdated) onIntegrationUpdated();
      }
    };

    window.addEventListener('message', handleAuthMessage);
    return () => window.removeEventListener('message', handleAuthMessage);
  }, [onIntegrationUpdated]);

  if (!isOpen) return null;

  const handleStartOAuth = async () => {
    setIsLoading(true);
    setStatusMessage(null);
    try {
      const data = await api.integrations.getGoogleAuthorizeUrl();
      if (data?.authorization_url) {
        const popupWidth = 520;
        const popupHeight = 650;
        const left = window.screenX + (window.outerWidth - popupWidth) / 2;
        const top = window.screenY + (window.outerHeight - popupHeight) / 2;

        window.open(
          data.authorization_url,
          'GoogleAuthPopup',
          `width=${popupWidth},height=${popupHeight},left=${left},top=${top},status=no,toolbar=no,menubar=no`
        );
      }
    } catch (err: any) {
      setStatusMessage({
        type: 'error',
        text: explainError(err, 'Failed to initialize Google OAuth session. Please check client credentials.'),
      });
    } finally {
      setIsLoading(false);
    }
  };

  const handleManualTokenSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!manualToken.trim()) return;

    setIsLoading(true);
    setStatusMessage(null);
    try {
      const res = await api.integrations.connectGoogleToken({
        access_token: manualToken.trim(),
        email: manualEmail.trim() || undefined,
      });
      setIsConnected(true);
      setConnectedEmail(res.channelOrScope || manualEmail || 'Authorized Account');
      setStatusMessage({
        type: 'success',
        text: 'Google credentials registered successfully!',
      });
      setShowManualToken(false);
      if (onIntegrationUpdated) onIntegrationUpdated();
    } catch (err: any) {
      setStatusMessage({
        type: 'error',
        text: explainError(err, 'Failed to verify Google access token. Please ensure it is valid and unexpired.'),
      });
    } finally {
      setIsLoading(false);
    }
  };

  const handleTestCalendarSync = async () => {
    setIsSyncingCalendar(true);
    setStatusMessage(null);
    try {
      const res = await api.integrations.syncCalendarEvent({
        title: 'Acme SOC-2 Type II Milestone',
        due_date_iso: '2026-10-25',
        description: 'Verified SLA deadline synced from PromiseCheck dashboard.',
      });
      setStatusMessage({
        type: 'success',
        text: `Milestone event created in Google Calendar!`,
        link: res.html_link || 'https://calendar.google.com/',
      });
    } catch (err: any) {
      setStatusMessage({
        type: 'error',
        text: explainError(err, 'Failed to sync event to Google Calendar.'),
      });
    } finally {
      setIsSyncingCalendar(false);
    }
  };

  const handleDisconnect = async () => {
    setIsLoading(true);
    setStatusMessage(null);
    try {
      await api.integrations.disconnect('gmail');
      setIsConnected(false);
      setConnectedEmail(null);
      setStatusMessage({
        type: 'success',
        text: 'Gmail & Google Calendar disconnected.',
      });
      if (onIntegrationUpdated) onIntegrationUpdated();
    } catch (err: any) {
      setStatusMessage({
        type: 'error',
        text: explainError(err, 'Failed to disconnect Google integration.'),
      });
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-neutral-900/50 backdrop-blur-xs animate-in fade-in">
      <div className="bg-white dark:bg-neutral-900 rounded-2xl max-w-lg w-full border border-neutral-200 dark:border-neutral-800 shadow-xl overflow-hidden flex flex-col max-h-[90vh]">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-neutral-100 dark:border-neutral-800 bg-neutral-50/50 dark:bg-neutral-850/50">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-white dark:bg-neutral-800 border border-neutral-200 dark:border-neutral-700 flex items-center justify-center shadow-2xs">
              <svg className="w-5 h-5 shrink-0" viewBox="0 0 24 24">
                <path
                  fill="#4285F4"
                  d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
                />
                <path
                  fill="#34A853"
                  d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
                />
                <path
                  fill="#FBBC05"
                  d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.06H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.94l2.85-2.22.81-.63z"
                />
                <path
                  fill="#EA4335"
                  d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.06l3.66 2.84c.87-2.6 3.3-4.52 6.16-4.52z"
                />
              </svg>
            </div>
            <div>
              <h3 className="text-base font-bold text-neutral-900 dark:text-white">
                Gmail & Google Calendar
              </h3>
              <p className="text-xs text-neutral-500 dark:text-neutral-400">
                Workspace: <span className="font-semibold text-neutral-700 dark:text-neutral-300">{workspace.name}</span>
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            aria-label="Close modal"
            className="p-1 rounded-lg text-neutral-400 hover:text-neutral-700 dark:hover:text-neutral-200 hover:bg-neutral-100 dark:hover:bg-neutral-800 transition-colors cursor-pointer"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Body */}
        <div className="p-6 space-y-5 overflow-y-auto flex-1">
          {/* Status Message Alert */}
          {statusMessage && (
            <div
              className={`p-3.5 rounded-xl text-xs flex items-start gap-2.5 animate-in fade-in ${
                statusMessage.type === 'success'
                  ? 'bg-emerald-50 dark:bg-emerald-950/40 border border-emerald-200 dark:border-emerald-800 text-emerald-800 dark:text-emerald-300'
                  : 'bg-red-50 dark:bg-red-950/40 border border-red-200 dark:border-red-800 text-red-800 dark:text-red-300'
              }`}
            >
              {statusMessage.type === 'success' ? (
                <CheckCircle2 className="w-4 h-4 shrink-0 mt-0.5 text-emerald-600 dark:text-emerald-400" />
              ) : (
                <AlertCircle className="w-4 h-4 shrink-0 mt-0.5 text-red-600 dark:text-red-400" />
              )}
              <div className="flex-1">
                <p>{statusMessage.text}</p>
                {statusMessage.link && (
                  <a
                    href={statusMessage.link}
                    target="_blank"
                    rel="noreferrer"
                    className="inline-flex items-center gap-1 font-semibold underline mt-1.5 hover:opacity-80"
                  >
                    <span>Open in Google Calendar</span>
                    <ExternalLink className="w-3 h-3" />
                  </a>
                )}
              </div>
            </div>
          )}

          {/* Connection Status Card */}
          <div className="p-4 border border-neutral-200 dark:border-neutral-700 rounded-xl bg-neutral-50/50 dark:bg-neutral-800/40 flex items-center justify-between">
            <div className="flex items-center gap-2.5">
              <span
                className={`w-2.5 h-2.5 rounded-full ${
                  isConnected ? 'bg-emerald-500 animate-pulse' : 'bg-neutral-400 dark:bg-neutral-600'
                }`}
              />
              <div>
                <div className="text-xs font-bold text-neutral-900 dark:text-white">
                  {isConnected ? 'Connected & Authorized' : 'Not Connected'}
                </div>
                <div className="text-[11px] text-neutral-500 dark:text-neutral-400">
                  {isConnected
                    ? `Account: ${connectedEmail}`
                    : 'Requires OAuth authorization with Gmail & Calendar scopes'}
                </div>
              </div>
            </div>

            {isConnected && (
              <button
                type="button"
                onClick={handleDisconnect}
                disabled={isLoading}
                className="text-xs font-semibold text-red-600 hover:text-red-700 dark:text-red-400 dark:hover:text-red-300 cursor-pointer"
              >
                Disconnect
              </button>
            )}
          </div>

          {/* Value Props & Scopes */}
          <div className="space-y-3">
            <div className="text-xs font-bold text-neutral-800 dark:text-neutral-200 uppercase tracking-wider text-[10px]">
              Included Capabilities
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
              <div className="p-3 rounded-xl border border-neutral-200/90 dark:border-neutral-800 bg-white dark:bg-neutral-850 space-y-1">
                <div className="flex items-center gap-1.5 font-bold text-neutral-900 dark:text-white">
                  <Mail className="w-4 h-4 text-rose-500" />
                  <span>Proactive Client Emails</span>
                </div>
                <p className="text-[11px] text-neutral-500 dark:text-neutral-400 leading-relaxed">
                  Send approved commitment status updates directly from your authorized corporate email account.
                </p>
              </div>

              <div className="p-3 rounded-xl border border-neutral-200/90 dark:border-neutral-800 bg-white dark:bg-neutral-850 space-y-1">
                <div className="flex items-center gap-1.5 font-bold text-neutral-900 dark:text-white">
                  <Calendar className="w-4 h-4 text-blue-500" />
                  <span>Calendar Milestone Sync</span>
                </div>
                <p className="text-[11px] text-neutral-500 dark:text-neutral-400 leading-relaxed">
                  Automatically sync delivery target dates into Google Calendar with early alerts before deadlines slip.
                </p>
              </div>
            </div>
          </div>

          {/* Action Trigger Buttons */}
          <div className="pt-2 space-y-3">
            {!isConnected ? (
              <button
                type="button"
                onClick={handleStartOAuth}
                disabled={isLoading}
                className="w-full py-3 px-4 rounded-xl text-xs sm:text-sm font-semibold transition-all cursor-pointer flex items-center justify-center gap-2 bg-neutral-900 hover:bg-neutral-800 text-white dark:bg-white dark:text-neutral-950 dark:hover:bg-neutral-100 shadow-sm"
              >
                <svg className="w-4 h-4 shrink-0" viewBox="0 0 24 24">
                  <path
                    fill="#4285F4"
                    d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
                  />
                  <path
                    fill="#34A853"
                    d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
                  />
                  <path
                    fill="#FBBC05"
                    d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.06H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.94l2.85-2.22.81-.63z"
                  />
                  <path
                    fill="#EA4335"
                    d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.06l3.66 2.84c.87-2.6 3.3-4.52 6.16-4.52z"
                  />
                </svg>
                <span>{isLoading ? 'Connecting...' : 'Authorize with Google'}</span>
              </button>
            ) : (
              <div className="flex flex-col sm:flex-row gap-2">
                <button
                  type="button"
                  onClick={handleTestCalendarSync}
                  disabled={isSyncingCalendar}
                  className="flex-1 py-2.5 px-3.5 rounded-lg border border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-800 hover:bg-neutral-50 dark:hover:bg-neutral-750 text-xs font-semibold text-neutral-800 dark:text-neutral-200 transition-colors flex items-center justify-center gap-1.5 cursor-pointer shadow-2xs"
                >
                  <Calendar className="w-3.5 h-3.5 text-blue-500" />
                  <span>{isSyncingCalendar ? 'Syncing...' : 'Test Calendar Sync'}</span>
                </button>
              </div>
            )}

            {/* Collapsible Manual Token Input for Developers */}
            <div className="pt-2">
              <button
                type="button"
                onClick={() => setShowManualToken(!showManualToken)}
                className="text-[11px] text-neutral-400 dark:text-neutral-500 hover:text-neutral-700 dark:hover:text-neutral-300 flex items-center gap-1 cursor-pointer"
              >
                <Terminal className="w-3 h-3" />
                <span>{showManualToken ? 'Hide manual token input' : 'Developer: Enter access token directly'}</span>
              </button>

              {showManualToken && (
                <form onSubmit={handleManualTokenSubmit} className="mt-3 p-3.5 rounded-xl border border-neutral-200 dark:border-neutral-800 bg-neutral-50 dark:bg-neutral-850 space-y-2.5">
                  <div>
                    <label className="text-[11px] font-semibold text-neutral-700 dark:text-neutral-300 block mb-1">
                      Google OAuth Access Token
                    </label>
                    <input
                      type="password"
                      placeholder="ya29.a0AcM612..."
                      value={manualToken}
                      onChange={(e) => setManualToken(e.target.value)}
                      required
                      className="w-full text-xs px-3 py-2 rounded-lg border border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-800 text-neutral-900 dark:text-white font-mono"
                    />
                  </div>

                  <div>
                    <label className="text-[11px] font-semibold text-neutral-700 dark:text-neutral-300 block mb-1">
                      Account Email (Optional)
                    </label>
                    <input
                      type="email"
                      placeholder="founder@acme.corp"
                      value={manualEmail}
                      onChange={(e) => setManualEmail(e.target.value)}
                      className="w-full text-xs px-3 py-2 rounded-lg border border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-800 text-neutral-900 dark:text-white"
                    />
                  </div>

                  <button
                    type="submit"
                    disabled={isLoading}
                    className="w-full py-2 rounded-lg bg-neutral-900 dark:bg-white text-white dark:text-neutral-900 text-xs font-semibold cursor-pointer hover:bg-neutral-800 dark:hover:bg-neutral-200 transition-colors"
                  >
                    {isLoading ? 'Saving...' : 'Register Access Token'}
                  </button>
                </form>
              )}
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="px-6 py-3.5 border-t border-neutral-100 dark:border-neutral-800 bg-neutral-50/50 dark:bg-neutral-850/50 flex items-center justify-between text-[11px] text-neutral-400">
          <div className="flex items-center gap-1.5">
            <ShieldCheck className="w-3.5 h-3.5 text-emerald-500" />
            <span>OAuth 2.0 PKCE with Tenant Isolation</span>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="px-3 py-1.5 rounded-lg border border-neutral-200 dark:border-neutral-700 text-neutral-700 dark:text-neutral-300 font-semibold cursor-pointer hover:bg-neutral-100 dark:hover:bg-neutral-800 transition-colors"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
};
