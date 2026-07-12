"""
Global application configuration.
"""

import os

from dotenv import load_dotenv

load_dotenv()

# ==========================================================
# APPLICATION
# ==========================================================

APP_NAME = "DataDumpAI"
APP_TAGLINE = "AI-powered business reporting in minutes."
APP_TAGLINE_SHORT = "AI-powered business reporting"
APP_VERSION = "1.0"
APP_RELEASE_LABEL = "Released July 2026"

SEO_TITLE = "DataDumpAI | AI-Powered Document Intelligence Platform"
SEO_DESCRIPTION = (
    "DataDumpAI transforms documents into executive reports, summaries, "
    "strategic insights, compliance analyses, and presentations using AI."
)
SEO_OG_TITLE = "DataDumpAI"
SEO_OG_DESCRIPTION = (
    "AI-powered platform that transforms documents into executive reports, "
    "strategic insights and presentations."
)
SEO_TWITTER_DESCRIPTION = "AI-powered document intelligence platform."
SEO_STRUCTURED_DESCRIPTION = "AI-powered document intelligence platform."

SITE_URL = os.getenv("SITE_URL", "https://www.getdatadump.com").strip()

PAGE_TITLE = SEO_TITLE
PAGE_ICON = "assets/logo.png"
LAYOUT = "wide"
SIDEBAR_STATE = "expanded"


# ==========================================================
# AUTHENTICATION (Supabase)
# ==========================================================

SUPABASE_URL = os.getenv("SUPABASE_URL", "").strip()
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY", "").strip()
AUTH_REDIRECT_URL = os.getenv("AUTH_REDIRECT_URL", "http://localhost:8501").strip()

# deployment environment: development | staging | production
ENVIRONMENT = os.getenv("ENVIRONMENT", "production").strip().lower()

# Explicit opt-in for legacy single-user dev auth (development only).
_AUTH_DEV_BYPASS_REQUESTED = os.getenv("AUTH_DEV_BYPASS", "false").lower() in {
    "1",
    "true",
    "yes",
}

# Legacy constant — raw env flag only. Use auth_dev_bypass_enabled() at runtime.
AUTH_DEV_BYPASS = _AUTH_DEV_BYPASS_REQUESTED

DEV_USER_ID = "00000000-0000-4000-8000-000000000001"
DEV_USER_EMAIL = "dev@localhost"


def auth_dev_bypass_enabled() -> bool:
    """Return True only when ENVIRONMENT=development and AUTH_DEV_BYPASS is set."""

    return ENVIRONMENT == "development" and _AUTH_DEV_BYPASS_REQUESTED


# ==========================================================
# DATABASE (Supabase PostgreSQL)
# ==========================================================

SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip()
DATABASE_BACKEND = os.getenv("DATABASE_BACKEND", "supabase").strip().lower()
STORAGE_BACKEND = os.getenv("STORAGE_BACKEND", "supabase").strip().lower()
SUPABASE_STORAGE_BUCKET = os.getenv("SUPABASE_STORAGE_BUCKET", "datadumpai-files").strip()

LOCKOUT_MAX_ATTEMPTS = int(os.getenv("LOCKOUT_MAX_ATTEMPTS", "5"))
LOCKOUT_DURATION_MINUTES = int(os.getenv("LOCKOUT_DURATION_MINUTES", "15"))


def use_database() -> bool:
    """Return True when metadata should be stored in Supabase PostgreSQL."""

    return DATABASE_BACKEND == "supabase" and is_supabase_configured()


def use_supabase_storage() -> bool:
    """Return True when blobs should be stored in Supabase Storage."""

    if STORAGE_BACKEND == "local":
        return False
    if STORAGE_BACKEND == "supabase":
        return is_supabase_configured()
    return is_supabase_configured()


def is_supabase_configured() -> bool:
    return bool(SUPABASE_URL and SUPABASE_ANON_KEY)


