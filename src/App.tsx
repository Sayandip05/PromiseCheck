/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useState, useEffect } from 'react';
import { Navbar } from './components/Navbar';
import { Hero } from './components/Hero';
import { LogosAndFeatures } from './components/LogosAndFeatures';
import { Testimonials } from './components/Testimonials';
import { PricingSection } from './components/PricingSection';
import { FaqSection } from './components/FaqSection';
import { Footer } from './components/Footer';
import { LoginModal, AuthMode } from './components/LoginModal';

export default function App() {
  const [darkMode, setDarkMode] = useState<boolean>(false);
  const [isLoginOpen, setIsLoginOpen] = useState<boolean>(false);
  const [authMode, setAuthMode] = useState<AuthMode>('signup');

  const handleOpenLogin = (mode: AuthMode = 'signup') => {
    setAuthMode(mode);
    setIsLoginOpen(true);
  };

  // Synchronize dark class on document element and root background color
  useEffect(() => {
    if (darkMode) {
      document.documentElement.classList.add('dark');
      document.body.style.backgroundColor = '#000000';
    } else {
      document.documentElement.classList.remove('dark');
      document.body.style.backgroundColor = '#ffffff';
    }
  }, [darkMode]);

  const handleToggleTheme = () => {
    setDarkMode(!darkMode);
  };

  const handleScrollTo = (id: string) => {
    const element = document.getElementById(id);
    if (element) {
      element.scrollIntoView({ behavior: 'smooth' });
    }
  };

  return (
    <div className={`min-h-screen w-full transition-colors duration-200 ${
      darkMode ? 'bg-black text-white' : 'bg-white text-neutral-900'
    }`}>
      {/* Centered architectural frame grid matching image.png */}
      <div className={`max-w-[1400px] mx-auto border-x min-h-screen flex flex-col transition-colors duration-200 ${
        darkMode ? 'border-neutral-800 bg-black' : 'border-neutral-200 bg-white'
      }`}>
        
        {/* Top Header / Navigation */}
        <Navbar 
          darkMode={darkMode}
          onToggleTheme={handleToggleTheme}
          onOpenLogin={handleOpenLogin}
          onScrollTo={handleScrollTo}
        />

        <main className="flex-1">
          {/* 1. Hero Section matching Screenshot 1 */}
          <Hero 
            darkMode={darkMode}
            onOpenLogin={handleOpenLogin}
          />

          {/* 2. Logos & 4-Column Feature Selector matching Screenshot 2 */}
          <LogosAndFeatures 
            darkMode={darkMode}
            onOpenLogin={handleOpenLogin}
          />

          {/* 3. Customer Testimonials Section matching Screenshot 3 */}
          <Testimonials 
            darkMode={darkMode}
          />

          {/* 4. Frequently Asked Questions matching image */}
          <FaqSection 
            darkMode={darkMode}
          />

          {/* 5. Pricing Section matching image */}
          <PricingSection 
            darkMode={darkMode}
            onOpenLogin={handleOpenLogin}
          />
        </main>

        {/* 6. Footer Section matching image */}
        <Footer 
          darkMode={darkMode}
          onScrollTo={handleScrollTo}
          onOpenLogin={handleOpenLogin}
        />

      </div>

      {/* Login & Sign-up Modal */}
      <LoginModal 
        isOpen={isLoginOpen}
        onClose={() => setIsLoginOpen(false)}
        darkMode={darkMode}
        initialMode={authMode}
      />
    </div>
  );
}
