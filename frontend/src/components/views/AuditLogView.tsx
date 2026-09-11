import React from 'react';
import { ShieldCheck, UserCheck, Send, CheckCircle2, Clock } from 'lucide-react';

export const AuditLogView: React.FC = () => {
  const auditEntries = [
    {
      id: 'aud-1',
      actor: 'Workspace Admin',
      action: 'Configured Slack Integration',
      details: 'Updated destination channel to #customer-commitments for workspace ws-acme-01',
      timestamp: 'Sep 24, 2026 · 14:10 EST',
      ip: '172.21.26.247',
    },
    {
      id: 'aud-2',
      actor: 'Maya Chen',
      action: 'Confirmed Commitment Terms',
      details: 'Reviewed and confirmed "Enable SSO for Acme" (target: Sep 30, 2026)',
      timestamp: 'Sep 23, 2026 · 16:42 EST',
      ip: '10.0.4.12',
    },
    {
      id: 'aud-3',
      actor: 'Celery Outbox Dispatcher',
      action: 'Synced Jira Issue Delivery',
      details: 'Jira ticket ENG-1042 target date updated from Sep 28 to Oct 05. Flagged conflict.',
      timestamp: 'Sep 23, 2026 · 16:30 EST',
      ip: 'Worker #2',
    },
    {
      id: 'aud-4',
      actor: 'Daniel Stone',
      action: 'Dispatched Customer Update',
      details: 'Transmitted proactive delay notification for "Export audit logs" to Northstar lead.',
      timestamp: 'Sep 22, 2026 · 11:15 EST',
      ip: '10.0.4.88',
    },
  ];

  return (
    <div className="flex-1 p-4 sm:p-6 lg:p-8 overflow-y-auto max-w-6xl mx-auto w-full">
      <div className="pb-6 border-b border-neutral-200">
        <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-neutral-900">
          Immutable Audit Log
        </h1>
        <p className="text-xs sm:text-sm text-neutral-500 mt-1">
          Cryptographically recorded log of approvals, outbound updates, and permission checks.
        </p>
      </div>

      <div className="bg-white border border-neutral-200 rounded-2xl overflow-hidden shadow-2xs mt-6">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead>
              <tr className="border-b border-neutral-100 text-[11px] font-semibold text-neutral-400 uppercase tracking-wider bg-neutral-50/50">
                <th className="py-3 px-5">Actor</th>
                <th className="py-3 px-4">Action</th>
                <th className="py-3 px-4">Details</th>
                <th className="py-3 px-4">Timestamp</th>
                <th className="py-3 px-5 text-right">Origin</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-neutral-100">
              {auditEntries.map((entry) => (
                <tr key={entry.id} className="hover:bg-neutral-50/70 transition-colors">
                  <td className="py-3.5 px-5 font-semibold text-neutral-900 whitespace-nowrap">
                    {entry.actor}
                  </td>
                  <td className="py-3.5 px-4 font-medium text-neutral-900 whitespace-nowrap">
                    {entry.action}
                  </td>
                  <td className="py-3.5 px-4 text-neutral-600 max-w-xs sm:max-w-sm truncate">
                    {entry.details}
                  </td>
                  <td className="py-3.5 px-4 text-neutral-400 whitespace-nowrap">
                    {entry.timestamp}
                  </td>
                  <td className="py-3.5 px-5 text-neutral-400 font-mono text-[11px] text-right whitespace-nowrap">
                    {entry.ip}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
