from __future__ import annotations

from ai_rpg.core.contracts import ActionType, SuccessTier


def ability_modifier(score: int) -> int:
    return (score - 10) // 2


def success_tier_from_roll(total: int, difficulty: int, natural_roll: int) -> SuccessTier:
    if natural_roll == 20:
        return SuccessTier.CRITICAL_SUCCESS
    if natural_roll == 1:
        return SuccessTier.CRITICAL_FAILURE
    margin = total - difficulty
    if margin >= 5:
        return SuccessTier.SUCCESS
    if margin >= 0:
        return SuccessTier.MIXED
    if margin <= -5:
        return SuccessTier.FAILURE
    return SuccessTier.FAILURE


def action_time_cost(action_type: ActionType, *, travel_minutes: int | None = None) -> int:
    if action_type == ActionType.MOVE and travel_minutes is not None:
        return travel_minutes
    if action_type == ActionType.TALK:
        return 5
    if action_type == ActionType.ATTACK:
        return 1
    if action_type == ActionType.WAIT:
        return 10
    return 0

