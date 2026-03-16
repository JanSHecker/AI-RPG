from __future__ import annotations

from ai_rpg.core.contracts import ActionAttribute, ActionType, SuccessTier


SKILL_BASE_ABILITIES = {
    ActionAttribute.DIPLOMACY: ActionAttribute.CHARISMA,
    ActionAttribute.SURVIVAL: ActionAttribute.WISDOM,
    ActionAttribute.STEALTH: ActionAttribute.DEXTERITY,
    ActionAttribute.MELEE: ActionAttribute.STRENGTH,
}


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


def resolve_action_modifier(stats, relevant_attribute: ActionAttribute) -> tuple[str, str | None, int]:
    if relevant_attribute in SKILL_BASE_ABILITIES:
        base_ability = SKILL_BASE_ABILITIES[relevant_attribute]
        ability_score = getattr(stats, base_ability.value, 10)
        skill_bonus = getattr(stats, relevant_attribute.value, 0)
        return base_ability.value, relevant_attribute.value, ability_modifier(ability_score) + skill_bonus
    ability_score = getattr(stats, relevant_attribute.value, 10)
    return relevant_attribute.value, None, ability_modifier(ability_score)


def calculate_outcome_chances(difficulty: int, modifier: int) -> tuple[float, float]:
    avoid_failure = 0
    clean_success = 0
    for roll in range(1, 21):
        total = roll + modifier
        tier = success_tier_from_roll(total, difficulty, roll)
        if tier in {SuccessTier.MIXED, SuccessTier.SUCCESS, SuccessTier.CRITICAL_SUCCESS}:
            avoid_failure += 1
        if tier in {SuccessTier.SUCCESS, SuccessTier.CRITICAL_SUCCESS}:
            clean_success += 1
    return round((avoid_failure / 20) * 100, 1), round((clean_success / 20) * 100, 1)
