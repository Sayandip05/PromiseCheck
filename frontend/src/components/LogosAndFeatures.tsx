import React, { useState } from 'react';
import { FEATURES_LIST } from '../data/mockData';
import { 
  ScanSearch, 
  Activity, 
  BellRing, 
  FileCheck2, 
  ArrowRight
} from 'lucide-react';

interface LogosAndFeaturesProps {
  darkMode: boolean;
  onOpenLogin: (mode?: 'signup' | 'login') => void;
}

const integrationsList = [
  {
    name: 'Google Meet',
    icon: (
      <svg className="w-5.5 h-5.5 shrink-0" viewBox="0 0 87.5 72">
        <path fill="#00832d" d="M52.5 36l13.1-13.1V9.5c0-4.6-5.6-6.9-8.8-3.6L43.8 18.9 52.5 36z" />
        <path fill="#0066da" d="M0 58.5C0 66 6 72 13.5 72H44c7.5 0 13.5-6 13.5-13.5V36L44 24H0v34.5z" />
        <path fill="#e51c24" d="M57.5 13.5C57.5 6 51.5 0 44 0H13.5C6 0 0 6 0 13.5V24h57.5V13.5z" />
        <path fill="#00ac47" d="M44 72l12.8-13 8.8 13.1c3.2 3.3 8.8 1 8.8-3.6V49.1L56.8 36 44 72z" />
        <path fill="#ffba00" d="M74.4 22.9l-8.8 8.8 8.8 8.8V22.9z" />
      </svg>
    ),
  },
  {
    name: 'Jira',
    icon: (
      <svg className="w-5.5 h-5.5 shrink-0" viewBox="0 0 24 24">
        <path fill="#2684FF" d="M11.5 2.5a1 1 0 0 1 1.4 0l8.6 8.6a1 1 0 0 1 0 1.4l-8.6 8.6a1 1 0 0 1-1.4 0l-8.6-8.6a1 1 0 0 1 0-1.4l8.6-8.6z" />
        <path fill="#0052CC" d="M11.5 2.5a1 1 0 0 1 1.4 0l8.6 8.6a1 1 0 0 1 0 1.4L17 17l-9.5-9.5 4-5z" opacity="0.85" />
        <circle cx="12" cy="12" r="3.2" fill="#FFFFFF" />
      </svg>
    ),
  },
  {
    name: 'Slack',
    icon: (
      <svg className="w-5.5 h-5.5 shrink-0" viewBox="0 0 24 24">
        <path fill="#E01E5A" d="M5.04 14.28a2.52 2.52 0 1 0 2.52 2.52v-2.52H5.04zm3.78 2.52a2.52 2.52 0 1 0 5.04 0v-6.3H8.82v6.3z" />
        <path fill="#36C5F0" d="M9.72 5.04a2.52 2.52 0 1 0-2.52 2.52h2.52V5.04zm-2.52 3.78a2.52 2.52 0 1 0 0 5.04h6.3V8.82h-6.3z" />
        <path fill="#2EB67D" d="M18.96 9.72a2.52 2.52 0 1 0-2.52-2.52v2.52h2.52zm-3.78-2.52a2.52 2.52 0 1 0-5.04 0v6.3h5.04v-6.3z" />
        <path fill="#ECB22E" d="M14.28 18.96a2.52 2.52 0 1 0 2.52-2.52h-2.52v2.52zm2.52-3.78a2.52 2.52 0 1 0 0-5.04h-6.3v5.04h6.3z" />
      </svg>
    ),
  },
  {
    name: 'Transcript upload',
    icon: (
      <svg className="w-5.5 h-5.5 shrink-0 text-slate-800 dark:text-slate-200" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
        <polyline points="14 2 14 8 20 8" />
        <line x1="16" y1="13" x2="8" y2="13" />
        <line x1="16" y1="17" x2="8" y2="17" />
        <line x1="10" y1="9" x2="8" y2="9" />
      </svg>
    ),
  },
  {
    name: 'Zoom',
    icon: (
      <svg className="w-5.5 h-5.5 shrink-0" viewBox="0 0 24 24" fill="none">
        <rect width="24" height="24" rx="6" fill="#2D8CFF" />
        <path d="M6 9a2 2 0 0 1 2-2h6a2 2 0 0 1 2 2v6a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2V9z" fill="#FFFFFF" />
        <path d="M16 10.5l4-2.5v8l-4-2.5v-3z" fill="#FFFFFF" />
      </svg>
    ),
  },
  {
    name: 'Linear',
    icon: (
      <svg className="w-5.5 h-5.5 shrink-0 text-neutral-900 dark:text-white" viewBox="0 0 24 24" fill="currentColor">
        <path d="M2.08 3.51A10.96 10.96 0 0 1 12 1c6.08 0 11 4.92 11 11a10.96 10.96 0 0 1-2.51 6.92L2.08 3.51zm-1.07 3.56L16.93 23A11 11 0 0 1 1 12c0-1.77.42-3.44 1.16-4.93z" />
      </svg>
    ),
  },
  {
    name: 'Microsoft Teams',
    icon: (
      <svg className="w-5.5 h-5.5 shrink-0" viewBox="0 0 24 24">
        <path fill="#5059C9" d="M19.5 7.5A2.5 2.5 0 0 0 17 5a2.5 2.5 0 0 0-2.5 2.5c0 1.13.75 2.08 1.77 2.38v4.62c0 .28.22.5.5.5h1.46c.28 0 .5-.22.5-.5V9.88c1.02-.3 1.77-1.25 1.77-2.38z" />
        <path fill="#7B83EB" d="M14.5 10c0-1.38-1.12-2.5-2.5-2.5S9.5 8.62 9.5 10c0 1.14.77 2.1 1.8 2.4v6.1c0 .28.22.5.5.5h1.4c.28 0 .5-.22.5-.5v-6.1c1.03-.3 1.8-1.26 1.8-2.4z" />
        <rect x="3" y="6.5" width="10" height="11" rx="2" fill="#4B53BC" />
        <path d="M6 10h4v1.5H8.75V15H7.25v-3.5H6V10z" fill="#FFFFFF" />
      </svg>
    ),
  },
  {
    name: 'GitHub',
    icon: (
      <svg className="w-5.5 h-5.5 shrink-0 text-neutral-900 dark:text-white" viewBox="0 0 24 24" fill="currentColor">
        <path fillRule="evenodd" clipRule="evenodd" d="M12 2C6.477 2 2 6.484 2 12.017c0 4.425 2.865 8.18 6.839 9.504.5.092.682-.217.682-.483 0-.237-.008-.868-.013-1.703-2.782.605-3.369-1.343-3.369-1.343-.454-1.158-1.11-1.466-1.11-1.466-.908-.62.069-.608.069-.608 1.003.07 1.53 1.032 1.53 1.032.892 1.53 2.341 1.088 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.113-4.555-4.951 0-1.093.39-1.988 1.029-2.688-.103-.253-.446-1.272.098-2.65 0 0 .84-.27 2.75 1.026A9.564 9.564 0 0112 6.844c.85.004 1.705.115 2.504.337 1.909-1.296 2.747-1.027 2.747-1.027.546 1.379.202 2.398.1 2.651.64.7 1.028 1.595 1.028 2.688 0 3.848-2.339 4.695-4.566 4.943.359.309.678.92.678 1.855 0 1.338-.012 2.419-.012 2.747 0 .268.18.58.688.482A10.019 10.019 0 0022 12.017C22 6.484 17.522 2 12 2z" />
      </svg>
    ),
  }
];

