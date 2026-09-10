import React, { useState } from 'react';
import { Check } from 'lucide-react';

interface PricingSectionProps {
  darkMode: boolean;
  onOpenLogin: (mode?: 'signup' | 'login' | 'contact') => void;
}

export const PricingSection: React.FC<PricingSectionProps> = ({
  darkMode,
  onOpenLogin
}) => {
  const [isAnnual, setIsAnnual] = useState<boolean>(true);

  return (
    <section
      id="pricing-section"
      className={`border-b transition-colors duration-200 ${
        darkMode ? 'bg-black text-white border-neutral-800' : 'bg-white text-neutral-900 border-neutral-200'
      }`}
    >
      <div className="pt-16 pb-12">
        {/* Header matching image.png */}
        <div className="text-center px-6">
          <h2 className="text-3xl sm:text-4xl font-normal tracking-[-0.025em]">
            Pricing
          </h2>
          <p className={`mt-2 text-xs sm:text-sm ${
            darkMode ? 'text-neutral-400' : 'text-neutral-500'
          }`}>
            Choose the plan that fits your needs
          </p>

          {/* Toggle matching image.png: [toggle] Billed annually */}
          <div className="mt-5 flex items-center justify-center gap-2">
            <button
              onClick={() => setIsAnnual(!isAnnual)}
              aria-label="Toggle annual billing"
              className={`relative inline-flex h-5 w-9 shrink-0 cursor-pointer rounded-full p-0.5 transition-colors duration-200 ease-in-out focus:outline-hidden ${
                isAnnual
                  ? darkMode ? 'bg-neutral-700' : 'bg-neutral-900'
                  : darkMode ? 'bg-neutral-800' : 'bg-neutral-300'
              }`}
            >
              <span
                className={`pointer-events-none inline-block h-4 w-4 transform rounded-full bg-white shadow-xs transition duration-200 ease-in-out ${
                  isAnnual ? 'translate-x-4' : 'translate-x-0'
                }`}
              />
            </button>
            <span
              onClick={() => setIsAnnual(!isAnnual)}
              className={`text-xs font-normal cursor-pointer select-none ${
                darkMode ? 'text-neutral-300' : 'text-neutral-800'
              }`}
            >
              Billed annually
            </span>
          </div>
        </div>

        {/* 3 Pricing Cards Grid matching image.png */}
        <div className="mt-12 grid grid-cols-1 md:grid-cols-3 gap-5 lg:gap-6 px-6 md:px-12 items-stretch">
          
          {/* Card 1: Free */}
          <div
            className={`rounded-2xl border p-6 sm:p-7 flex flex-col justify-between transition-colors ${
              darkMode 
                ? 'bg-black border-neutral-800' 
                : 'bg-white border-neutral-200'
            }`}
          >
            <div>
              <div className="text-lg font-bold tracking-tight">
                Free
              </div>
              <div className={`mt-2 text-base font-semibold ${
                darkMode ? 'text-neutral-200' : 'text-neutral-900'
              }`}>
                $0
              </div>

              <button
                onClick={() => onOpenLogin('signup')}
                className={`w-full mt-5 py-2 px-4 rounded-lg border text-xs sm:text-sm font-medium transition-colors cursor-pointer shadow-2xs ${
                  darkMode
                    ? 'bg-neutral-900 hover:bg-neutral-800 border-neutral-700 text-white'
                    : 'bg-white hover:bg-neutral-50 border-neutral-200 text-neutral-900'
                }`}
              >
                Get started
              </button>

              <div className="mt-6 space-y-3">
                <div className={`flex items-center gap-2 text-xs sm:text-[13px] ${
                  darkMode ? 'text-neutral-300' : 'text-neutral-700'
                }`}>
                  <Check className="w-3.5 h-3.5 text-neutral-900 dark:text-neutral-100 shrink-0 stroke-[2.2]" />
                  <span>Unlimited members</span>
                </div>
                <div className={`flex items-center gap-2 text-xs sm:text-[13px] ${
                  darkMode ? 'text-neutral-300' : 'text-neutral-700'
                }`}>
                  <Check className="w-3.5 h-3.5 text-neutral-900 dark:text-neutral-100 shrink-0 stroke-[2.2]" />
                  <span>2 teams</span>
                </div>
                <div className={`flex items-center gap-2 text-xs sm:text-[13px] ${
                  darkMode ? 'text-neutral-300' : 'text-neutral-700'
                }`}>
                  <Check className="w-3.5 h-3.5 text-neutral-900 dark:text-neutral-100 shrink-0 stroke-[2.2]" />
                  <span>500 issues</span>
                </div>
                <div className={`flex items-center gap-2 text-xs sm:text-[13px] ${
                  darkMode ? 'text-neutral-300' : 'text-neutral-700'
                }`}>
                  <Check className="w-3.5 h-3.5 text-neutral-900 dark:text-neutral-100 shrink-0 stroke-[2.2]" />
                  <span>Slack and Github integrations</span>
                </div>
              </div>
            </div>
          </div>

          {/* Card 2: Startup (Highlighted with lavender/tinted styling from image.png) */}
          <div
            className={`rounded-2xl border p-6 sm:p-7 flex flex-col justify-between transition-colors ${
              darkMode 
                ? 'bg-[#101017] border-neutral-800' 
                : 'bg-[#f4f4f7] border-neutral-200/90'
            }`}
          >
            <div>
              <div className="text-lg font-bold tracking-tight">
                Startup
              </div>
              <div className={`mt-2 text-base font-semibold ${
                darkMode ? 'text-neutral-200' : 'text-neutral-900'
              }`}>
                {isAnnual ? '$60 per user/annum' : '$7 per user/month'}
              </div>

              <button
                onClick={() => onOpenLogin('signup')}
                className={`w-full mt-5 py-2 px-4 rounded-lg text-xs sm:text-sm font-medium transition-colors cursor-pointer shadow-2xs ${
                  darkMode
                    ? 'bg-[#2f3045] hover:bg-[#393a52] text-white'
                    : 'bg-[#c8cadb] hover:bg-[#bbbdd0] text-neutral-900'
                }`}
              >
                7 day free trial
              </button>

              <div className="mt-6 space-y-3">
                <div className={`flex items-center gap-2 text-xs sm:text-[13px] ${
                  darkMode ? 'text-neutral-300' : 'text-neutral-700'
                }`}>
                  <Check className="w-3.5 h-3.5 text-neutral-900 dark:text-neutral-100 shrink-0 stroke-[2.2]" />
                  <span>All free plan features and...</span>
                </div>
                <div className={`flex items-center gap-2 text-xs sm:text-[13px] ${
                  darkMode ? 'text-neutral-300' : 'text-neutral-700'
                }`}>
                  <Check className="w-3.5 h-3.5 text-neutral-900 dark:text-neutral-100 shrink-0 stroke-[2.2]" />
                  <span>Streamline AI</span>
                </div>
                <div className={`flex items-center gap-2 text-xs sm:text-[13px] ${
                  darkMode ? 'text-neutral-300' : 'text-neutral-700'
                }`}>
                  <Check className="w-3.5 h-3.5 text-neutral-900 dark:text-neutral-100 shrink-0 stroke-[2.2]" />
                  <span>Unlimited teams</span>
                </div>
                <div className={`flex items-center gap-2 text-xs sm:text-[13px] ${
                  darkMode ? 'text-neutral-300' : 'text-neutral-700'
                }`}>
                  <Check className="w-3.5 h-3.5 text-neutral-900 dark:text-neutral-100 shrink-0 stroke-[2.2]" />
                  <span>Unlimited issues and file uploads</span>
                </div>
                <div className={`flex items-center gap-2 text-xs sm:text-[13px] ${
                  darkMode ? 'text-neutral-300' : 'text-neutral-700'
                }`}>
                  <Check className="w-3.5 h-3.5 text-neutral-900 dark:text-neutral-100 shrink-0 stroke-[2.2]" />
                  <span>Streamline Insights</span>
                </div>
                <div className={`flex items-center gap-2 text-xs sm:text-[13px] ${
                  darkMode ? 'text-neutral-300' : 'text-neutral-700'
                }`}>
                  <Check className="w-3.5 h-3.5 text-neutral-900 dark:text-neutral-100 shrink-0 stroke-[2.2]" />
                  <span>Admin roles</span>
                </div>
              </div>
            </div>
          </div>

          {/* Card 3: Enterprise */}
          <div
            className={`rounded-2xl border p-6 sm:p-7 flex flex-col justify-between transition-colors ${
              darkMode 
                ? 'bg-black border-neutral-800' 
                : 'bg-white border-neutral-200'
            }`}
          >
            <div>
              <div className="text-lg font-bold tracking-tight">
                Enterprise
              </div>
              <div className={`mt-2 text-base font-semibold ${
                darkMode ? 'text-neutral-200' : 'text-neutral-900'
              }`}>
                {isAnnual ? '$120 per user/annum' : '$14 per user/month'}
              </div>

              <button
                onClick={() => onOpenLogin('signup')}
                className={`w-full mt-5 py-2 px-4 rounded-lg border text-xs sm:text-sm font-medium transition-colors cursor-pointer shadow-2xs ${
                  darkMode
                    ? 'bg-neutral-900 hover:bg-neutral-800 border-neutral-700 text-white'
                    : 'bg-white hover:bg-neutral-50 border-neutral-200 text-neutral-900'
                }`}
              >
                Get started
              </button>

              <div className="mt-6 space-y-3">
                <div className={`flex items-center gap-2 text-xs sm:text-[13px] ${
                  darkMode ? 'text-neutral-300' : 'text-neutral-700'
                }`}>
                  <Check className="w-3.5 h-3.5 text-neutral-900 dark:text-neutral-100 shrink-0 stroke-[2.2]" />
                  <span>All free plan features and..</span>
                </div>
                <div className={`flex items-center gap-2 text-xs sm:text-[13px] ${
                  darkMode ? 'text-neutral-300' : 'text-neutral-700'
                }`}>
                  <Check className="w-3.5 h-3.5 text-neutral-900 dark:text-neutral-100 shrink-0 stroke-[2.2]" />
                  <span>Streamline AI</span>
                </div>
                <div className={`flex items-center gap-2 text-xs sm:text-[13px] ${
                  darkMode ? 'text-neutral-300' : 'text-neutral-700'
                }`}>
                  <Check className="w-3.5 h-3.5 text-neutral-900 dark:text-neutral-100 shrink-0 stroke-[2.2]" />
                  <span>Unlimited teams</span>
                </div>
                <div className={`flex items-center gap-2 text-xs sm:text-[13px] ${
                  darkMode ? 'text-neutral-300' : 'text-neutral-700'
                }`}>
                  <Check className="w-3.5 h-3.5 text-neutral-900 dark:text-neutral-100 shrink-0 stroke-[2.2]" />
                  <span>Unlimited issues and file uploads</span>
                </div>
                <div className={`flex items-center gap-2 text-xs sm:text-[13px] ${
                  darkMode ? 'text-neutral-300' : 'text-neutral-700'
                }`}>
                  <Check className="w-3.5 h-3.5 text-neutral-900 dark:text-neutral-100 shrink-0 stroke-[2.2]" />
                  <span>Streamline insights</span>
                </div>
                <div className={`flex items-center gap-2 text-xs sm:text-[13px] ${
                  darkMode ? 'text-neutral-300' : 'text-neutral-700'
                }`}>
                  <Check className="w-3.5 h-3.5 text-neutral-900 dark:text-neutral-100 shrink-0 stroke-[2.2]" />
                  <span>Admin roles</span>
                </div>
              </div>
            </div>
          </div>

        </div>
      </div>
    </section>
  );
};
