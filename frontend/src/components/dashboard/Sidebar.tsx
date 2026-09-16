import React, { useState } from 'react';
import {
  LayoutDashboard,
  FileText,
  Users,
  ListTodo,
  Video,
  Cable,
  ShieldCheck,
  Settings,
  LogOut,
  Building2,
  Sun,
  Moon,
} from 'lucide-react';
import { motion } from 'framer-motion';
import { DashboardView, Workspace } from '../../types/dashboard';
import { Sidebar as AceternitySidebar, SidebarBody, SidebarLink } from '../ui/sidebar';

interface SidebarProps {
  currentView: DashboardView;
  onSelectView: (view: DashboardView) => void;
  isOpenMobile: boolean;
  onCloseMobile: () => void;
  currentWorkspace: Workspace;
  onSwitchWorkspace: (workspace: Workspace) => void;
  reviewCount: number;
  onSignOut: () => void;
  darkMode?: boolean;
  onToggleTheme?: () => void;
  user?: { full_name?: string | null; name?: string | null; email?: string } | null;
}

export const Logo = () => {
  return (
    <div className="font-normal flex items-center gap-2.5 py-1 px-1 relative z-20">
      <div className="w-8 h-8 rounded-xl bg-neutral-900 flex items-center justify-center text-white shrink-0 shadow-xs">
        <svg
          viewBox="0 0 24 24"
          className="w-4.5 h-4.5 fill-none stroke-white stroke-[2]"
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          <path d="m12 3-8 4.5v9L12 21l8-4.5v-9L12 3Z" />
          <path d="M12 12 4 7.5" />
          <path d="m12 12 8-4.5" />
          <path d="M12 12v9" />
        </svg>
      </div>
      <motion.span
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        className="font-bold text-base tracking-tight text-neutral-900 dark:text-white whitespace-pre"
      >
        PromiseCheck
      </motion.span>
    </div>
  );
};

export const LogoIcon = () => {
  return (
    <div className="font-normal flex items-center justify-center py-1 relative z-20 w-10 h-10 mx-auto">
      <div className="w-8 h-8 rounded-xl bg-neutral-900 flex items-center justify-center text-white shrink-0 shadow-xs">
        <svg
          viewBox="0 0 24 24"
          className="w-4.5 h-4.5 fill-none stroke-white stroke-[2]"
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          <path d="m12 3-8 4.5v9L12 21l8-4.5v-9L12 3Z" />
          <path d="M12 12 4 7.5" />
          <path d="m12 12 8-4.5" />
          <path d="M12 12v9" />
        </svg>
      </div>
    </div>
  );
};

