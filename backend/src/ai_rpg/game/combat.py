from __future__ import annotations

import random

from ai_rpg.core.contracts import (
    EncounterState,
    EventType,
    PatchOperation,
    PatchOperationKind,
    StatePatch,
    SuccessTier,
    TimeScale,
    TurnIntent,
    TurnResolution,
)
from ai_rpg.db.combat_repo import CombatRepository
from ai_rpg.db.repositories import WorldRepository, new_id
from ai_rpg.game.combat_rules import attack_outcome, initiative_modifier, roll_damage, roll_d20
from ai_rpg.game.time import ability_modifier


class SimpleCombatEngine:
    def __init__(
        self,
        world_repository: WorldRepository,
        combat_repository: CombatRepository,
        *,
        rng: random.Random | None = None,
    ):
        self.world_repository = world_repository
        self.combat_repository = combat_repository
        self.rng = rng or random.Random()

    def start_encounter(self, save_id: str, location_entity_id: str, actor_ids: list[str]) -> str:
        encounter_id = self.combat_repository.create_encounter(save_id, location_entity_id, actor_ids)
        combatants = self.combat_repository.get_combatants(encounter_id)
        order: list[tuple[str, int]] = []
        for combatant in combatants:
            stats = self.world_repository.get_entity_stats(combatant.entity_id)
            dexterity = stats.dexterity if stats is not None else 10
            modifier = initiative_modifier(dexterity)
            check = roll_d20(modifier=modifier, rng=self.rng)
            order.append((combatant.id, check.total))
        order.sort(key=lambda item: item[1], reverse=True)
        self.combat_repository.set_initiative(encounter_id, order)
        return encounter_id

    def resolve_turn(self, encounter_id: str, combatant_id: str, intent: TurnIntent) -> TurnResolution:
        combatants = self.combat_repository.get_combatants(encounter_id)
        acting = next((combatant for combatant in combatants if combatant.id == combatant_id), None)
        if acting is None:
            raise ValueError(f"Unknown combatant {combatant_id}")
        attacker = self.world_repository.get_entity(acting.entity_id)
        if attacker is None:
            raise ValueError(f"Unknown entity for combatant {combatant_id}")

        target_combatant = next(
            (
                combatant
                for combatant in combatants
                if combatant.entity_id == intent.target_id and combatant.id != combatant_id and not combatant.is_defeated
            ),
            None,
        )
        if target_combatant is None:
            target_combatant = next(
                (
                    combatant
                    for combatant in combatants
                    if combatant.id != combatant_id and not combatant.is_defeated
                ),
                None,
            )
        if target_combatant is None:
            self.combat_repository.complete_encounter(encounter_id, EncounterState.WON)
            return TurnResolution(
                allowed=True,
                success_tier=SuccessTier.SUCCESS,
                narration="The fight is already over.",
                patch=StatePatch.empty(self._save_id_for(encounter_id)),
                time_advance_minutes=0,
                time_scale=TimeScale.COMBAT,
            )

        attacker_stats = self.world_repository.get_entity_stats(acting.entity_id)
        target_entity = self.world_repository.get_entity(target_combatant.entity_id)
        target_stats = self.world_repository.get_entity_stats(target_combatant.entity_id)
        if target_entity is None or target_stats is None:
            raise ValueError("Combat target is missing stats.")

        modifier = ability_modifier(attacker_stats.strength if attacker_stats else 10) + (
            attacker_stats.melee if attacker_stats else 0
        )
        check = roll_d20(modifier=modifier, rng=self.rng)
        difficulty = 10 + ability_modifier(target_stats.dexterity)
        success_tier = attack_outcome(check.total, difficulty, check.dice_roll.rolls[0])
        damage = 0
        if success_tier in {SuccessTier.SUCCESS, SuccessTier.MIXED, SuccessTier.CRITICAL_SUCCESS}:
            bonus = ability_modifier(attacker_stats.strength if attacker_stats else 10)
            damage = roll_damage(bonus=bonus, rng=self.rng)
            if success_tier == SuccessTier.CRITICAL_SUCCESS:
                damage += 4

        patch = StatePatch(
            save_id=self._save_id_for(encounter_id),
            operations=[
                PatchOperation(
                    kind=PatchOperationKind.CREATE_EVENT,
                    data={
                        "event_id": new_id("event"),
                        "event_type": EventType.COMBAT.value,
                        "title": "Combat action",
                        "description": f"{attacker.name} strikes at {target_entity.name}.",
                        "actor_entity_id": attacker.id,
                        "target_entity_id": target_entity.id,
                        "location_entity_id": attacker.location_entity_id,
                    },
                ),
                PatchOperation(
                    kind=PatchOperationKind.ADVANCE_TIME,
                    data={"minutes": 1},
                ),
            ],
        )

        narration = f"{attacker.name} lashes out at {target_entity.name}."
        if damage > 0:
            patch.operations.append(
                PatchOperation(
                    kind=PatchOperationKind.DAMAGE_ENTITY,
                    target_id=target_entity.id,
                    data={"amount": damage},
                )
            )
            narration = f"{attacker.name} hits {target_entity.name} for {damage} damage."
            remaining_hp = max(0, target_stats.hp - damage)
            if remaining_hp == 0:
                self.combat_repository.mark_defeated(encounter_id, target_entity.id)
                narration = f"{attacker.name} defeats {target_entity.name}."
        else:
            narration = f"{attacker.name} misses {target_entity.name}."

        self.combat_repository.advance_turn(encounter_id)
        self._run_enemy_rounds(encounter_id)
        encounter = self.combat_repository.get_encounter(encounter_id)
        enter_combat = encounter is not None and encounter.state == EncounterState.ACTIVE
        if not enter_combat and encounter is not None and encounter.state == EncounterState.ACTIVE:
            self.combat_repository.complete_encounter(encounter_id, EncounterState.WON)
            enter_combat = False

        if encounter is not None and encounter.state != EncounterState.ACTIVE:
            narration += " The skirmish ends."

        return TurnResolution(
            allowed=True,
            success_tier=success_tier,
            narration=narration,
            action_check=check,
            patch=patch,
            time_advance_minutes=1,
            time_scale=TimeScale.COMBAT,
            enter_combat=enter_combat,
            encounter_id=encounter_id if enter_combat else None,
        )

    def engage(self, save_id: str, location_entity_id: str, actor_id: str, target_id: str, intent: TurnIntent) -> TurnResolution:
        encounter_id = self.start_encounter(save_id, location_entity_id, [actor_id, target_id])
        return self.resolve_turn_for_entity(encounter_id, actor_id, intent)

    def resolve_turn_for_entity(self, encounter_id: str, entity_id: str, intent: TurnIntent) -> TurnResolution:
        combatants = self.combat_repository.get_combatants(encounter_id)
        combatant = next((row for row in combatants if row.entity_id == entity_id and not row.is_defeated), None)
        if combatant is None:
            raise ValueError(f"No combatant for entity {entity_id}")
        return self.resolve_turn(encounter_id, combatant.id, intent)

    def _save_id_for(self, encounter_id: str) -> str:
        encounter = self.combat_repository.get_encounter(encounter_id)
        if encounter is None:
            raise ValueError(f"Unknown encounter {encounter_id}")
        return encounter.save_id

    def _run_enemy_rounds(self, encounter_id: str) -> None:
        encounter = self.combat_repository.get_encounter(encounter_id)
        if encounter is None or encounter.state != EncounterState.ACTIVE:
            return
        combatants = self.combat_repository.get_combatants(encounter_id)
        player_combatant = next(
            (combatant for combatant in combatants if self.world_repository.get_entity(combatant.entity_id).is_player),
            None,
        )
        if player_combatant is None:
            return
        active = encounter.active_combatant_id
        if active is None:
            return
        current = next((combatant for combatant in combatants if combatant.id == active), None)
        if current is None or current.entity_id == player_combatant.entity_id or current.is_defeated:
            return

        enemy_entity = self.world_repository.get_entity(current.entity_id)
        player_entity = self.world_repository.get_entity(player_combatant.entity_id)
        player_stats = self.world_repository.get_entity_stats(player_combatant.entity_id)
        enemy_stats = self.world_repository.get_entity_stats(current.entity_id)
        if enemy_entity is None or player_entity is None or player_stats is None:
            return

        modifier = ability_modifier(enemy_stats.strength if enemy_stats else 10) + (enemy_stats.melee if enemy_stats else 0)
        check = roll_d20(modifier=modifier, rng=self.rng)
        difficulty = 10 + ability_modifier(player_stats.dexterity)
        outcome = attack_outcome(check.total, difficulty, check.dice_roll.rolls[0])
        if outcome in {SuccessTier.SUCCESS, SuccessTier.MIXED, SuccessTier.CRITICAL_SUCCESS}:
            damage = roll_damage(
                bonus=ability_modifier(enemy_stats.strength if enemy_stats else 10),
                rng=self.rng,
            )
            patch = StatePatch(
                save_id=self._save_id_for(encounter_id),
                operations=[
                    PatchOperation(
                        kind=PatchOperationKind.DAMAGE_ENTITY,
                        target_id=player_entity.id,
                        data={"amount": damage},
                    ),
                    PatchOperation(
                        kind=PatchOperationKind.CREATE_EVENT,
                        data={
                            "event_id": new_id("event"),
                            "event_type": EventType.COMBAT.value,
                            "title": "Enemy attack",
                            "description": f"{enemy_entity.name} hits {player_entity.name} for {damage} damage.",
                            "actor_entity_id": enemy_entity.id,
                            "target_entity_id": player_entity.id,
                            "location_entity_id": enemy_entity.location_entity_id,
                        },
                    ),
                ],
            )
            self.world_repository.apply_patch(patch)
            if max(0, player_stats.hp - damage) == 0:
                self.combat_repository.complete_encounter(encounter_id, EncounterState.LOST)
                return
        self.combat_repository.advance_turn(encounter_id)
        encounter = self.combat_repository.get_encounter(encounter_id)
        if encounter is None:
            return
        remaining = [
            combatant
            for combatant in self.combat_repository.get_combatants(encounter_id)
            if not combatant.is_defeated
        ]
        hostiles = [combatant for combatant in remaining if not self.world_repository.get_entity(combatant.entity_id).is_player]
        if not hostiles:
            self.combat_repository.complete_encounter(encounter_id, EncounterState.WON)

