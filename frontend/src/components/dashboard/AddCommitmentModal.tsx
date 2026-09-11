import React, { useState } from 'react';
import { X, Plus, CheckCircle2 } from 'lucide-react';
import { Commitment } from '../../types/dashboard';

interface AddCommitmentModalProps {
  isOpen: boolean;
  onClose: () => void;
  onAddCommitment: (newCommitment: Partial<Commitment>) => void;
}

export const AddCommitmentModal: React.FC<AddCommitmentModalProps> = ({
  isOpen,
  onClose,
  onAddCommitment,
}) => {
  if (!isOpen) return null;

  const [title, setTitle] = useState('');
  const [customer, setCustomer] = useState('Acme');
  const [ownerName, setOwnerName] = useState('Maya Chen');
  const [promisedDate, setPromisedDate] = useState('2026-10-15');
  const [quote, setQuote] = useState('');
  const [ticketId, setTicketId] = useState('');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!title.trim()) return;

    onAddCommitment({
      id: `comm-${Date.now()}`,
      title,
      customer,
      owner: {
        name: ownerName,
        initials: ownerName
          .split(' ')
          .map((n) => n[0])
          .join(''),
        avatarColor: 'bg-neutral-200 text-neutral-800',
      },
      promisedBy: new Date(promisedDate).toLocaleDateString('en-US', {
        month: 'short',
        day: '2-digit',
        year: 'numeric',
      }),
      promisedDateIso: promisedDate,
      status: 'confirmed',
      statusLabel: 'On track',
      isConfirmed: true,
      category: 'on-track',
      originalPromise: {
        quote: quote || `Commitment manually logged: ${title}`,
        sourceTitle: 'Manual dashboard entry',
        timestamp: 'Just now',
      },
      engineeringEvidence: ticketId
        ? {
            ticketId,
            ticketTitle: title,
            status: 'In progress',
            targetDelivery: new Date(promisedDate).toLocaleDateString('en-US', {
              month: 'short',
              day: '2-digit',
              year: 'numeric',
            }),
            syncedAt: 'Just now',
            provider: 'jira',
          }
        : undefined,
    });

    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-neutral-900/50 backdrop-blur-xs animate-in fade-in">
      <div className="bg-white dark:bg-neutral-900 rounded-2xl max-w-md w-full border border-neutral-200 dark:border-neutral-800 shadow-xl overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-neutral-100 dark:border-neutral-800 bg-neutral-50/50 dark:bg-neutral-850/50">
          <div>
            <h3 className="text-base font-bold text-neutral-900 dark:text-white">Add commitment</h3>
            <p className="text-xs text-neutral-500 dark:text-neutral-400">Record a new verified customer promise</p>
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded-lg text-neutral-400 dark:text-neutral-500 hover:text-neutral-700 dark:hover:text-neutral-200 hover:bg-neutral-100 dark:hover:bg-neutral-800 transition-colors cursor-pointer"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          <div className="space-y-1">
            <label className="text-xs font-semibold text-neutral-700 dark:text-neutral-300">Commitment Title</label>
            <input
              type="text"
              required
              placeholder="e.g. Enable SSO, Deliver SOC2 Report"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              className="w-full text-xs px-3 py-2 border border-neutral-200 dark:border-neutral-700 rounded-lg bg-white dark:bg-neutral-800 text-neutral-900 dark:text-white placeholder:text-neutral-400 dark:placeholder:text-neutral-500 focus:outline-none focus:ring-2 focus:ring-neutral-900/10 dark:focus:ring-neutral-600 focus:border-neutral-900 dark:focus:border-neutral-500"
            />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1">
              <label className="text-xs font-semibold text-neutral-700 dark:text-neutral-300">Customer</label>
              <select
                value={customer}
                onChange={(e) => setCustomer(e.target.value)}
                className="w-full text-xs px-3 py-2 border border-neutral-200 dark:border-neutral-700 rounded-lg bg-white dark:bg-neutral-800 text-neutral-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-neutral-900/10 dark:focus:ring-neutral-600 focus:border-neutral-900 dark:focus:border-neutral-500"
              >
                <option value="Acme">Acme</option>
                <option value="Northstar">Northstar</option>
                <option value="Orbit">Orbit</option>
                <option value="Pine Labs">Pine Labs</option>
              </select>
            </div>

            <div className="space-y-1">
              <label className="text-xs font-semibold text-neutral-700 dark:text-neutral-300">Owner</label>
              <select
                value={ownerName}
                onChange={(e) => setOwnerName(e.target.value)}
                className="w-full text-xs px-3 py-2 border border-neutral-200 dark:border-neutral-700 rounded-lg bg-white dark:bg-neutral-800 text-neutral-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-neutral-900/10 dark:focus:ring-neutral-600 focus:border-neutral-900 dark:focus:border-neutral-500"
              >
                <option value="Maya Chen">Maya Chen</option>
                <option value="Daniel Stone">Daniel Stone</option>
                <option value="Priya Sharma">Priya Sharma</option>
                <option value="Alex Rivera">Alex Rivera</option>
              </select>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1">
              <label className="text-xs font-semibold text-neutral-700 dark:text-neutral-300">Promised Date</label>
              <input
                type="date"
                required
                value={promisedDate}
                onChange={(e) => setPromisedDate(e.target.value)}
                className="w-full text-xs px-3 py-2 border border-neutral-200 dark:border-neutral-700 rounded-lg bg-white dark:bg-neutral-800 text-neutral-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-neutral-900/10 dark:focus:ring-neutral-600 focus:border-neutral-900 dark:focus:border-neutral-500"
              />
            </div>

            <div className="space-y-1">
              <label className="text-xs font-semibold text-neutral-700 dark:text-neutral-300">
                Jira / Linear Ticket (Optional)
              </label>
              <input
                type="text"
                placeholder="e.g. ENG-1042"
                value={ticketId}
                onChange={(e) => setTicketId(e.target.value)}
                className="w-full text-xs px-3 py-2 border border-neutral-200 dark:border-neutral-700 rounded-lg bg-white dark:bg-neutral-800 text-neutral-900 dark:text-white placeholder:text-neutral-400 dark:placeholder:text-neutral-500 focus:outline-none focus:ring-2 focus:ring-neutral-900/10 dark:focus:ring-neutral-600 focus:border-neutral-900 dark:focus:border-neutral-500"
              />
            </div>
          </div>

          <div className="space-y-1">
            <label className="text-xs font-semibold text-neutral-700 dark:text-neutral-300">
              Original Promise Quote or Context
            </label>
            <textarea
              rows={3}
              placeholder="Quote or agreement from meeting..."
              value={quote}
              onChange={(e) => setQuote(e.target.value)}
              className="w-full text-xs p-3 border border-neutral-200 dark:border-neutral-700 rounded-lg bg-white dark:bg-neutral-800 text-neutral-900 dark:text-white placeholder:text-neutral-400 dark:placeholder:text-neutral-500 focus:outline-none focus:ring-2 focus:ring-neutral-900/10 dark:focus:ring-neutral-600 focus:border-neutral-900 dark:focus:border-neutral-500"
            />
          </div>

          {/* Buttons */}
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
              className="inline-flex items-center gap-1.5 px-4 py-2 text-xs font-medium bg-neutral-900 dark:bg-white hover:bg-neutral-800 dark:hover:bg-neutral-200 text-white dark:text-neutral-900 rounded-lg transition-all shadow-xs cursor-pointer active:scale-98"
            >
              <Plus className="w-3.5 h-3.5" />
              <span>Create commitment</span>
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
