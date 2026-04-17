from __future__ import annotations
import logging
from typing import Any

logger = logging.getLogger(__name__)


def log_action(
    action: str,
    model_name: str = '',
    object_id: str = '',
    object_repr: str = '',
    changes: dict | None = None,
    user=None,
    request=None,
    extra: dict | None = None,
) -> None:
    """Helper to create an AuditLog entry safely (never raises)."""
    try:
        from .models import AuditLog
        ip = None
        ua = ''
        if request:
            ip = _get_client_ip(request)
            ua = request.META.get('HTTP_USER_AGENT', '')[:500]
            if user is None and request.user.is_authenticated:
                user = request.user

        AuditLog.objects.create(
            action=action,
            model_name=model_name,
            object_id=str(object_id),
            object_repr=object_repr[:500],
            changes=changes or {},
            user=user,
            ip_address=ip,
            user_agent=ua,
            extra=extra or {},
        )
    except Exception:
        logger.exception('Failed to write audit log')


def _get_client_ip(request) -> str | None:
    x_forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded:
        return x_forwarded.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')
