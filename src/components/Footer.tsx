import React from 'react';

interface FooterProps {
  darkMode: boolean;
  onScrollTo: (id: string) => void;
  onOpenLogin: (mode?: 'signup' | 'login' | 'contact') => void;
}

export const Footer: React.FC<FooterProps> = ({ darkMode, onScrollTo, onOpenLogin }) => {
  return (
    <footer
      className={`transition-colors duration-200 ${
        darkMode ? 'bg-black text-white' : 'bg-white text-neutral-900'
      }`}
    >
      {/* Empty horizontal divider band matching image.png */}
      <div
        className={`h-6 md:h-8 border-t ${
          darkMode ? 'border-neutral-800' : 'border-neutral-200'
        }`}
      />

      {/* 3 Columns: Product, Company, Social matching image.png */}
      <div
        className={`border-t grid grid-cols-1 md:grid-cols-12 ${
          darkMode ? 'border-neutral-800' : 'border-neutral-200'
        }`}
      >
        {/* Product Column */}
        <div
          className={`md:col-span-3 p-8 md:p-12 border-b md:border-b-0 md:border-r ${
            darkMode ? 'border-neutral-800' : 'border-neutral-200'
          }`}
        >
          <div className="font-bold text-base mb-4 tracking-tight">
            Product
          </div>
          <ul className={`space-y-3 text-sm ${darkMode ? 'text-neutral-400' : 'text-neutral-600'}`}>
            <li>
              <button
                onClick={() => onScrollTo('hero-section')}
                className="hover:text-neutral-900 dark:hover:text-white transition-colors cursor-pointer text-left"
              >
                Home
              </button>
            </li>
            <li>
              <button
                onClick={() => onScrollTo('features-section')}
                className="hover:text-neutral-900 dark:hover:text-white transition-colors cursor-pointer text-left"
              >
                Features
              </button>
            </li>
            <li>
              <a
                href="#blog"
                className="hover:text-neutral-900 dark:hover:text-white transition-colors block"
              >
                Blog
              </a>
            </li>
            <li>
              <button
                onClick={() => onScrollTo('pricing-section')}
                className="hover:text-neutral-900 dark:hover:text-white transition-colors cursor-pointer text-left"
              >
                Pricing
              </button>
            </li>
          </ul>
        </div>

        {/* Company Column */}
        <div
          className={`md:col-span-3 p-8 md:p-12 border-b md:border-b-0 md:border-r ${
            darkMode ? 'border-neutral-800' : 'border-neutral-200'
          }`}
        >
          <div className="font-bold text-base mb-4 tracking-tight">
            Company
          </div>
          <ul className={`space-y-3 text-sm ${darkMode ? 'text-neutral-400' : 'text-neutral-600'}`}>
            <li>
              <button
                onClick={() => onOpenLogin('signup')}
                className="hover:text-neutral-900 dark:hover:text-white transition-colors cursor-pointer text-left"
              >
                About
              </button>
            </li>
            <li>
              <button
                onClick={() => onScrollTo('faq-section')}
                className="hover:text-neutral-900 dark:hover:text-white transition-colors cursor-pointer text-left"
              >
                Faq
              </button>
            </li>
            <li>
              <button
                onClick={() => onOpenLogin('contact')}
                className="hover:text-neutral-900 dark:hover:text-white transition-colors cursor-pointer text-left"
              >
                Contact
              </button>
            </li>
          </ul>
        </div>

        {/* Social Icons Column matching image.png (aligned top-right) */}
        <div className="md:col-span-6 p-8 md:p-12 flex justify-start md:justify-end items-start">
          <div className="flex items-center gap-4 text-neutral-800 dark:text-neutral-200">
            {/* Facebook */}
            <a
              href="https://facebook.com"
              target="_blank"
              rel="noreferrer"
              aria-label="Facebook"
              className="p-1 hover:text-black dark:hover:text-white transition-colors"
            >
              <svg className="w-4 h-4 fill-current" viewBox="0 0 24 24">
                <path d="M24 12.073c0-6.627-5.373-12-12-12s-12 5.373-12 12c0 5.99 4.388 10.954 10.125 11.854v-8.385H7.078v-3.47h3.047V9.43c0-3.007 1.792-4.669 4.533-4.669 1.312 0 2.686.235 2.686.235v2.953H15.83c-1.491 0-1.956.925-1.956 1.874v2.25h3.328l-.532 3.47h-2.796v8.385C19.612 23.027 24 18.062 24 12.073z" />
              </svg>
            </a>

            {/* Twitter / X */}
            <a
              href="https://twitter.com"
              target="_blank"
              rel="noreferrer"
              aria-label="Twitter"
              className="p-1 hover:text-black dark:hover:text-white transition-colors"
            >
              <svg className="w-4 h-4 fill-current" viewBox="0 0 24 24">
                <path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z" />
              </svg>
            </a>

            {/* LinkedIn */}
            <a
              href="https://linkedin.com"
              target="_blank"
              rel="noreferrer"
              aria-label="LinkedIn"
              className="p-1 hover:text-black dark:hover:text-white transition-colors"
            >
              <svg className="w-4 h-4 fill-current" viewBox="0 0 24 24">
                <path d="M19 0h-14c-2.761 0-5 2.239-5 5v14c0 2.761 2.239 5 5 5h14c2.762 0 5-2.239 5-5v-14c0-2.761-2.238-5-5-5zm-11 19h-3v-11h3v11zm-1.5-12.268c-.966 0-1.75-.79-1.75-1.764s.784-1.764 1.75-1.764 1.75.79 1.75 1.764-.783 1.764-1.75 1.764zm13.5 12.268h-3v-5.604c0-3.368-4-3.113-4 0v5.604h-3v-11h3v1.765c1.396-2.586 7-2.777 7 2.476v6.759z" />
              </svg>
            </a>
          </div>
        </div>
      </div>

      {/* Regulatory disclaimer + Aspect Logo row matching image.png */}
      <div
        className={`border-t p-8 md:p-12 flex flex-col md:flex-row items-start md:items-center justify-between gap-8 ${
          darkMode ? 'border-neutral-800' : 'border-neutral-200'
        }`}
      >
        {/* Left: Regulatory disclaimer */}
        <div className="max-w-md">
          <div className="font-semibold text-xs text-neutral-900 dark:text-neutral-100 mb-1">
            Regulatory & Compliance
          </div>
          <p className="text-[11px] leading-relaxed text-neutral-500 dark:text-neutral-400">
            PromiseCheck is an enterprise commitment tracking and delivery governance platform. All systems and integrations are encrypted with enterprise-grade SOC2 compliance.
          </p>
        </div>

        {/* Right: PromiseCheck geometric wireframe logo + Wordmark */}
        <div className="flex items-center gap-3.5 self-start md:self-auto">
          <svg
            viewBox="0 0 70 70"
            className="w-11 h-11 stroke-current fill-none stroke-[1.4]"
          >
            {/* Outer Hexagon */}
            <polygon points="35,4 62,19.5 62,50.5 35,66 8,50.5 8,19.5" />
            
            {/* Inner Y branches */}
            <line x1="35" y1="35" x2="35" y2="66" />
            <line x1="35" y1="35" x2="62" y2="19.5" />
            <line x1="35" y1="35" x2="8" y2="19.5" />

            {/* Isometric subdivision lines top face */}
            <line x1="21.5" y1="11.75" x2="48.5" y2="27.25" />
            <line x1="48.5" y1="11.75" x2="21.5" y2="27.25" />

            {/* Isometric subdivision lines bottom-left face */}
            <line x1="8" y1="35" x2="35" y2="50.5" />
            <line x1="21.5" y1="27.25" x2="21.5" y2="58.25" />

            {/* Isometric subdivision lines bottom-right face */}
            <line x1="62" y1="35" x2="35" y2="50.5" />
            <line x1="48.5" y1="27.25" x2="48.5" y2="58.25" />

            {/* Additional internal wireframe diamond accents */}
            <line x1="35" y1="4" x2="35" y2="35" />
          </svg>
          <span className="text-3xl md:text-[38px] font-normal tracking-tight">
            PromiseCheck
          </span>
        </div>
      </div>

      {/* Bottom Copyright line */}
      <div
        className={`border-t px-6 md:px-12 py-4 flex flex-col sm:flex-row items-center justify-between text-[11px] text-neutral-500 dark:text-neutral-400 gap-2 ${
          darkMode ? 'border-neutral-800' : 'border-neutral-200'
        }`}
      >
        <div>
          © 2025 PromiseCheck. All rights reserved.
        </div>
        <div className="flex items-center gap-5">
          <a href="#privacy" className="hover:underline transition-colors">
            Privacy Policy
          </a>
          <a href="#cookies" className="hover:underline transition-colors">
            Cookie Settings
          </a>
          <a href="#terms" className="hover:underline transition-colors">
            Terms of Service
          </a>
        </div>
      </div>
    </footer>
  );
};
