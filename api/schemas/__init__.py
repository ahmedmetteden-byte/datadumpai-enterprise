"""
Pydantic schemas for the product API (camelCase for the React SPA).
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


def to_camel(name: str) -> str:
    parts = name.split("_")
    return parts[0] + "".join(part.capitalize() for part in parts[1:])


class CamelModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        serialize_by_alias=True,
    )


class CreateWorkspaceBody(CamelModel):
    name: str
    description: str | None = None


class UpdateWorkspaceBody(CamelModel):
    name: str | None = None
    description: str | None = None


class WorkspaceOut(CamelModel):
    id: str
    owner_id: str
    name: str
    description: str = ""
    created_at: str
    updated_at: str
    last_activity: str
    storage_used: int = 0


class WorkspaceMembershipOut(CamelModel):
    user_id: str
    workspace_id: str
    role: Literal["owner", "admin", "editor", "reviewer", "viewer"] = "owner"


class WorkspaceHealthOut(CamelModel):
    overall_percent: int = 0
    status: Literal["ready", "warning", "critical"] = "ready"
    indicators: list[dict[str, Any]] = Field(default_factory=list)
    last_updated: str = ""


class WorkspaceInsightsOverviewOut(CamelModel):
    health_percent: int = 0
    new_insight_count: int = 0
    reports_awaiting_review: int = 0
    last_updated: str = ""


class TeamMemberOut(CamelModel):
    id: str
    name: str
    role: str = "owner"
    title: str | None = None
    avatar_url: str | None = None
    status: Literal["online", "away", "offline"] = "offline"


class ActivityLogOut(CamelModel):
    id: str
    user_id: str
    action: str
    message: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: str


class ContinueWorkingOut(CamelModel):
    id: str
    title: str
    subtitle: str = ""
    kind: Literal["report", "document", "workspace", "draft"] = "document"
    progress_percent: int | None = None
    updated_at: str = ""
    href: str


class OrgIntelligenceSignalOut(CamelModel):
    id: str
    title: str
    summary: str
    trend: Literal["up", "down", "flat"] = "flat"
    value_label: str = ""


class KnowledgeListItemOut(CamelModel):
    id: str
    workspace_id: str
    type: str = "document"
    title: str
    summary: str | None = None
    status: str = "uploaded"
    tag_ids: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    project_id: str | None = None
    project_name: str | None = None
    author_id: str | None = None
    author_name: str | None = None
    updated_at: str
    created_at: str
    collection_ids: list[str] = Field(default_factory=list)
    collection_name: str | None = None
    filename: str | None = None
    mime_type: str | None = None
    size_bytes: int | None = None
    indexed_at: str | None = None
    progress_percent: int | None = None
    index_stage: str | None = None


class KnowledgeListResultOut(CamelModel):
    items: list[KnowledgeListItemOut]
    total: int
    limit: int
    offset: int


class KnowledgeDetailOut(KnowledgeListItemOut):
    metadata: dict[str, Any] = Field(default_factory=dict)
    storage_path: str | None = None
    relationships: list[Any] = Field(default_factory=list)
    related: list[Any] = Field(default_factory=list)
    referenced_by: list[Any] = Field(default_factory=list)
    timeline: list[Any] = Field(default_factory=list)
    versions_placeholder: str = ""


class KnowledgePreviewOut(CamelModel):
    knowledge_id: str
    kind: Literal["text", "pdf", "html", "unsupported"] = "text"
    text_excerpt: str | None = None
    url: str | None = None


class KnowledgeProcessingStatusOut(CamelModel):
    knowledge_id: str
    status: str
    stage: str
    index_stage: str | None = None
    progress_percent: int | None = None
    error_message: str | None = None
    updated_at: str


class KnowledgeFilterOptionsOut(CamelModel):
    tags: list[Any] = Field(default_factory=list)
    projects: list[dict[str, str]] = Field(default_factory=list)
    authors: list[dict[str, str]] = Field(default_factory=list)
    collections: list[Any] = Field(default_factory=list)
    types: list[str] = Field(default_factory=lambda: ["document"])


class StudioReadinessOut(CamelModel):
    ready: bool = False
    status: str = ""
    document_count: int = 0
    report_count: int = 0
    can_ask: bool = False
    web_research_available: bool = False


class IntelligenceSourceOut(CamelModel):
    id: str
    kind: str = "document"
    title: str
    location: str | None = None
    excerpt: str | None = None
    preview_url: str | None = None
    document_id: str | None = None
    score: float | None = None


class IntelligenceCitationOut(CamelModel):
    id: str
    index: int
    source_id: str
    label: str
    quote: str
    location: str | None = None


class IntelligenceMessageOut(CamelModel):
    id: str
    conversation_id: str
    role: Literal["user", "assistant", "system"]
    content: str = ""
    answer: str | None = None
    evidence: str | None = None
    confidence: float | None = None
    follow_ups: list[str] = Field(default_factory=list)
    sources: list[IntelligenceSourceOut] = Field(default_factory=list)
    citations: list[IntelligenceCitationOut] = Field(default_factory=list)
    linked_documents: list[IntelligenceSourceOut] = Field(default_factory=list)
    notice: str | None = None
    status: Literal["pending", "streaming", "complete", "error"] = "complete"
    created_at: str
    mode: str | None = None


class IntelligenceConversationSummaryOut(CamelModel):
    id: str
    workspace_id: str
    title: str
    pinned: bool = False
    updated_at: str
    preview: str = ""


class IntelligenceConversationOut(CamelModel):
    id: str
    workspace_id: str
    title: str
    pinned: bool = False
    updated_at: str
    messages: list[IntelligenceMessageOut] = Field(default_factory=list)


class StartConversationBody(CamelModel):
    title: str | None = None
    initial_message: str | None = None
    mode: str | None = None


class SendMessageBody(CamelModel):
    content: str
    mode: str = "ask"


class RenameConversationBody(CamelModel):
    title: str


class ReportTemplateOut(CamelModel):
    id: str
    name: str
    description: str = ""
    locked: bool = False
    required_plan: str | None = None


class ReportPeriodOut(CamelModel):
    id: str
    name: str


class ReportDetailOut(CamelModel):
    id: str
    filename: str
    name: str
    path: str = ""
    size: int = 0
    created_at: str
    updated_at: str | None = None
    report_type: str | None = None
    template_id: str | None = None
    period_id: str | None = None
    period_name: str | None = None
    status: Literal["draft", "ready", "awaiting_review", "archived"] = "draft"
    content: str | None = None
    source_documents: list[str] = Field(default_factory=list)
    instructions: str | None = None
    locked_export_formats: dict[str, str] = Field(default_factory=dict)


class GenerateReportBody(CamelModel):
    template_id: str
    period_id: str
    title: str | None = None
    instructions: str | None = None


class SaveReportBody(CamelModel):
    status: Literal["ready", "awaiting_review", "draft"] = "ready"


class UserOut(CamelModel):
    id: str
    email: str
    full_name: str = ""
    email_verified: bool = True


class NotificationOut(CamelModel):
    id: str
    message: str
    level: Literal["info", "success", "warning", "error"] = "info"
    created_at: str
    read: bool = False


class DashboardMetricOut(CamelModel):
    id: str
    label: str
    value: int
    unit: Literal["count", "percent"] = "count"


class DashboardRecentItemOut(CamelModel):
    id: str
    title: str
    subtitle: str = ""
    href: str
    kind: Literal["document", "report", "conversation", "workspace"] = "document"
    at: str
    meta: str | None = None


class HomeDashboardOut(CamelModel):
    metrics: list[DashboardMetricOut] = Field(default_factory=list)
    recent_uploads: list[DashboardRecentItemOut] = Field(default_factory=list)
    recent_reports: list[DashboardRecentItemOut] = Field(default_factory=list)
    recent_conversations: list[DashboardRecentItemOut] = Field(default_factory=list)


class HomePageOut(CamelModel):
    user: UserOut
    greeting: str
    active_workspace: WorkspaceOut | None = None
    workspaces: list[WorkspaceOut] = Field(default_factory=list)
    notifications: list[NotificationOut] = Field(default_factory=list)
    unread_notification_count: int = 0
    quick_actions: list[dict[str, Any]] = Field(default_factory=list)
    continue_working: list[ContinueWorkingOut] = Field(default_factory=list)
    insights_overview: WorkspaceInsightsOverviewOut
    dashboard: HomeDashboardOut
    search: dict[str, Any] = Field(default_factory=dict)
    reports_awaiting_review: list[Any] = Field(default_factory=list)
    insights: dict[str, Any] = Field(default_factory=dict)


class UpdateProfileBody(CamelModel):
    full_name: str | None = None
    company: str | None = None
    job_title: str | None = None


class OrganisationMembershipOut(CamelModel):
    workspace_id: str
    workspace_name: str
    role: Literal["owner", "admin", "editor", "reviewer", "viewer"] = "owner"
    user_id: str


class UserProfileOut(CamelModel):
    """Matches the SPA `UserProfile` DTO (camelCase)."""

    user_id: str
    email: str
    full_name: str = ""
    company: str = ""
    job_title: str = ""
    photo_url: str = ""
    role: str = "user"
    email_verified: bool = False
    organisation_name: str = ""
    memberships: list[OrganisationMembershipOut] = Field(default_factory=list)
    updated_at: str | None = None


# --- Billing -----------------------------------------------------------

PaymentProviderId = Literal["stripe", "paystack"]


class PlanOut(CamelModel):
    id: str
    label: str
    price_label: str
    tagline: str = ""
    ideal_for: str = ""
    reports_per_month: int | None = None
    uploads_per_month: int | None = None
    projects_max: int | None = None
    includes: list[str] = Field(default_factory=list)
    billable: bool = False


class UsageSnapshotOut(CamelModel):
    reports_used: int
    reports_limit: int | None
    uploads_used: int
    uploads_limit: int | None
    projects_max: int | None


class BillingSummaryOut(CamelModel):
    enabled: bool
    available_providers: list[PaymentProviderId] = Field(default_factory=list)
    billing_plan: str
    effective_plan: str
    subscription_status: str
    payment_provider: str | None = None
    cancel_at_period_end: bool = False
    current_period_end: str | None = None
    trial_days_remaining: int | None = None
    usage: UsageSnapshotOut


class StartCheckoutBody(CamelModel):
    plan_id: str
    provider: PaymentProviderId


class CheckoutUrlOut(CamelModel):
    checkout_url: str


class CompleteCheckoutBody(CamelModel):
    provider: PaymentProviderId
    session_id: str | None = None
    reference: str | None = None


class PortalUrlOut(CamelModel):
    portal_url: str


# --- Public (unauthenticated) -------------------------------------------


class ContactRequestBody(CamelModel):
    first_name: str
    last_name: str
    email: str
    company: str | None = None
    subject: Literal["general", "sales", "support", "partnership", "press"] = "general"
    message: str
    honeypot: str | None = None


class ContactResponseOut(CamelModel):
    status: Literal["sent", "skipped"]
