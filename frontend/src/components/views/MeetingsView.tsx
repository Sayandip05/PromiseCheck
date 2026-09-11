import React from 'react';
import { Video, Upload, Calendar, CheckCircle2, Clock, ExternalLink, FileAudio } from 'lucide-react';
import { GoogleMeetLogo } from '../ui/BrandLogos';

interface MeetingsViewProps {
  onOpenUpload: () => void;
}

export const MeetingsView: React.FC<MeetingsViewProps> = ({ onOpenUpload }) => {
  const meetings = [
    {
      id: 'meet-1',
      title: 'Acme Onboarding & SSO Discovery Call',
      date: 'Sep 18, 2026 · 14:30 EST',
      customer: 'Acme',
      source: 'Google Meet (Native Consent)',
      duration: '42 mins',
      promisesExtracted: 2,
      status: 'Processed',
    },
    {
      id: 'meet-2',
      title: 'Northstar Security Architecture Review',
      date: 'Sep 14, 2026 · 10:00 EST',
      customer: 'Northstar',
      source: 'Google Meet',
      duration: '55 mins',
      promisesExtracted: 1,
      status: 'Processed',
    },
    {
      id: 'meet-3',
      title: 'Orbit Design Product Roadmap Sync',
      date: 'Sep 19, 2026 · 16:00 EST',
      customer: 'Orbit',
      source: 'Manual VTT Upload',
      duration: '31 mins',
      promisesExtracted: 1,
      status: 'Processed',
    },
  ];

  return (
    <div className="flex-1 p-4 sm:p-6 lg:p-8 overflow-y-auto max-w-6xl mx-auto w-full">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-6 border-b border-neutral-200 dark:border-neutral-800">
        <div>
          <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-neutral-900 dark:text-white">
            Meetings & Transcripts
          </h1>
          <p className="text-xs sm:text-sm text-neutral-500 dark:text-neutral-400 mt-1">
            Recorded customer conversations, consent verification, and transcript extractions.
          </p>
        </div>

        <button
          onClick={onOpenUpload}
          className="inline-flex items-center gap-1.5 px-3.5 py-2 text-xs font-semibold text-white dark:text-neutral-900 bg-neutral-900 dark:bg-white rounded-lg hover:bg-neutral-800 dark:hover:bg-neutral-200 transition-colors shadow-xs self-start sm:self-auto cursor-pointer"
        >
          <Upload className="w-4 h-4" />
          <span>Upload recording or transcript</span>
        </button>
      </div>

      <div className="space-y-3 mt-6">
        {meetings.map((m) => (
          <div
            key={m.id}
            className="bg-white dark:bg-neutral-900 border border-neutral-200/90 dark:border-neutral-800 rounded-xl p-4 sm:p-5 shadow-2xs hover:border-neutral-300 dark:hover:border-neutral-700 transition-all flex flex-col sm:flex-row sm:items-center justify-between gap-4"
          >
            <div className="flex items-start gap-3.5">
              <div className="w-10 h-10 rounded-xl bg-white dark:bg-neutral-800 flex items-center justify-center shrink-0 border border-neutral-200/90 dark:border-neutral-700 p-2 shadow-2xs">
                {m.source.includes('Google Meet') ? (
                  <GoogleMeetLogo className="w-5 h-5 shrink-0" />
                ) : (
                  <FileAudio className="w-5 h-5 text-neutral-700 dark:text-neutral-300" />
                )}
              </div>
              <div>
                <h3 className="font-bold text-sm text-neutral-900 dark:text-white">{m.title}</h3>
                <div className="flex items-center flex-wrap gap-2 text-xs text-neutral-400 dark:text-neutral-500 mt-1">
                  <span>Customer: <strong className="text-neutral-700 dark:text-neutral-300">{m.customer}</strong></span>
                  <span>•</span>
                  <span>{m.date}</span>
                  <span>•</span>
                  <span>{m.duration}</span>
                </div>
              </div>
            </div>

            <div className="flex items-center justify-between sm:justify-end gap-4 border-t sm:border-t-0 pt-2 sm:pt-0 border-neutral-100 dark:border-neutral-800">
              <span className="text-xs font-semibold px-2.5 py-1 rounded-full bg-emerald-50 dark:bg-emerald-950/40 text-emerald-700 dark:text-emerald-300 border border-emerald-200/60 dark:border-emerald-800/60 flex items-center gap-1">
                <CheckCircle2 className="w-3.5 h-3.5" />
                <span>{m.promisesExtracted} promises found</span>
              </span>

              <button className="text-xs font-semibold text-neutral-900 dark:text-white hover:text-black dark:hover:text-neutral-200 inline-flex items-center gap-1 cursor-pointer underline-offset-2 hover:underline">
                <span>View transcript</span>
                <ExternalLink className="w-3 h-3" />
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
