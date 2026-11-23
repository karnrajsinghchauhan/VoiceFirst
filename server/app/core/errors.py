"""Every error the system raises. One tree so callers can catch by family."""

from __future__ import annotations


class AgodaVoiceError(Exception):
    """Root of every typed error. `code` is stable and goes into logs and records."""

    code = "agoda_voice_error"


# Configuration and boot
class ConfigError(AgodaVoiceError):
    code = "config_error"


class ProductionConfigError(ConfigError):
    code = "production_config_error"


class ProviderNotBuiltError(ConfigError):
    """A provider name is valid in config but no implementation is shipped yet."""

    code = "provider_not_built"


# Compliance gates (section 9.2). Each gate raises exactly one family.
class GateError(AgodaVoiceError):
    code = "gate_error"
    gate = "unknown"


class HeldOutError(GateError):
    code = "held_out"
    gate = "holdout"


class JurisdictionNotEnabledError(GateError):
    code = "jurisdiction_not_enabled"
    gate = "jurisdiction"


class KillSwitchEngagedError(GateError):
    code = "kill_switch_engaged"
    gate = "kill_switch"


class ConsentMissingError(GateError):
    code = "consent_missing"
    gate = "consent"


class ConsentExpiredError(GateError):
    code = "consent_expired"
    gate = "consent"


class PreferenceBlockedError(GateError):
    code = "preference_blocked"
    gate = "dnd"


class OptOutLockoutError(GateError):
    code = "opt_out_lockout"
    gate = "opt_out_lock"


class CliNotDeclaredError(GateError):
    code = "cli_not_declared"
    gate = "cli_declared"


class NumberSeriesMismatchError(GateError):
    code = "number_series_mismatch"
    gate = "series"


class CliPausedError(GateError):
    code = "cli_paused"
    gate = "cli_status"


class OutsideCallWindowError(GateError):
    code = "outside_call_window"
    gate = "window"


class AttemptCapError(GateError):
    code = "attempt_cap"
    gate = "cap_cooldown"


class CooldownError(GateError):
    code = "cooldown"
    gate = "cap_cooldown"


# Clearance and dial
class ClearanceForgeryError(AgodaVoiceError):
    """GateClearance constructed outside compliance.evaluate()."""

    code = "clearance_forgery"


class ClearanceInvalidError(AgodaVoiceError):
    """Clearance unknown, expired, already consumed, or killed after minting."""

    code = "clearance_invalid"


# Messaging
class WhatsAppOptInMissingError(AgodaVoiceError):
    code = "whatsapp_opt_in_missing"


class WhatsAppTemplateNotAllowedError(AgodaVoiceError):
    code = "whatsapp_template_not_allowed"


class WhatsAppWindowClosedError(AgodaVoiceError):
    code = "whatsapp_window_closed"


class WhatsAppPausedError(AgodaVoiceError):
    code = "whatsapp_paused"


class FallbackCapError(AgodaVoiceError):
    code = "fallback_cap"


# Agent
class ToolNotAllowedError(AgodaVoiceError):
    code = "tool_not_allowed"


class ReadBackMismatchError(AgodaVoiceError):
    code = "read_back_mismatch"


class PurposeFieldViolationError(AgodaVoiceError):
    code = "purpose_field_violation"


class DarkPatternError(AgodaVoiceError):
    code = "dark_pattern"


class PromptLintError(AgodaVoiceError):
    code = "prompt_lint"


# Providers
class ProviderError(AgodaVoiceError):
    """A provider call failed. Never caught to switch provider (rule 6.1)."""

    code = "provider_error"


class ProviderTimeoutError(ProviderError):
    code = "provider_timeout"


# Domain lookups
class NotFoundError(AgodaVoiceError):
    code = "not_found"


class AuthError(AgodaVoiceError):
    code = "auth_error"


class ForbiddenError(AgodaVoiceError):
    code = "forbidden"


class StateConflictError(AgodaVoiceError):
    code = "state_conflict"


class NotBuiltYetError(NotImplementedError):
    """Phase 2 stubs. Carries the ticket reference."""

    def __init__(self, ticket: str) -> None:
        super().__init__(f"not built yet; see {ticket}")
        self.ticket = ticket
