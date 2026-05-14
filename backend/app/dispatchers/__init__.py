"""Research dispatcher package (ADR 0009).

Public surface — use the factory and dependency, not the implementations directly:

    from app.dispatchers.factory import get_dispatcher
    from app.dispatchers.dependencies import get_dispatcher_dep
"""
