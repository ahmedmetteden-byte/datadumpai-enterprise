"""
DataDumpAI v1.0
Document Library — upload, view, replace, and delete.
"""

from __future__ import annotations

import streamlit as st

from application.use_cases.upload_documents import UploadDocumentsUseCase
from services.document_processor import DocumentProcessor
from services.document_service import DocumentService
from ui.feedback import loading, show_empty_state, show_error, show_success
from ui.formatting import file_type_info, format_file_size, format_relative_time
from ui.projects import get_active_workspace, initialize_projects, is_project_pending


def _upload_documents() -> UploadDocumentsUseCase:
    return UploadDocumentsUseCase()


def _document_service() -> DocumentService:
    return DocumentService()

SUPPORTED_TYPES = ["pdf", "docx", "xlsx", "pptx", "txt", "csv"]
PREVIEW_CHAR_LIMIT = 4000
UPLOADER_STATE_KEY = "document_uploader_key"
COMPLETED_UPLOAD_BATCH_KEY = "completed_upload_batch"


def _upload_batch_id(uploaded_files: list) -> str:
    """Identify a file-uploader batch without re-reading file bytes."""

    return "|".join(
        f"{uploaded_file.name}:{getattr(uploaded_file, 'size', 0)}"
        for uploaded_file in uploaded_files
    )


def _init_upload_state() -> None:
    if UPLOADER_STATE_KEY not in st.session_state:
        st.session_state[UPLOADER_STATE_KEY] = 0


def _render_upload_zone() -> list:
    _init_upload_state()

    st.markdown(
        """
<div class="dde-upload-prompt">
<div class="dde-upload-icon">📁</div>
<div class="dde-upload-title">Drag & drop documents here</div>
<div class="dde-upload-sub">or browse files · PDF, Word, Excel, PowerPoint, CSV, Text</div>
</div>
""",
        unsafe_allow_html=True,
    )

    return st.file_uploader(
        "Browse files",
        type=SUPPORTED_TYPES,
        accept_multiple_files=True,
        label_visibility="collapsed",
        key=f"document_uploader_{st.session_state[UPLOADER_STATE_KEY]}",
    )


def _preview_document(project_id: str, filename: str) -> str:
    try:
        text = _document_service().read_document_text(project_id, filename)
    except FileNotFoundError:
        return "_Document not found._"
    text = text.strip()

    if not text:
        return "_No readable text could be extracted from this file._"

    if len(text) > PREVIEW_CHAR_LIMIT:
        return (
            text[:PREVIEW_CHAR_LIMIT]
            + f"\n\n_… truncated ({len(text):,} characters total)._"
        )

    return text


def render_document_upload() -> None:
    """Upload documents into the active Quick Report or project workspace."""

    initialize_projects()

    if is_project_pending():
        return

    workspace = get_active_workspace()

    replace_existing = st.checkbox(
        "Replace files with the same name",
        value=False,
        help="When enabled, uploading a file that already exists will overwrite it.",
    )

    with st.container(border=True):
        uploaded_files = _render_upload_zone()

    if uploaded_files:
        batch_id = _upload_batch_id(uploaded_files)
        already_processed = (
            st.session_state.get(COMPLETED_UPLOAD_BATCH_KEY) == batch_id
        )

        if not already_processed:
            try:
                with loading("Uploading documents..."):
                    _, processed_documents = _upload_documents().execute(
                        project=workspace,
                        uploaded_files=uploaded_files,
                        overwrite=replace_existing,
                    )

                st.session_state[COMPLETED_UPLOAD_BATCH_KEY] = batch_id
                st.session_state[UPLOADER_STATE_KEY] += 1

                if processed_documents:
                    show_success(
                        f"Uploaded {len(processed_documents)} document(s)."
                    )
                st.rerun()
            except Exception as exc:
                show_error(exc)


