export interface CustomerAccount {
  id: string;
  name: string;
  status: 'on-track' | 'at-risk' | 'review' | 'completed';
  statusColor: string;
  activePromises: number;
  healthScore: number;
  recentPromise: string;
  dueDate: string;
  owner: string;
}

export interface PromiseItem {
  id: string;
  title: string;
  source: 'Meeting Notes' | 'Email Thread' | 'Slack Connect' | 'Zoom Transcript';
  sourceTitle: string;
  customer: string;
  dueDate: string;
  time: string;
  owner: string;
  status: 'on-track' | 'at-risk' | 'completed' | 'alert-sent';
  riskScore: number; // 0 to 100
  confidence: number;
  actionRequired?: string;
}

export const ACCOUNTS: CustomerAccount[] = [
  {
    id: 'aurora',
    name: 'Aurora Tech Inc.',
    status: 'on-track',
    statusColor: '#10b981', // green
    activePromises: 5,
    healthScore: 98,
    recentPromise: 'Deliver SOC2 Type II Report',
    dueDate: 'Sep 18, 2026',
    owner: 'Sarah Lin'
  },
  {
    id: 'maplewood',
    name: 'Maplewood Imports LLC',
    status: 'at-risk',
    statusColor: '#f59e0b', // amber
    activePromises: 3,
    healthScore: 71,
    recentPromise: 'Custom EDI Inventory Sync Gateway',
    dueDate: 'Sep 21, 2026',
    owner: 'David Chen'
  },
  {
    id: 'oceanview',
    name: 'OceanView Enterprises Ltd.',
    status: 'review',
    statusColor: '#525252', // neutral gray
    activePromises: 4,
    healthScore: 89,
    recentPromise: 'Single Sign-On SAML Multi-domain',
    dueDate: 'Sep 28, 2026',
    owner: 'Alex Rivera'
  },
  {
    id: 'evergreen',
    name: 'Evergreen Manufacturing Co.',
    status: 'on-track',
    statusColor: '#10b981', // green
    activePromises: 6,
    healthScore: 96,
    recentPromise: 'Automated CSV batch ingest endpoints',
    dueDate: 'Oct 04, 2026',
    owner: 'Marcus Vance'
  }
];

export const RECENT_PROMISES: PromiseItem[] = [
  {
    id: 'p-1',
    title: 'Deliver SOC2 Type II compliance audit package',
    source: 'Meeting Notes',
    sourceTitle: 'Executive Business Review - Aurora Tech',
    customer: 'Aurora Tech Inc.',
    dueDate: 'Sep 18, 2026',
    time: '11:45 AM',
    owner: 'Sarah Lin (DevSecOps)',
    status: 'alert-sent',
    riskScore: 68,
    confidence: 97,
    actionRequired: 'Security team needs 2 signed vendor appendices'
  },
  {
    id: 'p-2',
    title: 'Increase production API rate limit to 2,500 req/s',
    source: 'Email Thread',
    sourceTitle: 'Re: Q4 Scaling Requirements & Infrastructure SLA',
    customer: 'Maplewood Imports LLC',
    dueDate: 'Sep 16, 2026',
    time: '08:00 PM',
    owner: 'Tony Smith (Infra Lead)',
    status: 'on-track',
    riskScore: 22,
    confidence: 94
  },
  {
    id: 'p-3',
    title: 'Custom Webhook SLA: 99.95% uptime guarantees',
    source: 'Zoom Transcript',
    sourceTitle: 'Technical Architecture Deep Dive',
    customer: 'OceanView Enterprises',
    dueDate: 'Sep 16, 2026',
    time: '08:00 PM',
    owner: 'Elena Rostova (Solutions)',
    status: 'on-track',
    riskScore: 18,
    confidence: 99
  }
];

export const SAMPLE_MEETING_NOTES = [
  {
    id: 'sample-1',
    title: 'Customer QBR - Aurora Tech Inc.',
    date: 'Yesterday at 3:30 PM',
    source: 'Google Meet / Gong Transcript',
    rawText: `Alex (CSM): "Thanks everyone for joining today's quarterly sync. To recap the architecture review with Aurora Tech: Marcus mentioned that their security audit begins on October 1st. I promised their VP of Engineering that our team will deliver the full SOC2 Type II compliance report by September 18th at 11:45 AM. Also, Sarah confirmed we will patch the custom webhook latency within 48 hours."

Rachel (Aurora Tech VP): "That timeline works great for us. If the SOC2 report comes through on the 18th, our procurement board will greenlight the $450k enterprise contract."`,
    detectedPromises: [
      {
        commitment: 'Deliver full SOC2 Type II compliance report',
        recipient: 'Aurora Tech Inc.',
        dueDate: 'Sep 18, 2026 · 11:45 AM',
        responsible: 'Sarah Lin (DevSecOps)',
        confidence: '99% AI Match',
        riskLevel: 'Elevated (Audit queue pending)'
      },
      {
        commitment: 'Patch custom webhook latency',
        recipient: 'Aurora Tech Inc.',
        dueDate: 'Within 48 hours',
        responsible: 'Engineering Team',
        confidence: '94% AI Match',
        riskLevel: 'Low'
      }
    ]
  },
  {
    id: 'sample-2',
    title: 'Email: Enterprise Contract SLA Confirmation',
    date: 'Today at 9:15 AM',
    source: 'Gmail / Outlook Exchange',
    rawText: `From: david.chen@ourcompany.com
To: vp.operations@maplewoodimports.com
Subject: Re: Dedicated Kafka Sync cluster & Go-Live SLA

Hi Amanda,
Following up on our call: we commit to deploying your dedicated Kafka sync gateway to staging by September 21st, 2026. We will also provide 24/7 priority pager escalation access before your Black Friday inventory freeze.

Best,
David Chen
Head of Solutions Architecture`,
    detectedPromises: [
      {
        commitment: 'Deploy dedicated Kafka sync gateway to staging',
        recipient: 'Maplewood Imports LLC',
        dueDate: 'Sep 21, 2026',
        responsible: 'David Chen (Solutions)',
        confidence: '98% AI Match',
        riskLevel: 'At Risk (Behind schedule on cluster provisioning)'
      },
      {
        commitment: 'Provide 24/7 priority pager escalation access',
        recipient: 'Maplewood Imports LLC',
        dueDate: 'Before Black Friday freeze',
        responsible: 'On-Call Operations',
        confidence: '92% AI Match',
        riskLevel: 'On Track'
      }
    ]
  }
];

