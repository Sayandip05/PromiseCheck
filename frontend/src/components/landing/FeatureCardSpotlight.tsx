import React from 'react';
import { 
  Sparkles, 
  AlertTriangle, 
  CheckCircle2, 
  ShieldCheck, 
  Clock, 
  MessageSquare, 
  FileText,
  Activity,
  ArrowUpRight,
  TrendingUp,
  Lock
} from 'lucide-react';
import { GoogleMeetLogo, JiraLogo, LinearLogo, SlackLogo } from '../ui/BrandLogos';

interface FeatureCardSpotlightProps {
  activeTab: number;
  darkMode: boolean;
}

export const FeatureCardSpotlight: React.FC<FeatureCardSpotlightProps> = ({ activeTab, darkMode }) => {
  return (
    <div className={`w-full h-full p-4 sm:p-5 flex flex-col justify-between animate-in fade-in duration-200 select-none transition-colors duration-200 ${
      darkMode ? 'text-white' : 'text-neutral-800'
    }`}>
      
      {/* TAB 0: Commitment Detection */}
      {activeTab === 0 && (
        <div className="h-full flex flex-col justify-between">
          <div>
            {/* Header */}
            <div className={`flex items-center justify-between pb-3 border-b ${
              darkMode ? 'border-neutral-800' : 'border-neutral-100'
            }`}>
              <div className="flex items-center gap-2">
                <div className={`w-6 h-6 rounded-md border flex items-center justify-center p-1 shadow-2xs ${
                  darkMode ? 'bg-neutral-800 border-neutral-700' : 'bg-white border-neutral-200'
                }`}>
                  <GoogleMeetLogo className="w-4 h-4" />
                </div>
                <div>
                  <h4 className={`text-xs font-bold leading-tight ${darkMode ? 'text-white' : 'text-neutral-900'}`}>
                    Google Meet Transcript
                  </h4>
                  <p className={`text-[10px] ${darkMode ? 'text-neutral-400' : 'text-neutral-500'}`}>
                    Call with Acme Corp • Today 11:30 AM
                  </p>
                </div>
              </div>
              <span className={`inline-flex items-center gap-1 text-[10px] font-semibold px-2 py-0.5 rounded-full border ${
                darkMode ? 'bg-emerald-950/60 text-emerald-300 border-emerald-800' : 'bg-emerald-50 text-emerald-700 border-emerald-200'
              }`}>
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
                Detected
              </span>
            </div>

            {/* Verbatim Call Bubble */}
            <div className={`mt-3 rounded-lg p-2.5 border ${
              darkMode ? 'bg-black/50 border-neutral-800 text-neutral-300' : 'bg-neutral-50 border-neutral-200/80 text-neutral-800'
            }`}>
              <div className="flex items-center gap-1 text-[10.5px] font-medium text-neutral-400 mb-1">
                <MessageSquare className="w-3 h-3 text-neutral-400" />
                <span>Sarah Connor (Account Exec):</span>
              </div>
              <p className={`text-xs italic leading-relaxed ${darkMode ? 'text-neutral-200' : 'text-neutral-800'}`}>
                &ldquo;We commit to delivering SAML 2.0 Single Sign-On and SOC2 reports by November 15, 2026.&rdquo;
              </p>
            </div>

            {/* Extracted Entity Matrix */}
            <div className="mt-3 grid grid-cols-2 gap-2 text-xs">
              <div className={`p-2 rounded border shadow-2xs ${
                darkMode ? 'bg-[#121217] border-neutral-800' : 'bg-white border-neutral-200'
              }`}>
                <span className="text-[10px] text-neutral-400 uppercase font-bold tracking-wider block">Deliverable</span>
                <span className={`font-semibold text-[11.5px] truncate block ${darkMode ? 'text-white' : 'text-neutral-900'}`}>
                  SAML 2.0 SSO
                </span>
              </div>
              <div className={`p-2 rounded border shadow-2xs ${
                darkMode ? 'bg-[#121217] border-neutral-800' : 'bg-white border-neutral-200'
              }`}>
                <span className="text-[10px] text-neutral-400 uppercase font-bold tracking-wider block">Customer</span>
                <span className={`font-semibold text-[11.5px] truncate block ${darkMode ? 'text-white' : 'text-neutral-900'}`}>
                  Acme Corp
                </span>
              </div>
              <div className={`p-2 rounded border shadow-2xs ${
                darkMode ? 'bg-[#121217] border-neutral-800' : 'bg-white border-neutral-200'
              }`}>
                <span className="text-[10px] text-neutral-400 uppercase font-bold tracking-wider block">Promised Date</span>
                <span className="font-semibold text-blue-500 text-[11.5px] truncate block">Nov 15, 2026</span>
              </div>
              <div className={`p-2 rounded border shadow-2xs ${
                darkMode ? 'bg-[#121217] border-neutral-800' : 'bg-white border-neutral-200'
              }`}>
                <span className="text-[10px] text-neutral-400 uppercase font-bold tracking-wider block">AI Confidence</span>
                <span className="font-semibold text-indigo-400 text-[11.5px] flex items-center gap-1">
                  <Sparkles className="w-3 h-3" />
                  99.4% Verified
                </span>
              </div>
            </div>
          </div>

          {/* Footer Card Status */}
          <div className={`pt-2 border-t flex items-center justify-between text-[11px] ${
            darkMode ? 'border-neutral-800 text-neutral-400' : 'border-neutral-100 text-neutral-500'
          }`}>
            <span className="flex items-center gap-1 text-emerald-500 font-semibold">
              <CheckCircle2 className="w-3.5 h-3.5" />
              Candidate Verified & Stored
            </span>
            <span className="font-mono text-[10px] text-neutral-500">ID: PRM-094</span>
          </div>
        </div>
      )}

      {/* TAB 1: Progress Sentinel */}
      {activeTab === 1 && (
        <div className="h-full flex flex-col justify-between">
          <div>
            {/* Header */}
            <div className={`flex items-center justify-between pb-3 border-b ${
              darkMode ? 'border-neutral-800' : 'border-neutral-100'
            }`}>
              <div className="flex items-center gap-2">
                <div className={`w-6 h-6 rounded-md border flex items-center justify-center ${
                  darkMode ? 'bg-blue-950/60 border-blue-800 text-blue-400' : 'bg-blue-50 border-blue-200 text-blue-600'
                }`}>
                  <Activity className="w-4 h-4" />
                </div>
                <div>
                  <h4 className={`text-xs font-bold leading-tight ${darkMode ? 'text-white' : 'text-neutral-900'}`}>
                    Sentinel Velocity Radar
                  </h4>
                  <p className={`text-[10px] ${darkMode ? 'text-neutral-400' : 'text-neutral-500'}`}>
                    Live Engineering Tracker Sync
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-1">
                <div className={`w-5 h-5 rounded-full border flex items-center justify-center p-0.5 shadow-2xs ${
                  darkMode ? 'bg-neutral-800 border-neutral-700' : 'bg-white border-neutral-200'
                }`}>
                  <JiraLogo className="w-3.5 h-3.5" />
                </div>
                <div className={`w-5 h-5 rounded-full border flex items-center justify-center p-0.5 shadow-2xs ${
                  darkMode ? 'bg-neutral-800 border-neutral-700' : 'bg-white border-neutral-200'
                }`}>
                  <LinearLogo className="w-3.5 h-3.5" />
                </div>
              </div>
            </div>

            {/* Velocity Bar */}
            <div className={`mt-3 rounded-lg p-3 border ${
              darkMode ? 'bg-black/50 border-neutral-800' : 'bg-neutral-50 border-neutral-200/80'
            }`}>
              <div className="flex items-center justify-between text-xs mb-1.5 font-medium">
                <span className={darkMode ? 'text-neutral-300' : 'text-neutral-800'}>Sprint 42 Completion</span>
                <span className="font-bold text-emerald-500">78% Complete</span>
              </div>
              <div className={`w-full h-2 rounded-full overflow-hidden ${darkMode ? 'bg-neutral-800' : 'bg-neutral-200'}`}>
                <div className="bg-emerald-500 h-full rounded-full transition-all duration-700" style={{ width: '78%' }} />
              </div>
              <div className={`flex items-center justify-between text-[10px] mt-2 ${
                darkMode ? 'text-neutral-400' : 'text-neutral-500'
              }`}>
                <span>Promised: <strong className={darkMode ? 'text-white' : 'text-neutral-900'}>Nov 15, 2026</strong></span>
                <span className="text-emerald-500 font-semibold">Projected: Nov 13 (2d Ahead)</span>
              </div>
            </div>

            {/* Linked Ticket Breakdown */}
            <div className="mt-3 flex flex-col gap-1.5 text-xs">
              <div className={`flex items-center justify-between p-2 rounded border shadow-2xs text-[11px] ${
                darkMode ? 'bg-[#121217] border-neutral-800' : 'bg-white border-neutral-200'
              }`}>
                <div className="flex items-center gap-1.5">
                  <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500" />
                  <span className="font-mono text-neutral-400">PROJ-428</span>
                  <span className={darkMode ? 'text-white' : 'text-neutral-800'}>SAML IdP Metadata Endpoint</span>
                </div>
                <span className={`px-1.5 py-0.5 rounded text-[10px] font-semibold ${
                  darkMode ? 'bg-emerald-950/60 text-emerald-300' : 'bg-emerald-50 text-emerald-700'
                }`}>
                  Done
                </span>
              </div>
              <div className={`flex items-center justify-between p-2 rounded border shadow-2xs text-[11px] ${
                darkMode ? 'bg-[#121217] border-neutral-800' : 'bg-white border-neutral-200'
              }`}>
                <div className="flex items-center gap-1.5">
                  <Clock className="w-3.5 h-3.5 text-blue-500" />
                  <span className="font-mono text-neutral-400">PROJ-429</span>
                  <span className={darkMode ? 'text-white' : 'text-neutral-800'}>Okta SSO Integration Suite</span>
                </div>
                <span className={`px-1.5 py-0.5 rounded text-[10px] font-semibold ${
                  darkMode ? 'bg-blue-950/60 text-blue-300' : 'bg-blue-50 text-blue-700'
                }`}>
                  In Review
                </span>
              </div>
            </div>
          </div>

          {/* Footer */}
          <div className={`pt-2 border-t flex items-center justify-between text-[11px] ${
            darkMode ? 'border-neutral-800 text-neutral-400' : 'border-neutral-100 text-neutral-500'
          }`}>
            <span className="text-emerald-500 font-semibold flex items-center gap-1">
              <TrendingUp className="w-3.5 h-3.5" />
              Velocity Healthy (94/100)
            </span>
            <span>0 Blockers</span>
          </div>
        </div>
      )}

      {/* TAB 2: Early Risk Alerts */}
      {activeTab === 2 && (
        <div className="h-full flex flex-col justify-between">
          <div>
            {/* Header */}
            <div className={`flex items-center justify-between pb-3 border-b ${
              darkMode ? 'border-neutral-800' : 'border-neutral-100'
            }`}>
              <div className="flex items-center gap-2">
                <div className={`w-6 h-6 rounded-md border flex items-center justify-center ${
                  darkMode ? 'bg-amber-950/60 border-amber-800 text-amber-400' : 'bg-amber-50 border-amber-200 text-amber-600'
                }`}>
                  <AlertTriangle className="w-4 h-4" />
                </div>
                <div>
                  <h4 className={`text-xs font-bold leading-tight ${darkMode ? 'text-white' : 'text-neutral-900'}`}>
                    Delivery Conflict Alert
                  </h4>
                  <p className={`text-[10px] ${darkMode ? 'text-neutral-400' : 'text-neutral-500'}`}>
                    Timeline Slippage Pre-empted
                  </p>
                </div>
              </div>
              <span className={`inline-flex items-center gap-1 text-[10px] font-bold px-2 py-0.5 rounded-full border ${
                darkMode ? 'bg-amber-950/70 text-amber-300 border-amber-800' : 'bg-amber-100 text-amber-800 border-amber-300'
              }`}>
                5-Day Delay
              </span>
            </div>

            {/* Alert Conflict Card */}
            <div className={`mt-3 rounded-lg p-2.5 border text-xs ${
              darkMode ? 'bg-amber-950/30 border-amber-900/60' : 'bg-amber-50/60 border-amber-200/90'
            }`}>
              <div className="flex items-center justify-between mb-1.5">
                <span className={`font-bold text-[11.5px] ${darkMode ? 'text-amber-300' : 'text-amber-900'}`}>
                  Acme Corp • SAML 2.0 SSO
                </span>
                <span className={`text-[10px] font-medium ${darkMode ? 'text-amber-400' : 'text-amber-800'}`}>
                  4 Days Remaining
                </span>
              </div>
              <div className="grid grid-cols-2 gap-2 text-[11px] pt-1">
                <div className={`p-1.5 rounded border ${
                  darkMode ? 'bg-black/60 border-amber-900/70 text-white' : 'bg-white/90 border-amber-200 text-neutral-900'
                }`}>
                  <span className="text-[10px] text-neutral-400 block">Customer Promise</span>
                  <strong className={darkMode ? 'text-white' : 'text-neutral-900'}>Nov 15, 2026</strong>
                </div>
                <div className={`p-1.5 rounded border ${
                  darkMode ? 'bg-black/60 border-amber-900/70 text-white' : 'bg-white/90 border-amber-200 text-neutral-900'
                }`}>
                  <span className="text-[10px] text-neutral-400 block">Engineering Sprint</span>
                  <strong className="text-amber-500">Nov 20, 2026 (+5d)</strong>
                </div>
              </div>
            </div>

            {/* Slack Real-time Dispatch */}
            <div className={`mt-3 rounded-lg p-2.5 border shadow-2xs ${
              darkMode ? 'bg-[#121217] border-neutral-800 text-neutral-300' : 'bg-white border-neutral-200 text-neutral-600'
            }`}>
              <div className="flex items-center justify-between text-[11px] mb-1">
                <div className={`flex items-center gap-1.5 font-semibold ${darkMode ? 'text-white' : 'text-neutral-800'}`}>
                  <SlackLogo className="w-3.5 h-3.5" />
                  <span>Dispatched to #all-aishield</span>
                </div>
                <span className="text-[10px] text-neutral-400">Sent instantly</span>
              </div>
              <p className={`text-[11px] leading-tight ${darkMode ? 'text-neutral-300' : 'text-neutral-600'}`}>
                Warning routed to <strong className={darkMode ? 'text-white' : 'text-neutral-900'}>Sarah Connor</strong>: Customer deadline will slip unless sprint priority is updated.
              </p>
            </div>
          </div>

          {/* Footer */}
          <div className={`pt-2 border-t flex items-center justify-between text-[11px] ${
            darkMode ? 'border-neutral-800 text-neutral-400' : 'border-neutral-100 text-neutral-500'
          }`}>
            <span className="text-amber-500 font-semibold flex items-center gap-1">
              Escalation Active
            </span>
            <span className="text-blue-500 font-medium">Customer Trust Protected</span>
          </div>
        </div>
      )}

      {/* TAB 3: Audit & Trust Reports */}
      {activeTab === 3 && (
        <div className="h-full flex flex-col justify-between">
          <div>
            {/* Header */}
            <div className={`flex items-center justify-between pb-3 border-b ${
              darkMode ? 'border-neutral-800' : 'border-neutral-100'
            }`}>
              <div className="flex items-center gap-2">
                <div className={`w-6 h-6 rounded-md border flex items-center justify-center ${
                  darkMode ? 'bg-emerald-950/60 border-emerald-800 text-emerald-400' : 'bg-emerald-50 border-emerald-200 text-emerald-600'
                }`}>
                  <ShieldCheck className="w-4 h-4" />
                </div>
                <div>
                  <h4 className={`text-xs font-bold leading-tight ${darkMode ? 'text-white' : 'text-neutral-900'}`}>
                    Delivery Verification Certificate
                  </h4>
                  <p className={`text-[10px] ${darkMode ? 'text-neutral-400' : 'text-neutral-500'}`}>
                    Immutable Audit Trail • SOC2 Ready
                  </p>
                </div>
              </div>
              <span className={`text-[10px] font-mono px-2 py-0.5 rounded border ${
                darkMode ? 'bg-neutral-900 border-neutral-800 text-neutral-400' : 'bg-neutral-100 border-neutral-200 text-neutral-600'
              }`}>
                AUD-9481
              </span>
            </div>

            {/* Proof of Delivery Box */}
            <div className={`mt-3 rounded-lg p-2.5 border ${
              darkMode ? 'bg-black/50 border-neutral-800' : 'bg-neutral-50 border-neutral-200/80'
            }`}>
              <div className="flex items-center justify-between mb-1 text-[11px]">
                <span className={`font-bold ${darkMode ? 'text-white' : 'text-neutral-900'}`}>
                  Acme Corp — SOC2 & SAML SSO
                </span>
                <span className="text-emerald-500 font-semibold flex items-center gap-0.5">
                  <CheckCircle2 className="w-3 h-3" />
                  Delivered
                </span>
              </div>
              <p className={`text-[11px] leading-relaxed ${darkMode ? 'text-neutral-300' : 'text-neutral-600'}`}>
                Evidence verified: PR #842 deployed to production. Live IdP handshake validated on Okta sandbox.
              </p>
            </div>

            {/* Trust Metrics */}
            <div className="mt-3 grid grid-cols-2 gap-2 text-xs">
              <div className={`p-2 rounded border shadow-2xs ${
                darkMode ? 'bg-[#121217] border-neutral-800' : 'bg-white border-neutral-200'
              }`}>
                <span className="text-[10px] text-neutral-400 uppercase font-bold tracking-wider block">Reliability Rating</span>
                <span className="font-bold text-emerald-500 text-sm">98.5% On-Time</span>
              </div>
              <div className={`p-2 rounded border shadow-2xs ${
                darkMode ? 'bg-[#121217] border-neutral-800' : 'bg-white border-neutral-200'
              }`}>
                <span className="text-[10px] text-neutral-400 uppercase font-bold tracking-wider block">Audit Log Status</span>
                <span className={`font-semibold text-[11.5px] flex items-center gap-1 ${
                  darkMode ? 'text-white' : 'text-neutral-800'
                }`}>
                  <Lock className="w-3 h-3 text-neutral-400" />
                  Tamper-Proof
                </span>
              </div>
            </div>
          </div>

          {/* Footer */}
          <div className={`pt-2 border-t flex items-center justify-between text-[11px] ${
            darkMode ? 'border-neutral-800 text-neutral-400' : 'border-neutral-100 text-neutral-500'
          }`}>
            <span className={`flex items-center gap-1 font-medium ${darkMode ? 'text-neutral-300' : 'text-neutral-700'}`}>
              <FileText className="w-3.5 h-3.5 text-neutral-400" />
              Verified by Sarah Connor
            </span>
            <span className="text-blue-500 font-semibold flex items-center gap-0.5">
              Export Proof PDF <ArrowUpRight className="w-3 h-3" />
            </span>
          </div>
        </div>
      )}

    </div>
  );
};
