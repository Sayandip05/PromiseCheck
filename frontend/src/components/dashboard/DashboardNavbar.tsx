import React from 'react';
import { Search, Bell, Menu, HelpCircle, Sun, Moon } from 'lucide-react';

interface DashboardNavbarProps {
  workspaceName?: string;
  darkMode?: boolean;
  onToggleTheme?: () => void;
  onSetTheme?: (dark: boolean) => void;
  onNavigateLanding?: () => void;
  onOpenMobileMenu?: () => void;
  onSearchChange?: (query: string) => void;
}

export const DashboardNavbar: React.FC<DashboardNavbarProps> = ({
  workspaceName = 'Acme Workspace',
  darkMode = false,
  onToggleTheme,
  onSetTheme,
  onNavigateLanding,
  onOpenMobileMenu,
  onSearchChange,
}) => {
  return (
    <header className="h-16 bg-white dark:bg-neutral-900 border-b border-neutral-200/90 dark:border-neutral-800 px-4 sm:px-6 flex items-center justify-between shrink-0 sticky top-0 z-30 rounded-none md:rounded-tl-2xl transition-colors duration-200">
      {/* Left: Mobile Toggle */}
      <div className="flex items-center gap-2">
        {onOpenMobileMenu && (
          <button
            onClick={onOpenMobileMenu}
            className="lg:hidden p-2 -ml-2 text-neutral-600 dark:text-neutral-300 hover:text-neutral-900 dark:hover:text-white rounded-lg hover:bg-neutral-100 dark:hover:bg-neutral-800 transition-colors cursor-pointer"
            aria-label="Open sidebar"
          >
            <Menu className="w-5 h-5" />
          </button>
        )}
      </div>

      {/* Right: Search Bar + Theme Toggle Bar + Help + Notifications */}
      <div className="flex items-center gap-2 sm:gap-3 ml-auto shrink-0">
        {/* Search Bar */}
        <div className="relative hidden md:block w-44 lg:w-60">
          <Search className="w-3.5 h-3.5 text-neutral-400 absolute left-3 top-1/2 -translate-y-1/2 pointer-events-none" />
          <input
            type="text"
            placeholder="Search commitments, tickets..."
            onChange={(e) => onSearchChange && onSearchChange(e.target.value)}
            className="w-full pl-8 pr-10 py-1.5 text-xs bg-neutral-50/80 hover:bg-neutral-100/60 focus:bg-white dark:bg-neutral-800/80 dark:hover:bg-neutral-800 dark:focus:bg-neutral-800 dark:border-neutral-700 border border-neutral-200/90 rounded-lg text-neutral-800 dark:text-neutral-100 placeholder:text-neutral-400 dark:placeholder:text-neutral-500 focus:outline-none focus:ring-2 focus:ring-neutral-900/10 dark:focus:ring-neutral-700 focus:border-neutral-900 dark:focus:border-neutral-600 transition-all"
          />
          <kbd className="absolute right-2 top-1/2 -translate-y-1/2 text-[10px] font-medium text-neutral-400 bg-white dark:bg-neutral-750 dark:border-neutral-700 px-1.5 py-0.5 rounded border border-neutral-200 shadow-2xs pointer-events-none">
            ⌘K
          </kbd>
        </div>

        {/* Theme Toggle Sun/Moon Button (Replicated from landing page) */}
        <button
          id="theme-toggle-btn"
          onClick={onToggleTheme}
          aria-label="Toggle dark/light mode"
          title={darkMode ? 'Switch to light mode' : 'Switch to dark mode'}
          className={`p-2 rounded-full border transition-all cursor-pointer ${
            darkMode 
              ? 'border-neutral-700 text-neutral-200 hover:bg-neutral-800' 
              : 'border-neutral-200 text-neutral-800 hover:bg-neutral-100 shadow-2xs'
          }`}
        >
          {darkMode ? <Moon className="w-4 h-4" /> : <Sun className="w-4 h-4" />}
        </button>

        {/* Help Icon */}
        <button
          className="p-2 text-neutral-400 hover:text-neutral-700 dark:hover:text-neutral-200 hover:bg-neutral-100 dark:hover:bg-neutral-800 rounded-lg transition-colors cursor-pointer"
          aria-label="Help & Documentation"
          title="Help & Documentation"
        >
          <HelpCircle className="w-4 h-4" />
        </button>

        {/* Notification Bell with theme indicator dot */}
        <button
          className="p-2 text-neutral-600 dark:text-neutral-300 hover:text-neutral-900 dark:hover:text-white hover:bg-neutral-100 dark:hover:bg-neutral-800 rounded-lg transition-colors relative cursor-pointer"
          aria-label="Notifications"
          title="Notifications"
        >
          <Bell className="w-4 h-4" />
          <span className="w-2 h-2 rounded-full bg-neutral-900 dark:bg-white absolute top-1.5 right-1.5 ring-2 ring-white dark:ring-neutral-900" />
        </button>
      </div>
    </header>
  );
};