def validate_production_auth_configuration() -> list[str]:
    """Return fatal misconfiguration messages for production auth."""

    warnings: list[str] = []

    if _AUTH_DEV_BYPASS_REQUESTED and ENVIRONMENT != "development":
        warnings.append(
            "AUTH_DEV_BYPASS=true is only permitted when ENVIRONMENT=development. "
            f"Current ENVIRONMENT={ENVIRONMENT!r}. Disable AUTH_DEV_BYPASS or set "
            "ENVIRONMENT=development for local single-user mode."
        )

    if not auth_dev_bypass_enabled() and not is_supabase_configured():
        warnings.append(
            "Supabase Auth is required for multi-user mode. Set SUPABASE_URL and "
            "SUPABASE_ANON_KEY in your environment."
        )

    return warnings


def backend_configuration_warnings() -> list[str]:
    """Return user-visible warnings when production backends are misconfigured."""

    warnings: list[str] = []
    wants_supabase_db = DATABASE_BACKEND == "supabase"
    wants_supabase_storage = STORAGE_BACKEND == "supabase"

    if (wants_supabase_db or wants_supabase_storage) and not is_supabase_configured():
        warnings.append(
            "Supabase is selected for database or storage, but SUPABASE_URL and "
            "SUPABASE_ANON_KEY are missing. Metadata and files will fall back to "
            "local JSON storage until Supabase is configured."
        )

    if wants_supabase_db and is_supabase_configured() and not SUPABASE_SERVICE_ROLE_KEY:
        warnings.append(
            "SUPABASE_SERVICE_ROLE_KEY is required for server-side database "
            "operations such as login lockout tracking."
        )

    return warnings


# Legacy placeholders — use core.auth.get_current_user() instead.
CURRENT_USER = "Local User"
CURRENT_ROLE = "Workspace"


# ==========================================================
# AI CONFIGURATION
# ==========================================================

AI_MODEL = os.getenv("OPENAI_MODEL", "gpt-5")
AI_REPORT_MODEL = os.getenv("OPENAI_REPORT_MODEL", "gpt-4.1-mini")
AI_TEMPERATURE = 0.2
AI_MAX_OUTPUT_TOKENS = 4000
AI_REPORT_MAX_OUTPUT_TOKENS = int(os.getenv("AI_REPORT_MAX_OUTPUT_TOKENS", "2500"))
AI_INTELLIGENCE_REPORT_MAX_OUTPUT_TOKENS = int(
    os.getenv("AI_INTELLIGENCE_REPORT_MAX_OUTPUT_TOKENS", "4500"),
)
AI_FULL_REPORT_MAX_OUTPUT_TOKENS = int(
    os.getenv("AI_FULL_REPORT_MAX_OUTPUT_TOKENS", "6000"),
)
AI_REQUEST_TIMEOUT_SECONDS = float(os.getenv("AI_REQUEST_TIMEOUT_SECONDS", "120"))

# Keep report prompts responsive when users select many/large files.
AI_REPORT_MAX_CHARS_PER_DOC = int(os.getenv("AI_REPORT_MAX_CHARS_PER_DOC", "12000"))
AI_REPORT_MAX_TOTAL_CHARS = int(os.getenv("AI_REPORT_MAX_TOTAL_CHARS", "48000"))
AI_REPORT_DIRECT_MAX_CHARS = int(
    os.getenv("AI_REPORT_DIRECT_MAX_CHARS", str(AI_REPORT_MAX_TOTAL_CHARS)),
)
AI_REPORT_CHUNK_SIZE_CHARS = int(os.getenv("AI_REPORT_CHUNK_SIZE_CHARS", "10000"))
AI_REPORT_CHUNK_SUMMARY_MAX_CHARS = int(
    os.getenv("AI_REPORT_CHUNK_SUMMARY_MAX_CHARS", "600"),
)
AI_REPORT_SYNTHESIS_MAX_CHARS = int(
    os.getenv("AI_REPORT_SYNTHESIS_MAX_CHARS", "120000"),
)
AI_REPORT_CHUNK_SUMMARY_OUTPUT_TOKENS = int(
    os.getenv("AI_REPORT_CHUNK_SUMMARY_OUTPUT_TOKENS", "350"),
)
AI_REPORT_MAX_PDF_PAGES = int(os.getenv("AI_REPORT_MAX_PDF_PAGES", "25"))
AI_REPORT_MAX_TABULAR_ROWS = int(os.getenv("AI_REPORT_MAX_TABULAR_ROWS", "150"))

