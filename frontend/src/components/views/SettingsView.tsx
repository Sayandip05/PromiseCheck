import React from 'react';
import { Settings, Shield, Users, Key, Building2, Bell } from 'lucide-react';
import { Workspace } from '../../types/dashboard';

interface SettingsViewProps {
  workspace: Workspace;
}

export const SettingsView: React.FC<SettingsViewProps> = ({ workspace }) => {
  return (
    <div className="flex-1 p-4 sm:p-6 lg:p-8 overflow-y-auto max-w-4xl mx-auto w-full">
      <div className="pb-6 border-b border-neutral-200">
        <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-neutral-900">
          Workspace Settings
        </h1>
        <p className="text-xs sm:text-sm text-neutral-500 mt-1">
          Manage tenant configuration, team memberships, and security policies.
        </p>
      </div>

      <div className="space-y-6 mt-6">
        {/* Workspace Identity Card */}
        <div className="bg-white border border-neutral-200 rounded-2xl p-6 shadow-2xs">
          <div className="flex items-center gap-3 mb-4">
            <div className="w-10 h-10 rounded-xl bg-neutral-100 text-neutral-800 flex items-center justify-center font-bold">
              <Building2 className="w-5 h-5" />
            </div>
            <div>
              <h3 className="font-bold text-sm text-neutral-900">Tenant Workspace</h3>
              <p className="text-xs text-neutral-500">Workspace ID: <code className="font-mono text-neutral-800 font-semibold">{workspace.id}</code></p>
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs">
            <div>
              <label className="font-semibold text-neutral-700 block mb-1">Workspace Name</label>
              <input
                type="text"
                defaultValue={workspace.name}
                className="w-full px-3 py-2 border border-neutral-200 rounded-lg bg-white"
              />
            </div>

            <div>
              <label className="font-semibold text-neutral-700 block mb-1">Subscription Tier</label>
              <input
                type="text"
                disabled
                defaultValue={workspace.plan}
                className="w-full px-3 py-2 border border-neutral-200 rounded-lg bg-neutral-50 text-neutral-500 font-semibold"
              />
            </div>
          </div>
        </div>

        {/* Security & Access Policy Card */}
        <div className="bg-white border border-neutral-200 rounded-2xl p-6 shadow-2xs">
          <h3 className="font-bold text-sm text-neutral-900 mb-1 flex items-center gap-2">
            <Shield className="w-4 h-4 text-neutral-700" />
            <span>Customer Communication Safety Rules</span>
          </h3>
          <p className="text-xs text-neutral-500 mb-4">
            Controls and approval workflows for outbound Slack messages and emails.
          </p>

          <div className="space-y-3 text-xs">
            <label className="flex items-center justify-between p-3 rounded-xl border border-neutral-100 hover:bg-neutral-50 cursor-pointer">
              <div>
                <span className="font-semibold text-neutral-800 block">Require Human Review for Customer Messages</span>
                <span className="text-[11px] text-neutral-400">Never allow AI to automatically dispatch an external update without owner confirmation.</span>
              </div>
              <input type="checkbox" defaultChecked className="rounded accent-neutral-900 w-4 h-4" />
            </label>

            <label className="flex items-center justify-between p-3 rounded-xl border border-neutral-100 hover:bg-neutral-50 cursor-pointer">
              <div>
                <span className="font-semibold text-neutral-800 block">Redact Raw Transcripts from External Exports</span>
                <span className="text-[11px] text-neutral-400">Only export verified quotes; never leak unredacted meeting audio or raw text.</span>
              </div>
              <input type="checkbox" defaultChecked className="rounded accent-neutral-900 w-4 h-4" />
            </label>
          </div>
        </div>

        {/* Team Members Card */}
        <div className="bg-white border border-neutral-200 rounded-2xl p-6 shadow-2xs">
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-bold text-sm text-neutral-900 flex items-center gap-2">
              <Users className="w-4 h-4 text-neutral-600" />
              <span>Workspace Members</span>
            </h3>
            <button className="text-xs font-semibold text-neutral-900 hover:text-neutral-700">
              + Invite member
            </button>
          </div>

          <div className="space-y-2.5 text-xs">
            {[
              { name: 'Workspace Admin', email: 'admin@workspace.internal', role: 'Workspace Owner / Admin' },
              { name: 'Maya Chen', email: 'maya@acme.corp', role: 'Account Executive' },
              { name: 'Daniel Stone', email: 'daniel@northstar.io', role: 'Solutions Engineer' },
            ].map((m) => (
              <div key={m.email} className="flex items-center justify-between p-2.5 rounded-lg border border-neutral-100">
                <div>
                  <span className="font-semibold text-neutral-800 block">{m.name}</span>
                  <span className="text-[11px] text-neutral-400">{m.email}</span>
                </div>
                <span className="text-xs font-medium px-2 py-0.5 rounded-full bg-neutral-100 text-neutral-600">
                  {m.role}
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};
