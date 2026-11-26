"""The eleven gates (9.2), in order. Each is pure: it reads a GateContext and either returns or raises.

`GATES` is the single ordered list; evaluate() and the tests both use it.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import timedelta

from app.compliance.context import ConsentView, GateContext
from app.compliance.holdout import is_held_out
from app.compliance.jurisdiction import policy_for
from app.core.errors import (
    AttemptCapError,
    CliNotDeclaredError,
    CliPausedError,
    ConsentExpiredError,
    ConsentMissingError,
    CooldownError,
    HeldOutError,
    KillSwitchEngagedError,
    NumberSeriesMismatchError,
    OptOutLockoutError,
    OutsideCallWindowError,
    PreferenceBlockedError,
)

Gate = Callable[[GateContext], None]


def gate_holdout(ctx: GateContext) -> None:
    if is_held_out(ctx.holdout.experiment_salt, ctx.event.booking_id, ctx.holdout.percent):
        raise HeldOutError("booking is in the no-call holdout")


def gate_jurisdiction(ctx: GateContext) -> None:
    phone = ctx.event.customer.phone_e164
    policy_for(phone, ctx.compliance.enabled_country_codes).validate_number(phone)


def gate_kill_switch(ctx: GateContext) -> None:
    if ctx.kill_switch_engaged:
        raise KillSwitchEngagedError("kill switch engaged")
    if ctx.campaigns_paused:
        raise KillSwitchEngagedError("all campaigns paused by the complaint guardrail")


def _consent_is_live(consent: ConsentView, ctx: GateContext) -> bool:
    if consent.revoked_at is not None or consent.purpose != ctx.purpose:
        return False
    if consent.basis == "transaction":
        # The transaction relationship lasts while this booking is live and unpaid or upcoming.
        return consent.booking_id == ctx.event.booking_id and ctx.event.status != "cancelled"
    return consent.expires_at is not None and ctx.now < consent.expires_at


def live_consents(ctx: GateContext) -> tuple[ConsentView, ...]:
    return tuple(c for c in ctx.consents if _consent_is_live(c, ctx))


def gate_consent(ctx: GateContext) -> None:
    relevant = [c for c in ctx.consents if c.purpose == ctx.purpose]
    if not relevant:
        raise ConsentMissingError(f"no consent record for {ctx.purpose}")
    if not live_consents(ctx):
        raise ConsentExpiredError(f"every consent record for {ctx.purpose} is expired or revoked")


def gate_dnd(ctx: GateContext) -> None:
    if ctx.preference == "none":
        return
    if ctx.category == "promotional":
        raise PreferenceBlockedError("DND blocks promotional traffic")
    if ctx.purpose == "J2":
        raise PreferenceBlockedError("house rule: any DND flag blocks J2")
    # J1 under DND: only on a transaction basis, and only with counsel's recorded sign-off.
    signed_off = ctx.compliance.dnd_j1_transaction_signoff_ref is not None
    on_transaction = any(c.basis == "transaction" for c in live_consents(ctx))
    if not (signed_off and on_transaction):
        raise PreferenceBlockedError("DND blocks J1 without transaction basis and legal sign-off")


def gate_opt_out_lock(ctx: GateContext) -> None:
    if ctx.opted_out_at is None:
        return
    # Only the customer's own explicit consent, given after the opt-out, reopens the number.
    reconsented = any(
        c.basis == "explicit" and c.obtained_at > ctx.opted_out_at for c in live_consents(ctx)
    )
    if not reconsented:
        raise OptOutLockoutError("number opted out")


def gate_cli_declared(ctx: GateContext) -> None:
    cli = ctx.cli
    if cli is None:
        raise CliNotDeclaredError("CLI not in registry")
    if not (cli.a2p_declared and cli.declaration_ref and cli.dlt_recorded_at and cli.oap):
        raise CliNotDeclaredError(f"CLI {cli.cli_e164} lacks an A2P declaration on DLT")


def gate_series(ctx: GateContext) -> None:
    assert ctx.cli is not None  # gate_cli_declared runs first; evaluate() stops on its failure
    allowed = (
        ctx.compliance.promotional_series
        if ctx.category == "promotional"
        else ctx.compliance.service_series
    )
    if ctx.cli.series not in allowed:
        raise NumberSeriesMismatchError(f"series {ctx.cli.series} not allowed for {ctx.category}")
    cli_is_promo = ctx.cli.purpose == "promotional"
    if cli_is_promo != (ctx.category == "promotional"):
        raise NumberSeriesMismatchError(f"CLI purpose {ctx.cli.purpose} != call {ctx.category}")


def gate_cli_status(ctx: GateContext) -> None:
    assert ctx.cli is not None
    if ctx.cli.status != "active":
        raise CliPausedError(f"CLI is {ctx.cli.status}")


def gate_window(ctx: GateContext) -> None:
    policy = policy_for(ctx.event.customer.phone_e164, ctx.compliance.enabled_country_codes)
    local = ctx.now.astimezone(policy.timezone).time()
    window = ctx.compliance.call_window
    if not (window.start <= local < window.end):
        raise OutsideCallWindowError(f"recipient local time {local:%H:%M:%S} outside window")


def gate_cap_cooldown(ctx: GateContext) -> None:
    if ctx.attempts_for_event >= ctx.compliance.max_attempts_per_event:
        raise AttemptCapError(f"{ctx.attempts_for_event} attempts already made for this event")
    last = ctx.last_dial_at_for_number
    if last is not None and ctx.now - last < timedelta(hours=ctx.compliance.cooldown_hours):
        raise CooldownError("number dialled within the cooldown period")


GATES: tuple[tuple[str, Gate], ...] = (
    ("holdout", gate_holdout),
    ("jurisdiction", gate_jurisdiction),
    ("kill_switch", gate_kill_switch),
    ("consent", gate_consent),
    ("dnd", gate_dnd),
    ("opt_out_lock", gate_opt_out_lock),
    ("cli_declared", gate_cli_declared),
    ("series", gate_series),
    ("cli_status", gate_cli_status),
    ("window", gate_window),
    ("cap_cooldown", gate_cap_cooldown),
)