PDF_OCR_ENABLED = os.getenv("PDF_OCR_ENABLED", "true").lower() in {"1", "true", "yes"}
PDF_OCR_MAX_PAGES = int(os.getenv("PDF_OCR_MAX_PAGES", "15"))
PDF_OCR_MIN_TEXT_CHARS = int(os.getenv("PDF_OCR_MIN_TEXT_CHARS", "80"))

AI_SYSTEM_PROMPT = """
You are DataDumpAI.

You turn business documents into professional, evidence-backed executive reports.

- Write professionally and objectively.
- Use the required markdown structure when provided.
- Every major finding must cite source documents.
- Assign confidence scores based on evidence strength.
- Rank findings by executive importance.
- Quantify recurring themes when the documents support it.
- Make recommendations specific and actionable.
- Never invent facts, dates, figures, or document names.
- Base conclusions only on the supplied documents.
"""

# ==========================================================
# REPORT TYPES
# ==========================================================

FREE_REPORT_TYPES = [
    "Executive Summary",
]

FULL_REPORT_PERIODS = [
    "Monthly Report",
    "Quarterly Report",
    "Annual Report",
    "Weekly Report",
    "Comprehensive Report",
]

STARTER_REPORT_TYPES = [
    "Full Report",
    "Board Report",
    "Management Report",
    "Financial Analysis",
    "Meeting Minutes",
]

PRO_REPORT_TYPES = [
    "Regulatory Compliance Report",
    "Risk Assessment Report",
    "Meeting Intelligence Report",
    "Market Intelligence Report",
    "Strategic Planning Report",
    "Executive Intelligence Dashboard",
]

REPORT_TYPES = FREE_REPORT_TYPES + STARTER_REPORT_TYPES + PRO_REPORT_TYPES

# ==========================================================
# COPILOT (v1.0 launch prompts)
# ==========================================================

WEB_SEARCH_MAX_RESULTS = 5

COPILOT_PROMPTS = [
    "Summarize these documents",
    "What are the risks?",
    "What recommendations were made?",
    "What is the current inflation rate of Nigeria?",
]

DEBUG = os.getenv("DEBUG", "false").lower() in {"1", "true", "yes"}


# ==========================================================
# COMPANY & SUPPORT
# ==========================================================

COMPANY_NAME = "DataDumpAI"
COMPANY_LEGAL_NAME = "DataDumpAI Ltd"
COMPANY_WEBSITE = "https://getdatadump.com"
SUPPORT_EMAIL = "support@datadumpai.com"
FEEDBACK_EMAIL = "feedback@datadumpai.com"

# ==========================================================
# EMAIL & NOTIFICATIONS
# ==========================================================

EMAIL_ENABLED = os.getenv("EMAIL_ENABLED", "false").lower() in {"1", "true", "yes"}
EMAIL_FROM = os.getenv("EMAIL_FROM", f"noreply@{COMPANY_NAME.lower().replace(' ', '')}.com").strip()
EMAIL_FROM_NAME = os.getenv("EMAIL_FROM_NAME", COMPANY_NAME).strip()

SMTP_HOST = os.getenv("SMTP_HOST", "").strip()
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "").strip()
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "").strip()
SMTP_USE_TLS = os.getenv("SMTP_USE_TLS", "true").lower() in {"1", "true", "yes"}

RESEND_API_KEY = os.getenv("RESEND_API_KEY", "").strip()

DEFAULT_NOTIFICATION_PREFERENCES = {
    "report_ready": True,
    "usage_alerts": True,
    "billing": True,
    "product_updates": False,
}

# ==========================================================
# ADMIN
# ==========================================================

def _parse_csv_env(name: str) -> tuple[str, ...]:
    raw = os.getenv(name, "").strip()
    if not raw:
        return ()
    return tuple(item.strip() for item in raw.split(",") if item.strip())


