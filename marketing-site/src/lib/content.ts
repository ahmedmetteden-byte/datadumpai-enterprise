export const FEATURES = [
  {
    title: "AI Summaries",
    description:
      "Distill lengthy documents into precise, actionable summaries in seconds.",
    icon: "sparkles",
  },
  {
    title: "Executive Reports",
    description:
      "Generate board-ready reports, management updates, and executive briefings.",
    icon: "document",
  },
  {
    title: "Meeting Intelligence",
    description:
      "Transform meeting minutes and transcripts into decisions, actions, and insights.",
    icon: "users",
  },
  {
    title: "Compliance Intelligence",
    description:
      "Map policies and controls to regulatory requirements with audit-ready outputs.",
    icon: "shield",
  },
  {
    title: "Regulatory Analysis",
    description:
      "Analyze regulations, circulars, and guidance documents across jurisdictions.",
    icon: "scale",
  },
  {
    title: "Knowledge Repository",
    description:
      "Build a searchable AI knowledge base from your organization's documents.",
    icon: "database",
  },
  {
    title: "Cross-Document Analysis",
    description:
      "Connect insights across multiple files to surface patterns and contradictions.",
    icon: "layers",
  },
  {
    title: "Presentations",
    description:
      "Export polished PowerPoint decks and slide-ready narratives from your data.",
    icon: "presentation",
  },
  {
    title: "Citations",
    description:
      "Every insight is traceable back to source documents with verifiable references.",
    icon: "link",
  },
  {
    title: "DataTokens",
    description:
      "Transparent usage metering so teams understand and control AI consumption.",
    icon: "token",
  },
  {
    title: "Team Collaboration",
    description:
      "Shared workspaces, project libraries, and role-based access for teams.",
    icon: "team",
  },
] as const;

export const INDUSTRIES = [
  {
    name: "Insurance",
    description:
      "Underwriting memos, claims analysis, regulatory filings, and board reporting.",
    icon: "umbrella",
  },
  {
    name: "Government",
    description:
      "Policy briefs, parliamentary research, public sector compliance, and audits.",
    icon: "building",
  },
  {
    name: "Financial Services",
    description:
      "Risk reports, regulatory submissions, investment memos, and compliance packs.",
    icon: "chart",
  },
  {
    name: "Healthcare",
    description:
      "Clinical guidelines, accreditation documents, and operational intelligence.",
    icon: "heart",
  },
  {
    name: "Legal",
    description:
      "Contract review, case research, due diligence, and client-ready summaries.",
    icon: "gavel",
  },
  {
    name: "Energy",
    description:
      "Environmental compliance, safety reports, and stakeholder communications.",
    icon: "bolt",
  },
  {
    name: "Manufacturing",
    description:
      "Quality documentation, supply chain reports, and operational audits.",
    icon: "factory",
  },
  {
    name: "Education",
    description:
      "Research synthesis, accreditation reports, and institutional planning.",
    icon: "graduation",
  },
] as const;

export const SOLUTIONS = [
  {
    title: "Executive Teams",
    description:
      "Board packs, strategic briefings, and decision-ready intelligence delivered in minutes instead of days.",
    audience: "C-suite & leadership",
  },
  {
    title: "Regulators",
    description:
      "Structured analysis of submissions, policy documents, and compliance evidence across portfolios.",
    audience: "Regulatory bodies",
  },
  {
    title: "Compliance Officers",
    description:
      "Gap analysis, control mapping, and audit-ready documentation from your policy library.",
    audience: "Compliance & GRC",
  },
  {
    title: "Risk Managers",
    description:
      "Risk registers, scenario analysis, and cross-document risk intelligence from disparate sources.",
    audience: "Risk & audit",
  },
  {
    title: "Researchers",
    description:
      "Literature synthesis, citation-backed findings, and research briefs from large document sets.",
    audience: "Research & analytics",
  },
  {
    title: "Consultants",
    description:
      "Client-ready deliverables, proposal support, and rapid due diligence from uploaded materials.",
    audience: "Advisory firms",
  },
  {
    title: "Boards",
    description:
      "Governance packs, fiduciary summaries, and strategic oversight materials with full citations.",
    audience: "Boards & committees",
  },
] as const;

