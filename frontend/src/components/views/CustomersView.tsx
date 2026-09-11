import React from 'react';
import { Users, FileText, ArrowRight, ShieldCheck, Building2 } from 'lucide-react';
import { ACCOUNTS } from '../../data/mockData';

interface CustomersViewProps {
  onSelectCustomer?: (customerName: string) => void;
}

export const CustomersView: React.FC<CustomersViewProps> = ({ onSelectCustomer }) => {
  return (
    <div className="flex-1 p-4 sm:p-6 lg:p-8 overflow-y-auto max-w-6xl mx-auto w-full">
      <div className="pb-6 border-b border-neutral-200">
        <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-neutral-900">
          Customer Accounts
        </h1>
        <p className="text-xs sm:text-sm text-neutral-500 mt-1">
          Review customer relationships, delivery health scores, and active commitments.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 mt-6">
        {ACCOUNTS.map((acc) => (
          <div
            key={acc.id}
            onClick={() => onSelectCustomer && onSelectCustomer(acc.name)}
            className="bg-white border border-neutral-200/90 rounded-2xl p-5 shadow-2xs hover:border-neutral-400 hover:shadow-xs transition-all cursor-pointer flex flex-col justify-between"
          >
            <div>
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-2.5">
                  <div className="w-9 h-9 rounded-xl bg-neutral-100 text-neutral-800 flex items-center justify-center font-bold text-sm border border-neutral-200">
                    <Building2 className="w-4 h-4" />
                  </div>
                  <div>
                    <h3 className="font-bold text-sm text-neutral-900">{acc.name}</h3>
                    <div className="text-[11px] text-neutral-400">Account Owner: {acc.owner}</div>
                  </div>
                </div>

                <span
                  className={`text-[11px] font-semibold px-2 py-0.5 rounded-full ${
                    acc.status === 'on-track'
                      ? 'bg-emerald-100/80 text-emerald-800'
                      : 'bg-amber-100/80 text-amber-800'
                  }`}
                >
                  {acc.status === 'on-track' ? 'Healthy' : 'At Risk'}
                </span>
              </div>

              <div className="space-y-2 py-3 border-y border-neutral-100 text-xs">
                <div className="flex items-center justify-between text-neutral-500">
                  <span>Active commitments</span>
                  <span className="font-bold text-neutral-800">{acc.activePromises}</span>
                </div>
                <div className="flex items-center justify-between text-neutral-500">
                  <span>Delivery health index</span>
                  <span className="font-bold text-neutral-800">{acc.healthScore}%</span>
                </div>
                <div className="text-[11px] text-neutral-500 pt-1">
                  Latest promise:{' '}
                  <span className="font-medium text-neutral-700 italic">"{acc.recentPromise}"</span>
                </div>
              </div>
            </div>

            <div className="pt-3 flex items-center justify-between text-xs text-neutral-900 font-semibold hover:text-neutral-700">
              <span>View account commitments</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
