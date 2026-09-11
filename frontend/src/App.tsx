import React, { useState } from 'react';
import { Sidebar } from './components/dashboard/Sidebar';
import { CommitmentsView } from './components/views/CommitmentsView';
import { IntegrationsView } from './components/views/IntegrationsView';
import { CustomersView } from './components/views/CustomersView';
import { ReviewQueueView } from './components/views/ReviewQueueView';
import { MeetingsView } from './components/views/MeetingsView';
import { AuditLogView } from './components/views/AuditLogView';
import { SettingsView } from './components/views/SettingsView';
import { DashboardNavbar } from './components/dashboard/DashboardNavbar';

// Modals
import { DraftUpdateModal } from './components/dashboard/DraftUpdateModal';
import { UploadTranscriptModal } from './components/dashboard/UploadTranscriptModal';
import { AddCommitmentModal } from './components/dashboard/AddCommitmentModal';
import { SlackIntegrationModal } from './components/dashboard/SlackIntegrationModal';

// Landing Page Components (accessible via toggle)
import { Navbar } from './components/Navbar';
import { Hero } from './components/Hero';
import { LogosAndFeatures } from './components/LogosAndFeatures';
import { Testimonials } from './components/Testimonials';
import { PricingSection } from './components/PricingSection';
import { FaqSection } from './components/FaqSection';
import { Footer } from './components/Footer';
import { LoginModal, AuthMode } from './components/LoginModal';

import {
  CURRENT_WORKSPACE,
  INITIAL_COMMITMENTS,
  RECENT_ACTIVITIES,
  INITIAL_INTEGRATIONS,
} from './data/dashboardData';
import { Commitment, DashboardView, Workspace } from './types/dashboard';
import { LayoutDashboard, Globe } from 'lucide-react';

