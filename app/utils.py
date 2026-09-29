"""
Small shared helpers used across blueprints: role-based access control
decorators and a helper to safely read the client's IP address for audit
logging.
"""

from functools import wraps
from flask import abort, request
from flask_login import current_user


def roles_required(*allowed_roles):
    """
    Restrict a view to users whose `role` is in `allowed_roles`.

    Must be combined with @login_required (put @login_required first) so
    that anonymous users are sent to the login page rather than getting a
    raw 403.
    """

    def decorator(view_func):
        @wraps(view_func)
        def wrapped(*args, **kwargs):
            if not current_user.is_authenticated:
                abort(403)
            if current_user.role not in allowed_roles:
                abort(403)
            return view_func(*args, **kwargs)

        return wrapped

    return decorator


def get_client_ip():
    """Best-effort client IP, respecting a single trusted proxy hop."""
    forwarded = request.headers.get("X-Forwarded-For", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.remote_addr or "unknown"
