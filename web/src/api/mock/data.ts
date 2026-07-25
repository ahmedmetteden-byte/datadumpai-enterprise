import type {
  ActivityLog,
  NotificationItem,
  Project,
  ReportSummary,
  User,
} from '@/types/api';
import type {
  AiRecommendation,
  ContinueWorkingItem,
  OrgIntelligenceSignal,
  QuickAction,
  TodaysBrief,
  UniversalSearchPayload,
  WorkspaceHealthSummary,
  WorkspaceInsight,
  WorkspaceInsightsOverview,
  TeamMember,
} from '@/types/home';
import type { PublishJob } from '@/api/services/contracts';

export const mockUser: User = {
  id: 'usr_01',
  email: 'alex.morgan@contoso.com',
  fullName: 'Alex Morgan',
  emailVerified: true,
};

export const mockGreeting = 'Good evening, Alex';

export const mockWorkspaces: Project[] = [
  {
    id: 'ws_ops',
    ownerId: 'usr_01',
    name: 'Operations Hub',
    description: 'Cross-functional operating reports and knowledge',
    createdAt: '2025-11-02T09:00:00Z',
    updatedAt: '2026-07-24T18:40:00Z',
    lastActivity: '2026-07-24T18:40:00Z',
    storageUsed: 482_000_000,
  },
  {
    id: 'ws_board',
    ownerId: 'usr_01',
    name: 'Board Pack 2026',
    description: 'Board materials and executive summaries',
    createdAt: '2026-01-14T11:20:00Z',
    updatedAt: '2026-07-22T16:05:00Z',
    lastActivity: '2026-07-22T16:05:00Z',
    storageUsed: 210_000_000,
  },
  {
    id: 'ws_risk',
    ownerId: 'usr_01',
    name: 'Risk & Compliance',
    description: 'Policy library and audit trails',
    createdAt: '2025-08-19T08:00:00Z',
    updatedAt: '2026-07-20T10:12:00Z',
    lastActivity: '2026-07-20T10:12:00Z',
    storageUsed: 156_000_000,
  },
];

export const mockNotifications: NotificationItem[] = [
  {
    id: 'n1',
    message: 'Q2 Board Report is ready for review',
    level: 'success',
    createdAt: '2026-07-24T17:55:00Z',
    read: false,
  },
  {
    id: 'n2',
    message: '3 documents finished indexing',
    level: 'info',
    createdAt: '2026-07-24T15:10:00Z',
    read: false,
  },
];

export const mockSearchSuggestions: UniversalSearchPayload = {
  recentSearches: [
    { id: 'rs1', label: 'revenue variance Q2', meta: '2h ago' },
    { id: 'rs2', label: 'supplier risk summary', meta: 'Yesterday' },
    { id: 'rs3', label: 'headcount plan FY26', meta: '3 days ago' },
  ],
  suggestedActions: [
    { id: 'sa1', label: 'Generate a board report', href: '/reports/new' },
    { id: 'sa2', label: 'Ask Copilot about this workspace', href: '/copilot' },
    { id: 'sa3', label: 'Upload meeting notes', href: '/documents' },
  ],
  recentReports: [
    {
      id: 'rr1',
      label: 'Q2 Operating Review',
      meta: 'Ready',
      href: '/reports/q2-operating-review',
    },
    {
      id: 'rr2',
      label: 'Customer Retention Brief',
      meta: 'Draft',
      href: '/reports/retention-brief',
    },
  ],
  recentWorkspaces: [
    { id: 'rw1', label: 'Operations Hub', href: '/home?workspace=ws_ops' },
    { id: 'rw2', label: 'Board Pack 2026', href: '/home?workspace=ws_board' },
  ],
};

export const mockQuickActions: QuickAction[] = [
  {
    id: 'upload',
    label: 'Upload',
    description: 'Add documents to this workspace',
    icon: 'upload',
    href: '/documents',
  },
  {
    id: 'generate',
    label: 'Generate Report',
    description: 'Create a new AI-assisted report',
    icon: 'report',
    href: '/reports/new',
  },
  {
    id: 'copilot',
    label: 'Ask Copilot',
    description: 'Chat with your knowledge base',
    icon: 'copilot',
    href: '/copilot',
  },
  {
    id: 'export',
    label: 'Export',
    description: 'Download the latest package',
    icon: 'export',
    href: '/reports',
  },
];

