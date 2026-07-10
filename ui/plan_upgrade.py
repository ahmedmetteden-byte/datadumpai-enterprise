"""
Upgrade prompts for Professional plan features.
"""

from __future__ import annotations

import streamlit as st

from config import PLANS

FEATURE_UPGRADE_COPY = {
    "report_types": (
        "Premium report types — Board Report, Risk Assessment, Market Intelligence, "
        "and more — are available on the **Professional** plan."
    ),
    "intelligence_reports": (
        "Executive Intelligence outputs — health scores, confidence ratings, "
        "priority heat maps, and strategic recommendations — are part of "
        "the **Professional** experience."
    ),
    "professional_charts": (
        "Presentation-ready charts are generated automatically on the "
        "**Professional** plan."
    ),
    "cross_document_intelligence": (
        "Cross-document intelligence — patterns like \"this issue appeared in "
        "7 of the last 10 meetings\" — requires **Professional**."
    ),
    "web_research": (
        "Live internet research, combined with your uploaded documents, is a "
        "**Professional** feature."
    ),
    "deep_copilot": (
        "Deep-context AI — contradictions, period comparisons, strategic actions, "
        "and cited evidence — is available on **Professional**."
    ),
    "professional_exports": (
        "Word, PowerPoint, board packs, and branded exports are available on "
        "**Professional**. Free includes PDF with DataDumpAI branding."
    ),
    "projects": (
        "The Free plan supports up to 3 projects. Upgrade to **Professional** "
        "for unlimited projects."
    ),
}


def render_upgrade_prompt(feature: str) -> None:
    """Show a concise upgrade message for a gated feature."""

    message = FEATURE_UPGRADE_COPY.get(
        feature,
        "This capability is available on the **Professional** plan.",
    )
    st.info(f"{message} See **Settings → Plan & Usage** to compare plans.")


def render_professional_cta() -> None:
    """Show a call-to-action for upgrading."""

    label = PLANS["professional"]["label"]
    st.markdown(
        f"**Upgrade to {label}** — move from an assistant to an analyst. "
        "Compare plans in **Settings → Plan & Usage**."
    )
