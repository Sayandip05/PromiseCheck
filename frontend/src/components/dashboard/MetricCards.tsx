import React from 'react';
import { FileText, AlertTriangle, Clock, CheckCircle2 } from 'lucide-react';

interface MetricCardsProps {
  activeCount?: number;
  needsAttentionCount?: number;
  awaitingReviewCount?: number;
  deliveredCount?: number;
  onSelectCategory?: (category: 'all' | 'needs-attention' | 'awaiting-review' | 'delivered') => void;
  selectedCategory?: string;
}

export const MetricCards: React.FC<MetricCardsProps> = ({
  activeCount = 24,
  needsAttentionCount = 4,
  awaitingReviewCount = 3,
  deliveredCount = 12,
  onSelectCategory,
  selectedCategory = 'needs-attention',
}) => {
  const cards = [
    {
      id: 'all',
      title: 'Active commitments',
      value: activeCount,
      hasDot: false,
      icon: <FileText className="w-5 h-5 text-blue-600 dark:text-blue-400" />,
    },
    {
      id: 'needs-attention',
      title: 'Needs attention',
      value: needsAttentionCount,
      hasDot: true,
      dotColor: 'bg-amber-400',
      icon: <AlertTriangle className="w-5 h-5 text-amber-500 dark:text-amber-400" />,
    },
    {
      id: 'awaiting-review',
      title: 'Awaiting review',
      value: awaitingReviewCount,
      hasDot: false,
      icon: <Clock className="w-5 h-5 text-purple-600 dark:text-purple-400" />,
    },
    {
      id: 'delivered',
      title: 'Delivered this month',
      value: deliveredCount,
      hasDot: false,
      icon: <CheckCircle2 className="w-5 h-5 text-emerald-600 dark:text-emerald-400" />,
    },
  ];

  return (
    <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4 mb-6">
      {cards.map((card) => {
        const isSelected = selectedCategory === card.id;
        return (
          <div
            key={card.id}
            onClick={() => onSelectCategory && onSelectCategory(card.id as any)}
            className={`p-4 sm:p-5 rounded-xl border bg-white shadow-2xs transition-all cursor-default ${
              isSelected
                ? 'border-neutral-900 ring-2 ring-neutral-200'
                : 'border-neutral-200/90 hover:border-neutral-300 hover:shadow-xs'
            }`}
          >
            {/* Top Label with optional dot */}
            <div className="flex items-center gap-1.5 text-xs font-medium text-neutral-500 mb-2">
              {card.hasDot && (
                <span className={`w-2 h-2 rounded-full ${card.dotColor || 'bg-amber-400'}`} />
              )}
              <span className="truncate">{card.title}</span>
            </div>

            {/* Bottom Value & Icon */}
            <div className="flex items-baseline justify-between">
              <span className="text-2xl sm:text-3xl font-bold tracking-tight text-neutral-900">
                {card.value}
              </span>
              <div className="p-1">{card.icon}</div>
            </div>
          </div>
        );
      })}
    </div>
  );
};