ADMIN_USER_IDS = _parse_csv_env("ADMIN_USER_IDS")
ADMIN_EMAILS = _parse_csv_env("ADMIN_EMAILS")

# ==========================================================
# ANALYTICS
# ==========================================================

ANALYTICS_ENABLED = os.getenv("ANALYTICS_ENABLED", "false").lower() in {"1", "true", "yes"}
ANALYTICS_PROVIDER = os.getenv("ANALYTICS_PROVIDER", "local").strip().lower()
POSTHOG_API_KEY = os.getenv("POSTHOG_API_KEY", "").strip()
POSTHOG_HOST = os.getenv("POSTHOG_HOST", "https://app.posthog.com").strip()
PLAUSIBLE_DOMAIN = os.getenv("PLAUSIBLE_DOMAIN", "").strip()
ANALYTICS_EVENTS_PATH = os.getenv("ANALYTICS_EVENTS_PATH", "data/analytics_events.json").strip()


# ==========================================================
# PLANS & USAGE LIMITS
# ==========================================================

PLANS = {
    "free": {
        "label": "Free",
        "price_label": "$0",
        "tagline": "Try the platform without replacing your existing workflow.",
        "ideal_for": "Individuals trying the platform.",
        "reports_per_month": 5,
        "uploads_per_month": 10,
        "projects_max": 3,
        "report_types": FREE_REPORT_TYPES,
        "features": {
            "intelligence_reports": False,
            "professional_charts": False,
            "cross_document_intelligence": False,
            "web_research": False,
            "deep_copilot": False,
            "saved_ai_knowledge": False,
            "professional_exports": False,
            "word_export": False,
            "pptx_export": False,
            "custom_branding": False,
            "team_sharing": False,
            "priority_processing": False,
            "priority_support": False,
        },
        "includes": [
            "Up to 3 projects",
            "10 document uploads per month",
            "5 AI-generated reports per month",
            "Executive Summary reports",
            "Basic AI Assistant",
            "PDF download with DataDumpAI branding",
            "Standard support",
        ],
    },
    "starter": {
        "label": "Starter",
        "price_label": "~$15/mo",
        "tagline": "Everything you need for regular reporting.",
        "ideal_for": "Solo operators, analysts, and team leads.",
        "reports_per_month": 100,
        "uploads_per_month": 100,
        "projects_max": None,
        "report_types": FREE_REPORT_TYPES + STARTER_REPORT_TYPES,
        "features": {
            "intelligence_reports": False,
            "professional_charts": False,
            "cross_document_intelligence": False,
            "web_research": False,
            "deep_copilot": True,
            "saved_ai_knowledge": False,
            "professional_exports": True,
            "word_export": True,
            "pptx_export": False,
            "custom_branding": False,
            "team_sharing": False,
            "priority_processing": False,
            "priority_support": False,
        },
        "includes": [
            "Unlimited projects",
            "100 document uploads per month",
            "100 AI-generated reports per month",
            "Board, Management, Financial, Meeting, and Full Report rollups",
            "AI Assistant with project context",
            "Word and PDF exports",
            "Email support",
        ],
    },
    "professional": {
        "label": "Professional",
        "price_label": "~$39/mo",
        "tagline": "Move from an assistant to an analyst.",
        "ideal_for": (
            "Consultants, managers, board secretaries, researchers, "
            "SMEs, NGOs, and government teams."
        ),
        "reports_per_month": None,
        "uploads_per_month": None,
        "projects_max": None,
        "report_types": REPORT_TYPES,
        "features": {
            "intelligence_reports": True,
            "professional_charts": True,
            "cross_document_intelligence": True,
            "web_research": True,
            "deep_copilot": True,
            "saved_ai_knowledge": True,
            "professional_exports": True,
            "word_export": True,
            "pptx_export": True,
            "custom_branding": True,
            "team_sharing": True,
            "priority_processing": True,
            "priority_support": True,
        },
        "includes": [
            "Unlimited projects, uploads, and reports",
            "Premium intelligence report outputs",
            "Professional charts and trend analysis",
            "Cross-document intelligence",
            "Live internet research",
            "AI Assistant with deep context and citations",
            "PDF, Word, PowerPoint, and Markdown exports",
            "Branded reports with your logo and colors",
            "Priority processing and email support",
        ],
    },
    "enterprise": {
        "label": "Enterprise",
        "price_label": "Custom",
        "tagline": "Security, scale, and control for large teams.",
        "ideal_for": "Organizations with compliance, SSO, and deployment needs.",
        "reports_per_month": None,
        "uploads_per_month": None,
        "projects_max": None,
        "report_types": REPORT_TYPES,
        "features": {
            "intelligence_reports": True,
            "professional_charts": True,
            "cross_document_intelligence": True,
            "web_research": True,
            "deep_copilot": True,
            "saved_ai_knowledge": True,
            "professional_exports": True,
            "word_export": True,
            "pptx_export": True,
            "custom_branding": True,
            "team_sharing": True,
            "priority_processing": True,
            "priority_support": True,
            "sso": True,
            "admin_dashboard": True,
            "audit_logs": True,
            "api_access": True,
            "on_premise": True,
            "white_label": True,
        },
        "includes": [
            "Everything in Professional",
            "SSO and team workspaces",
            "Admin dashboard and audit logs",
            "API access",
            "On-premise deployment",
            "White labeling",
            "Dedicated support",
        ],
    },
}

