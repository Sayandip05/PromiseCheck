import React, { useState, useEffect } from 'react';
import { 
  Sparkles, 
  AlertTriangle, 
  CheckCircle2, 
  ArrowRight, 
  MessageSquare, 
  GitPullRequest, 
  ShieldCheck, 
  RefreshCw,
  Clock,
  Layers
} from 'lucide-react';
import { GoogleMeetLogo, GmailLogo, JiraLogo, LinearLogo, SlackLogo } from '../ui/BrandLogos';

interface BusinessFlowHeroVisualProps {
  onOpenLogin?: (mode?: 'signup' | 'login') => void;
}

export const BusinessFlowHeroVisual: React.FC<BusinessFlowHeroVisualProps> = ({ onOpenLogin }) => {
  const [activeStep, setActiveStep] = useState<number>(0);
  const [isAutoPlaying, setIsAutoPlaying] = useState<boolean>(true);

  const steps = [
    {
      id: 0,
      title: '1. Ingest & Listen',
      shortLabel: 'Capture',
      subtitle: 'Captures promises made in customer calls and email threads.',
      badge: 'Real-time Ingestion',
      badgeColor: 'bg-emerald-50 text-emerald-700 border-emerald-200',
    },
    {
      id: 1,
      title: '2. AI Extraction',
      shortLabel: 'AI Extract',
      subtitle: 'Groq LLM extracts exact quotes, dates, deliverables, and customers.',
      badge: '99% AI Precision',
      badgeColor: 'bg-blue-50 text-blue-700 border-blue-200',
    },
    {
      id: 2,
      title: '3. Engineering Sync',
      shortLabel: 'Jira Sync',
      subtitle: 'Matches promises against Jira & Linear sprints to detect date conflicts.',
      badge: 'Conflict Alert',
      badgeColor: 'bg-amber-50 text-amber-700 border-amber-200',
    },
    {
      id: 3,
      title: '4. Slack & Delivery',
      shortLabel: 'Slack Alert',
      subtitle: 'Dispatches instant warnings to #all-aishield before trust is damaged.',
      badge: 'Delivery Verified',
      badgeColor: 'bg-purple-50 text-purple-700 border-purple-200',
    },
  ];

  // Auto-cycle through the 4 steps smoothly every 3.8 seconds if user isn't hovering/clicking
  useEffect(() => {
    if (!isAutoPlaying) return;
    const interval = setInterval(() => {
      setActiveStep((prev) => (prev + 1) % steps.length);
    }, 3800);
    return () => clearInterval(interval);
  }, [isAutoPlaying]);

  return (
    <div 
      className="w-full h-full flex flex-col justify-between select-none text-neutral-800"
      onMouseEnter={() => setIsAutoPlaying(false)}
      onMouseLeave={() => setIsAutoPlaying(true)}
    >
      {/* Top Bar: Pipeline Header + Step Scrubber */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-3 sm:pb-4 border-b border-neutral-100 gap-2">
        <div className="flex items-center gap-2">
          <div className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
          <span className="text-xs font-semibold tracking-wider uppercase text-neutral-500">
            PromiseCheck Flow Engine
          </span>
          <span className="text-[11px] px-2 py-0.5 rounded-full font-medium bg-neutral-100 text-neutral-600 border border-neutral-200/80">
            End-to-End
          </span>
        </div>

        {/* Step Scrubber Pills */}
        <div className="flex items-center gap-1 bg-neutral-100/90 p-1 rounded-lg border border-neutral-200/60 self-start sm:self-auto">
          {steps.map((step) => {
            const isActive = activeStep === step.id;
            return (
              <button
                key={step.id}
                onClick={() => {
                  setActiveStep(step.id);
                  setIsAutoPlaying(false);
                }}
                className={`text-[11px] font-medium px-2 sm:px-2.5 py-1 rounded transition-all cursor-pointer ${
                  isActive
                    ? 'bg-white text-neutral-900 shadow-xs border border-neutral-200/80 font-semibold'
                    : 'text-neutral-500 hover:text-neutral-800'
                }`}
              >
                {step.shortLabel}
              </button>
            );
          })}
        </div>
      </div>

      {/* Main 4-Stage Connected Workflow Diagram */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-2.5 sm:gap-3 py-3 sm:py-4">
        
        {/* Stage 1: Capture */}
        <div 
          onClick={() => { setActiveStep(0); setIsAutoPlaying(false); }}
          className={`cursor-pointer rounded-xl p-3 border transition-all duration-300 flex flex-col justify-between ${
            activeStep === 0
              ? 'bg-blue-50/50 border-blue-400 ring-2 ring-blue-100 shadow-xs scale-[1.01]'
              : 'bg-neutral-50/70 border-neutral-200 hover:border-neutral-300'
          }`}
        >
          <div>
            <div className="flex items-center justify-between mb-2">
              <span className="text-[10px] font-bold uppercase tracking-wider text-neutral-400">Step 1</span>
              <div className="flex items-center -space-x-1.5">
                <div className="w-5 h-5 rounded-full bg-white border border-neutral-200 flex items-center justify-center p-0.5 shadow-2xs">
                  <GoogleMeetLogo className="w-3.5 h-3.5" />
                </div>
                <div className="w-5 h-5 rounded-full bg-white border border-neutral-200 flex items-center justify-center p-0.5 shadow-2xs">
                  <GmailLogo className="w-3.5 h-3.5" />
                </div>
              </div>
            </div>
            <h4 className="text-xs font-bold text-neutral-900">Meeting & Mail</h4>
            <p className="text-[11px] text-neutral-500 leading-tight mt-1 line-clamp-2">
              Syncs transcripts & call recordings automatically.
            </p>
          </div>
          <div className="mt-2.5 pt-2 border-t border-neutral-200/60 flex items-center justify-between text-[10px] text-neutral-600 font-medium">
            <span>Customer call</span>
            <span className="text-emerald-600 font-semibold">Captured</span>
          </div>
        </div>

        {/* Stage 2: AI Extract */}
        <div 
          onClick={() => { setActiveStep(1); setIsAutoPlaying(false); }}
          className={`cursor-pointer rounded-xl p-3 border transition-all duration-300 flex flex-col justify-between ${
            activeStep === 1
              ? 'bg-indigo-50/50 border-indigo-400 ring-2 ring-indigo-100 shadow-xs scale-[1.01]'
              : 'bg-neutral-50/70 border-neutral-200 hover:border-neutral-300'
          }`}
        >
          <div>
            <div className="flex items-center justify-between mb-2">
              <span className="text-[10px] font-bold uppercase tracking-wider text-neutral-400">Step 2</span>
              <div className="w-5 h-5 rounded-full bg-indigo-600 text-white flex items-center justify-center shadow-2xs">
                <Sparkles className="w-3 h-3" />
              </div>
            </div>
            <h4 className="text-xs font-bold text-neutral-900">AI Detection</h4>
            <p className="text-[11px] text-neutral-500 leading-tight mt-1 line-clamp-2">
              Groq LLM extracts dates, quotes, and target promises.
            </p>
          </div>
          <div className="mt-2.5 pt-2 border-t border-neutral-200/60 flex items-center justify-between text-[10px] text-neutral-600 font-medium">
            <span>Verbatim quote</span>
            <span className="text-indigo-600 font-semibold">99% Conf.</span>
          </div>
        </div>

        {/* Stage 3: Tracker Reconciliation */}
        <div 
          onClick={() => { setActiveStep(2); setIsAutoPlaying(false); }}
          className={`cursor-pointer rounded-xl p-3 border transition-all duration-300 flex flex-col justify-between ${
            activeStep === 2
              ? 'bg-amber-50/50 border-amber-400 ring-2 ring-amber-100 shadow-xs scale-[1.01]'
              : 'bg-neutral-50/70 border-neutral-200 hover:border-neutral-300'
          }`}
        >
          <div>
            <div className="flex items-center justify-between mb-2">
              <span className="text-[10px] font-bold uppercase tracking-wider text-neutral-400">Step 3</span>
              <div className="flex items-center -space-x-1.5">
                <div className="w-5 h-5 rounded-full bg-white border border-neutral-200 flex items-center justify-center p-0.5 shadow-2xs">
                  <JiraLogo className="w-3.5 h-3.5" />
                </div>
                <div className="w-5 h-5 rounded-full bg-white border border-neutral-200 flex items-center justify-center p-0.5 shadow-2xs">
                  <LinearLogo className="w-3.5 h-3.5" />
                </div>
              </div>
            </div>
            <h4 className="text-xs font-bold text-neutral-900">Engineering Sync</h4>
            <p className="text-[11px] text-neutral-500 leading-tight mt-1 line-clamp-2">
              Links Jira/Linear tickets & catches timeline slippage.
            </p>
          </div>
          <div className="mt-2.5 pt-2 border-t border-neutral-200/60 flex items-center justify-between text-[10px] text-neutral-600 font-medium">
            <span>Sprint link</span>
            <span className="text-amber-600 font-semibold">5d Conflict</span>
          </div>
        </div>

        {/* Stage 4: Alert & Delivery */}
        <div 
          onClick={() => { setActiveStep(3); setIsAutoPlaying(false); }}
          className={`cursor-pointer rounded-xl p-3 border transition-all duration-300 flex flex-col justify-between ${
            activeStep === 3
              ? 'bg-purple-50/50 border-purple-400 ring-2 ring-purple-100 shadow-xs scale-[1.01]'
              : 'bg-neutral-50/70 border-neutral-200 hover:border-neutral-300'
          }`}
        >
          <div>
            <div className="flex items-center justify-between mb-2">
              <span className="text-[10px] font-bold uppercase tracking-wider text-neutral-400">Step 4</span>
              <div className="w-5 h-5 rounded-full bg-white border border-neutral-200 flex items-center justify-center p-0.5 shadow-2xs">
                <SlackLogo className="w-3.5 h-3.5" />
              </div>
            </div>
            <h4 className="text-xs font-bold text-neutral-900">Alert & Verify</h4>
            <p className="text-[11px] text-neutral-500 leading-tight mt-1 line-clamp-2">
              Dispatches alerts to Slack and tracks proof of delivery.
            </p>
          </div>
          <div className="mt-2.5 pt-2 border-t border-neutral-200/60 flex items-center justify-between text-[10px] text-neutral-600 font-medium">
            <span>#all-aishield</span>
            <span className="text-purple-600 font-semibold">Notified</span>
          </div>
        </div>

      </div>

      {/* Interactive Detail Box Representing the Business Object */}
      <div className="rounded-xl border border-neutral-200 bg-neutral-50/80 p-3 sm:p-4 transition-all">
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center gap-2">
            <span className="font-semibold text-xs text-neutral-900 flex items-center gap-1.5">
              <ShieldCheck className="w-4 h-4 text-emerald-600" />
              Live Promise Item:
            </span>
            <span className="text-xs font-bold text-neutral-800">
              Deliver SAML 2.0 SSO Integration
            </span>
          </div>
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold bg-amber-100 text-amber-800 border border-amber-300/80">
            <AlertTriangle className="w-3 h-3 text-amber-600" />
            5-Day Conflict Detected
          </span>
        </div>

        {/* Verbatim quote and context pill */}
        <div className="bg-white rounded-lg p-2.5 border border-neutral-200/90 text-xs shadow-2xs flex flex-col gap-1.5">
          <div className="flex items-center justify-between text-[11px] text-neutral-500">
            <span className="flex items-center gap-1">
              <MessageSquare className="w-3 h-3 text-neutral-400" />
              Verbatim source from <strong className="text-neutral-700">Google Meet</strong> with <strong className="text-neutral-700">Acme Corp</strong>:
            </span>
            <span className="font-mono text-[10px] text-neutral-400">Oct 14, 2026</span>
          </div>
          <p className="text-neutral-700 italic text-[11.5px] bg-neutral-50 p-1.5 rounded border border-neutral-100">
            &ldquo;We promise Acme Corp that SAML SSO will be live by November 15, 2026.&rdquo;
          </p>

          {/* Sync details grid */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-2 pt-1 border-t border-neutral-100 text-[11px]">
            <div className="flex items-center gap-1.5 text-neutral-600">
              <Clock className="w-3.5 h-3.5 text-blue-500 shrink-0" />
              <span>Promised: <strong>Nov 15, 2026</strong></span>
            </div>
            <div className="flex items-center gap-1.5 text-neutral-600">
              <div className="w-3.5 h-3.5 rounded flex items-center justify-center shrink-0">
                <JiraLogo className="w-3.5 h-3.5" />
              </div>
              <span>Jira #PROJ-429: <strong className="text-amber-600">Nov 20</strong></span>
            </div>
            <div className="flex items-center gap-1.5 text-neutral-600">
              <div className="w-3.5 h-3.5 rounded flex items-center justify-center shrink-0">
                <SlackLogo className="w-3.5 h-3.5" />
              </div>
              <span>Alert sent to <strong className="text-purple-700">#all-aishield</strong></span>
            </div>
          </div>
        </div>
      </div>

      {/* Bottom Summary Callout with CTA */}
      <div className="pt-3 border-t border-neutral-100 flex items-center justify-between text-xs">
        <div className="flex items-center gap-2 text-neutral-500">
          <span className="inline-block w-2 h-2 rounded-full bg-blue-500" />
          <span className="text-[11.5px] leading-tight">
            <strong>Active Integrations:</strong> Google Meet • Gmail • Jira • Linear • Slack
          </span>
        </div>
        {onOpenLogin && (
          <button
            onClick={() => onOpenLogin('signup')}
            className="inline-flex items-center gap-1 text-[11.5px] font-semibold text-blue-600 hover:text-blue-700 transition-colors cursor-pointer"
          >
            Explore live workflow <ArrowRight className="w-3 h-3" />
          </button>
        )}
      </div>

    </div>
  );
};
