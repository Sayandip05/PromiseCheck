import React from 'react';
import { Upload, Plus, Menu } from 'lucide-react';

interface HeaderProps {
  title?: string;
  subtitle?: string;
  dateStr?: string;
  onOpenUpload: () => void;
  onOpenAddCommitment: () => void;
  onOpenMobileMenu: () => void;
}

export const Header: React.FC<HeaderProps> = ({
  title = 'Customer commitments',
  subtitle = 'Track every promise from conversation to delivery.',
  dateStr = 'As of Sep 24, 2026',
  onOpenUpload,
  onOpenAddCommitment,
  onOpenMobileMenu,
}) => {
  return (
    <header className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-6 pt-2">
      {/* Title & Subtitle + Mobile Hamburger */}
      <div className="flex items-start gap-3">
        <button
          onClick={onOpenMobileMenu}
          className="lg:hidden p-2 -ml-2 text-neutral-600 dark:text-neutral-300 hover:text-neutral-900 dark:hover:text-white rounded-lg hover:bg-neutral-100 dark:hover:bg-neutral-800 transition-colors mt-0.5"
          aria-label="Open navigation menu"
        >
          <Menu className="w-5 h-5" />
        </button>

        <div>
          <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-neutral-900 dark:text-white">
            {title}
          </h1>
          <p className="text-xs sm:text-sm text-neutral-500 dark:text-neutral-400 mt-0.5">{subtitle}</p>
        </div>
      </div>

      {/* Date & Action Buttons */}
      <div className="flex items-center flex-wrap gap-2.5 sm:gap-3">
        {dateStr && (
          <span className="text-xs text-neutral-400 dark:text-neutral-500 font-medium hidden sm:inline-block mr-1">
            {dateStr}
          </span>
        )}

        <button
          onClick={onOpenUpload}
          className="inline-flex items-center gap-2 px-3.5 py-2 text-xs sm:text-sm font-medium text-neutral-700 dark:text-neutral-200 bg-white dark:bg-neutral-800 border border-neutral-300 dark:border-neutral-700 rounded-lg shadow-2xs hover:bg-neutral-50 dark:hover:bg-neutral-750 hover:text-neutral-900 dark:hover:text-white transition-all active:scale-98 cursor-pointer"
        >
          <Upload className="w-3.5 h-3.5 sm:w-4 sm:h-4 text-neutral-500 dark:text-neutral-400" />
          <span>Upload transcript</span>
        </button>

        <button
          onClick={onOpenAddCommitment}
          className="inline-flex items-center gap-1.5 px-3.5 py-2 text-xs sm:text-sm font-medium text-white dark:text-neutral-950 bg-neutral-950 dark:bg-white rounded-lg shadow-xs hover:bg-neutral-800 dark:hover:bg-neutral-200 transition-all active:scale-98 cursor-pointer"
        >
          <Plus className="w-3.5 h-3.5 sm:w-4 sm:h-4" />
          <span>Add commitment</span>
        </button>
      </div>
    </header>
  );
};