export const PRICING_PLANS = [
  {
    id: "starter",
    name: "Starter",
    price: "$15",
    period: "/month",
    description: "Everything you need for regular reporting.",
    highlighted: false,
    cta: "Start Analyzing Documents",
    features: [
      "Unlimited projects",
      "100 document uploads / month",
      "100 AI-generated reports / month",
      "Board, Management & Meeting reports",
      "AI Assistant with project context",
      "Word and PDF exports",
      "Email support",
    ],
  },
  {
    id: "professional",
    name: "Professional",
    price: "$39",
    period: "/month",
    description: "Move from an assistant to an analyst.",
    highlighted: true,
    cta: "Start Analyzing Documents",
    features: [
      "Unlimited projects, uploads & reports",
      "Premium intelligence report outputs",
      "Professional charts & trend analysis",
      "Cross-document intelligence",
      "Live internet research",
      "AI Assistant with citations",
      "PDF, Word, PowerPoint & Markdown exports",
      "Branded reports with your logo",
      "Priority processing & support",
    ],
  },
  {
    id: "enterprise",
    name: "Enterprise",
    price: "Custom",
    period: "",
    description: "Security, scale, and control for large teams.",
    highlighted: false,
    cta: "Contact Sales",
    features: [
      "Everything in Professional",
      "Single sign-on (SSO)",
      "Admin dashboard & audit logs",
      "API access",
      "Dedicated account manager",
      "Custom deployment options",
      "SLA & priority support",
      "AI governance controls",
    ],
  },
] as const;

export const SECURITY_FEATURES = [
  {
    title: "Encryption",
    description:
      "Data encrypted in transit (TLS 1.2+) and at rest. Enterprise-grade key management available.",
  },
  {
    title: "Role-Based Access",
    description:
      "Granular permissions ensure users only access documents and projects they're authorized for.",
  },
  {
    title: "Audit Logs",
    description:
      "Comprehensive activity logging for compliance, forensics, and governance requirements.",
  },
  {
    title: "Enterprise Security",
    description:
      "SSO, dedicated infrastructure options, and security reviews for regulated industries.",
  },
  {
    title: "AI Governance",
    description:
      "Transparent AI usage, citation requirements, and controls over model behavior and data retention.",
  },
] as const;

export const DOC_SECTIONS = [
  {
    title: "Getting Started",
    slug: "getting-started",
    items: [
      { slug: "getting-started", title: "Introduction" },
      { slug: "quickstart", title: "Quickstart" },
      { slug: "upload-documents", title: "Upload Documents" },
    ],
  },
  {
    title: "Platform",
    slug: "platform",
    items: [
      { slug: "reports", title: "Generating Reports" },
      { slug: "copilot", title: "AI Assistant" },
      { slug: "exports", title: "Exports & Downloads" },
    ],
  },
  {
    title: "Enterprise",
    slug: "enterprise",
    items: [
      { slug: "security", title: "Security Overview" },
      { slug: "api", title: "API Reference" },
      { slug: "sso", title: "Single Sign-On" },
    ],
  },
] as const;

export const DOC_CONTENT: Record<
  string,
  { title: string; description: string; sections: { heading: string; body: string }[] }
