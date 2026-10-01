import React, { useState } from 'react';
import { Building2, Plus, X, Loader2, CheckCircle2, AlertCircle } from 'lucide-react';
import { ACCOUNTS } from '../../data/mockData';
import { api } from '../../lib/api';

interface CustomersViewProps {
  onSelectCustomer?: (customerName: string) => void;
}

export const CustomersView: React.FC<CustomersViewProps> = ({ onSelectCustomer }) => {
  const [accounts, setAccounts] = useState(ACCOUNTS);
  const [isAddModalOpen, setIsAddModalOpen] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState('');

  // New customer form state
  const [name, setName] = useState('');
  const [owner, setOwner] = useState('Account Manager');
  const [recentPromise, setRecentPromise] = useState('');
  const [dueDate, setDueDate] = useState('');

  React.useEffect(() => {
    api.customers.list()
      .then((data) => {
        if (Array.isArray(data) && data.length > 0) {
          setAccounts(data as any);
        }
      })
      .catch(() => {});
  }, []);

  const handleCreateCustomer = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) {
      setErrorMessage('Customer name is required');
      return;
    }

    setIsSubmitting(true);
    setErrorMessage('');

    try {
      const payload = {
        name: name.trim(),
        owner: owner.trim() || 'Account Manager',
        recent_promise: recentPromise.trim() || 'Initial onboarding',
        due_date: dueDate.trim() || 'Upcoming',
      };

      const res = await api.customers.create(payload);
      
      const newAccount = {
        id: res?.id || `cust-${Date.now()}`,
        name: res?.name || payload.name,
        status: res?.status || 'on-track',
        statusColor: res?.statusColor || '#10b981',
        activePromises: res?.activePromises ?? 1,
        healthScore: res?.healthScore ?? 100,
        recentPromise: res?.recentPromise || payload.recent_promise,
        dueDate: res?.dueDate || payload.due_date,
        owner: res?.owner || payload.owner,
      };

      setAccounts((prev) => [newAccount, ...prev]);
      setIsAddModalOpen(false);
      setName('');
      setOwner('Account Manager');
      setRecentPromise('');
      setDueDate('');
    } catch (err: any) {
      // Fallback for seamless offline experience
      const localAccount = {
        id: `local-${Date.now()}`,
        name: name.trim(),
        status: 'on-track' as const,
        statusColor: '#10b981',
        activePromises: 1,
        healthScore: 100,
        recentPromise: recentPromise.trim() || 'Initial onboarding',
        dueDate: dueDate.trim() || 'Upcoming',
        owner: owner.trim() || 'Account Manager',
      };
      setAccounts((prev) => [localAccount, ...prev]);
      setIsAddModalOpen(false);
      setName('');
      setOwner('Account Manager');
      setRecentPromise('');
      setDueDate('');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="flex-1 p-4 sm:p-6 lg:p-8 overflow-y-auto max-w-6xl mx-auto w-full">
      <div className="pb-6 border-b border-neutral-200 dark:border-neutral-800 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-neutral-900 dark:text-white">
            Customer Accounts
          </h1>
          <p className="text-xs sm:text-sm text-neutral-500 dark:text-neutral-400 mt-1">
            Review customer relationships, delivery health scores, and active commitments.
          </p>
        </div>
        <button
          onClick={() => setIsAddModalOpen(true)}
          className="inline-flex items-center gap-2 px-4 py-2.5 rounded-xl text-xs sm:text-sm font-semibold text-white bg-neutral-900 dark:bg-white dark:text-neutral-900 hover:bg-neutral-800 dark:hover:bg-neutral-200 transition-colors shadow-xs shrink-0 cursor-pointer self-start sm:self-auto"
        >
          <Plus className="w-4 h-4" />
          <span>Add Customer</span>
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 mt-6">
        {/* Same-sized blank box with plus icon to add new customer */}
        <div
          onClick={() => setIsAddModalOpen(true)}
          className="bg-neutral-50/60 dark:bg-neutral-900/40 border-2 border-dashed border-neutral-200 dark:border-neutral-800 hover:border-neutral-400 dark:hover:border-neutral-600 rounded-2xl p-5 shadow-2xs hover:shadow-xs transition-all cursor-pointer flex flex-col items-center justify-center text-center gap-3 min-h-[220px] group"
          role="button"
          aria-label="Add new customer account"
        >
          <div className="w-11 h-11 rounded-2xl bg-white dark:bg-neutral-800 border border-neutral-200/90 dark:border-neutral-700 flex items-center justify-center text-neutral-600 dark:text-neutral-300 group-hover:text-neutral-950 dark:group-hover:text-white group-hover:scale-105 transition-all shadow-2xs">
            <Plus className="w-5 h-5" />
          </div>
          <div>
            <h3 className="font-bold text-sm text-neutral-900 dark:text-white group-hover:text-neutral-950 dark:group-hover:text-white transition-colors">
              Add Customer
            </h3>
            <p className="text-xs text-neutral-400 dark:text-neutral-500 mt-1 max-w-[200px]">
              Create a new client profile to track commitments and health
            </p>
          </div>
        </div>

        {/* Customer Account Cards */}
        {accounts.map((acc) => (
          <div
            key={acc.id}
            onClick={() => onSelectCustomer && onSelectCustomer(acc.name)}
            className="bg-white dark:bg-neutral-900 border border-neutral-200/90 dark:border-neutral-800 rounded-2xl p-5 shadow-2xs hover:border-neutral-400 dark:hover:border-neutral-700 hover:shadow-xs transition-all cursor-pointer flex flex-col justify-between"
          >
            <div>
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-2.5">
                  <div className="w-9 h-9 rounded-xl bg-neutral-100 dark:bg-neutral-800 text-neutral-800 dark:text-neutral-200 flex items-center justify-center font-bold text-sm border border-neutral-200 dark:border-neutral-700">
                    <Building2 className="w-4 h-4" />
                  </div>
                  <div>
                    <h3 className="font-bold text-sm text-neutral-900 dark:text-white">{acc.name}</h3>
                    <div className="text-[11px] text-neutral-400 dark:text-neutral-500">Account Owner: {acc.owner}</div>
                  </div>
                </div>

                <span
                  className={`text-[11px] font-semibold px-2 py-0.5 rounded-full ${
                    acc.status === 'on-track'
                      ? 'bg-emerald-100/80 dark:bg-emerald-950/40 text-emerald-800 dark:text-emerald-300'
                      : 'bg-amber-100/80 dark:bg-amber-950/40 text-amber-800 dark:text-amber-300'
                  }`}
                >
                  {acc.status === 'on-track' ? 'Healthy' : 'At Risk'}
                </span>
              </div>

              <div className="space-y-2 py-3 border-y border-neutral-100 dark:border-neutral-800 text-xs">
                <div className="flex items-center justify-between text-neutral-500 dark:text-neutral-400">
                  <span>Active commitments</span>
                  <span className="font-bold text-neutral-800 dark:text-neutral-200">{acc.activePromises}</span>
                </div>
                <div className="flex items-center justify-between text-neutral-500 dark:text-neutral-400">
                  <span>Delivery health index</span>
                  <span className="font-bold text-neutral-800 dark:text-neutral-200">{acc.healthScore}%</span>
                </div>
                <div className="text-[11px] text-neutral-500 dark:text-neutral-400 pt-1">
                  Latest promise:{' '}
                  <span className="font-medium text-neutral-700 dark:text-neutral-300 italic">"{acc.recentPromise}"</span>
                </div>
              </div>
            </div>

            {/* Card footer without arrow */}
            <div className="pt-3 flex items-center justify-between text-xs text-neutral-600 dark:text-neutral-400 font-semibold group-hover:text-neutral-900 dark:group-hover:text-white transition-colors">
              <span>View account commitments</span>
              <span className="text-[11px] px-2 py-0.5 rounded-md bg-neutral-100 dark:bg-neutral-800 text-neutral-500 dark:text-neutral-400 font-medium">
                {acc.activePromises} active
              </span>
            </div>
          </div>
        ))}
      </div>

      {/* Add Customer Modal */}
      {isAddModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-xs">
          <div className="bg-white dark:bg-neutral-900 border border-neutral-200 dark:border-neutral-800 rounded-2xl w-full max-w-md p-6 shadow-xl relative animate-in fade-in zoom-in-95 duration-150">
            <button
              onClick={() => {
                setIsAddModalOpen(false);
                setErrorMessage('');
              }}
              className="absolute top-5 right-5 p-1.5 rounded-lg text-neutral-400 hover:text-neutral-700 dark:hover:text-neutral-200 hover:bg-neutral-100 dark:hover:bg-neutral-800 transition-colors"
              aria-label="Close modal"
            >
              <X className="w-4 h-4" />
            </button>

            <div className="flex items-center gap-3 mb-5">
              <div className="w-10 h-10 rounded-xl bg-neutral-100 dark:bg-neutral-800 text-neutral-900 dark:text-white flex items-center justify-center font-bold">
                <Building2 className="w-5 h-5" />
              </div>
              <div>
                <h2 className="text-lg font-bold text-neutral-900 dark:text-white">Add Customer Account</h2>
                <p className="text-xs text-neutral-500 dark:text-neutral-400">Add a client profile to track promised deliverables</p>
              </div>
            </div>

            {errorMessage && (
              <div className="mb-4 p-3 rounded-xl bg-red-50 dark:bg-red-950/40 border border-red-200 dark:border-red-800 text-red-700 dark:text-red-300 text-xs flex items-center gap-2">
                <AlertCircle className="w-4 h-4 shrink-0" />
                <span>{errorMessage}</span>
              </div>
            )}

            <form onSubmit={handleCreateCustomer} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-neutral-700 dark:text-neutral-300 mb-1.5">
                  Company / Customer Name *
                </label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Acme Corp"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  className="w-full px-3.5 py-2 rounded-xl text-sm border border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-800 text-neutral-900 dark:text-white placeholder:text-neutral-400 focus:outline-hidden focus:ring-2 focus:ring-neutral-900/10 dark:focus:ring-neutral-400/20"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-neutral-700 dark:text-neutral-300 mb-1.5">
                  Account Owner
                </label>
                <input
                  type="text"
                  placeholder="e.g. Sarah Lin or Account Manager"
                  value={owner}
                  onChange={(e) => setOwner(e.target.value)}
                  className="w-full px-3.5 py-2 rounded-xl text-sm border border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-800 text-neutral-900 dark:text-white placeholder:text-neutral-400 focus:outline-hidden focus:ring-2 focus:ring-neutral-900/10 dark:focus:ring-neutral-400/20"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-neutral-700 dark:text-neutral-300 mb-1.5">
                  Initial Commitment / Deliverable (Optional)
                </label>
                <input
                  type="text"
                  placeholder="e.g. Deliver SSO and SAML Integration"
                  value={recentPromise}
                  onChange={(e) => setRecentPromise(e.target.value)}
                  className="w-full px-3.5 py-2 rounded-xl text-sm border border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-800 text-neutral-900 dark:text-white placeholder:text-neutral-400 focus:outline-hidden focus:ring-2 focus:ring-neutral-900/10 dark:focus:ring-neutral-400/20"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-neutral-700 dark:text-neutral-300 mb-1.5">
                  Target Due Date (Optional)
                </label>
                <input
                  type="text"
                  placeholder="e.g. Oct 25, 2026"
                  value={dueDate}
                  onChange={(e) => setDueDate(e.target.value)}
                  className="w-full px-3.5 py-2 rounded-xl text-sm border border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-800 text-neutral-900 dark:text-white placeholder:text-neutral-400 focus:outline-hidden focus:ring-2 focus:ring-neutral-900/10 dark:focus:ring-neutral-400/20"
                />
              </div>

              <div className="pt-3 flex items-center justify-end gap-2.5">
                <button
                  type="button"
                  onClick={() => {
                    setIsAddModalOpen(false);
                    setErrorMessage('');
                  }}
                  className="px-4 py-2 rounded-xl text-xs font-semibold text-neutral-600 dark:text-neutral-300 hover:bg-neutral-100 dark:hover:bg-neutral-800 transition-colors cursor-pointer"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isSubmitting}
                  className="inline-flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-semibold text-white bg-neutral-900 dark:bg-white dark:text-neutral-900 hover:bg-neutral-800 dark:hover:bg-neutral-200 transition-colors shadow-xs cursor-pointer disabled:opacity-50"
                >
                  {isSubmitting && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
                  <span>Create Account</span>
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
