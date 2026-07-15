"""
Use the OS certificate store for HTTPS on Windows and other environments
where Python's bundled CA bundle is incomplete.

httpx (used by the Supabase client) and the stdlib ssl module must both
trust the system CAs; otherwise auth and storage calls fail with
CERTIFICATE_VERIFY_FAILED and surface as generic "Sign up failed" errors.
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def bootstrap_system_ssl() -> None:
    try:
        import truststore

        truststore.inject_into_ssl()
        return
    except Exception:
        logger.debug("truststore.inject_into_ssl failed", exc_info=True)

    try:
        from pip_system_certs.wrapt_requests import inject_truststore

        inject_truststore()
    except Exception:
        logger.debug("pip_system_certs inject_truststore failed", exc_info=True)