export const Sidebar: React.FC<SidebarProps> = ({
  currentView,
  onSelectView,
  isOpenMobile,
  onCloseMobile,
  currentWorkspace,
  onSwitchWorkspace,
  reviewCount,
  onSignOut,
  darkMode = false,
  onToggleTheme,
  user,
}) => {
  const [open, setOpen] = useState(false);

  const handleNavClick = (view: DashboardView) => {
    onSelectView(view);
    onCloseMobile();
  };

  const primaryLinks = [
    {
      label: 'Commitments',
      icon: <FileText className="text-neutral-700 dark:text-neutral-300 h-4.5 w-4.5 shrink-0" />,
      onClick: () => handleNavClick('commitments'),
      isActive: currentView === 'commitments',
    },
    {
      label: 'Customers',
      icon: <Users className="text-neutral-700 dark:text-neutral-300 h-4.5 w-4.5 shrink-0" />,
      onClick: () => handleNavClick('customers'),
      isActive: currentView === 'customers',
    },
    {
      label: 'Review queue',
      icon: <ListTodo className="text-neutral-700 dark:text-neutral-300 h-4.5 w-4.5 shrink-0" />,
      badge: reviewCount,
      onClick: () => handleNavClick('review-queue'),
      isActive: currentView === 'review-queue',
    },
    {
      label: 'Meetings',
      icon: <Video className="text-neutral-700 dark:text-neutral-300 h-4.5 w-4.5 shrink-0" />,
      onClick: () => handleNavClick('meetings'),
      isActive: currentView === 'meetings',
    },
  ];

  const secondaryLinks = [
    {
      label: 'Integrations',
      icon: <Cable className="text-neutral-700 dark:text-neutral-300 h-4.5 w-4.5 shrink-0" />,
      onClick: () => handleNavClick('integrations'),
      isActive: currentView === 'integrations',
    },
    {
      label: 'Audit log',
      icon: <ShieldCheck className="text-neutral-700 dark:text-neutral-300 h-4.5 w-4.5 shrink-0" />,
      onClick: () => handleNavClick('audit-log'),
      isActive: currentView === 'audit-log',
    },
    {
      label: 'Settings',
      icon: <Settings className="text-neutral-700 dark:text-neutral-300 h-4.5 w-4.5 shrink-0" />,
      onClick: () => handleNavClick('settings'),
      isActive: currentView === 'settings',
    },
  ];

  return (
    <AceternitySidebar open={open} setOpen={setOpen}>
      <SidebarBody className="justify-between gap-6">
        <div className="flex flex-col flex-1 overflow-y-auto overflow-x-hidden">
          {/* Logo */}
          <div className="h-10 flex items-center">
            {open ? <Logo /> : <LogoIcon />}
          </div>

          {/* Primary Navigation */}
          <div className="mt-6 flex flex-col gap-1.5">
            {primaryLinks.map((link, idx) => (
              <SidebarLink key={idx} link={link} />
            ))}
          </div>

          {/* Divider */}
          <div className="my-3.5 border-t border-neutral-200/80 dark:border-neutral-800" />

          {/* Secondary Navigation */}
          <div className="flex flex-col gap-1.5">
            {secondaryLinks.map((link, idx) => (
              <SidebarLink key={idx} link={link} />
            ))}
          </div>
        </div>

        {/* Bottom Profile & Sign out */}
        <div className="pt-2 border-t border-neutral-200/80 dark:border-neutral-800 flex flex-col gap-1.5">
          {onToggleTheme && (
            <div className={`flex items-center ${open ? 'justify-between px-2.5 py-1' : 'justify-center py-1'}`}>
              {open && (
                <span className="text-xs font-medium text-neutral-600 dark:text-neutral-400">
                  {darkMode ? 'Dark mode' : 'Light mode'}
                </span>
              )}
              <button
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
            </div>
          )}

          {(() => {
            const displayName = user?.full_name || user?.name || user?.email || 'Workspace Admin';
            const initials = (user?.full_name || user?.name)
              ? (user.full_name || user.name || '')
                  .split(' ')
                  .filter(Boolean)
                  .map((n) => n[0])
                  .join('')
                  .slice(0, 2)
              : user?.email
              ? user.email.slice(0, 2)
              : 'WA';

            return (
              <SidebarLink
                link={{
                  label: displayName,
                  icon: (
                    <div className="h-7 w-7 rounded-full bg-neutral-900 dark:bg-white text-white dark:text-neutral-900 flex items-center justify-center font-bold text-[11px] shrink-0 uppercase">
                      {initials}
                    </div>
                  ),
                  onClick: () => handleNavClick('settings'),
                }}
              />
            );
          })()}

          <SidebarLink
            link={{
              label: 'Sign out',
              icon: <LogOut className="text-neutral-500 hover:text-neutral-900 dark:text-neutral-400 h-4.5 w-4.5 shrink-0" />,
              onClick: onSignOut,
            }}
          />
        </div>
      </SidebarBody>
    </AceternitySidebar>
  );
};

export function SidebarDemo() {
  const links = [
    {
      label: "Dashboard",
      icon: <LayoutDashboard className="text-neutral-700 dark:text-neutral-200 h-5 w-5 flex-shrink-0" />,
    },
    {
      label: "Profile",
      icon: <Users className="text-neutral-700 dark:text-neutral-200 h-5 w-5 flex-shrink-0" />,
    },
    {
      label: "Settings",
      icon: <Settings className="text-neutral-700 dark:text-neutral-200 h-5 w-5 flex-shrink-0" />,
    },
    {
      label: "Logout",
      icon: <LogOut className="text-neutral-700 dark:text-neutral-200 h-5 w-5 flex-shrink-0" />,
    },
  ];
  const [open, setOpen] = useState(false);
  return (
    <div className="rounded-md flex flex-col md:flex-row bg-gray-100 dark:bg-neutral-800 w-full flex-1 max-w-7xl mx-auto border border-neutral-200 dark:border-neutral-700 overflow-hidden h-screen">
      <AceternitySidebar open={open} setOpen={setOpen}>
        <SidebarBody className="justify-between gap-10">
          <div className="flex flex-col flex-1 overflow-y-auto overflow-x-hidden">
            {open ? <Logo /> : <LogoIcon />}
            <div className="mt-8 flex flex-col gap-2">
              {links.map((link, idx) => (
                <SidebarLink key={idx} link={link} />
              ))}
            </div>
          </div>
          <div>
            <SidebarLink
              link={{
                label: "Workspace Admin",
                icon: (
                  <div className="h-7 w-7 rounded-full bg-neutral-900 text-white flex items-center justify-center font-bold text-[11px] shrink-0">
                    WA
                  </div>
                ),
              }}
            />
          </div>
        </SidebarBody>
      </AceternitySidebar>
    </div>
  );
}

