export type CommitmentStatus = 'at-risk' | 'overdue' | 'blocked' | 'confirmed' | 'delivered' | 'awaiting-review';

export interface Owner {
  name: string;
  initials: string;
  avatarColor?: string;
  email?: string;
}

export interface OriginalPromise {
  quote: string;
  sourceTitle: string;
  timestamp: string;
  transcriptId?: string;
}

export interface EngineeringEvidence {
  ticketId: string;
  ticketTitle: string;
  status: string;
  targetDelivery: string;
  syncedAt: string;
  provider: 'jira' | 'linear';
  ticketUrl?: string;
}

export interface RiskAnalysis {
  hasConflict: boolean;
  conflictTitle?: string;
  conflictDescription?: string;
  daysDiscrepancy?: number;
}

export interface RecommendedStep {
  text: string;
  actionType: 'draft_update' | 'review' | 'remind_owner';
}

export interface Commitment {
  id: string;
  title: string;
  customer: string;
  owner: Owner;
  promisedBy: string;
  promisedDateIso: string;
  status: CommitmentStatus;
  statusLabel: string;
  isConfirmed: boolean;
  category: 'needs-attention' | 'awaiting-review' | 'on-track' | 'delivered';
  originalPromise: OriginalPromise;
  engineeringEvidence?: EngineeringEvidence;
  risk?: RiskAnalysis;
  recommendedNextStep?: RecommendedStep;
}

export interface RecentActivityItem {
  id: string;
  title: string;
  source: string;
  timeAgo: string;
  type: 'jira' | 'confirmation' | 'meet' | 'slack' | 'linear';
}

export interface Integration {
  id: string;
  provider: 'google_meet' | 'jira' | 'slack' | 'linear' | 'gmail' | 'recall';
  name: string;
  connected: boolean;
  statusText: string;
  lastSync?: string;
  channelOrScope?: string;
  workspaceId: string;
  description: string;
}

export interface Workspace {
  id: string;
  name: string;
  role: string;
  plan: string;
}

export type DashboardView = 
  | 'commitments' 
  | 'customers' 
  | 'review-queue' 
  | 'meetings' 
  | 'integrations' 
  | 'audit-log' 
  | 'settings';
