import React from 'react';

interface TestimonialsProps {
  darkMode: boolean;
}

export const Testimonials: React.FC<TestimonialsProps> = ({ darkMode }) => {
  return (
    <section 
      id="testimonials-section" 
      className={`border-b transition-colors duration-200 ${
        darkMode ? 'bg-black text-white border-neutral-800' : 'bg-white text-neutral-900 border-neutral-200'
      }`}
    >
      <div className="pt-20 pb-16 px-6 md:px-12 text-center max-w-3xl mx-auto">
        {/* Section Header */}
        <h2 className="text-3xl sm:text-4xl lg:text-[44px] font-normal tracking-[-0.03em] leading-[1.15]">
          What Our Customers Are Saying
        </h2>

        <p className={`mt-4 text-[15px] max-w-xl mx-auto leading-relaxed ${
          darkMode ? 'text-neutral-400' : 'text-neutral-600'
        }`}>
          Don't just take our word for it—see how our platform is empowering teams to achieve more, streamline workflows, and transform their day-to-day operations.
        </p>

        {/* Rating Pill Badge: 5 stars + "Real Results." */}
        <div className={`mt-8 inline-flex items-center gap-3 px-3.5 py-1.5 rounded-full border shadow-2xs ${
          darkMode 
            ? 'bg-neutral-900 border-neutral-800 text-neutral-200' 
            : 'bg-neutral-50 border-neutral-200 text-neutral-800'
        }`}>
          <div className="flex items-center gap-1 text-neutral-900 dark:text-neutral-100">
            {[...Array(5)].map((_, i) => (
              <svg 
                key={i} 
                viewBox="0 0 24 24" 
                className="w-4 h-4 fill-current"
              >
                <path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z" />
              </svg>
            ))}
          </div>
          <div className={`w-[1px] h-3.5 ${darkMode ? 'bg-neutral-700' : 'bg-neutral-300'}`} />
          <span className="text-xs font-semibold">
            Real Results.
          </span>
        </div>
      </div>

      {/* 2-Column Testimonial Grid with vertical divider */}
      <div className={`border-t grid grid-cols-1 md:grid-cols-2 divide-y md:divide-y-0 md:divide-x ${
        darkMode ? 'border-neutral-800 divide-neutral-800' : 'border-neutral-200 divide-neutral-200'
      }`}>
        
        {/* Testimonial Card 1: MERCURY */}
        <div className={`p-8 sm:p-12 lg:p-16 flex flex-col justify-between transition-colors ${
          darkMode ? 'hover:bg-neutral-950' : 'hover:bg-neutral-50/60'
        }`}>
          <div>
            {/* Mercury Logo */}
            <div className="flex items-center gap-2">
              <svg viewBox="0 0 24 24" className="w-6 h-6 fill-none stroke-current stroke-2">
                <circle cx="12" cy="12" r="8" />
                <circle cx="12" cy="12" r="4" />
              </svg>
              <span className="font-semibold tracking-[0.2em] text-sm">
                MERCURY
              </span>
            </div>

            {/* Quote matching typography */}
            <p className={`mt-8 text-lg sm:text-[19px] font-normal leading-relaxed ${
              darkMode ? 'text-neutral-200' : 'text-neutral-800'
            }`}>
              “Since integrating PromiseCheck’s unified dashboard, we’ve consolidated all our customer commitments into one view—no more juggling multiple spreadsheets or missed deadlines in Slack.”
            </p>
          </div>

          {/* Author Info */}
          <div className="mt-10 flex items-center gap-3.5">
            <img
              src="https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=120&auto=format&fit=crop&q=80"
              alt="John Doe"
              className={`w-10 h-10 rounded-full object-cover border ${
                darkMode ? 'border-neutral-700' : 'border-neutral-300'
              }`}
            />
            <div>
              <div className="font-semibold text-sm">
                John Doe
              </div>
              <div className={`text-xs ${darkMode ? 'text-neutral-400' : 'text-neutral-500'}`}>
                Mercury, Inc.
              </div>
            </div>
          </div>
        </div>

        {/* Testimonial Card 2: Watershed */}
        <div className={`p-8 sm:p-12 lg:p-16 flex flex-col justify-between transition-colors ${
          darkMode ? 'hover:bg-neutral-950' : 'hover:bg-neutral-50/60'
        }`}>
          <div>
            {/* Watershed Logo */}
            <div className="flex items-center gap-2">
              <svg viewBox="0 0 24 24" className="w-6 h-6 fill-none stroke-current stroke-2">
                <circle cx="12" cy="12" r="9" />
                <path d="M3.6 9h16.8M3.6 15h16.8" />
                <path d="M12 3a14 14 0 0 1 0 18M12 3a14 14 0 0 0 0 18" />
              </svg>
              <span className="font-semibold text-base tracking-tight">
                Watershed
              </span>
            </div>

            {/* Quote matching typography */}
            <p className={`mt-8 text-lg sm:text-[19px] font-normal leading-relaxed ${
              darkMode ? 'text-neutral-200' : 'text-neutral-800'
            }`}>
              “PromiseCheck has been a game-changer for our Watershed team—real-time commitment tracking and proactive alerts keep us on top of customer deliverables like never before.”
            </p>
          </div>

          {/* Author Info */}
          <div className="mt-10 flex items-center gap-3.5">
            <img
              src="https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=120&auto=format&fit=crop&q=80"
              alt="Jane Smith"
              className={`w-10 h-10 rounded-full object-cover border ${
                darkMode ? 'border-neutral-700' : 'border-neutral-300'
              }`}
            />
            <div>
              <div className="font-semibold text-sm">
                Jane Smith
              </div>
              <div className={`text-xs ${darkMode ? 'text-neutral-400' : 'text-neutral-500'}`}>
                Watershed Labs
              </div>
            </div>
          </div>
        </div>

      </div>
    </section>
  );
};
