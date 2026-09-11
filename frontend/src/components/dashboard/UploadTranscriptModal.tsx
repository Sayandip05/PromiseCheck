import React, { useState } from 'react';
import { X, Upload, FileText, Sparkles, CheckCircle2 } from 'lucide-react';

interface UploadTranscriptModalProps {
  isOpen: boolean;
  onClose: () => void;
  onTranscriptUploaded: (data: { customer: string; meetingTitle: string; quote: string }) => void;
}

export const UploadTranscriptModal: React.FC<UploadTranscriptModalProps> = ({
  isOpen,
  onClose,
  onTranscriptUploaded,
}) => {
  if (!isOpen) return null;

  const [customer, setCustomer] = useState('Acme');
  const [meetingTitle, setMeetingTitle] = useState('Customer Sync & Feature Review');
  const [fileSelected, setFileSelected] = useState<string | null>('acme_onboarding_transcript.vtt');
  const [isProcessing, setIsProcessing] = useState(false);
  const [isDone, setIsDone] = useState(false);

  const handleUpload = (e: React.FormEvent) => {
    e.preventDefault();
    setIsProcessing(true);

    setTimeout(() => {
      setIsProcessing(false);
      setIsDone(true);
      setTimeout(() => {
        onTranscriptUploaded({
          customer,
          meetingTitle,
          quote: "We'll enable custom webhook integrations and deliver the sandbox testing environment by next Friday.",
        });
        setIsDone(false);
        onClose();
      }, 1000);
    }, 1500);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-neutral-900/50 backdrop-blur-xs animate-in fade-in">
      <div className="bg-white rounded-none max-w-md w-full border border-neutral-200 shadow-xl overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-neutral-100 bg-neutral-50/50">
          <div>
            <h3 className="text-base font-bold text-neutral-900">Upload transcript</h3>
            <p className="text-xs text-neutral-500">
              Extract commitments from Google Meet, Zoom, or audio
            </p>
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded-lg text-neutral-400 hover:text-neutral-700 hover:bg-neutral-100 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        {isDone ? (
          <div className="p-8 text-center space-y-3">
            <div className="w-12 h-12 bg-emerald-100 text-emerald-600 rounded-full flex items-center justify-center mx-auto">
              <CheckCircle2 className="w-6 h-6" />
            </div>
            <h4 className="font-bold text-neutral-900 text-base">Transcript Parsed</h4>
            <p className="text-xs text-neutral-500">
              New customer promises extracted and routed to Review Queue.
            </p>
          </div>
        ) : (
          <form onSubmit={handleUpload} className="p-6 space-y-4">
            {/* Customer Account */}
            <div className="space-y-1">
              <label className="text-xs font-semibold text-neutral-700">Customer Account</label>
              <select
                value={customer}
                onChange={(e) => setCustomer(e.target.value)}
                className="w-full text-xs px-3 py-2 border border-neutral-200 rounded-lg bg-white focus:outline-none focus:ring-2 focus:ring-neutral-900/10 focus:border-neutral-900"
              >
                <option value="Acme">Acme</option>
                <option value="Northstar">Northstar</option>
                <option value="Orbit">Orbit</option>
                <option value="Pine Labs">Pine Labs</option>
              </select>
            </div>

            {/* Meeting Title */}
            <div className="space-y-1">
              <label className="text-xs font-semibold text-neutral-700">Meeting Title</label>
              <input
                type="text"
                value={meetingTitle}
                onChange={(e) => setMeetingTitle(e.target.value)}
                className="w-full text-xs px-3 py-2 border border-neutral-200 rounded-lg bg-white focus:outline-none focus:ring-2 focus:ring-neutral-900/10 focus:border-neutral-900"
              />
            </div>

            {/* File Dropzone */}
            <div className="space-y-1">
              <label className="text-xs font-semibold text-neutral-700">Transcript / Audio File</label>
              <div className="border-2 border-dashed border-neutral-200 rounded-xl p-5 text-center bg-neutral-50/50 hover:bg-neutral-50 transition-colors cursor-pointer">
                <Upload className="w-6 h-6 text-neutral-400 mx-auto mb-2" />
                <p className="text-xs font-medium text-neutral-800">
                  {fileSelected ? fileSelected : 'Click or drop VTT, TXT, MP3 files'}
                </p>
                <p className="text-[10px] text-neutral-400 mt-1">
                  Supports Google Meet VTT, Zoom transcripts, Teams transcripts, and audio recordings
                </p>
              </div>
            </div>

            {/* AI Extraction Banner */}
            <div className="flex items-center gap-2 p-3 bg-neutral-100 border border-neutral-200 rounded-xl text-xs text-neutral-800">
              <Sparkles className="w-4 h-4 text-neutral-700 shrink-0" />
              <span>
                Gemini LLM pipeline will extract promises, dates, speaker commitments, and evidence.
              </span>
            </div>

            {/* Actions */}
            <div className="flex items-center justify-end gap-2 pt-2">
              <button
                type="button"
                onClick={onClose}
                className="px-4 py-2 text-xs font-medium text-neutral-600 hover:bg-neutral-100 rounded-lg transition-colors"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={isProcessing}
                className="inline-flex items-center gap-1.5 px-4 py-2 text-xs font-medium bg-neutral-900 hover:bg-neutral-800 text-white rounded-lg transition-all shadow-xs cursor-pointer active:scale-98"
              >
                {isProcessing ? (
                  <>
                    <span className="w-3.5 h-3.5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                    <span>Analyzing transcript...</span>
                  </>
                ) : (
                  <>
                    <Upload className="w-3.5 h-3.5" />
                    <span>Upload & Extract</span>
                  </>
                )}
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
};
