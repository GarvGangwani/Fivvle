"""FastAPI dependency for the ResearchDispatcher (ADR 0009).

Reads the dispatcher from app.state (set once during lifespan startup by
main.py).  Route handlers use this via Depends():

    @router.post("/{experiment_id}/confirm")
    async def confirm_research(
        ...
        dispatcher: ResearchDispatcher = Depends(get_dispatcher_dep),
    ):
        await dispatcher.dispatch(experiment_id)

Tests override this dependency via app.dependency_overrides to inject a
FakeDispatcher without touching app.state:

    app.dependency_overrides[get_dispatcher_dep] = lambda: FakeDispatcher()
"""

from __future__ import annotations

from fastapi import Request

from app.dispatchers.protocol import ResearchDispatcher


async def get_dispatcher_dep(request: Request) -> ResearchDispatcher:
    """Return the dispatcher stored on app.state by the lifespan handler."""
    return request.app.state.dispatcher  # type: ignore[no-any-return]
