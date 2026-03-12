from __future__ import annotations

import random

from ai_rpg.core.contracts import ActionCheck, DiceRoll
from ai_rpg.game.time import ability_modifier, success_tier_from_roll


def roll_d20(modifier: int = 0, *, rng: random.Random | None = None) -> ActionCheck:
    roller = rng or random.Random()
    natural = roller.randint(1, 20)
    total = natural + modifier
    dice_roll = DiceRoll(sides=20, rolls=[natural], modifier=modifier, total=total)
    return ActionCheck(
        stat="combat",
        difficulty=10,
        dice_roll=dice_roll,
        modifier=modifier,
        total=total,
    )


def roll_damage(*, bonus: int = 0, rng: random.Random | None = None) -> int:
    roller = rng or random.Random()
    return max(1, roller.randint(1, 6) + bonus)


def initiative_modifier(dexterity: int) -> int:
    return ability_modifier(dexterity)


def attack_outcome(total: int, difficulty: int, natural_roll: int):
    return success_tier_from_roll(total, difficulty, natural_roll)

