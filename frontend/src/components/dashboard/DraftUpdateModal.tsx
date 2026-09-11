import React, { useState } from 'react';
import { X, Send, CheckCircle2, MessageSquare, Mail, AlertCircle } from 'lucide-react';
import { Commitment } from '../../types/dashboard';

interface DraftUpdateModalProps {
  isOpen: boolean;
  onClose: () => void;
  commitment: Commitment | null;
  onSendUpdate: (channel: string, message: string) => void;
}

export const DraftUpdateModal: React.FC<DraftUpdateModalProps> = ({
  isOpen,
  onClose,
  commitment,
  onSendUpdate,
}) => {
  if (!isOpen || !commitment) return null;

  const [destination, setDestination] = useState<'slack' | 'email'>('slack');
  const [slackChannel, setSlackChannel] = useState('#customer-commitments');
  const [emailRecipient, setEmailRecipient] = useState('lead@acme.corp');
  const [isApproved, setIsApproved] = useState(false);
  const [isSent, setIsSent] = useState(false);

  const defaultMessage = `Hi ${commitment.customer} team,

Regarding our commitment on "${commitment.title}" (originally targeted for ${commitment.promisedBy}):

Our engineering team is currently finishing up ${commitment.engineeringEvidence?.ticketId || 'the rollout'}. Due to scheduled verification cycles, our target delivery date has been adjusted to ${commitment.engineeringEvidence?.targetDelivery || 'Oct 05, 2026'}.

We want to be completely transparent early and keep you updated on progress. Please let us know if you have any questions!

Best,
${commitment.owner.name}
PromiseCheck SaaS`;

  const [messageText, setMessageText] = useState(defaultMessage);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!isApproved) return;
    setIsSent(true);
    setTimeout(() => {
      onSendUpdate(destination === 'slack' ? slackChannel : emailRecipient, messageText);
      setIsSent(false);
      onClose();
    }, 1200);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-neutral-900/50 backdrop-blur-xs animate-in fade-in">
      <div className="bg-white dark:bg-neutral-900 rounded-2xl max-w-lg w-full border border-neutral-200 dark:border-neutral-800 shadow-xl overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-neutral-100 dark:border-neutral-800 bg-neutral-50/50 dark:bg-neutral-850/50">
          <div>
            <h3 className="text-base font-bold text-neutral-900 dark:text-white">Draft customer update</h3>
            <p className="text-xs text-neutral-500 dark:text-neutral-400">
              Isolated workspace communication for {commitment.customer}
            </p>
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded-lg text-neutral-400 dark:text-neutral-500 hover:text-neutral-700 dark:hover:text-neutral-200 hover:bg-neutral-100 dark:hover:bg-neutral-800 transition-colors cursor-pointer"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Body */}
        {isSent ? (
          <div className="p-8 text-center space-y-3">
            <div className="w-12 h-12 bg-emerald-100 dark:bg-emerald-950/50 text-emerald-600 dark:text-emerald-400 rounded-full flex items-center justify-center mx-auto">
              <CheckCircle2 className="w-6 h-6" />
            </div>
            <h4 className="font-bold text-neutral-900 dark:text-white text-base">Update Sent Successfully</h4>
            <p className="text-xs text-neutral-500 dark:text-neutral-400">
              Delivered to {destination === 'slack' ? slackChannel : emailRecipient} via isolated
              integration webhook.
            </p>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="p-6 space-y-4">
            {/* Destination Toggle */}
            <div className="space-y-1.5">
              <label className="text-xs font-semibold text-neutral-700 dark:text-neutral-300">Delivery Channel</label>
              <div className="grid grid-cols-2 gap-2">
                <button
                  type="button"
                  onClick={() => setDestination('slack')}
                  className={`flex items-center justify-center gap-2 py-2 px-3 rounded-lg border text-xs font-medium transition-all cursor-pointer ${
                    destination === 'slack'
                      ? 'border-neutral-900 dark:border-white bg-neutral-100 dark:bg-neutral-800 text-neutral-900 dark:text-white font-bold'
                      : 'border-neutral-200 dark:border-neutral-700 text-neutral-600 dark:text-neutral-400 hover:bg-neutral-50 dark:hover:bg-neutral-800/60'
                  }`}
                >
                  <MessageSquare className="w-3.5 h-3.5" />
                  <span>Slack Webhook</span>
                </button>

                <button
                  type="button"
                  onClick={() => setDestination('email')}
                  className={`flex items-center justify-center gap-2 py-2 px-3 rounded-lg border text-xs font-medium transition-all cursor-pointer ${
                    destination === 'email'
                      ? 'border-neutral-900 dark:border-white bg-neutral-100 dark:bg-neutral-800 text-neutral-900 dark:text-white font-bold'
                      : 'border-neutral-200 dark:border-neutral-700 text-neutral-600 dark:text-neutral-400 hover:bg-neutral-50 dark:hover:bg-neutral-800/60'
                  }`}
                >
                  <Mail className="w-3.5 h-3.5" />
                  <span>Customer Email</span>
                </button>
              </div>
            </div>

            {/* Target Channel or Email */}
            {destination === 'slack' ? (
              <div className="space-y-1">
                <label className="text-xs font-medium text-neutral-600 dark:text-neutral-400">
                  Target Slack Channel (Isolated to Acme Workspace)
                </label>
                <select
                  value={slackChannel}
                  onChange={(e) => setSlackChannel(e.target.value)}
                  className="w-full text-xs px-3 py-2 border border-neutral-200 dark:border-neutral-700 rounded-lg bg-white dark:bg-neutral-800 text-neutral-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-neutral-900/10 dark:focus:ring-neutral-600 focus:border-neutral-900 dark:focus:border-neutral-500"
                >
                  <option value="#customer-commitments">#customer-commitments (Default)</option>
                  <option value="#acme-delivery-alerts">#acme-delivery-alerts</option>
                  <option value="#client-updates">#client-updates</option>
                </select>
              </div>
            ) : (
              <div className="space-y-1">
                <label className="text-xs font-medium text-neutral-600 dark:text-neutral-400">Recipient Email</label>
                <input
                  type="email"
                  value={emailRecipient}
                  onChange={(e) => setEmailRecipient(e.target.value)}
                  className="w-full text-xs px-3 py-2 border border-neutral-200 dark:border-neutral-700 rounded-lg bg-white dark:bg-neutral-800 text-neutral-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-neutral-900/10 dark:focus:ring-neutral-600 focus:border-neutral-900 dark:focus:border-neutral-500"
                />
              </div>
            )}

            {/* Message Draft */}
            <div className="space-y-1">
              <label className="text-xs font-medium text-neutral-600 dark:text-neutral-400">Message Content</label>
              <textarea
                rows={7}
                value={messageText}
                onChange={(e) => setMessageText(e.target.value)}
                className="w-full text-xs p-3 border border-neutral-200 dark:border-neutral-700 rounded-lg bg-neutral-50/50 dark:bg-neutral-800/80 font-mono text-neutral-800 dark:text-neutral-100 focus:bg-white dark:focus:bg-neutral-800 focus:outline-none focus:ring-2 focus:ring-neutral-900/10 dark:focus:ring-neutral-600 focus:border-neutral-900 dark:focus:border-neutral-500 leading-relaxed"
              />
            </div>

            {/* Policy Notice & Approval Checkbox */}
            <div className="p-3 bg-neutral-50 dark:bg-neutral-800/60 rounded-xl border border-neutral-200/80 dark:border-neutral-700 space-y-2">
              <div className="flex items-start gap-2 text-[11px] text-neutral-500 dark:text-neutral-400">
                <AlertCircle className="w-3.5 h-3.5 text-neutral-400 dark:text-neutral-500 shrink-0 mt-0.5" />
                <span>
                  Policy requires explicit human approval before transmitting updates to external
                  destinations.
                </span>
              </div>
              <label className="flex items-center gap-2 cursor-pointer pt-1">
                <input
                  type="checkbox"
                  checked={isApproved}
                  onChange={(e) => setIsApproved(e.target.checked)}
                  className="rounded accent-neutral-900 dark:accent-white w-3.5 h-3.5"
                />
                <span className="text-xs font-semibold text-neutral-800 dark:text-neutral-200">
                  I review and approve this update for immediate delivery
                </span>
              </label>
            </div>

            {/* Submit Button */}
            <div className="flex items-center justify-end gap-2 pt-2">
              <button
                type="button"
                onClick={onClose}
                className="px-4 py-2 text-xs font-medium text-neutral-600 dark:text-neutral-300 hover:bg-neutral-100 dark:hover:bg-neutral-800 rounded-lg transition-colors cursor-pointer"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={!isApproved}
                className={`inline-flex items-center gap-1.5 px-4 py-2 text-xs font-medium rounded-lg transition-all ${
                  isApproved
                    ? 'bg-neutral-900 dark:bg-white text-white dark:text-neutral-900 hover:bg-neutral-800 dark:hover:bg-neutral-200 shadow-xs cursor-pointer active:scale-98'
                    : 'bg-neutral-300 dark:bg-neutral-800 text-neutral-500 dark:text-neutral-600 cursor-not-allowed'
                }`}
              >
                <Send className="w-3.5 h-3.5" />
                <span>Send {destination === 'slack' ? 'to Slack' : 'Email'}</span>
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
};