def render_document_library() -> None:
    """View, preview, and delete documents in the active workspace."""

    initialize_projects()
    workspace = get_active_workspace()

    st.markdown("## My Documents")
    st.caption("Your **Dump Box** — uploaded files for this workspace.")

    if workspace.get("is_pending"):
        st.caption("Create a project in the sidebar to manage project documents.")
        show_empty_state(
            icon="📁",
            title="No project yet",
            message="Select **Project** in the sidebar and create one to get started.",
        )
        return

    if workspace.get("is_quick_report"):
        st.caption(
            "Quick Report files uploaded without a project. "
            "Upload new documents from **AI Workspace** or your **Dump Box** while Quick Report is selected."
        )
    else:
        st.caption(
            f"Files uploaded to **{workspace['name']}**. "
            "Upload new documents from **AI Workspace** or your **Dump Box** while this project is selected."
        )

    documents = _document_service().get_documents(workspace["id"])

    st.markdown("### Uploaded documents")

    if not documents:
        show_empty_state(
            icon="📁",
            title="No documents yet",
            message=(
                "Upload your first file from **AI Workspace** or your **Dump Box** while "
                f"{'Quick Report' if workspace.get('is_quick_report') else workspace['name']} "
                "is selected in the sidebar."
            ),
        )
        return

    for document in documents:
        _render_document_row(workspace["id"], document)


def _render_document_row(project_id: str, document: dict) -> None:
    filename = document["filename"]
    safe_key = filename.replace(" ", "_").replace(".", "_")
    type_label, type_icon, type_dot = file_type_info(filename)
    uploaded_at = format_relative_time(document.get("uploaded_at", ""))
    size_label = format_file_size(document["size"])
    is_previewing = st.session_state.get("viewing_document") == filename

    with st.container(border=True):
        info_col, actions_col = st.columns([5.5, 1.5], gap="small")

        with info_col:
            st.markdown(
                f"""
<div class="dde-document-row">
<div class="dde-document-name">{type_icon} {filename}</div>
<div class="dde-document-meta">
<span class="dde-document-type">{type_dot} {type_label}</span>
<span>{size_label}</span>
<span>Uploaded {uploaded_at}</span>
</div>
</div>
""",
                unsafe_allow_html=True,
            )

        with actions_col:
            st.markdown('<div class="dde-document-actions">', unsafe_allow_html=True)
            preview_col, delete_col = st.columns(2, gap="small")

            with preview_col:
                preview_label = "👁️" if not is_previewing else "✕"
                preview_help = "Hide preview" if is_previewing else "Preview"
                if st.button(
                    preview_label,
                    key=f"view_doc_{safe_key}",
                    help=preview_help,
                    use_container_width=True,
                ):
                    if is_previewing:
                        st.session_state.pop("viewing_document", None)
                    else:
                        st.session_state.viewing_document = filename
                    st.rerun()

            with delete_col:
                if st.button(
                    "🗑️",
                    key=f"delete_doc_{safe_key}",
                    help="Delete",
                    use_container_width=True,
                ):
                    st.session_state.confirm_delete_document = filename

            st.markdown("</div>", unsafe_allow_html=True)

        if is_previewing:
            try:
                preview = _preview_document(project_id, filename)
                st.markdown("#### Preview")
                st.markdown(preview)
            except Exception as exc:
                show_error(exc)

        if st.session_state.get("confirm_delete_document") == filename:
            st.warning(f"Delete **{filename}**? This cannot be undone.")

            yes_col, no_col = st.columns(2)

            with yes_col:
                if st.button(
                    "Yes, delete",
                    key=f"confirm_delete_doc_yes_{safe_key}",
                    type="primary",
                    use_container_width=True,
                ):
                    try:
                        with loading("Deleting document..."):
                            _document_service().delete_document(project_id, filename)

                        st.session_state.pop("confirm_delete_document", None)
                        st.session_state.pop("viewing_document", None)
                        show_success(f"Deleted {filename}.")
                        st.rerun()
                    except Exception as exc:
                        show_error(exc)

            with no_col:
                if st.button(
                    "Cancel",
                    key=f"confirm_delete_doc_no_{safe_key}",
                    use_container_width=True,
                ):
                    st.session_state.pop("confirm_delete_document", None)
                    st.rerun()
