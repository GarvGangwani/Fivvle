"""
SQLAlchemy 2.0 declarative base class.

All models (added in build step 2B) inherit from ``Base``.
Using DeclarativeBase — the SQLAlchemy 2.0 class-based idiom that
replaces the older ``declarative_base()`` factory function.
"""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass
