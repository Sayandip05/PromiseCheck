import React, { useState, useEffect } from 'react';
import {
  X,
  CheckCircle2,
  AlertCircle,
  ExternalLink,
  Loader2,
  Trash2,
  Search,
  FileText,
} from 'lucide-react';
import { Workspace } from '../../types/dashboard';
import { GoogleDriveLogo } from '../ui/BrandLogos';
import { api, explainError } from '../../lib/api';

interface GoogleDriveIntegrationModalProps {
  isOpen: boolean;
  onClose: () => void;
  workspace: Workspace;
  onIntegrationUpdated?: () => void;
}

export const GoogleDriveIntegrationModal: React.FC<GoogleDriveIntegrationModalProps> = ({
  isOpen,
  onClose,
  workspace,
  onIntegrationUpdated,
}) => {
  const [accessToken, setAccessToken] = useState('');
  const [folderScope, setFolderScope] = useState('Customer Folders & MSA Contracts');

  const [isConnected, setIsConnected] = useState(true);
  const [statusText, setStatusText] = useState('Connected to Google Workspace Drive');
  const [isLoading, setIsLoading] = useState(false);
  const [isTesting, setIsTesting] = useState(false);
  const [queriedDocs, setQueriedDocs] = useState<any[]>([]);
  const [statusMessage, setStatusMessage] = useState<{
    type: 'success' | 'error';
    text: string;
    details?: any;
  } | null>(null);

  useEffect(() => {
    if (!isOpen) return;
    setStatusMessage(null);
    setQueriedDocs([]);
    api.integrations
      .list()
      .then((items) => {
        const drive = items.find((i: any) => i.provider === 'google_drive');
        if (drive) {
          setIsConnected(Boolean(drive.connected));
          setStatusText(drive.statusText || '');
          if (drive.channelOrScope) {
            setFolderScope(drive.channelOrScope);
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
      const res = await api.integrations.test('google_drive', {
        access_token: accessToken.trim() || undefined,
        scope: folderScope.trim() || undefined,
      });
      const docs = res.details?.documents || [];
      setQueriedDocs(docs);
      setStatusMessage({
        type: 'success',
        text: res.message || 'Google Drive verified! Accessible files queried.',
        details: res.details,
      });
    } catch (err: any) {
      setStatusMessage({
        type: 'error',
        text: explainError(err, 'Failed to query Google Drive. Verify token permissions.'),
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
      await api.integrations.connect('google_drive', {
        access_token: accessToken.trim() || undefined,
        scope: folderScope.trim() || 'Customer Folders & MSA Contracts',
      });
      setIsConnected(true);
      setStatusMessage({
        type: 'success',
        text: 'Google Drive configuration saved and synchronized!',
      });
      if (onIntegrationUpdated) onIntegrationUpdated();
      setTimeout(() => {
        onClose();
      }, 1000);
    } catch (err: any) {
      setStatusMessage({
        type: 'error',
        text: explainError(err, 'Failed to save Google Drive configuration.'),
      });
    } finally {
      setIsLoading(false);
    }
  };

  const handleDisconnect = async () => {
    if (!window.confirm('Are you sure you want to disconnect Google Drive?')) return;
    setIsLoading(true);
    setStatusMessage(null);
    try {
      await api.integrations.disconnect('google_drive');
      setIsConnected(false);
      setStatusText('Disconnected');
      setQueriedDocs([]);
      setStatusMessage({
        type: 'success',
        text: 'Google Drive disconnected from active workspace.',
      });
      if (onIntegrationUpdated) onIntegrationUpdated();
    } catch (err: any) {
      setStatusMessage({
        type: 'error',
        text: explainError(err, 'Failed to disconnect Google Drive.'),
      });
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-xs animate-in fade-in duration-150">
      <div className="bg-white dark:bg-neutral-900 border border-neutral-200 dark:border-neutral-800 rounded-2xl w-full max-w-lg shadow-2xl overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-neutral-100 dark:border-neutral-800">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-emerald-50 dark:bg-emerald-950/60 rounded-xl border border-emerald-100 dark:border-emerald-900">
              <GoogleDriveLogo className="w-5 h-5 shrink-0" />
            </div>
            <div>
              <h3 className="text-base font-bold text-neutral-900 dark:text-white">Google Drive</h3>
              <p className="text-xs text-neutral-500 dark:text-neutral-400">
                Customer Folders, MSA Contracts & Deliverable Scans
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 text-neutral-400 hover:text-neutral-600 dark:hover:text-neutral-200 rounded-lg transition-colors cursor-pointer"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Form Body */}
        <form onSubmit={handleSave} className="p-6 space-y-4">
          {statusMessage && (
            <div
              className={`p-3.5 rounded-xl text-xs flex items-start gap-2.5 ${
                statusMessage.type === 'success'
                  ? 'bg-emerald-50 dark:bg-emerald-950/40 text-emerald-800 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800'
                  : 'bg-rose-50 dark:bg-rose-950/40 text-rose-800 dark:text-rose-300 border border-rose-200 dark:border-rose-800'
              }`}
            >
              {statusMessage.type === 'success' ? (
                <CheckCircle2 className="w-4 h-4 shrink-0 text-emerald-600 dark:text-emerald-400 mt-0.5" />
              ) : (
                <AlertCircle className="w-4 h-4 shrink-0 text-rose-600 dark:text-rose-400 mt-0.5" />
              )}
              <div className="flex-1 leading-relaxed">{statusMessage.text}</div>
            </div>
          )}

          {/* Connection Status Banner */}
          <div className="flex items-center justify-between p-3.5 bg-neutral-50 dark:bg-neutral-800/60 rounded-xl border border-neutral-100 dark:border-neutral-800">
            <div className="flex items-center gap-2.5">
              <div
                className={`w-2.5 h-2.5 rounded-full ${
                  isConnected ? 'bg-emerald-500 shadow-xs shadow-emerald-500/50' : 'bg-neutral-300 dark:bg-neutral-600'
                }`}
              />
              <div>
                <div className="text-xs font-semibold text-neutral-800 dark:text-neutral-200">
                  {isConnected ? 'Google Drive Connected' : 'Not Configured'}
                </div>
                <div className="text-[10px] text-neutral-400 dark:text-neutral-500">
                  {statusText || (isConnected ? 'Auto-scanning customer contracts' : 'Provide token or link account')}
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

          {/* Folder Scope */}
          <div className="space-y-1.5">
            <label className="text-xs font-semibold text-neutral-700 dark:text-neutral-300 flex items-center justify-between">
              <span>Drive Target Folder Scope</span>
              <span className="text-[10px] text-neutral-400">Query / Folder filter</span>
            </label>
            <input
              type="text"
              value={folderScope}
              onChange={(e) => setFolderScope(e.target.value)}
              placeholder="Customer Folders & MSA Contracts"
              className="w-full text-xs px-3 py-2 border border-neutral-200 dark:border-neutral-700 rounded-lg bg-white dark:bg-neutral-800 text-neutral-900 dark:text-white font-medium focus:outline-none focus:ring-2 focus:ring-neutral-900/10 dark:focus:ring-neutral-600"
            />
            <p className="text-[10px] text-neutral-400 dark:text-neutral-500">
              Restricts automatic commitment extraction to shared client folders and legal contracts.
            </p>
          </div>

          {/* Access Token Override */}
          <div className="space-y-1.5">
            <div className="flex items-center justify-between">
              <label className="text-xs font-semibold text-neutral-700 dark:text-neutral-300">
                Access Token / Service Account Override (Optional)
              </label>
              <span className="text-[10px] text-neutral-400">Uses Workspace OAuth if omitted</span>
            </div>
            <input
              type="password"
              value={accessToken}
              onChange={(e) => setAccessToken(e.target.value)}
              placeholder="ya29.a0AfH6SM..."
              className="w-full text-xs px-3 py-2 border border-neutral-200 dark:border-neutral-700 rounded-lg bg-white dark:bg-neutral-800 text-neutral-900 dark:text-white font-mono focus:outline-none focus:ring-2 focus:ring-neutral-900/10 dark:focus:ring-neutral-600"
            />
          </div>

          {/* Document Preview List if tested */}
          {queriedDocs.length > 0 && (
            <div className="space-y-1.5 pt-2">
              <div className="text-[11px] font-semibold text-neutral-700 dark:text-neutral-300 flex items-center gap-1.5">
                <FileText className="w-3.5 h-3.5 text-neutral-500" />
                <span>Accessible Documents ({queriedDocs.length})</span>
              </div>
              <div className="max-h-32 overflow-y-auto space-y-1 bg-neutral-50 dark:bg-neutral-800/40 p-2 rounded-lg border border-neutral-200 dark:border-neutral-800">
                {queriedDocs.map((doc: any) => (
                  <div key={doc.id} className="text-[11px] text-neutral-700 dark:text-neutral-300 flex items-center justify-between">
                    <span className="truncate max-w-[280px] font-medium">{doc.name}</span>
                    <span className="text-[9px] text-neutral-400 shrink-0 font-mono">{doc.mimeType?.split('.').pop() || 'file'}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

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
              <span>{isTesting ? 'Scanning Drive...' : 'Test Connection'}</span>
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
