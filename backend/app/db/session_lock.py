"""Per-AsyncSession asyncio.Lock registry.

SQLAlchemy AsyncSession is NOT safe for concurrent use by multiple coroutines.
This module provides a per-session asyncio.Lock so that code paths which must
add + flush rows concurrently (e.g. integration wrappers logging API calls
from inside asyncio.gather) can serialize their session mutations.

Locks are stored in a WeakKeyDictionary so they are garbage-collected together
with the sessions they guard. A module-level threading.Lock closes the
TOCTOU window between dict lookup and insert when two coroutines request the
lock for the same session at the same instant.
"""

from __future__ import annotations

import asyncio
import threading
from weakref import WeakKeyDictionary

from sqlalchemy.ext.asyncio import AsyncSession

_locks: WeakKeyDictionary[AsyncSession, asyncio.Lock] = WeakKeyDictionary()
_registry_guard = threading.Lock()


def lock_for(session: AsyncSession) -> asyncio.Lock:
    """Return (or create) the asyncio.Lock for *session*.

    The lock is cached in a WeakKeyDictionary keyed on the session, so the
    same session always returns the same lock and locks are auto-released
    when their sessions are garbage-collected.
    """
    existing = _locks.get(session)
    if existing is not None:
        return existing
    with _registry_guard:
        # Re-check inside the guard to avoid double-create race.
        existing = _locks.get(session)
        if existing is not None:
            return existing
        new_lock = asyncio.Lock()
        _locks[session] = new_lock
        return new_lock
