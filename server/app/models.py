"""Imports every package's models so Base.metadata knows all tables. Add one line per package."""

from app.campaigns import models as campaigns_models  # noqa: F401
from app.compliance import models as compliance_models  # noqa: F401
from app.core import audit as core_audit  # noqa: F401
from app.handoff import models as handoff_models  # noqa: F401
from app.incidents import models as incidents_models  # noqa: F401
from app.messaging import models as messaging_models  # noqa: F401
from app.postcall import models as postcall_models  # noqa: F401
from app.qa import scorecard as qa_scorecard  # noqa: F401
from app.rights import models as rights_models  # noqa: F401
