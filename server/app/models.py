"""Imports every package's models so Base.metadata knows all tables. Add one line per package."""

from app.compliance import models as compliance_models  # noqa: F401
from app.core import audit as core_audit  # noqa: F401
