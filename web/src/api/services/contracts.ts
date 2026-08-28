import type { ActivityLog, NotificationItem, Project, ReportSummary, User } from '@/types/api';
import type {
  AiRecommendation,
  ContinueWorkingItem,
  HomePageData,
  OrgIntelligenceSignal,
  QuickAction,
  TodaysBrief,
  UniversalSearchPayload,
  WorkspaceHealthSummary,
  WorkspaceInsight,
  WorkspaceInsightsOverview,
  TeamMember,
} from '@/types/home';
import type {
  CreateWorkspaceInput,
  UpdateWorkspaceInput,
  WorkspaceMembership,
} from '@/types/workspace';
import type {
  IntelligenceConversation,
  IntelligenceConversationSummary,
  IntelligenceMessage,
  SendMessageInput,
  StartConversationInput,
  StudioReadiness,
} from '@/types/intelligence';
import type {
  KnowledgeDetail,
  KnowledgeFilterOptions,
  KnowledgeListItem,
  KnowledgeListQuery,
  KnowledgeListResult,
  KnowledgePreview,
  KnowledgeProcessingStatus,
  KnowledgeRelationship,
  KnowledgeUploadInput,
} from '@/types/knowledge';
import type { ServiceAuth } from '@/api/config';
import type {
  BillingSummary,
  CompleteCheckoutInput,
  Plan,
  StartCheckoutInput,
} from '@/types/billing';

export interface HomeService {
  /** Aggregate Home DTO — maps to GET /api/v1/home */
  getHome(workspaceId?: string, auth?: ServiceAuth): Promise<HomePageData>;
  getGreeting(auth?: ServiceAuth): Promise<{ greeting: string; user: User }>;
  listNotifications(
    auth?: ServiceAuth,
  ): Promise<{ items: NotificationItem[]; unreadCount: number }>;
}

export interface WorkspaceService {
  listWorkspaces(auth?: ServiceAuth): Promise<Project[]>;
  getWorkspace(workspaceId: string, auth?: ServiceAuth): Promise<Project>;
  createWorkspace(
    input: CreateWorkspaceInput,
    auth?: ServiceAuth,
  ): Promise<Project>;
  updateWorkspace(
    workspaceId: string,
    input: UpdateWorkspaceInput,
    auth?: ServiceAuth,
  ): Promise<Project>;
  archiveWorkspace(workspaceId: string, auth?: ServiceAuth): Promise<void>;
  deleteWorkspace(workspaceId: string, auth?: ServiceAuth): Promise<void>;
  getMyMembership(
    workspaceId: string,
    auth?: ServiceAuth,
  ): Promise<WorkspaceMembership | null>;
  getHealth(
    workspaceId: string,
    auth?: ServiceAuth,
  ): Promise<WorkspaceHealthSummary>;
  getInsightsOverview(
    workspaceId: string,
    auth?: ServiceAuth,
  ): Promise<WorkspaceInsightsOverview>;
  getTeam(workspaceId: string, auth?: ServiceAuth): Promise<TeamMember[]>;
  getOrganizationalIntelligence(
    workspaceId: string,
    auth?: ServiceAuth,
  ): Promise<OrgIntelligenceSignal[]>;
  getRecentActivity(
    workspaceId: string,
    limit?: number,
    auth?: ServiceAuth,
  ): Promise<ActivityLog[]>;
  getContinueWorking(
    workspaceId: string,
    auth?: ServiceAuth,
  ): Promise<ContinueWorkingItem[]>;
}

export interface KnowledgeService {
  getSearchSuggestions(
    workspaceId: string,
    auth?: ServiceAuth,
  ): Promise<UniversalSearchPayload>;
  /** Organisational Memory corpus search (keyword / semantic mock). */
  search(
    workspaceId: string,
    query: KnowledgeListQuery,
    auth?: ServiceAuth,
  ): Promise<KnowledgeListResult>;
  listKnowledge(
    workspaceId: string,
    query?: KnowledgeListQuery,
    auth?: ServiceAuth,
  ): Promise<KnowledgeListResult>;
  getKnowledge(
    workspaceId: string,
    knowledgeId: string,
    auth?: ServiceAuth,
  ): Promise<KnowledgeDetail>;
  upload(
    workspaceId: string,
    input: KnowledgeUploadInput,
    auth?: ServiceAuth,
  ): Promise<KnowledgeListItem>;
  delete(
    workspaceId: string,
    knowledgeId: string,
    auth?: ServiceAuth,
  ): Promise<void>;
  tag(
    workspaceId: string,
    knowledgeId: string,
    tagIds: string[],
    auth?: ServiceAuth,
  ): Promise<KnowledgeListItem>;
  related(
    workspaceId: string,
    knowledgeId: string,
    auth?: ServiceAuth,
  ): Promise<KnowledgeRelationship[]>;
  preview(
    workspaceId: string,
    knowledgeId: string,
    auth?: ServiceAuth,
  ): Promise<KnowledgePreview>;
  processingStatus(
    workspaceId: string,
    knowledgeId: string,
    auth?: ServiceAuth,
  ): Promise<KnowledgeProcessingStatus>;
  reindex(
    workspaceId: string,
    knowledgeId: string,
    auth?: ServiceAuth,
  ): Promise<KnowledgeProcessingStatus>;
  download(
    workspaceId: string,
    knowledgeId: string,
    auth?: ServiceAuth,
  ): Promise<Blob>;
  getFilterOptions(
    workspaceId: string,
    auth?: ServiceAuth,
  ): Promise<KnowledgeFilterOptions>;
}