export const mockContinueWorking: ContinueWorkingItem[] = [
  {
    id: 'cw1',
    title: 'Q2 Operating Review',
    subtitle: 'Operations Hub · Awaiting your edits',
    kind: 'report',
    progressPercent: 72,
    updatedAt: '2026-07-24T16:20:00Z',
    href: '/reports/q2-operating-review',
  },
  {
    id: 'cw2',
    title: 'Supplier Risk Memo',
    subtitle: 'Risk & Compliance · Draft',
    kind: 'draft',
    progressPercent: 40,
    updatedAt: '2026-07-23T11:05:00Z',
    href: '/reports/supplier-risk-memo',
  },
  {
    id: 'cw3',
    title: 'Board Pack 2026',
    subtitle: 'Workspace · Last opened yesterday',
    kind: 'workspace',
    updatedAt: '2026-07-23T18:40:00Z',
    href: '/home?workspace=ws_board',
  },
];

export const mockInsightsOverview: WorkspaceInsightsOverview = {
  healthPercent: 86,
  newInsightCount: 5,
  reportsAwaitingReview: 2,
  lastUpdated: '2026-07-24T18:40:00Z',
};

export const mockReports: ReportSummary[] = [
  {
    filename: 'q2-operating-review.md',
    name: 'Q2 Operating Review',
    path: '/reports/q2-operating-review.md',
    size: 84_200,
    createdAt: '2026-07-24T12:00:00Z',
    status: 'awaiting_review',
  },
  {
    filename: 'retention-brief.md',
    name: 'Customer Retention Brief',
    path: '/reports/retention-brief.md',
    size: 52_100,
    createdAt: '2026-07-22T09:30:00Z',
    status: 'awaiting_review',
  },
  {
    filename: 'supplier-risk-memo.md',
    name: 'Supplier Risk Memo',
    path: '/reports/supplier-risk-memo.md',
    size: 41_800,
    createdAt: '2026-07-20T14:10:00Z',
    status: 'draft',
  },
];

export const mockTodaysBrief: TodaysBrief = {
  date: '2026-07-24T00:00:00Z',
  greeting: 'Here is what matters today',
  items: [
    {
      id: 'b1',
      headline: 'Two reports need executive review',
      detail: 'Q2 Operating Review and Retention Brief are waiting.',
      priority: 'high',
      href: '/reports',
    },
    {
      id: 'b2',
      headline: 'Knowledge base grew overnight',
      detail: '12 new pages indexed from uploaded board packs.',
      priority: 'medium',
    },
    {
      id: 'b3',
      headline: 'Copilot found a margin anomaly',
      detail: 'Gross margin dipped 1.8pts vs prior quarter in EMEA.',
      priority: 'high',
      href: '/copilot',
    },
  ],
};

export const mockRecommendations: AiRecommendation[] = [
  {
    id: 'rec1',
    title: 'Refresh the board narrative with latest KPI pack',
    rationale: 'Source documents updated 6 hours ago; report is stale.',
    actionLabel: 'Regenerate',
    actionHref: '/reports/q2-operating-review',
    confidence: 0.91,
  },
  {
    id: 'rec2',
    title: 'Invite Risk to the Operations Hub',
    rationale: 'Three shared documents reference compliance owners.',
    actionLabel: 'Open team',
    actionHref: '/settings/team',
    confidence: 0.74,
  },
  {
    id: 'rec3',
    title: 'Archive unused supplier drafts',
    rationale: 'Four drafts have not been opened in 45 days.',
    actionLabel: 'Review drafts',
    actionHref: '/reports',
    confidence: 0.68,
  },
];

export const mockActivity: ActivityLog[] = [
  {
    id: 'a1',
    userId: 'usr_01',
    action: 'report.generated',
    message: 'Board Report Generated',
    metadata: {},
    createdAt: '2026-07-24T09:14:00Z',
  },
  {
    id: 'a2',
    userId: 'usr_01',
    action: 'document.uploaded',
    message: 'Annual Report Uploaded',
    metadata: {},
    createdAt: '2026-07-24T09:42:00Z',
  },
  {
    id: 'a3',
    userId: 'usr_02',
    action: 'ai.summary',
    message: 'AI Summary Completed',
    metadata: {},
    createdAt: '2026-07-24T10:06:00Z',
  },
  {
    id: 'a4',
    userId: 'usr_01',
    action: 'document.indexed',
    message: 'Meeting Recording Indexed',
    metadata: {},
    createdAt: '2026-07-24T11:30:00Z',
  },
];

