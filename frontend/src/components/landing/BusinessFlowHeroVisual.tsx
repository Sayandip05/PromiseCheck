import React, { useState, useEffect } from 'react';
import { 
  Sparkles, 
  AlertTriangle, 
  ShieldCheck, 
  Clock, 
  MessageSquare
} from 'lucide-react';
import { GoogleMeetLogo, GmailLogo, JiraLogo, LinearLogo, SlackLogo } from '../ui/BrandLogos';

interface BusinessFlowHeroVisualProps {
  darkMode: boolean;
}

export const BusinessFlowHeroVisual: React.FC<BusinessFlowHeroVisualProps> = ({ darkMode }) => {
  const [activeStep, setActiveStep] = useState<number>(0);

  const steps = [
    {
      id: 0,
      title: '1. Ingest & Listen',
      shortLabel: 'Capture',
      subtitle: 'Captures commitments made in customer calls and email threads.',
    },
    {
      id: 1,
      title: '2. AI Extraction',
      shortLabel: 'AI Extract',
      subtitle: 'Intelligent AI extracts exact quotes, dates, deliverables, and customers.',
    },
    {
      id: 2,
      title: '3. Engineering Sync',
      shortLabel: 'Jira Sync',
      subtitle: 'Matches promises against Jira & Linear sprints to detect date conflicts.',
    },
    {
      id: 3,
      title: '4. Slack & Delivery',
      shortLabel: 'Slack Alert',
      subtitle: 'Dispatches instant warnings to #all-aishield before trust is damaged.',
    },
  ];

  // Auto-cycle through the 4 steps smoothly every 3.2 seconds
  useEffect(() => {
    const interval = setInterval(() => {
      setActiveStep((prev) => (prev + 1) % steps.length);
    }, 3200);
    return () => clearInterval(interval);
  }, [steps.length]);

  return (
    <div 
      className={`w-full h-full flex flex-col justify-between pointer-events-none select-none cursor-default transition-colors duration-200 ${
        darkMode ? 'text-white' : 'text-neutral-900'
      }`}
    >
      {/* Top Bar: Clean Header + Single-Line Step Scrubber (Automated Pipeline badge removed) */}
      <div className={`flex flex-row items-center justify-between pb-3 sm:pb-3.5 border-b transition-colors duration-200 gap-3 ${
        darkMode ? 'border-neutral-800' : 'border-neutral-200/90'
      }`}>
        <div className="flex items-center gap-2 shrink-0">
          <div className="w-2 h-2 rounded-full bg-emerald-500 shrink-0" />
          <span className={`text-[11px] font-semibold tracking-wider uppercase whitespace-nowrap ${
            darkMode ? 'text-neutral-400' : 'text-neutral-500'
          }`}>
            PromiseCheck Flow Engine
          </span>
        </div>

        {/* Step Progression: Strictly single line, no line break, zero text-width shifts */}
        <div className={`flex items-center flex-nowrap gap-1 p-1 rounded-lg border transition-colors duration-200 shrink-0 ${
          darkMode ? 'bg-neutral-900/90 border-neutral-800' : 'bg-neutral-100/90 border-neutral-200/80'
        }`}>
          {steps.map((step) => {
            const isActive = activeStep === step.id;
            return (
              <div
                key={step.id}
                className={`text-[11px] font-medium whitespace-nowrap px-2.5 sm:px-3 py-1 rounded transition-colors duration-200 border ${
                  isActive
                    ? darkMode
                      ? 'bg-neutral-800 text-white border-neutral-700 shadow-2xs'
                      : 'bg-white text-neutral-900 border-neutral-200/90 shadow-2xs'
                    : 'text-neutral-500 border-transparent'
                }`}
              >
                {step.shortLabel}
              </div>
            );
          })}
        </div>
      </div>

      {/* Main 4-Stage Connected Workflow Cards (No scale, fixed dimensions, zero jitter) */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-2.5 sm:gap-3 py-3 sm:py-3.5">
        
        {/* Stage 1: Capture */}
        <div 
          className={`rounded-xl p-3 border transition-colors duration-300 flex flex-col justify-between ${
            activeStep === 0
              ? darkMode
                ? 'bg-blue-950/40 border-blue-500 shadow-sm'
                : 'bg-blue-50/70 border-blue-400 shadow-sm'
              : darkMode
                ? 'bg-neutral-900/50 border-neutral-800/90'
                : 'bg-neutral-50/70 border-neutral-200'
          }`}
        >
          <div>
            <div className="flex items-center justify-between mb-2">
              <span className={`text-[10px] font-bold uppercase tracking-wider ${
                darkMode ? 'text-neutral-500' : 'text-neutral-400'
              }`}>
                Step 1
              </span>
              <div className="flex items-center -space-x-1.5">
                <div className={`w-5 h-5 rounded-full border flex items-center justify-center p-0.5 shadow-2xs ${
                  darkMode ? 'bg-neutral-800 border-neutral-700' : 'bg-white border-neutral-200'
                }`}>
                  <GoogleMeetLogo className="w-3.5 h-3.5" />
                </div>
                <div className={`w-5 h-5 rounded-full border flex items-center justify-center p-0.5 shadow-2xs ${
                  darkMode ? 'bg-neutral-800 border-neutral-700' : 'bg-white border-neutral-200'
                }`}>
                  <GmailLogo className="w-3.5 h-3.5" />
                </div>
              </div>
            </div>
            <h4 className={`text-xs font-bold ${darkMode ? 'text-white' : 'text-neutral-900'}`}>Meeting & Mail</h4>
            <p className={`text-[11px] leading-tight mt-1 line-clamp-2 ${
              darkMode ? 'text-neutral-400' : 'text-neutral-500'
            }`}>
              Syncs transcripts & call recordings automatically.
            </p>
          </div>
          <div className={`mt-2.5 pt-2 border-t flex items-center justify-between text-[10px] font-medium ${
            darkMode ? 'border-neutral-800 text-neutral-400' : 'border-neutral-200/60 text-neutral-600'
          }`}>
            <span>Customer call</span>
            <span className="text-emerald-500 font-semibold">Captured</span>
          </div>
        </div>

        {/* Stage 2: AI Extract */}
        <div 
          className={`rounded-xl p-3 border transition-colors duration-300 flex flex-col justify-between ${
            activeStep === 1
              ? darkMode
                ? 'bg-indigo-950/40 border-indigo-500 shadow-sm'
                : 'bg-indigo-50/70 border-indigo-400 shadow-sm'
              : darkMode
                ? 'bg-neutral-900/50 border-neutral-800/90'
                : 'bg-neutral-50/70 border-neutral-200'
          }`}
        >
          <div>
            <div className="flex items-center justify-between mb-2">
              <span className={`text-[10px] font-bold uppercase tracking-wider ${
                darkMode ? 'text-neutral-500' : 'text-neutral-400'
              }`}>
                Step 2
              </span>
              <div className="w-5 h-5 rounded-full bg-indigo-600 text-white flex items-center justify-center shadow-2xs">
                <Sparkles className="w-3 h-3" />
              </div>
            </div>
            <h4 className={`text-xs font-bold ${darkMode ? 'text-white' : 'text-neutral-900'}`}>AI Detection</h4>
            <p className={`text-[11px] leading-tight mt-1 line-clamp-2 ${
              darkMode ? 'text-neutral-400' : 'text-neutral-500'
            }`}>
              AI engine isolates exact dates, quotes & commitments.
            </p>
          </div>
          <div className={`mt-2.5 pt-2 border-t flex items-center justify-between text-[10px] font-medium ${
            darkMode ? 'border-neutral-800 text-neutral-400' : 'border-neutral-200/60 text-neutral-600'
          }`}>
            <span>Verbatim quote</span>
            <span className="text-indigo-400 font-semibold">99% Conf.</span>
          </div>
        </div>

        {/* Stage 3: Engineering Sync */}
        <div 
          className={`rounded-xl p-3 border transition-colors duration-300 flex flex-col justify-between ${
            activeStep === 2
              ? darkMode
                ? 'bg-amber-950/40 border-amber-500 shadow-sm'
                : 'bg-amber-50/70 border-amber-400 shadow-sm'
              : darkMode
                ? 'bg-neutral-900/50 border-neutral-800/90'
                : 'bg-neutral-50/70 border-neutral-200'
          }`}
        >
          <div>
            <div className="flex items-center justify-between mb-2">
              <span className={`text-[10px] font-bold uppercase tracking-wider ${
                darkMode ? 'text-neutral-500' : 'text-neutral-400'
              }`}>
                Step 3
              </span>
              <div className="flex items-center -space-x-1.5">
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
            <h4 className={`text-xs font-bold ${darkMode ? 'text-white' : 'text-neutral-900'}`}>Engineering Sync</h4>
            <p className={`text-[11px] leading-tight mt-1 line-clamp-2 ${
              darkMode ? 'text-neutral-400' : 'text-neutral-500'
            }`}>
              Links Jira & Linear tickets to catch timeline slippage.
            </p>
          </div>
          <div className={`mt-2.5 pt-2 border-t flex items-center justify-between text-[10px] font-medium ${
            darkMode ? 'border-neutral-800 text-neutral-400' : 'border-neutral-200/60 text-neutral-600'
          }`}>
            <span>Sprint link</span>
            <span className="text-amber-500 font-semibold">5d Conflict</span>
          </div>
        </div>

        {/* Stage 4: Alert & Delivery */}
        <div 
          className={`rounded-xl p-3 border transition-colors duration-300 flex flex-col justify-between ${
            activeStep === 3
              ? darkMode
                ? 'bg-purple-950/40 border-purple-500 shadow-sm'
                : 'bg-purple-50/70 border-purple-400 shadow-sm'
              : darkMode
                ? 'bg-neutral-900/50 border-neutral-800/90'
                : 'bg-neutral-50/70 border-neutral-200'
          }`}
        >
          <div>
            <div className="flex items-center justify-between mb-2">
              <span className={`text-[10px] font-bold uppercase tracking-wider ${
                darkMode ? 'text-neutral-500' : 'text-neutral-400'
              }`}>
                Step 4
              </span>
              <div className={`w-5 h-5 rounded-full border flex items-center justify-center p-0.5 shadow-2xs ${
                darkMode ? 'bg-neutral-800 border-neutral-700' : 'bg-white border-neutral-200'
              }`}>
                <SlackLogo className="w-3.5 h-3.5" />
              </div>
            </div>
            <h4 className={`text-xs font-bold ${darkMode ? 'text-white' : 'text-neutral-900'}`}>Alert & Verify</h4>
            <p className={`text-[11px] leading-tight mt-1 line-clamp-2 ${
              darkMode ? 'text-neutral-400' : 'text-neutral-500'
            }`}>
              Dispatches alerts to Slack and tracks proof of delivery.
            </p>
          </div>
          <div className={`mt-2.5 pt-2 border-t flex items-center justify-between text-[10px] font-medium ${
            darkMode ? 'border-neutral-800 text-neutral-400' : 'border-neutral-200/60 text-neutral-600'
          }`}>
            <span>#all-aishield</span>
            <span className="text-purple-400 font-semibold">Notified</span>
          </div>
        </div>

      </div>

      {/* The Live Promise Item Card (Detailed Business Representation, fixed height/layout) */}
      <div className={`rounded-xl border p-3 sm:p-3.5 transition-colors duration-200 ${
        darkMode ? 'bg-neutral-900/70 border-neutral-800' : 'bg-neutral-50/90 border-neutral-200'
      }`}>
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center gap-2">
            <span className={`font-semibold text-xs flex items-center gap-1.5 ${
              darkMode ? 'text-white' : 'text-neutral-900'
            }`}>
              <ShieldCheck className="w-4 h-4 text-emerald-500" />
              Active Commitment:
            </span>
            <span className={`text-xs font-bold ${darkMode ? 'text-neutral-200' : 'text-neutral-800'}`}>
              Deliver SAML 2.0 SSO Integration
            </span>
          </div>
          <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold border ${
            darkMode 
              ? 'bg-amber-950/70 text-amber-300 border-amber-800/80' 
              : 'bg-amber-100 text-amber-800 border-amber-300/80'
          }`}>
            <AlertTriangle className="w-3 h-3 text-amber-500" />
            5-Day Conflict Detected
          </span>
        </div>

        {/* Verbatim quote and context */}
        <div className={`rounded-lg p-2.5 border text-xs shadow-2xs flex flex-col gap-1.5 ${
          darkMode ? 'bg-[#0f0f14] border-neutral-800' : 'bg-white border-neutral-200/90'
        }`}>
          <div className={`flex items-center justify-between text-[11px] ${
            darkMode ? 'text-neutral-400' : 'text-neutral-500'
          }`}>
            <span className="flex items-center gap-1">
              <MessageSquare className="w-3 h-3 text-neutral-400" />
              Verbatim source from <strong className={darkMode ? 'text-neutral-200' : 'text-neutral-700'}>Google Meet</strong> with <strong className={darkMode ? 'text-neutral-200' : 'text-neutral-700'}>Acme Corp</strong>:
            </span>
            <span className="font-mono text-[10px] text-neutral-400">Oct 14, 2026</span>
          </div>
          <p className={`italic text-[11.5px] p-1.5 rounded border ${
            darkMode 
              ? 'bg-black/50 border-neutral-800 text-neutral-300' 
              : 'bg-neutral-50 border-neutral-100 text-neutral-700'
          }`}>
            &ldquo;We promise Acme Corp that SAML SSO will be live by November 15, 2026.&rdquo;
          </p>

          {/* Sync details grid */}
          <div className={`grid grid-cols-1 sm:grid-cols-3 gap-2 pt-1 border-t text-[11px] ${
            darkMode ? 'border-neutral-800 text-neutral-300' : 'border-neutral-100 text-neutral-600'
          }`}>
            <div className="flex items-center gap-1.5">
              <Clock className="w-3.5 h-3.5 text-blue-500 shrink-0" />
              <span>Promised: <strong className={darkMode ? 'text-white' : 'text-neutral-800'}>Nov 15, 2026</strong></span>
            </div>
            <div className="flex items-center gap-1.5">
              <div className="w-3.5 h-3.5 rounded flex items-center justify-center shrink-0">
                <JiraLogo className="w-3.5 h-3.5" />
              </div>
              <span>Jira #PROJ-429: <strong className="text-amber-500">Nov 20</strong></span>
            </div>
            <div className="flex items-center gap-1.5">
              <div className="w-3.5 h-3.5 rounded flex items-center justify-center shrink-0">
                <SlackLogo className="w-3.5 h-3.5" />
              </div>
              <span>Alert sent to <strong className={darkMode ? 'text-purple-300' : 'text-purple-700'}>#all-aishield</strong></span>
            </div>
          </div>
        </div>
      </div>

      {/* Bottom Summary Callout */}
      <div className={`pt-2.5 border-t flex items-center justify-between text-xs ${
        darkMode ? 'border-neutral-800 text-neutral-400' : 'border-neutral-200/80 text-neutral-500'
      }`}>
        <div className="flex items-center gap-2">
          <span className="inline-block w-2 h-2 rounded-full bg-blue-500" />
          <span className="text-[11.5px] leading-tight">
            <strong>Active Integrations:</strong> Google Meet • Gmail • Jira • Linear • Slack
          </span>
        </div>
        <div className="flex items-center gap-1 text-[11px] font-semibold text-blue-500">
          <span>Continuous audit & risk detection</span>
        </div>
      </div>

    </div>
  );
};
