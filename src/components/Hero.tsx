import React from 'react';

interface HeroProps {
  darkMode: boolean;
  onOpenLogin: (mode?: 'signup' | 'login') => void;
}

export const Hero: React.FC<HeroProps> = ({ darkMode, onOpenLogin }) => {
  return (
    <section 
      id="hero-section"
      className={`relative pt-16 pb-20 lg:pt-24 lg:pb-32 px-6 md:px-12 border-b transition-colors duration-200 ${
        darkMode 
          ? 'bg-black border-neutral-800 text-white' 
          : 'bg-white border-neutral-200 text-neutral-900'
      }`}
    >
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-10 lg:gap-14 items-center">
        
        {/* Left Column: Heading, Subheading, CTAs */}
        <div className="lg:col-span-5 flex flex-col justify-center">
          <h1 
            id="hero-title"
            className="text-[40px] sm:text-[50px] lg:text-[56px] font-normal tracking-[-0.035em] leading-[1.12]"
          >
            All Your Customer Promises in One Unified Dashboard
          </h1>

          <p className={`mt-7 text-[16px] sm:text-[17px] leading-relaxed max-w-lg font-normal ${
            darkMode ? 'text-neutral-400' : 'text-neutral-600'
          }`}>
            PromiseCheck automatically catches commitments in your meeting notes and emails, keeps team progress on track, and gives you a heads-up before deadlines slip so customer trust stays protected.
          </p>

          <div className="mt-9 flex flex-wrap items-center gap-3">
            {/* Try for free button */}
            <button
              id="hero-try-free-btn"
              onClick={() => onOpenLogin('signup')}
              className={`font-medium text-[15px] px-6 py-2.5 rounded-lg transition-all cursor-pointer ${
                darkMode
                  ? 'bg-neutral-800 hover:bg-neutral-700 text-white border border-neutral-700'
                  : 'bg-[#d8dadf] hover:bg-[#cbced5] text-neutral-900'
              }`}
            >
              Try for free
            </button>

            {/* Book a demo button */}
            <button
              id="hero-book-demo-btn"
              onClick={() => onOpenLogin('signup')}
              className={`font-medium text-[15px] px-6 py-2.5 rounded-lg transition-all cursor-pointer ${
                darkMode
                  ? 'bg-neutral-900 hover:bg-neutral-800 text-neutral-300 border border-neutral-800'
                  : 'bg-[#eeeff2] hover:bg-[#e4e6ea] text-neutral-900 border border-neutral-200'
              }`}
            >
              Book a demo
            </button>
          </div>
        </div>

        {/* Right Column: Blank Space & White Placeholder with Sharp Corners */}
        <div className="lg:col-span-7">
          {/* Framed container with sharp corners */}
          <div 
            className={`p-3 sm:p-5 lg:p-6 rounded-none border transition-colors duration-200 shadow-xs ${
              darkMode 
                ? 'bg-[#0e0e12] border-neutral-800' 
                : 'bg-[#f4f5f8] border-neutral-200'
            }`}
          >
            {/* The White Placeholder (blank space, sharp corners) */}
            <div 
              id="hero-dashboard-placeholder"
              className="w-full min-h-[360px] sm:min-h-[440px] lg:min-h-[480px] bg-white border border-neutral-200/90 rounded-none shadow-xs flex items-center justify-center p-6 sm:p-8"
            >
              {/* Blank placeholder space */}
            </div>
          </div>
        </div>

      </div>
    </section>
  );
};
