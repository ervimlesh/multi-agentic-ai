"""Declarative base for all SQLAlchemy ORM models (the Model layer)."""
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Shared declarative base. All models inherit from this."""

    pass