export default function App() {
  // Mode defaults to 'landing' so http://localhost:3000/ opens the landing page first
  const [appMode, setAppMode] = useState<'dashboard' | 'landing'>('landing');

  // Dashboard state
  const [currentView, setCurrentView] = useState<DashboardView>('commitments');
  const [workspace, setWorkspace] = useState<Workspace>(CURRENT_WORKSPACE);
  const [commitments, setCommitments] = useState<Commitment[]>(INITIAL_COMMITMENTS);
  const [selectedCommitmentId, setSelectedCommitmentId] = useState<string>('comm-1');
  const [activeTab, setActiveTab] = useState<string>('needs-attention');
  const [activities, setActivities] = useState(RECENT_ACTIVITIES);
  const [integrations, setIntegrations] = useState(INITIAL_INTEGRATIONS);

  // Responsive UI state
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const [isDetailOpen, setIsDetailOpen] = useState(false);

  // Modal states
  const [isUploadOpen, setIsUploadOpen] = useState(false);
  const [isAddCommitmentOpen, setIsAddCommitmentOpen] = useState(false);
  const [isDraftUpdateOpen, setIsDraftUpdateOpen] = useState(false);
  const [isSlackModalOpen, setIsSlackModalOpen] = useState(false);

  // Landing page state
  const [darkMode, setDarkMode] = useState(false);
  const [isLoginOpen, setIsLoginOpen] = useState(false);
  const [authMode, setAuthMode] = useState<AuthMode>('signup');

  React.useEffect(() => {
    if (darkMode) {
      document.documentElement.classList.add('dark');
    } else {
      document.documentElement.classList.remove('dark');
    }
  }, [darkMode]);

  // Toast notification state
  const [toastMessage, setToastMessage] = useState<string | null>(null);

  const showToast = (msg: string) => {
    setToastMessage(msg);
    setTimeout(() => {
      setToastMessage(null);
    }, 4000);
  };

  const selectedCommitment =
    commitments.find((c) => c.id === selectedCommitmentId) || commitments[0] || null;

  // Handlers
  const handleSelectCommitment = (comm: Commitment) => {
    setSelectedCommitmentId(comm.id);
    setIsDetailOpen(true);
  };

  const handleAddCommitment = (newComm: Partial<Commitment>) => {
    const created: Commitment = {
      id: newComm.id || `comm-${Date.now()}`,
      title: newComm.title || 'Untitled Commitment',
      customer: newComm.customer || 'Acme',
      owner: newComm.owner || {
        name: 'Maya Chen',
        initials: 'MC',
        avatarColor: 'bg-neutral-200 text-neutral-800',
      },
      promisedBy: newComm.promisedBy || 'Oct 15, 2026',
      promisedDateIso: newComm.promisedDateIso || '2026-10-15',
      status: (newComm.status as any) || 'confirmed',
      statusLabel: newComm.statusLabel || 'On track',
      isConfirmed: true,
      category: newComm.category || 'on-track',
      originalPromise: newComm.originalPromise || {
        quote: 'Manually logged customer commitment',
        sourceTitle: 'Manual dashboard entry',
        timestamp: 'Just now',
      },
      engineeringEvidence: newComm.engineeringEvidence,
    };

    setCommitments([created, ...commitments]);
    setSelectedCommitmentId(created.id);
    showToast(`Created commitment "${created.title}"`);
  };

  const handleTranscriptUploaded = (data: { customer: string; meetingTitle: string; quote: string }) => {
    const extracted: Commitment = {
      id: `comm-${Date.now()}`,
      title: 'Sandbox Testing & Webhook Deployment',
      customer: data.customer,
      owner: {
        name: 'Maya Chen',
        initials: 'MC',
        avatarColor: 'bg-neutral-200 text-neutral-800',
      },
      promisedBy: 'Oct 09, 2026',
      promisedDateIso: '2026-10-09',
      status: 'awaiting-review',
      statusLabel: 'Awaiting review',
      isConfirmed: false,
      category: 'awaiting-review',
      originalPromise: {
        quote: data.quote,
        sourceTitle: data.meetingTitle,
        timestamp: 'Just now',
      },
      recommendedNextStep: {
        text: 'Review and confirm extracted terms before adding to customer SLA.',
        actionType: 'review',
      },
    };

    setCommitments([extracted, ...commitments]);
    setSelectedCommitmentId(extracted.id);
    setCurrentView('review-queue');
    showToast(`Transcript parsed! 1 new candidate promise awaiting review.`);
  };

  const handleConfirmCommitment = (id: string) => {
    setCommitments(
      commitments.map((c) =>
        c.id === id
          ? {
              ...c,
              isConfirmed: true,
              status: 'confirmed',
              statusLabel: 'On track',
              category: 'on-track',
            }
          : c
      )
    );
    showToast('Commitment confirmed and active on customer timeline!');
  };

  const handleRejectCommitment = (id: string) => {
    setCommitments(commitments.filter((c) => c.id !== id));
    showToast('Candidate promise dismissed from queue.');
  };

  const handleSendUpdate = (destination: string, message: string) => {
    showToast(`Delivered approved customer update to ${destination}`);
  };

  const unreviewedCount = commitments.filter((c) => c.category === 'awaiting-review').length;

  const getPageHeading = (view: DashboardView): string => {
    switch (view) {
      case 'commitments':
        return 'Customer commitments';
      case 'customers':
        return 'Customer Accounts';
      case 'review-queue':
        return 'Review Queue';
      case 'meetings':
        return 'Meetings & Transcripts';
      case 'integrations':
        return 'Workspace Integrations';
      case 'audit-log':
        return 'Audit Log';
      case 'settings':
        return 'Workspace Settings';
      default:
        return 'Customer commitments';
    }
  };

  // Render Public Landing Page
  if (appMode === 'landing') {
    return (
      <div className={`min-h-screen w-full transition-colors duration-200 ${
        darkMode ? 'dark bg-black text-white' : 'bg-white text-neutral-900'
      }`}>
        <div className={`max-w-[1400px] mx-auto border-x min-h-screen flex flex-col transition-colors duration-200 ${
          darkMode ? 'border-neutral-800 bg-black' : 'border-neutral-200 bg-white'
        }`}>
          <Navbar 
            darkMode={darkMode}
            onToggleTheme={() => setDarkMode(!darkMode)}
            onOpenLogin={() => {
              setAuthMode('login');
              setIsLoginOpen(true);
            }}
            onScrollTo={(id) => {
              const el = document.getElementById(id);
              if (el) el.scrollIntoView({ behavior: 'smooth' });
            }}
            onOpenDashboard={() => setAppMode('dashboard')}
          />

          <main className="flex-1">
            <Hero darkMode={darkMode} onOpenLogin={() => setAppMode('dashboard')} />
            <LogosAndFeatures darkMode={darkMode} onOpenLogin={() => setAppMode('dashboard')} />
            <Testimonials darkMode={darkMode} />
            <FaqSection darkMode={darkMode} />
            <PricingSection darkMode={darkMode} onOpenLogin={() => setAppMode('dashboard')} />
          </main>

          <Footer 
            darkMode={darkMode}
            onScrollTo={() => {}}
            onOpenLogin={() => setAppMode('dashboard')}
          />
        </div>

        <LoginModal 
          isOpen={isLoginOpen}
          onClose={() => setIsLoginOpen(false)}
          darkMode={darkMode}
          initialMode={authMode}
          onLoginSuccess={() => setAppMode('dashboard')}
        />
      </div>
    );
  }

  // Render Internal SaaS Dashboard
  return (
    <div className="h-screen w-full bg-neutral-100 dark:bg-neutral-950 text-neutral-900 flex flex-col md:flex-row font-sans overflow-hidden">
      {/* Left Responsive Sidebar */}
      <Sidebar
        currentView={currentView}
        onSelectView={setCurrentView}
        isOpenMobile={isMobileMenuOpen}
        onCloseMobile={() => setIsMobileMenuOpen(false)}
        currentWorkspace={workspace}
        onSwitchWorkspace={setWorkspace}
        reviewCount={unreviewedCount}
        onSignOut={() => setAppMode('landing')}
      />

      {/* Main Content Area Card with Rounded Upper Corner (Goes all the way to the bottom) */}
      <div className="flex-1 flex flex-col min-w-0 md:pt-2 md:pr-2 h-full min-h-0 overflow-hidden">
        <div className="flex-1 flex flex-col min-w-0 bg-white dark:bg-neutral-900 rounded-none md:rounded-tl-2xl border-0 md:border-t md:border-l md:border-r border-neutral-200/90 dark:border-neutral-800 overflow-hidden shadow-2xs h-full min-h-0">
          <DashboardNavbar
            workspaceName={workspace.name}
            onNavigateLanding={() => setAppMode('landing')}
            onOpenMobileMenu={() => setIsMobileMenuOpen(true)}
          />
          <div className="flex-1 min-h-0 overflow-y-auto flex flex-col">
            {currentView === 'commitments' && (
              <CommitmentsView
                commitments={commitments}
                selectedCommitment={selectedCommitment}
                onSelectCommitment={handleSelectCommitment}
                activeTab={activeTab}
                onTabChange={setActiveTab}
                activities={activities}
                onOpenUpload={() => setIsUploadOpen(true)}
                onOpenAddCommitment={() => setIsAddCommitmentOpen(true)}
                onOpenMobileMenu={() => setIsMobileMenuOpen(true)}
                onViewIntegrations={() => setCurrentView('integrations')}
                onDraftCustomerUpdate={() => setIsDraftUpdateOpen(true)}
                onReviewCommitment={() => setCurrentView('review-queue')}
                isDetailOpen={isDetailOpen}
                onCloseDetail={() => setIsDetailOpen(false)}
                onOpenDetail={() => setIsDetailOpen(true)}
              />
            )}

            {currentView === 'integrations' && (
              <IntegrationsView
                workspace={workspace}
                integrations={integrations}
                onConfigureSlack={() => setIsSlackModalOpen(true)}
                onOpenMobileMenu={() => setIsMobileMenuOpen(true)}
              />
            )}

            {currentView === 'customers' && (
              <CustomersView
                onSelectCustomer={() => setCurrentView('commitments')}
              />
            )}

            {currentView === 'review-queue' && (
              <ReviewQueueView
                commitments={commitments}
                onConfirm={handleConfirmCommitment}
                onReject={handleRejectCommitment}
                onSelectCommitment={(comm) => {
                  setSelectedCommitmentId(comm.id);
                  setIsDetailOpen(true);
                  setCurrentView('commitments');
                }}
              />
            )}

            {currentView === 'meetings' && (
              <MeetingsView onOpenUpload={() => setIsUploadOpen(true)} />
            )}

            {currentView === 'audit-log' && <AuditLogView />}

            {currentView === 'settings' && <SettingsView workspace={workspace} />}
          </div>
        </div>
      </div>

      {/* Global Interactive Modals */}
      <DraftUpdateModal
        isOpen={isDraftUpdateOpen}
        onClose={() => setIsDraftUpdateOpen(false)}
        commitment={selectedCommitment}
        onSendUpdate={handleSendUpdate}
      />

      <UploadTranscriptModal
        isOpen={isUploadOpen}
        onClose={() => setIsUploadOpen(false)}
        onTranscriptUploaded={handleTranscriptUploaded}
      />

      <AddCommitmentModal
        isOpen={isAddCommitmentOpen}
        onClose={() => setIsAddCommitmentOpen(false)}
        onAddCommitment={handleAddCommitment}
      />

      <SlackIntegrationModal
        isOpen={isSlackModalOpen}
        onClose={() => setIsSlackModalOpen(false)}
        workspace={workspace}
      />

      {/* Floating Toast Notification */}
      {toastMessage && (
        <div className="fixed bottom-5 right-5 z-50 bg-neutral-900 text-white text-xs px-4 py-3 rounded-xl shadow-lg flex items-center gap-2 border border-neutral-800 animate-in fade-in slide-in-from-bottom-2">
          <span className="w-2 h-2 rounded-full bg-emerald-400" />
          <span>{toastMessage}</span>
        </div>
      )}
    </div>
  );
}
