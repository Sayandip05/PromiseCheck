import React, { useState } from 'react';
import { ChevronDown } from 'lucide-react';

interface FaqSectionProps {
  darkMode: boolean;
}

interface FaqItem {
  question: string;
  answer: string;
}

export const FaqSection: React.FC<FaqSectionProps> = ({ darkMode }) => {
  const [openIndex, setOpenIndex] = useState<number | null>(null);

  const faqs: FaqItem[] = [
    {
      question: 'What is Streamline?',
      answer:
        'Streamline is an all-in-one financial operations platform that consolidates multi-entity bank accounts, corporate cards, transactions, and real-time cash flow telemetry into a unified command center.'
    },
    {
      question: 'How is Streamline different from Linear and Jira?',
      answer:
        'While Linear and Jira are purpose-built for software issue tracking, Streamline is built specifically for financial operations, reconciliation, automated commitment auditing, and cross-subsidiary treasury management.'
    },
    {
      question: 'How do I update my account?',
      answer:
        'You can modify your account details, billing preferences, seat allocation, and connected entities at any time through the Account Settings tab or via our SCIM/SSO directory integrations.'
    },
    {
      question: 'Is support free, or do I need to Google everything?',
      answer:
        'All plans include access to our 24/7 dedicated support engineers, in-depth documentation, video guides, and direct Slack/Teams shared channels for enterprise customers.'
    },
    {
      question: 'Are you going to be subsumed by AI?',
      answer:
        'We build with AI at the foundational layer—automating invoice reconciliation, anomaly detection, and predictive runway forecasting to augment your team rather than compete with it.'
    },
    {
      question: 'How do I connect my bank accounts and subsidiaries?',
      answer:
        'Connect bank accounts in minutes via our secure Plaid, MX, and direct API integrations. Multi-currency and multi-subsidiary rollup hierarchies can be configured with a single click.'
    },
    {
      question: 'Which banks and financial institutions are supported?',
      answer:
        'We support over 12,000+ global financial institutions across North America, Europe, and APAC, including Chase, Bank of America, SVB, Brex, Mercury, HSBC, Barclays, and Revolut.'
    }
  ];

  const toggleItem = (idx: number) => {
    setOpenIndex(openIndex === idx ? null : idx);
  };

  return (
    <section
      id="faq-section"
      className={`border-b transition-colors duration-200 ${
        darkMode ? 'bg-black text-white border-neutral-800' : 'bg-white text-neutral-900 border-neutral-200'
      }`}
    >
      {/* Top Header Block matching image.png */}
      <div className="pt-16 pb-12 px-6 md:px-12">
        <h2 className="text-3xl sm:text-4xl font-normal tracking-[-0.025em]">
          Frequently Asked Questions
        </h2>
        <p className={`mt-3 text-xs sm:text-sm max-w-xl leading-relaxed ${
          darkMode ? 'text-neutral-400' : 'text-neutral-500'
        }`}>
          Browse our most common user questions and discover practical tips for getting the most out of our platform.
        </p>
        <button
          className={`mt-4 px-3 py-1.5 rounded-md text-xs font-medium transition-colors cursor-pointer ${
            darkMode
              ? 'bg-neutral-900 hover:bg-neutral-800 text-neutral-200 border border-neutral-800'
              : 'bg-[#f0f1f4] hover:bg-[#e4e6ea] text-neutral-800'
          }`}
        >
          Read more
        </button>
      </div>

      {/* Accordion list separated by horizontal borders across full width matching image.png */}
      <div className="w-full">
        {faqs.map((faq, idx) => {
          const isOpen = openIndex === idx;
          return (
            <div
              key={idx}
              className={`border-t transition-colors ${
                idx === faqs.length - 1 ? 'border-b' : ''
              } ${
                darkMode ? 'border-neutral-800' : 'border-neutral-200'
              }`}
            >
              <button
                onClick={() => toggleItem(idx)}
                className={`w-full py-5 px-6 md:px-12 flex items-center justify-between text-left transition-colors cursor-pointer group ${
                  darkMode ? 'hover:bg-neutral-950/60' : 'hover:bg-neutral-50/70'
                }`}
                aria-expanded={isOpen}
              >
                <span className={`text-[15px] sm:text-[16px] font-medium tracking-tight ${
                  darkMode ? 'text-neutral-200 group-hover:text-white' : 'text-neutral-900'
                }`}>
                  {faq.question}
                </span>
                <ChevronDown
                  className={`w-3.5 h-3.5 shrink-0 transition-transform duration-200 ${
                    isOpen ? 'rotate-180 text-neutral-900 dark:text-white' : 'text-neutral-400'
                  }`}
                  strokeWidth={1.75}
                />
              </button>

              {isOpen && (
                <div className={`px-6 md:px-12 pb-5 text-sm leading-relaxed ${
                  darkMode ? 'text-neutral-400' : 'text-neutral-500'
                }`}>
                  {faq.answer}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </section>
  );
};
