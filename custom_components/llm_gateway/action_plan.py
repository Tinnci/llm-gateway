"""Typed, bounded Home Assistant action plans for compound voice turns."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Literal, Protocol

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

PolicyStage = Literal[
    "before_plan",
    "before_execute",
    "after_execute",
    "before_playback",
]
PlanStatus = Literal[
    "executed", "dry_run", "condition_false", "partial", "blocked", "error"
]

POLICY_STAGES: tuple[PolicyStage, ...] = (
    "before_plan",
    "before_execute",
    "after_execute",
    "before_playback",
)
MAX_PLAN_STEPS = 8
ALLOWED_SERVICES = {
    "climate": {"set_temperature", "turn_off", "turn_on"},
    "fan": {"turn_off", "turn_on", "set_percentage"},
    "light": {"turn_off", "turn_on"},
    "media_player": {"turn_off", "turn_on", "volume_set", "volume_mute"},
    "notify": {"send_message"},
    "switch": {"turn_off", "turn_on"},
}


@dataclass(frozen=True, slots=True)
class PlanRead:
    """One named HA state read."""

    alias: str
    entity_id: str


@dataclass(frozen=True, slots=True)
class PlanCondition:
    """One equality predicate over a named read."""

    read: str
    equals: str


@dataclass(frozen=True, slots=True)
class PlanAction:
    """One allowlisted HA service call."""

    domain: str
    service: str
    entity_id: str = ""
    data: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "domain": self.domain,
            "service": self.service,
            "entity_id": self.entity_id,
            "data": dict(self.data),
        }


@dataclass(frozen=True, slots=True)
class ActionPlan:
    """Bounded declarative reads, conditions and actions."""

    reads: tuple[PlanRead, ...] = ()
    conditions: tuple[PlanCondition, ...] = ()
    actions: tuple[PlanAction, ...] = ()
    success_speech: str = "操作已完成。"
    condition_false_speech: str = "条件不满足，没有执行操作。"

    @classmethod
    def from_payload(cls, payload: object) -> ActionPlan:
        if not isinstance(payload, dict):
            raise TypeError("action plan must be an object")
        reads = tuple(
            PlanRead(str(item.get("alias") or ""), str(item.get("entity_id") or ""))
            for item in payload.get("reads", ())
            if isinstance(item, dict)
        )
        conditions = tuple(
            PlanCondition(str(item.get("read") or ""), str(item.get("equals") or ""))
            for item in payload.get("conditions", ())
            if isinstance(item, dict)
        )
        actions = tuple(
            PlanAction(
                domain=str(item.get("domain") or ""),
                service=str(item.get("service") or ""),
                entity_id=str(item.get("entity_id") or ""),
                data=dict(item.get("data") or {})
                if isinstance(item.get("data"), dict)
                else {},
            )
            for item in payload.get("actions", ())
            if isinstance(item, dict)
        )
        return cls(
            reads=reads,
            conditions=conditions,
            actions=actions,
            success_speech=str(payload.get("success_speech") or "操作已完成。")[:200],
            condition_false_speech=str(
                payload.get("condition_false_speech") or "条件不满足，没有执行操作。"
            )[:200],
        )


@dataclass(frozen=True, slots=True)
class PlanPolicyDecision:
    """Closed policy result for one finite pipeline stage."""

    allowed: bool
    policy: str
    stage: PolicyStage
    reason: str = "allowed"

    def as_dict(self) -> dict[str, Any]:
        return {
            "allowed": self.allowed,
            "policy": self.policy,
            "stage": self.stage,
            "reason": self.reason,
        }


class ActionPlanPolicy(Protocol):
    """Adapter evaluated at each fixed plan stage."""

    name: str

    def evaluate(self, stage: PolicyStage, plan: ActionPlan) -> PlanPolicyDecision:
        """Return a closed allow/deny decision."""


class PlanShapePolicy:
    """Reject empty, oversized or internally inconsistent plans."""

    name = "plan_shape"

    def evaluate(self, stage: PolicyStage, plan: ActionPlan) -> PlanPolicyDecision:
        reason = "allowed"
        if stage == "before_plan":
            aliases = {item.alias for item in plan.reads if item.alias}
            if not plan.actions:
                reason = "no_actions"
            elif len(plan.reads) + len(plan.actions) > MAX_PLAN_STEPS:
                reason = "step_limit_exceeded"
            elif any(not item.alias or not item.entity_id for item in plan.reads):
                reason = "invalid_read"
            elif any(item.read not in aliases for item in plan.conditions):
                reason = "unknown_condition_read"
        return PlanPolicyDecision(reason == "allowed", self.name, stage, reason)


class HomeAssistantSafetyPolicy:
    """Allow only low-risk domains, services and explicit entity targets."""

    name = "ha_safety"

    def evaluate(self, stage: PolicyStage, plan: ActionPlan) -> PlanPolicyDecision:
        reason = "allowed"
        if stage == "before_plan":
            for action in plan.actions:
                if action.service not in ALLOWED_SERVICES.get(action.domain, set()):
                    reason = "service_not_allowed"
                    break
                if not action.entity_id or not action.entity_id.startswith(
                    f"{action.domain}."
                ):
                    reason = "explicit_target_required"
                    break
        return PlanPolicyDecision(reason == "allowed", self.name, stage, reason)


@dataclass(frozen=True, slots=True)
class ActionPlanResult:
    """Execution outcome with complete per-stage and per-action evidence."""

    status: PlanStatus
    speech: str
    actions: tuple[dict[str, Any], ...]
    policy: tuple[dict[str, Any], ...]
    reads: dict[str, str] = field(default_factory=dict)
    failed_actions: tuple[dict[str, Any], ...] = ()
    reason: str = ""


class ActionPlanExecutor:
    """Validate and execute a declarative plan through finite policy stages."""

    def __init__(self, policies: tuple[ActionPlanPolicy, ...] | None = None) -> None:
        self._policies = policies or (PlanShapePolicy(), HomeAssistantSafetyPolicy())

    async def async_execute(
        self, hass: HomeAssistant, plan: ActionPlan, *, dry_run: bool = False
    ) -> ActionPlanResult:
        evidence: list[dict[str, Any]] = []
        blocked = self._evaluate("before_plan", plan, evidence)
        if blocked:
            return ActionPlanResult(
                "blocked",
                "这个复合操作不符合安全策略。",
                (),
                tuple(evidence),
                reason=blocked,
            )
        reads = {
            item.alias: (
                state.state if (state := hass.states.get(item.entity_id)) else ""
            )
            for item in plan.reads
        }
        if any(reads.get(item.read) != item.equals for item in plan.conditions):
            return ActionPlanResult(
                "condition_false",
                plan.condition_false_speech,
                (),
                tuple(evidence),
                reads=reads,
            )
        blocked = self._evaluate("before_execute", plan, evidence)
        if blocked:
            return ActionPlanResult(
                "blocked", "这个复合操作不符合安全策略。", (), tuple(evidence),
                reads=reads, reason=blocked
            )
        proposed = tuple(item.as_dict() for item in plan.actions)
        if dry_run:
            self._evaluate("after_execute", plan, evidence)
            self._evaluate("before_playback", plan, evidence)
            return ActionPlanResult(
                "dry_run", plan.success_speech, proposed, tuple(evidence), reads=reads
            )
        completed: list[dict[str, Any]] = []
        failed: list[dict[str, Any]] = []
        for action in plan.actions:
            data = dict(action.data)
            if action.entity_id:
                data["entity_id"] = action.entity_id
            try:
                await hass.services.async_call(
                    action.domain, action.service, data, blocking=True
                )
            except Exception as err:  # noqa: BLE001 - HA integrations vary
                failed.append(action.as_dict() | {"reason": type(err).__name__})
            else:
                completed.append(action.as_dict())
        self._evaluate("after_execute", plan, evidence)
        self._evaluate("before_playback", plan, evidence)
        status: PlanStatus = (
            "partial" if failed and completed else "error" if failed else "executed"
        )
        speech = (
            f"已完成{len(completed)}项操作，{len(failed)}项失败。"
            if failed
            else plan.success_speech
        )
        return ActionPlanResult(
            status,
            speech,
            tuple(completed),
            tuple(evidence),
            reads=reads,
            failed_actions=tuple(failed),
            reason=(
                "partial_failure"
                if failed and completed
                else "execution_failed"
                if failed
                else ""
            ),
        )

    def _evaluate(
        self,
        stage: PolicyStage,
        plan: ActionPlan,
        evidence: list[dict[str, Any]],
    ) -> str:
        for policy in self._policies:
            decision = policy.evaluate(stage, plan)
            evidence.append(decision.as_dict())
            if not decision.allowed:
                return decision.reason
        return ""


async def async_execute_action_plan(
    hass: HomeAssistant, plan: ActionPlan
) -> ActionPlanResult:
    """Default action-plan adapter used by the turn-loop runtime."""
    return await ActionPlanExecutor().async_execute(hass, plan)