PLAN_ALIASES = {
    "pro": "professional",
}

DEFAULT_PLAN = "free"
TRIAL_PLAN = "professional"
TRIAL_DAYS = 14


def resolve_plan_id(plan_id: str) -> str:
    return PLAN_ALIASES.get(plan_id, plan_id)


# ==========================================================
# PAYMENTS (Stripe + Paystack)
# ==========================================================

PAYMENTS_ENABLED = os.getenv("PAYMENTS_ENABLED", "false").lower() in {
    "1",
    "true",
    "yes",
}

STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY", "").strip()
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "").strip()
STRIPE_STARTER_PRICE_ID = os.getenv("STRIPE_STARTER_PRICE_ID", "").strip()
STRIPE_PROFESSIONAL_PRICE_ID = os.getenv("STRIPE_PROFESSIONAL_PRICE_ID", "").strip()

PAYSTACK_SECRET_KEY = os.getenv("PAYSTACK_SECRET_KEY", "").strip()
PAYSTACK_STARTER_PLAN_CODE = os.getenv("PAYSTACK_STARTER_PLAN_CODE", "").strip()
PAYSTACK_PROFESSIONAL_PLAN_CODE = os.getenv("PAYSTACK_PROFESSIONAL_PLAN_CODE", "").strip()

BILLING_SUCCESS_URL = os.getenv("BILLING_SUCCESS_URL", AUTH_REDIRECT_URL).strip()
BILLING_CANCEL_URL = os.getenv("BILLING_CANCEL_URL", AUTH_REDIRECT_URL).strip()
BILLING_WEBHOOK_BASE_URL = os.getenv("BILLING_WEBHOOK_BASE_URL", "http://localhost:8000").strip()

# Fallback amounts when price IDs / plan codes are not configured (USD cents / NGN kobo)
PLAN_PRICES = {
    "starter": {
        "stripe_amount_cents": int(os.getenv("STRIPE_STARTER_AMOUNT_CENTS", "1500")),
        "paystack_amount_kobo": int(os.getenv("PAYSTACK_STARTER_AMOUNT_KOBO", "1500000")),
    },
    "professional": {
        "stripe_amount_cents": int(os.getenv("STRIPE_PROFESSIONAL_AMOUNT_CENTS", "3900")),
        "paystack_amount_kobo": int(os.getenv("PAYSTACK_PROFESSIONAL_AMOUNT_KOBO", "3900000")),
    },
}

BILLABLE_PLANS = ("starter", "professional")


def is_stripe_configured() -> bool:
    return bool(STRIPE_SECRET_KEY)


def is_paystack_configured() -> bool:
    return bool(PAYSTACK_SECRET_KEY)