export const FEATURES_LIST = [
  {
    id: 'detection',
    title: 'Commitment Detection',
    subtitle: 'Find promises in meeting notes & emails automatically.',
    headline: 'Autonomous Promise Detection',
    description: 'PromiseCheck scans Zoom transcripts, Gong calls, Slack threads, and customer emails to extract every explicit and implicit promise made to your clients before it slips through the cracks.',
    statLabel: 'Total Active Commitments',
    statValue: '148 Commitments',
    statDiff: '+98.2% on-time',
    statSub: '6 detected this week · 2 at-risk'
  },
  {
    id: 'sentinel',
    title: 'Progress Sentinel',
    subtitle: 'Continuously check team progress and ticket velocity.',
    headline: 'Continuous Engineering Sync',
    description: 'Seamlessly cross-references extracted promises with Jira issues, Linear tickets, GitHub pull requests, and Asana deliverables to monitor true execution velocity in real time.',
    statLabel: 'Velocity Alignment',
    statValue: '96.4% Synced',
    statDiff: '+4.1% vs last sprint',
    statSub: '32 tickets linked to active promises'
  },
  {
    id: 'alerts',
    title: 'Early Risk Alerts',
    subtitle: 'Alert responsible owners days before deadlines are missed.',
    headline: 'Proactive Early-Warning Radar',
    description: 'When engineering momentum slows or scope shifts endanger a promised delivery date, PromiseCheck alerts the promise owner and leadership days ahead so you can course-correct before the customer ever notices.',
    statLabel: 'Avg. Warning Lead Time',
    statValue: '5.2 Days Ahead',
    statDiff: 'Zero surprise escalations',
    statSub: '98% early resolution rate'
  },
  {
    id: 'audit',
    title: 'Audit & Trust Reports',
    subtitle: 'Generate transparent proof of reliability for enterprise clients.',
    headline: 'Customer Trust & SLA Certification',
    description: 'Export verifiable promise fulfillment reports and live client trust portals that prove your organization honors every commitment made during sales and account reviews.',
    statLabel: 'Customer Trust Index',
    statValue: '99.4% Fulfillment',
    statDiff: 'Top decile SLA score',
    statSub: 'Audited across 42 enterprise accounts'
  }
];

export const TESTIMONIALS = [
  {
    id: 'mercury',
    companyName: 'MERCURY',
    quote: 'Since integrating PromiseCheck’s unified dashboard, we’ve consolidated all customer commitments into one view—no more surprise escalations or missed deadlines in Slack.',
    authorName: 'John Doe',
    authorRole: 'VP of Customer Operations, Mercury, Inc.',
    avatarUrl: 'https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=150&auto=format&fit=crop&q=80'
  },
  {
    id: 'watershed',
    companyName: 'Watershed',
    quote: 'PromiseCheck has been a game-changer for our customer delivery team—automated promise extraction from emails and meetings keeps our client trust airtight.',
    authorName: 'Jane Smith',
    authorRole: 'Head of Customer Delivery, Watershed Labs',
    avatarUrl: 'https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=150&auto=format&fit=crop&q=80'
  }
];

export const FAQS = [
  {
    question: 'How does PromiseCheck detect promises in meeting notes and emails?',
    answer: 'PromiseCheck connects to your email (Google Workspace, Microsoft 365) and meeting recording tools (Zoom, Gong, Google Meet). Our context-aware natural language engine analyzes statements where team members commit to deliverables, timelines, or specifications (e.g., "We will send the updated roadmap by Friday"), extracting the deadline, assignee, and customer account automatically.'
  },
  {
    question: 'How does the team progress checking work?',
    answer: 'PromiseCheck connects bi-directionally with your project management platforms like Jira, Linear, GitHub, and Asana. It matches detected customer commitments with active engineering issues, checking PR merges, sprint velocity, and ticket statuses to evaluate if a delivery is realistically on schedule.'
  },
  {
    question: 'Who receives early risk alerts and how?',
    answer: 'Alerts are dispatched via Slack, Microsoft Teams, or email directly to the promise owner (e.g., the account executive, solutions architect, or engineering lead). If no corrective action is taken within 48 hours, team leadership receives an escalation digest.'
  },
  {
    question: 'Is customer communication data private and secure?',
    answer: 'Yes. PromiseCheck is SOC2 Type II certified and GDPR compliant. Your email threads and meeting transcripts are encrypted in transit and at rest using AES-256. We never use your confidential customer data to train public AI models.'
  },
  {
    question: 'Can we manually adjust or dismiss detected promises?',
    answer: 'Absolutely. Every detected commitment includes a one-click review button where you can adjust due dates, reassign team members, link specific Jira tickets, or mark false-positives with a single click.'
  }
];