export const LogosAndFeatures: React.FC<LogosAndFeaturesProps> = ({ 
  darkMode, 
  onOpenLogin
}) => {
  const [activeTab, setActiveTab] = useState<number>(0);

  const icons = [
    ScanSearch,
    Activity,
    BellRing,
    FileCheck2
  ];

  const currentFeature = FEATURES_LIST[activeTab];

  return (
    <section 
      id="features-section" 
      className={`border-b transition-colors duration-200 ${
        darkMode ? 'bg-black text-white border-neutral-800' : 'bg-white text-neutral-900 border-neutral-200'
      }`}
    >
      {/* 1. Integrations Strip: Bring conversation and delivery into one view */}
      <div className="py-8 sm:py-9 px-6 md:px-12 text-center overflow-hidden relative">
        {/* Section Headline */}
        <h2 className="text-xl sm:text-2xl md:text-3xl font-semibold tracking-tight max-w-3xl mx-auto text-neutral-950 dark:text-white">
          Bring conversation and delivery into one view
        </h2>

        {/* Continuous Scrolling Integrations Marquee */}
        <div className="relative mt-5 sm:mt-6 w-full overflow-hidden">
          {/* Gradient Edge Masks for soft fade */}
          <div
            className={`pointer-events-none absolute inset-y-0 left-0 w-16 sm:w-28 bg-gradient-to-r to-transparent z-10 ${
              darkMode ? 'from-black' : 'from-white'
            }`}
          />
          <div
            className={`pointer-events-none absolute inset-y-0 right-0 w-16 sm:w-28 bg-gradient-to-l to-transparent z-10 ${
              darkMode ? 'from-black' : 'from-white'
            }`}
          />

          {/* Marquee Track */}
          <div className="animate-marquee gap-4 sm:gap-5 py-2">
            {[...integrationsList, ...integrationsList].map((item, idx) => (
              <div
                key={`${item.name}-${idx}`}
                className={`flex items-center gap-3 sm:gap-3.5 px-5 sm:px-6 py-3 sm:py-3.5 rounded-xl border transition-all duration-200 shrink-0 shadow-xs hover:shadow-sm cursor-default select-none ${
                  darkMode
                    ? 'bg-[#121215] border-neutral-800/90 text-neutral-200 hover:border-neutral-700'
                    : 'bg-white border-neutral-200/90 text-neutral-900 hover:border-neutral-300'
                }`}
              >
                <div className="w-6 h-6 flex items-center justify-center shrink-0">
                  {item.icon}
                </div>
                <span className="text-[14px] sm:text-[15px] font-medium tracking-tight whitespace-nowrap">
                  {item.name}
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Four-Column Feature Navigation Bar */}
      <div className={`border-t border-b grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 divide-y sm:divide-y-0 sm:divide-x ${
        darkMode ? 'border-neutral-800 divide-neutral-800' : 'border-neutral-200 divide-neutral-200'
      }`}>
        {FEATURES_LIST.map((feature, idx) => {
          const Icon = icons[idx];
          const isActive = activeTab === idx;
          return (
            <button
              key={feature.id}
              onClick={() => setActiveTab(idx)}
              className={`p-6 text-left transition-all relative cursor-pointer group flex flex-col justify-between min-h-[116px] ${
                isActive 
                  ? darkMode 
                    ? 'bg-neutral-900/70 text-white' 
                    : 'bg-neutral-100/80 text-neutral-900 font-medium'
                  : darkMode 
                    ? 'hover:bg-neutral-900/40 text-neutral-400' 
                    : 'hover:bg-neutral-50 text-neutral-600'
              }`}
            >
              {/* Active top line accent */}
              {isActive && (
                <div className={`absolute top-0 left-0 right-0 h-0.5 ${
                  darkMode ? 'bg-white' : 'bg-neutral-900'
                }`} />
              )}

              <div className="flex items-start justify-between">
                <span className={`font-medium text-[15px] ${
                  isActive ? (darkMode ? 'text-white' : 'text-neutral-900') : (darkMode ? 'text-neutral-300' : 'text-neutral-800')
                }`}>
                  {feature.title}
                </span>
                <Icon className={`w-4 h-4 shrink-0 transition-transform group-hover:scale-110 ${
                  isActive ? (darkMode ? 'text-white' : 'text-neutral-900') : 'text-neutral-400'
                }`} />
              </div>

              <p className={`mt-2 text-xs leading-relaxed ${
                darkMode ? 'text-neutral-400' : 'text-neutral-500'
              }`}>
                {feature.subtitle}
              </p>
            </button>
          );
        })}
      </div>

      {/* 3. Feature Spotlight with Universal Sizing Across All 4 Sections */}
      <div className="grid grid-cols-1 lg:grid-cols-12 items-stretch min-h-[500px] lg:min-h-[540px]">
        
        {/* Left Column: Heading, description, Read more button with vertical divider */}
        <div className={`lg:col-span-5 p-8 sm:p-12 lg:p-16 flex flex-col justify-center border-b lg:border-b-0 lg:border-r ${
          darkMode ? 'border-neutral-800' : 'border-neutral-200'
        }`}>
          {/* Universal fixed height container for headline so section size never shifts */}
          <div className="min-h-[72px] sm:min-h-[84px] flex items-center">
            <h3 className="text-3xl sm:text-4xl font-normal tracking-[-0.025em] leading-[1.18]">
              {currentFeature.headline}
            </h3>
          </div>

          {/* Universal fixed height container for description */}
          <div className="mt-5 min-h-[96px] sm:min-h-[110px] flex items-start">
            <p className={`text-[16px] leading-relaxed font-normal ${
              darkMode ? 'text-neutral-400' : 'text-neutral-600'
            }`}>
              {currentFeature.description}
            </p>
          </div>

          <div className="mt-8 flex items-center gap-4">
            <button
              id="feature-read-more-btn"
              onClick={() => onOpenLogin('signup')}
              className={`font-medium text-xs px-4 py-2 rounded-lg transition-colors cursor-pointer ${
                darkMode
                  ? 'bg-neutral-800 hover:bg-neutral-700 text-white'
                  : 'bg-[#f0f1f4] hover:bg-[#e4e6ea] text-neutral-900'
              }`}
            >
              Read more
            </button>

            <button
              onClick={() => onOpenLogin('signup')}
              className="text-xs font-semibold text-neutral-900 dark:text-neutral-100 hover:underline flex items-center gap-1 cursor-pointer"
            >
              <span>Test this module</span>
              <ArrowRight className="w-3 h-3" />
            </button>
          </div>
        </div>

        {/* Right Column: Square Blank White Card with Sharp Corners */}
        <div className={`lg:col-span-7 p-6 sm:p-10 lg:p-12 flex items-center justify-center ${
          darkMode ? 'bg-[#08080a]' : 'bg-[#fafbfc]'
        }`}>
          {/* Framed container with sharp corners */}
          <div className={`w-full max-w-[460px] p-4 sm:p-6 rounded-none border transition-all duration-200 ${
            darkMode ? 'bg-[#0e0e13] border-neutral-800' : 'bg-[#f4f5f8] border-neutral-200'
          }`}>
            
            {/* The Square Blank White Card with Sharp Corners (zero information) */}
            <div 
              id="feature-blank-square-card"
              className="w-full aspect-square bg-white border border-neutral-200/90 rounded-none shadow-xs flex items-center justify-center"
            >
              {/* Nothing, zero information */}
            </div>

          </div>
        </div>

      </div>
    </section>
  );
};
