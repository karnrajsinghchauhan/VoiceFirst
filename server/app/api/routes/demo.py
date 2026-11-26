"""The private /demo: scenario runs and the kill switch, behind a passcode header (S10)."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Header
from pydantic import BaseModel, ConfigDict

from app.api.deps import Deps
from app.api.ports import DemoRun, DemoScenario, KillSwitchResult

router = APIRouter(prefix="/demo", tags=["demo"])


class RunIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    scenario: DemoScenario


def _passcode(deps: Deps, x_demo_passcode: Annotated[str, Header()]) -> None:
    deps.demo.check_passcode(x_demo_passcode)


Gate = Annotated[None, Depends(_passcode)]


@router.post("/run")
def run(body: RunIn, deps: Deps, _gate: Gate) -> DemoRun:
    return deps.demo.run(body.scenario)


@router.post("/killswitch")
def kill(deps: Deps, _gate: Gate) -> KillSwitchResult:
    return deps.demo.kill()


@router.post("/killswitch/release")
def release(deps: Deps, _gate: Gate) -> KillSwitchResult:
    return deps.demo.release()
