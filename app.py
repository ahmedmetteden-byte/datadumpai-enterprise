"""
DataDumpAI v1.0
Application Entry Point
"""

from core.ssl_bootstrap import bootstrap_system_ssl

bootstrap_system_ssl()

import streamlit as st

from config import LAYOUT, PAGE_ICON, PAGE_TITLE, SIDEBAR_STATE, backend_configuration_warnings, validate_production_auth_configuration
from core.runtime_investigation import investigation_enabled, log_startup_configuration
from core.auth import initialize_auth, is_authenticated, is_auth_bootstrap_pending, complete_auth_bootstrap, render_auth_gate
from core.auth_persistence import cookies_are_ready
from core.billing_callbacks import handle_billing_return
from core.navigation import (
    DEFAULT_PAGE,
    PUBLIC_DEFAULT_PAGE,
    PUBLIC_PAGES,
    get_active_page,
    initialize_navigation,
    set_active_page,
)
from core.router import render_page
from core.session import initialize_session
from core.workspace_navigation import initialize_workspace_navigation
from ui.sidebar import render_sidebar
from ui.footer import render_app_footer
from ui.seo import inject_seo_head
from ui.styles import load_styles

st.set_page_config(
    page_title=PAGE_TITLE,
    page_icon=PAGE_ICON,
    layout=LAYOUT,
    initial_sidebar_state=SIDEBAR_STATE,
)

inject_seo_head()

initialize_session()

if not cookies_are_ready():
    st.info("Loading…")
    st.stop()

initialize_auth()

initialize_navigation()
initialize_workspace_navigation()
load_styles()

if investigation_enabled():
    for fatal in log_startup_configuration():
        st.error(fatal)

for warning in backend_configuration_warnings():
    st.warning(warning)

for fatal in validate_production_auth_configuration():
    st.error(fatal)
    st.stop()

if not is_authenticated():
    page = get_active_page()
    if page == "workspace":
        set_active_page(PUBLIC_DEFAULT_PAGE)
        page = PUBLIC_DEFAULT_PAGE

    if page == "landing":
        from ui.landing.page import render_landing_page

        render_landing_page()
        render_app_footer()
        st.stop()

    if page == "auth":
        render_auth_gate()
        render_app_footer()
        st.stop()

    set_active_page(PUBLIC_DEFAULT_PAGE)
    from ui.landing.page import render_landing_page

    render_landing_page()
    render_app_footer()
    st.stop()

handle_billing_return()

if is_auth_bootstrap_pending():
    with st.spinner("Loading workspace…"):
        complete_auth_bootstrap()
    st.rerun()

if get_active_page() in PUBLIC_PAGES:
    set_active_page(DEFAULT_PAGE)

render_sidebar()
render_page()
render_app_footer()