export interface ReportService {
  listReports(workspaceId: string, auth?: ServiceAuth): Promise<ReportSummary[]>;
  listAwaitingReview(
    workspaceId: string,
    auth?: ServiceAuth,
  ): Promise<ReportSummary[]>;
  getQuickActions(
    workspaceId: string,
    auth?: ServiceAuth,
  ): Promise<QuickAction[]>;
  listTemplates(
    workspaceId: string,
    auth?: ServiceAuth,
  ): Promise<import('@/types/reports').ReportTemplate[]>;
  listPeriods(
    workspaceId: string,
    auth?: ServiceAuth,
  ): Promise<import('@/types/reports').ReportPeriod[]>;
  listReportDetails(
    workspaceId: string,
    auth?: ServiceAuth,
  ): Promise<import('@/types/reports').ReportDetail[]>;
  getReport(
    workspaceId: string,
    reportId: string,
    auth?: ServiceAuth,
  ): Promise<import('@/types/reports').ReportDetail>;
  generate(
    workspaceId: string,
    input: import('@/types/reports').GenerateReportInput,
    auth?: ServiceAuth,
  ): Promise<import('@/types/reports').ReportDetail>;
  save(
    workspaceId: string,
    reportId: string,
    status?: import('@/types/reports').ReportStatus,
    auth?: ServiceAuth,
  ): Promise<import('@/types/reports').ReportDetail>;
  export(
    workspaceId: string,
    reportId: string,
    format: import('@/types/reports').ReportExportFormat,
    auth?: ServiceAuth,
    preparedBy?: string,
  ): Promise<Blob>;
}

export interface PublishJob {
  id: string;
  title: string;
  format: 'pdf' | 'docx' | 'pptx' | 'zip';
  status: 'queued' | 'running' | 'ready' | 'failed';
  createdAt: string;
  downloadUrl?: string;
}

export interface PublishService {
  listJobs(workspaceId: string, auth?: ServiceAuth): Promise<PublishJob[]>;
  enqueueExport(
    workspaceId: string,
    input: { reportId: string; format: PublishJob['format'] },
    auth?: ServiceAuth,
  ): Promise<PublishJob>;
}

export interface AIService {
  getTodaysBrief(workspaceId: string, auth?: ServiceAuth): Promise<TodaysBrief>;
  getRecommendations(
    workspaceId: string,
    auth?: ServiceAuth,
  ): Promise<AiRecommendation[]>;
  listInsights(
    workspaceId: string,
    auth?: ServiceAuth,
  ): Promise<WorkspaceInsight[]>;
}

/** Interactive Intelligence Studio — separate from Home insight cards. */
export interface IntelligenceService {
  checkReadiness(
    workspaceId: string,
    auth?: ServiceAuth,
  ): Promise<StudioReadiness>;
  listConversations(
    workspaceId: string,
    auth?: ServiceAuth,
  ): Promise<IntelligenceConversationSummary[]>;
  getConversation(
    workspaceId: string,
    conversationId: string,
    auth?: ServiceAuth,
  ): Promise<IntelligenceConversation>;
  startConversation(
    workspaceId: string,
    input?: StartConversationInput,
    auth?: ServiceAuth,
  ): Promise<IntelligenceConversation>;
  sendMessage(
    workspaceId: string,
    conversationId: string,
    input: SendMessageInput,
    auth?: ServiceAuth,
  ): Promise<IntelligenceConversation>;
  renameConversation(
    workspaceId: string,
    conversationId: string,
    title: string,
    auth?: ServiceAuth,
  ): Promise<IntelligenceConversationSummary>;
  deleteConversation(
    workspaceId: string,
    conversationId: string,
    auth?: ServiceAuth,
  ): Promise<void>;
  togglePin(
    workspaceId: string,
    conversationId: string,
    auth?: ServiceAuth,
  ): Promise<IntelligenceConversationSummary>;
  listSuggestions(workspaceId: string, auth?: ServiceAuth): Promise<string[]>;
  /** Answer a question without creating or saving a conversation ("temporary chat"). */
  askTemporary(
    workspaceId: string,
    input: SendMessageInput,
    auth?: ServiceAuth,
  ): Promise<IntelligenceMessage>;
}

export interface ProfileService {
  getProfile(auth?: ServiceAuth): Promise<import('@/types/auth').UserProfile>;
  updateProfile(
    input: import('@/types/auth').UpdateProfileInput,
    auth?: ServiceAuth,
  ): Promise<import('@/types/auth').UserProfile>;
  listOrganisationMemberships(
    auth?: ServiceAuth,
  ): Promise<import('@/types/auth').OrganisationMembership[]>;
}

export interface BrandingService {
  getLogo(auth?: ServiceAuth): Promise<import('@/types/auth').BrandingLogo>;
  uploadLogo(
    file: File,
    auth?: ServiceAuth,
  ): Promise<import('@/types/auth').BrandingLogo>;
  removeLogo(auth?: ServiceAuth): Promise<import('@/types/auth').BrandingLogo>;
}

export interface BillingService {
  listPlans(auth?: ServiceAuth): Promise<Plan[]>;
  getSummary(auth?: ServiceAuth): Promise<BillingSummary>;
  startCheckout(
    input: StartCheckoutInput,
    auth?: ServiceAuth,
  ): Promise<{ checkoutUrl: string }>;
  completeCheckout(
    input: CompleteCheckoutInput,
    auth?: ServiceAuth,
  ): Promise<BillingSummary>;
  openPortal(auth?: ServiceAuth): Promise<{ portalUrl: string }>;
  cancelAtPeriodEnd(auth?: ServiceAuth): Promise<BillingSummary>;
}

export interface ServiceContainer {
  home: HomeService;
  workspace: WorkspaceService;
  knowledge: KnowledgeService;
  report: ReportService;
  publish: PublishService;
  ai: AIService;
  intelligence: IntelligenceService;
  profile: ProfileService;
  billing: BillingService;
  branding: BrandingService;
}