export const mockHealth: WorkspaceHealthSummary = {
  overallPercent: 86,
  status: 'ready',
  lastUpdated: '2026-07-24T18:40:00Z',
  indicators: [
    {
      status: 'ready',
      icon: 'ready',
      message: 'AI corpus ready — 128 documents indexed',
    },
    {
      status: 'warning',
      icon: 'warning',
      message: '2 reports awaiting review',
    },
    {
      status: 'ready',
      icon: 'ready',
      message: 'Storage healthy — 482 MB of 5 GB used',
    },
  ],
};

export const mockTeam: TeamMember[] = [
  {
    id: 'usr_01',
    name: 'Alex Morgan',
    role: 'owner',
    title: 'Workspace owner',
    status: 'online',
  },
  {
    id: 'usr_02',
    name: 'Jordan Lee',
    role: 'editor',
    title: 'Analyst',
    status: 'online',
  },
  {
    id: 'usr_03',
    name: 'Sam Rivera',
    role: 'reviewer',
    title: 'Reviewer',
    status: 'away',
  },
  {
    id: 'usr_04',
    name: 'Casey Nguyen',
    role: 'viewer',
    title: 'Contributor',
    status: 'offline',
  },
];

export const mockOrgIntelligence: OrgIntelligenceSignal[] = [
  {
    id: 'oi1',
    title: 'Cross-workspace reuse',
    summary: '18% of knowledge is referenced in multiple workspaces.',
    trend: 'up',
    valueLabel: '+4% MoM',
  },
  {
    id: 'oi2',
    title: 'Decision latency',
    summary: 'Average time from draft to approval is 2.4 days.',
    trend: 'down',
    valueLabel: '−0.6d',
  },
  {
    id: 'oi3',
    title: 'Coverage gaps',
    summary: 'EMEA region has fewer indexed sources than APAC.',
    trend: 'flat',
    valueLabel: '3 gaps',
  },
];

export const mockInsights: WorkspaceInsight[] = [
  {
    id: 'ins1',
    title: 'EMEA margin pressure',
    confidence: 0.88,
    summary: 'Gross margin declined 1.8pts vs prior quarter.',
    updatedAt: '2026-07-24T14:20:00Z',
    category: 'finance',
  },
  {
    id: 'ins2',
    title: 'Supplier concentration risk',
    confidence: 0.81,
    summary: 'Top vendor accounts for 41% of critical SKUs.',
    updatedAt: '2026-07-24T11:05:00Z',
    category: 'risk',
  },
  {
    id: 'ins3',
    title: 'Retention cohort lift',
    confidence: 0.76,
    summary: 'Enterprise cohort retention improved 3pts QoQ.',
    updatedAt: '2026-07-23T19:40:00Z',
    category: 'growth',
  },
  {
    id: 'ins4',
    title: 'Stale policy documents',
    confidence: 0.72,
    summary: '7 compliance docs have not been refreshed in 90 days.',
    updatedAt: '2026-07-23T08:15:00Z',
    category: 'compliance',
  },
  {
    id: 'ins5',
    title: 'Meeting-to-action gap',
    confidence: 0.69,
    summary: '4 recorded actions lack an assigned owner.',
    updatedAt: '2026-07-22T16:50:00Z',
    category: 'ops',
  },
];

export const mockPublishJobs: PublishJob[] = [
  {
    id: 'pub_1',
    title: 'Q2 Operating Review',
    format: 'pdf',
    status: 'ready',
    createdAt: '2026-07-24T13:05:00Z',
    downloadUrl: '/exports/q2-operating-review.pdf',
  },
  {
    id: 'pub_2',
    title: 'Board Pack bundle',
    format: 'zip',
    status: 'running',
    createdAt: '2026-07-24T18:10:00Z',
  },
];

export function resolveWorkspace(workspaceId?: string): Project {
  return (
    mockWorkspaces.find((workspace) => workspace.id === workspaceId) ??
    mockWorkspaces[0]!
  );
}
