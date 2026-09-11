import React, { useState, useEffect } from 'react';
import { X, CheckCircle2, ArrowLeft } from 'lucide-react';

export type AuthMode = 'signup' | 'login' | 'contact';

interface LoginModalProps {
  isOpen: boolean;
  onClose: () => void;
  darkMode: boolean;
  initialMode?: AuthMode;
  onLoginSuccess?: () => void;
}

export const LoginModal: React.FC<LoginModalProps> = ({
  isOpen,
  onClose,
  darkMode,
  initialMode = 'signup',
  onLoginSuccess,
}) => {
  const [mode, setMode] = useState<AuthMode>(initialMode);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [contactMessage, setContactMessage] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isSubmitted, setIsSubmitted] = useState(false);

  // Sync mode whenever initialMode changes or modal opens
  useEffect(() => {
    if (isOpen) {
      setMode(initialMode);
      setIsSubmitted(false);
    }
  }, [isOpen, initialMode]);

  if (!isOpen) return null;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    setTimeout(() => {
      setIsSubmitting(false);
      setIsSubmitted(true);
      setTimeout(() => {
        setIsSubmitted(false);
        onClose();
        if (onLoginSuccess) onLoginSuccess();
      }, 1000);
    }, 600);
  };

  const handleGoogleAuth = () => {
    setIsSubmitting(true);
    setTimeout(() => {
      setIsSubmitting(false);
      setIsSubmitted(true);
      setTimeout(() => {
        setIsSubmitted(false);
        onClose();
        if (onLoginSuccess) onLoginSuccess();
      }, 1000);
    }, 600);
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-neutral-900/40 dark:bg-black/80 backdrop-blur-xs animate-in fade-in duration-200"
      onClick={onClose}
    >
      {/* Centered Authentication Card */}
      <div
        onClick={(e) => e.stopPropagation()}
        className={`w-full max-w-[420px] rounded-none p-8 sm:p-10 shadow-xl sm:shadow-2xl border transition-all relative ${
          darkMode
            ? 'bg-[#0f0f12] border-neutral-800 text-white'
            : 'bg-white border-neutral-200/90 text-neutral-950'
        }`}
      >
        {/* Subtle Close Button */}
        <button
          onClick={onClose}
          aria-label="Close modal"
          className={`absolute top-5 right-5 p-1.5 rounded-full transition-colors cursor-pointer ${
            darkMode
              ? 'text-neutral-400 hover:text-white hover:bg-neutral-800'
              : 'text-neutral-400 hover:text-neutral-900 hover:bg-neutral-100'
          }`}
        >
          <X className="w-4 h-4" />
        </button>

        {/* Brand Logo & Wordmark matching PromiseCheck */}
        <div className="flex items-center justify-center gap-2.5 mb-8">
          <div className="relative w-8 h-8 flex items-center justify-center">
            <svg 
              viewBox="0 0 36 36" 
              className="w-8 h-8 text-neutral-950 dark:text-white"
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
          <span className="font-bold text-xl sm:text-[22px] tracking-tight">
            PromiseCheck
          </span>
        </div>

        {isSubmitted ? (
          <div className="py-8 text-center space-y-3">
            <div className="w-12 h-12 rounded-full bg-emerald-500/10 text-emerald-500 flex items-center justify-center mx-auto">
              <CheckCircle2 className="w-6 h-6" />
            </div>
            <h4 className="font-semibold text-base">
              {mode === 'contact' ? 'Message Received' : 'Welcome!'}
            </h4>
            <p className={`text-xs ${darkMode ? 'text-neutral-400' : 'text-neutral-500'}`}>
              {mode === 'contact'
                ? 'Our team will get back to you shortly.'
                : 'Authentication successful. Loading dashboard...'}
            </p>
          </div>
        ) : (
          <div>
            {/* Form */}
            <form onSubmit={handleSubmit} className="space-y-3.5">
              {/* Email Input */}
              <div>
                <input
                  type="email"
                  required
                  placeholder="Email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className={`w-full px-3.5 py-2.5 text-sm rounded-lg border transition-colors ${
                    darkMode
                      ? 'bg-neutral-900/60 border-neutral-700 text-white placeholder-neutral-500 focus:border-white'
                      : 'bg-white border-neutral-300 text-neutral-900 placeholder-neutral-400 focus:border-neutral-950'
                  } focus:outline-hidden`}
                />
              </div>

              {/* Password Input (Hidden in Contact mode) */}
              {mode !== 'contact' ? (
                <div>
                  <input
                    type="password"
                    required
                    placeholder="Password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    className={`w-full px-3.5 py-2.5 text-sm rounded-lg border transition-colors ${
                      darkMode
                        ? 'bg-neutral-900/60 border-neutral-700 text-white placeholder-neutral-500 focus:border-white'
                        : 'bg-white border-neutral-300 text-neutral-900 placeholder-neutral-400 focus:border-neutral-950'
                    } focus:outline-hidden`}
                  />
                </div>
              ) : (
                <div>
                  <textarea
                    required
                    rows={3}
                    placeholder="How can we help you?"
                    value={contactMessage}
                    onChange={(e) => setContactMessage(e.target.value)}
                    className={`w-full px-3.5 py-2.5 text-sm rounded-lg border transition-colors resize-none ${
                      darkMode
                        ? 'bg-neutral-900/60 border-neutral-700 text-white placeholder-neutral-500 focus:border-white'
                        : 'bg-white border-neutral-300 text-neutral-900 placeholder-neutral-400 focus:border-neutral-950'
                    } focus:outline-hidden`}
                  />
                </div>
              )}

              {/* Primary Submit Button */}
              <button
                type="submit"
                disabled={isSubmitting}
                className={`w-full py-2.5 px-4 rounded-lg text-sm font-medium transition-colors cursor-pointer shadow-xs ${
                  darkMode
                    ? 'bg-white hover:bg-neutral-200 text-neutral-950'
                    : 'bg-[#18181b] hover:bg-[#27272a] text-white'
                }`}
              >
                {isSubmitting
                  ? 'Processing...'
                  : mode === 'signup'
                  ? 'Create an account'
                  : mode === 'login'
                  ? 'Log in'
                  : 'Send message'}
              </button>

              {/* Secondary Google OAuth Button */}
              {mode !== 'contact' && (
                <button
                  type="button"
                  onClick={handleGoogleAuth}
                  disabled={isSubmitting}
                  className={`w-full py-2.5 px-4 rounded-lg text-sm font-medium border transition-colors cursor-pointer flex items-center justify-center gap-2.5 shadow-2xs ${
                    darkMode
                      ? 'bg-neutral-900/50 hover:bg-neutral-800 border-neutral-700 text-neutral-200'
                      : 'bg-white hover:bg-neutral-50 border-neutral-300 text-neutral-700'
                  }`}
                >
                  <svg className="w-4 h-4 shrink-0" viewBox="0 0 24 24">
                    <path
                      fill="#4285F4"
                      d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
                    />
                    <path
                      fill="#34A853"
                      d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
                    />
                    <path
                      fill="#FBBC05"
                      d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.06H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.94l2.85-2.22.81-.63z"
                    />
                    <path
                      fill="#EA4335"
                      d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.06l3.66 2.84c.87-2.6 3.3-4.52 6.16-4.52z"
                    />
                  </svg>
                  <span>
                    {mode === 'signup' ? 'Sign up with Google' : 'Sign in with Google'}
                  </span>
                </button>
              )}
            </form>

            {/* Auth Mode Switch Link */}
            <div className="mt-8 text-center text-xs sm:text-[13px] text-neutral-600 dark:text-neutral-400 space-y-2">
              {mode === 'signup' && (
                <div>
                  Already have an account?{' '}
                  <button
                    type="button"
                    onClick={() => setMode('login')}
                    className="font-semibold text-neutral-900 dark:text-white hover:underline cursor-pointer"
                  >
                    Login
                  </button>
                </div>
              )}

              {mode === 'login' && (
                <div>
                  Don't have an account?{' '}
                  <button
                    type="button"
                    onClick={() => setMode('signup')}
                    className="font-semibold text-neutral-900 dark:text-white hover:underline cursor-pointer"
                  >
                    Sign up
                  </button>
                </div>
              )}

              {mode === 'contact' ? (
                <div className="pt-2">
                  <button
                    type="button"
                    onClick={() => setMode('login')}
                    className="inline-flex items-center gap-1 font-semibold text-neutral-900 dark:text-white hover:underline cursor-pointer"
                  >
                    <ArrowLeft className="w-3.5 h-3.5" />
                    Back to Login
                  </button>
                </div>
              ) : (
                <div className="pt-1 text-[12px] text-neutral-500 dark:text-neutral-500">
                  Need custom assistance?{' '}
                  <button
                    type="button"
                    onClick={() => setMode('contact')}
                    className="font-medium text-neutral-800 dark:text-neutral-300 hover:underline cursor-pointer"
                  >
                    Contact us
                  </button>
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