> = {
  "getting-started": {
    title: "Introduction",
    description: "Welcome to DataDumpAI — your AI-powered document intelligence platform.",
    sections: [
      {
        heading: "What is DataDumpAI?",
        body: "DataDumpAI transforms unstructured documents into executive intelligence. Upload PDFs, Word files, spreadsheets, and presentations — then generate reports, insights, and presentations powered by AI.",
      },
      {
        heading: "Who is it for?",
        body: "DataDumpAI serves executive teams, compliance officers, researchers, consultants, and boards who need to extract actionable intelligence from large document volumes quickly and reliably.",
      },
    ],
  },
  quickstart: {
    title: "Quickstart",
    description: "Get up and running with DataDumpAI in five minutes.",
    sections: [
      {
        heading: "1. Create your account",
        body: "Sign up for a free trial at the application. No credit card required for the 14-day Professional trial.",
      },
      {
        heading: "2. Create a project",
        body: "Projects organize your documents and reports. Create a project for each engagement, client, or reporting cycle.",
      },
      {
        heading: "3. Upload documents",
        body: "Drag and drop PDFs, DOCX, XLSX, PPTX, and more. DataDumpAI processes and indexes your files automatically.",
      },
      {
        heading: "4. Generate your first report",
        body: "Choose a report type — Executive Summary, Board Pack, Compliance Analysis — and let AI do the heavy lifting.",
      },
    ],
  },
  "upload-documents": {
    title: "Upload Documents",
    description: "Supported formats and best practices for document uploads.",
    sections: [
      {
        heading: "Supported formats",
        body: "PDF, DOCX, DOC, XLSX, XLS, PPTX, PPT, TXT, MD, and CSV. Maximum file size depends on your plan.",
      },
      {
        heading: "Best practices",
        body: "Use clear filenames, group related documents in projects, and upload source materials before generating reports for best results.",
      },
    ],
  },
  reports: {
    title: "Generating Reports",
    description: "Report types and configuration options.",
    sections: [
      {
        heading: "Report types",
        body: "Executive Summary, Board Pack, Management Update, Financial Analysis, Meeting Intelligence, Compliance Analysis, Regulatory Brief, and more.",
      },
      {
        heading: "Customization",
        body: "Professional and Enterprise plans support custom branding, chart generation, and cross-document intelligence.",
      },
    ],
  },
  copilot: {
    title: "AI Assistant",
    description: "Ask questions and explore your document library with AI.",
    sections: [
      {
        heading: "Project context",
        body: "The AI Assistant has access to all documents in your active project, providing cited answers grounded in your data.",
      },
      {
        heading: "Deep research",
        body: "Professional plans include live web research to supplement your document intelligence with current information.",
      },
    ],
  },
  exports: {
    title: "Exports & Downloads",
    description: "Download reports in multiple formats.",
    sections: [
      {
        heading: "Formats",
        body: "Export as PDF, Word (DOCX), PowerPoint (PPTX), or Markdown depending on your plan.",
      },
      {
        heading: "Branding",
        body: "Professional and Enterprise plans support custom logos and color schemes on exported documents.",
      },
    ],
  },
  security: {
    title: "Security Overview",
    description: "How DataDumpAI protects your data.",
    sections: [
      {
        heading: "Data isolation",
        body: "Each user workspace is isolated. Documents are never shared across accounts without explicit team permissions.",
      },
      {
        heading: "Compliance",
        body: "Enterprise customers can request security questionnaires, DPAs, and compliance documentation.",
      },
    ],
  },
  api: {
    title: "API Reference",
    description: "Programmatic access to DataDumpAI (Enterprise).",
    sections: [
      {
        heading: "Authentication",
        body: "API keys are issued through the Enterprise admin dashboard. All requests require Bearer token authentication.",
      },
      {
        heading: "Endpoints",
        body: "Upload documents, trigger report generation, and retrieve results via REST API. Full OpenAPI specification available on request.",
      },
    ],
  },
  sso: {
    title: "Single Sign-On",
    description: "Configure SSO for your organization.",
    sections: [
      {
        heading: "Supported providers",
        body: "SAML 2.0 and OIDC compatible with Okta, Azure AD, Google Workspace, and other identity providers.",
      },
      {
        heading: "Setup",
        body: "Contact your account manager to configure SSO. Typical setup takes 1–2 business days.",
      },
    ],
  },
};
