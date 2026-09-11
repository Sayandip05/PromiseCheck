import React from 'react';

export const SlackLogo: React.FC<{ className?: string }> = ({ className = 'w-5 h-5' }) => (
  <svg viewBox="0 0 24 24" className={className} fill="none">
    <path fill="#E01E5A" d="M5.04 14.28a2.52 2.52 0 1 0 2.52 2.52v-2.52H5.04zm3.78 2.52a2.52 2.52 0 1 0 5.04 0v-6.3H8.82v6.3z" />
    <path fill="#36C5F0" d="M9.72 5.04a2.52 2.52 0 1 0-2.52 2.52h2.52V5.04zm-2.52 3.78a2.52 2.52 0 1 0 0 5.04h6.3V8.82h-6.3z" />
    <path fill="#2EB67D" d="M18.96 9.72a2.52 2.52 0 1 0-2.52-2.52v2.52h2.52zm-3.78-2.52a2.52 2.52 0 1 0-5.04 0v6.3h5.04v-6.3z" />
    <path fill="#ECB22E" d="M14.28 18.96a2.52 2.52 0 1 0 2.52-2.52h-2.52v2.52zm2.52-3.78a2.52 2.52 0 1 0 0-5.04h-6.3v5.04h6.3z" />
  </svg>
);

export const GoogleMeetLogo: React.FC<{ className?: string }> = ({ className = 'w-5 h-5' }) => (
  <svg viewBox="0 0 87.5 72" className={className} fill="none">
    <path fill="#00832D" d="M49.5 36l8.53 9.75 11.47 7.33 2-17.02-2-16.64-11.69 6.44z" />
    <path fill="#0066DA" d="M0 51.5V66c0 3.315 2.685 6 6 6h14.5l3-10.96-3-9.54-9.95-3z" />
    <path fill="#E94235" d="M20.5 0L0 20.5l10.55 3 9.95-3 2.95-9.41z" />
    <path fill="#2684FC" d="M20.5 20.5H0v31h20.5z" />
    <path fill="#00AC47" d="M82.6 8.68L69.5 19.42v33.66l13.16 10.79c1.97 1.54 4.85.135 4.85-2.37V11c0-2.535-2.945-3.925-4.91-2.32zM49.5 36v15.5h-29V72h43c3.315 0 6-2.685 6-6V53.08z" />
    <path fill="#FFBA00" d="M63.5 0h-43v20.5h29V36l20-16.57V6c0-3.315-2.685-6-6-6z" />
  </svg>
);

export const GmailLogo: React.FC<{ className?: string }> = ({ className = 'w-5 h-5' }) => (
  <svg viewBox="52 42 88 66" className={className}>
    <path fill="#4285F4" d="M58 108h14V74L52 59v43c0 3.32 2.69 6 6 6" />
    <path fill="#34A853" d="M120 108h14c3.32 0 6-2.69 6-6V59l-20 15" />
    <path fill="#FBBC04" d="M120 48v26l20-15v-8c0-7.42-8.47-11.65-14.4-7.2" />
    <path fill="#EA4335" d="M72 74V48l24 18 24-18v26L96 92" />
    <path fill="#C5221F" d="M52 51v8l20 15V48l-5.6-4.2c-5.94-4.45-14.4-.22-14.4 7.2" />
  </svg>
);

export const JiraLogo: React.FC<{ className?: string }> = ({ className = 'w-5 h-5' }) => (
  <svg viewBox="0 0 28 28" className={className} fill="none">
    <defs>
      <linearGradient id="jira-grad-blue1" x1="19.35" y1="9.02" x2="14.23" y2="14.45" gradientUnits="userSpaceOnUse">
        <stop offset="0.176" stopColor="#0052CC" />
        <stop offset="1" stopColor="#2684FF" />
      </linearGradient>
      <linearGradient id="jira-grad-blue2" x1="13.56" y1="15.05" x2="7.64" y2="20.99" gradientUnits="userSpaceOnUse">
        <stop offset="0.176" stopColor="#0052CC" />
        <stop offset="1" stopColor="#2684FF" />
      </linearGradient>
    </defs>
    <path d="M24.664 3H12.26C12.26 5.994 14.77 8.432 17.853 8.432H20.147V10.556C20.147 13.55 22.656 15.988 25.74 15.988V4.045C25.74 3.453 25.274 3 24.664 3Z" fill="#2684FF" />
    <path d="M18.534 8.989H6.13C6.13 11.983 8.64 14.42 11.723 14.42H14.017V16.58C14.017 19.574 16.526 22.011 19.61 22.011V10.033C19.61 9.476 19.143 8.989 18.534 8.989Z" fill="url(#jira-grad-blue1)" />
    <path d="M12.404 15.012H0C0 18.007 2.51 20.444 5.592 20.444H7.887V22.568C7.887 25.563 10.396 28 13.48 28V16.057C13.48 15.465 12.977 15.012 12.404 15.012Z" fill="url(#jira-grad-blue2)" />
  </svg>
);

