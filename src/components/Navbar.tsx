import React, { useState } from 'react';
import { 
  ChevronDown, 
  Sun, 
  Moon, 
  Menu, 
  X, 
  ShieldCheck, 
  ScanSearch, 
  BellRing, 
  FileCheck2, 
  Sparkles,
  ArrowRight
} from 'lucide-react';

interface NavbarProps {
  darkMode: boolean;
  onToggleTheme: () => void;
  onOpenLogin: (mode?: 'signup' | 'login' | 'contact') => void;
  onScrollTo: (id: string) => void;
}

export const Navbar: React.FC<NavbarProps> = ({
  darkMode,
  onToggleTheme,
  onOpenLogin,
  onScrollTo
}) => {
  const [productDropdownOpen, setProductDropdownOpen] = useState(false);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  return (
    <header 
      id="top-navbar" 
      className={`sticky top-0 z-50 w-full transition-colors duration-200 border-b ${
        darkMode 
          ? 'bg-black border-neutral-800 text-white' 
          : 'bg-white border-neutral-200 text-neutral-900'
      }`}
    >
      <div className="px-6 md:px-12 h-18 flex items-center justify-between">
        {/* Brand Logo */}
        <div 
          onClick={() => window.scrollTo({ top: 0, behavior: 'smooth' })} 
          className="flex items-center gap-3 cursor-pointer group select-none"
          id="brand-logo-container"
        >
          {/* Geometric wireframe icon matching Aspect's polygon style */}
          <div className="relative w-8 h-8 flex items-center justify-center">
            <svg 
              viewBox="0 0 36 36" 
              className="w-8 h-8 transition-transform duration-300 group-hover:scale-105"
              fill="none" 
              stroke="currentColor" 
              strokeWidth="1.6"
            >
              <polygon points="18,3 31,10.5 31,25.5 18,33 5,25.5 5,10.5" />
              <line x1="18" y1="3" x2="18" y2="33" />
              <line x1="5" y1="10.5" x2="31" y2="25.5" />
              <line x1="5" y1="25.5" x2="31" y2="10.5" />
              <circle cx="18" cy="18" r="3" fill="currentColor" fillOpacity="0.2" />
            </svg>
          </div>
          <span className="text-xl font-bold tracking-tight">PromiseCheck</span>
        </div>

        {/* Desktop Navigation Links */}
        <nav className={`hidden md:flex items-center gap-7 text-sm font-normal ${
          darkMode ? 'text-neutral-300' : 'text-neutral-600'
        }`}>
          {/* Product Dropdown */}
          <div 
            className="relative"
            onMouseEnter={() => setProductDropdownOpen(true)}
            onMouseLeave={() => setProductDropdownOpen(false)}
          >
            <button 
              id="nav-product-btn"
              onClick={() => onScrollTo('features-section')}
              className={`flex items-center gap-1 transition-colors py-2 cursor-pointer ${
                darkMode ? 'hover:text-white' : 'hover:text-black'
              }`}
            >
              <span>Product</span>
              <ChevronDown className={`w-3.5 h-3.5 transition-transform duration-200 ${productDropdownOpen ? 'rotate-180' : ''}`} />
            </button>

            {productDropdownOpen && (
              <div 
                className={`absolute top-full left-0 w-80 p-3 rounded-xl shadow-xl border ${
                  darkMode ? 'bg-[#0f0f14] border-neutral-800 text-neutral-200' : 'bg-white border-neutral-200 text-neutral-800'
                } animate-in fade-in slide-in-from-top-2 duration-150`}
              >
                <div 
                  onClick={() => { setProductDropdownOpen(false); onScrollTo('features-section'); }}
                  className={`p-2.5 rounded-lg cursor-pointer transition-colors ${
                    darkMode ? 'hover:bg-neutral-900' : 'hover:bg-neutral-100'
                  }`}
                >
                  <div className="flex items-center gap-2.5 font-medium text-sm">
                    <ScanSearch className="w-4 h-4 text-indigo-500" />
                    <span>Meeting & Email Extraction</span>
                  </div>
                  <p className={`text-xs mt-0.5 pl-6 ${darkMode ? 'text-neutral-400' : 'text-neutral-500'}`}>
                    Detect commitments in Gong, Zoom transcripts and threads.
                  </p>
                </div>

                <div 
                  onClick={() => { setProductDropdownOpen(false); onScrollTo('features-section'); }}
                  className={`p-2.5 rounded-lg cursor-pointer transition-colors ${
                    darkMode ? 'hover:bg-neutral-900' : 'hover:bg-neutral-100'
                  }`}
                >
                  <div className="flex items-center gap-2.5 font-medium text-sm">
                    <BellRing className="w-4 h-4 text-amber-500" />
                    <span>Early Deadline Radar</span>
                  </div>
                  <p className={`text-xs mt-0.5 pl-6 ${darkMode ? 'text-neutral-400' : 'text-neutral-500'}`}>
                    Proactive alerts to team leads before promises are delayed.
                  </p>
                </div>

                <div 
                  onClick={() => { setProductDropdownOpen(false); onOpenLogin('signup'); }}
                  className={`p-2.5 rounded-lg cursor-pointer transition-colors border-t mt-1 ${
                    darkMode ? 'hover:bg-neutral-900 border-neutral-800' : 'hover:bg-neutral-100 border-neutral-100'
                  }`}
                >
                  <div className="flex items-center justify-between text-xs font-semibold text-indigo-500">
                    <span className="flex items-center gap-1.5">
                      <Sparkles className="w-3.5 h-3.5" />
                      Try Interactive Scanner
                    </span>
                    <ArrowRight className="w-3.5 h-3.5" />
                  </div>
                </div>
              </div>
            )}
          </div>

          <button 
            id="nav-about-btn"
            onClick={() => onOpenLogin('signup')}
            className={`transition-colors cursor-pointer ${darkMode ? 'hover:text-white' : 'hover:text-black'}`}
          >
            About us
          </button>
          
          <button 
            id="nav-pricing-btn"
            onClick={() => onScrollTo('pricing-section')}
            className={`transition-colors cursor-pointer ${darkMode ? 'hover:text-white' : 'hover:text-black'}`}
          >
            Pricing
          </button>

          <button 
            id="nav-faq-btn"
            onClick={() => onScrollTo('faq-section')}
            className={`transition-colors cursor-pointer ${darkMode ? 'hover:text-white' : 'hover:text-black'}`}
          >
            FAQ
          </button>

          <button 
            id="nav-blog-btn"
            onClick={() => onScrollTo('testimonials-section')}
            className={`transition-colors cursor-pointer ${darkMode ? 'hover:text-white' : 'hover:text-black'}`}
          >
            Blog
          </button>

          <button 
            id="nav-contact-btn"
            onClick={() => onOpenLogin('contact')}
            className={`transition-colors cursor-pointer ${darkMode ? 'hover:text-white' : 'hover:text-black'}`}
          >
            Contact
          </button>
        </nav>

        {/* Right Action Items: Login button + Theme Toggle matching Screenshot 1 */}
        <div className="flex items-center gap-3">
          <button
            id="nav-login-btn"
            onClick={() => onOpenLogin('login')}
            className={`font-medium text-sm px-4 py-1.5 rounded-lg transition-all cursor-pointer ${
              darkMode 
                ? 'bg-neutral-800 hover:bg-neutral-700 text-white border border-neutral-700' 
                : 'bg-[#e5e7eb] hover:bg-[#d8dadf] text-neutral-900'
            }`}
          >
            Login
          </button>

          {/* Theme Toggle Sun/Moon Button matching Screenshot 1 */}
          <button
            id="theme-toggle-btn"
            onClick={onToggleTheme}
            aria-label="Toggle dark/light mode"
            className={`p-2 rounded-full border transition-all cursor-pointer ${
              darkMode 
                ? 'border-neutral-700 text-neutral-200 hover:bg-neutral-800' 
                : 'border-neutral-200 text-neutral-800 hover:bg-neutral-100 shadow-2xs'
            }`}
          >
            {darkMode ? <Moon className="w-4 h-4" /> : <Sun className="w-4 h-4" />}
          </button>

          {/* Mobile hamburger menu */}
          <button
            id="mobile-menu-toggle-btn"
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            className={`md:hidden p-2 rounded-lg ${
              darkMode ? 'text-neutral-300 hover:bg-neutral-900' : 'text-neutral-700 hover:bg-neutral-100'
            }`}
          >
            {mobileMenuOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
          </button>
        </div>
      </div>

      {/* Mobile Menu Drawer */}
      {mobileMenuOpen && (
        <div className={`md:hidden border-t px-6 py-4 space-y-3 ${
          darkMode ? 'bg-black border-neutral-800 text-neutral-200' : 'bg-white border-neutral-200 text-neutral-800'
        }`}>
          <button 
            onClick={() => { setMobileMenuOpen(false); onScrollTo('features-section'); }}
            className="block w-full text-left py-2 font-medium"
          >
            Product
          </button>
          <button 
            onClick={() => { setMobileMenuOpen(false); onOpenLogin('signup'); }}
            className="block w-full text-left py-2 font-medium"
          >
            About us
          </button>
          <button 
            onClick={() => { setMobileMenuOpen(false); onScrollTo('pricing-section'); }}
            className="block w-full text-left py-2 font-medium"
          >
            Pricing
          </button>
          <button 
            onClick={() => { setMobileMenuOpen(false); onScrollTo('faq-section'); }}
            className="block w-full text-left py-2 font-medium"
          >
            FAQ
          </button>
          <button 
            onClick={() => { setMobileMenuOpen(false); onScrollTo('testimonials-section'); }}
            className="block w-full text-left py-2 font-medium"
          >
            Customer Stories
          </button>
          <button 
            onClick={() => { setMobileMenuOpen(false); onOpenLogin('contact'); }}
            className="block w-full text-left py-2 font-medium"
          >
            Contact
          </button>
          <button 
            onClick={() => { setMobileMenuOpen(false); onOpenLogin('signup'); }}
            className="w-full py-2.5 mt-2 text-center rounded-lg bg-neutral-900 dark:bg-white text-white dark:text-black font-medium text-sm transition-colors"
          >
            Create an account / Login
          </button>
        </div>
      )}
    </header>
  );
};
