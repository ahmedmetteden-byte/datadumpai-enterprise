"""
DataDumpAI v1.0
Feedback, support, and legal content.
"""

from __future__ import annotations

import streamlit as st

from config import (
    APP_NAME,
    APP_TAGLINE,
    APP_VERSION,
    COMPANY_LEGAL_NAME,
    COMPANY_NAME,
    COMPANY_WEBSITE,
    FEEDBACK_EMAIL,
    SUPPORT_EMAIL,
)
from services.feedback_service import FeedbackService
from services.feedback_delivery import feedback_mailto, support_mailto
from ui.feedback import loading, show_error, show_success

feedback_service = FeedbackService()


def render_feedback_form() -> None:
    st.markdown("### Send Feedback")
    st.caption(
        f"Messages are saved securely and reviewed by our team at **{FEEDBACK_EMAIL}**. "
        "Set `FEEDBACK_WEBHOOK_URL` in your environment to forward submissions automatically."
    )

    category = st.selectbox(
        "Category",
        [
            "General",
            "Bug report",
            "Feature request",
            "Report quality",
            "Other",
        ],
        label_visibility="collapsed",
    )

    message = st.text_area(
        "Your feedback",
        placeholder="What's on your mind?",
        height=140,
        label_visibility="collapsed",
    )

    email = st.text_input(
        "Email (optional)",
        placeholder="you@company.com — so we can follow up",
    )

    if st.button("Submit feedback", type="primary", use_container_width=True):
        if not message.strip():
            st.warning("Please enter your feedback before submitting.")
            return

        try:
            with loading("Sending feedback..."):
                entry = feedback_service.submit_feedback(
                    message=message,
                    category=category,
                    email=email,
                )

            if entry.get("delivery") == "webhook":
                show_success(
                    "Thank you — your feedback was sent to the DataDumpAI team."
                )
            else:
                show_success(
                    "Thank you — your feedback was recorded. "
                    f"We read every message at {FEEDBACK_EMAIL}."
                )

            st.link_button(
                "Open in email app",
                feedback_mailto(entry),
                use_container_width=True,
            )
        except Exception as exc:
            show_error(exc)


def render_support_form() -> None:
    st.markdown("### Contact Support")
    st.caption(
        f"We typically respond within one business day at **{SUPPORT_EMAIL}**. "
        "Set `SUPPORT_WEBHOOK_URL` or `FEEDBACK_WEBHOOK_URL` to forward requests automatically."
    )

    name = st.text_input("Name")
    email = st.text_input("Email")
    subject = st.text_input("Subject")
    message = st.text_area(
        "Message",
        placeholder="Describe the issue or question...",
        height=140,
    )

    if st.button("Send message", type="primary", use_container_width=True):
        if not name.strip() or not email.strip() or not subject.strip() or not message.strip():
            st.warning("Please fill in all fields.")
            return

        try:
            with loading("Sending message..."):
                entry = feedback_service.submit_support_request(
                    name=name,
                    email=email,
                    subject=subject,
                    message=message,
                )

            if entry.get("delivery") == "webhook":
                show_success(
                    "Your message was sent. Our team will get back to you soon."
                )
            else:
                show_success(
                    "Your message was recorded. "
                    f"Our team will get back to you at {email.strip()}."
                )

            st.link_button(
                "Open in email app",
                support_mailto(entry),
                use_container_width=True,
            )
        except Exception as exc:
            show_error(exc)


def render_about_section() -> None:
    st.markdown("### About")
    st.markdown(
        f"""
**{APP_NAME}**  
{APP_TAGLINE}  
**Version** {APP_VERSION}

**Company:** [{COMPANY_NAME}]({COMPANY_WEBSITE})  
**Legal entity:** {COMPANY_LEGAL_NAME}
"""
    )

    with st.expander("Privacy Policy"):
        st.markdown(
            f"""
**Last updated:** Version {APP_VERSION}

{COMPANY_LEGAL_NAME} ("we", "us") operates {APP_NAME}. This policy explains how we handle your data.

**What we collect**
- Account information (name, email) when you sign up
- Documents you upload to generate reports
- Usage data (reports generated, uploads) to enforce plan limits
- Feedback and support messages you send us

**How we use it**
- To generate AI reports from your documents
- To operate your account and enforce subscription limits
- To improve the product and respond to support requests

**AI processing**
- Document content is sent to our AI provider to generate reports
- We do not sell your documents or report content to third parties

**Data retention**
- You can delete projects, documents, and reports at any time
- Account data is retained while your account is active

**Contact**
- Privacy questions: {SUPPORT_EMAIL}
"""
        )

    with st.expander("Terms of Service"):
        st.markdown(
            f"""
**Last updated:** Version {APP_VERSION}

By using {APP_NAME}, you agree to these terms.

**Service**
- {APP_NAME} converts business documents into professional reports using AI
- Output quality depends on the source documents you provide
- You are responsible for reviewing reports before sharing them

**Your content**
- You retain ownership of documents and reports you create
- You grant us permission to process your content solely to provide the service

**Acceptable use**
- Do not upload unlawful, harmful, or confidential third-party data without permission
- Do not attempt to abuse usage limits or reverse-engineer the service

**Plans & billing**
- Free and Professional plans offer different levels of intelligence — not just higher limits
- Free includes Executive Summary reports and a basic AI assistant
- Professional unlocks premium report types, intelligence dashboards, charts, cross-document analysis, web research, and branded exports
- Paid subscriptions and billing terms will apply when checkout is enabled

**Disclaimer**
- Reports are AI-generated drafts, not professional advice
- We are not liable for decisions made based on generated content

**Contact**
- {SUPPORT_EMAIL}
"""
        )

    st.caption(f"© {COMPANY_LEGAL_NAME}. All rights reserved.")
