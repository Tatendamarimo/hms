from .context import Actor, reset_actor, set_actor


def _client_ip(request) -> str | None:
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


class AuditContextMiddleware:
    """Binds the authenticated user and client IP to the audit contextvar for
    the duration of the request, so model-level audit hooks can attribute
    every mutation without access to the request."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, "user", None)
        token = set_actor(
            Actor(
                user_id=user.pk if user is not None and user.is_authenticated else None,
                ip_address=_client_ip(request),
            )
        )
        try:
            return self.get_response(request)
        finally:
            reset_actor(token)