export const LinearLogo: React.FC<{ className?: string }> = ({ className = 'w-5 h-5' }) => (
  <svg viewBox="0 0 24 24" className={className} fill="#5E6AD2">
    <path d="M2.886 4.18A11.982 11.982 0 0 1 11.99 0C18.624 0 24 5.376 24 12.009c0 3.64-1.62 6.903-4.18 9.105L2.887 4.18ZM1.817 5.626l16.556 16.556c-.524.33-1.075.62-1.65.866L.951 7.277c.247-.575.537-1.126.866-1.65ZM.322 9.163l14.515 14.515c-.71.172-1.443.282-2.195.322L0 11.358a12 12 0 0 1 .322-2.195Zm-.17 4.862 9.823 9.824a12.02 12.02 0 0 1-9.824-9.824Z" />
  </svg>
);

export const RecallLogo: React.FC<{ className?: string }> = ({ className = 'w-5 h-5' }) => (
  <svg viewBox="0 0 24 24" className={className} fill="none">
    <rect width="24" height="24" rx="6" fill="#6366F1" />
    <circle cx="12" cy="12" r="5" stroke="#FFFFFF" strokeWidth="2" />
    <circle cx="12" cy="12" r="2" fill="#FFFFFF" />
    <path d="M12 3v3M12 18v3M3 12h3M18 12h3" stroke="#FFFFFF" strokeWidth="1.5" strokeLinecap="round" />
  </svg>
);

export const ZoomLogo: React.FC<{ className?: string }> = ({ className = 'w-5 h-5' }) => (
  <svg viewBox="0 0 24 24" className={className} fill="none">
    <rect width="24" height="24" rx="6" fill="#2D8CFF" />
    <path d="M6 9a2 2 0 0 1 2-2h6a2 2 0 0 1 2 2v6a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2V9z" fill="#FFFFFF" />
    <path d="M16 10.5l4-2.5v8l-4-2.5v-3z" fill="#FFFFFF" />
  </svg>
);

export const TeamsLogo: React.FC<{ className?: string }> = ({ className = 'w-5 h-5' }) => (
  <svg viewBox="0 0 24 24" className={className}>
    <path fill="#5059C9" d="M19.5 7.5A2.5 2.5 0 0 0 17 5a2.5 2.5 0 0 0-2.5 2.5c0 1.13.75 2.08 1.77 2.38v4.62c0 .28.22.5.5.5h1.46c.28 0 .5-.22.5-.5V9.88c1.02-.3 1.77-1.25 1.77-2.38z" />
    <path fill="#7B83EB" d="M14.5 10c0-1.38-1.12-2.5-2.5-2.5S9.5 8.62 9.5 10c0 1.14.77 2.1 1.8 2.4v6.1c0 .28.22.5.5.5h1.4c.28 0 .5-.22.5-.5v-6.1c1.03-.3 1.8-1.26 1.8-2.4z" />
    <rect x="3" y="6.5" width="10" height="11" rx="2" fill="#4B53BC" />
    <path d="M6 10h4v1.5H8.75V15H7.25v-3.5H6V10z" fill="#FFFFFF" />
  </svg>
);

export const BrandLogo: React.FC<{ provider: string; className?: string }> = ({
  provider,
  className = 'w-5 h-5',
}) => {
  switch (provider.toLowerCase()) {
    case 'slack':
      return <SlackLogo className={className} />;
    case 'google_meet':
    case 'meet':
    case 'gmeet':
      return <GoogleMeetLogo className={className} />;
    case 'jira':
      return <JiraLogo className={className} />;
    case 'linear':
      return <LinearLogo className={className} />;
    case 'gmail':
      return <GmailLogo className={className} />;
    case 'recall':
      return <RecallLogo className={className} />;
    case 'zoom':
      return <ZoomLogo className={className} />;
    case 'teams':
      return <TeamsLogo className={className} />;
    default:
      return null;
  }
};
