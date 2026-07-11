"""
Use the OS certificate store for HTTPS on Windows and other environments
where Python's bundled CA bundle is incomplete.
"""

from __future__ import annotations


def bootstrap_system_ssl() -> None:
    try:
        from pip_system_certs.wrapt_requests import inject_truststore

        inject_truststore()
    except Exception:
        pass
