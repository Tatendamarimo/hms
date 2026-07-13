"""Per-request actor context.

The audit signal handlers fire deep inside model saves where no request object
exists. AuditContextMiddleware stores the acting user and request metadata in a
contextvar so audit entries can always answer "who did this, from where".
Celery tasks and management commands may set the actor explicitly via
`set_actor` / `actor_context`.
"""

from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field


@dataclass
class Actor:
    user_id: int | None = None
    ip_address: str | None = None
    extra: dict = field(default_factory=dict)


_actor: ContextVar[Actor | None] = ContextVar("audit_actor", default=None)


def get_actor() -> Actor | None:
    return _actor.get()


def set_actor(actor: Actor | None):
    return _actor.set(actor)


def reset_actor(token):
    _actor.reset(token)


@contextmanager
def actor_context(actor: Actor | None):
    token = _actor.set(actor)
    try:
        yield
    finally:
        _actor.reset(token)
