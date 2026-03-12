from __future__ import annotations

import random

from ai_rpg.core.contracts import (
    ActionCheck,
    ActionType,
    EventType,
    NarrationRequest,
    PatchOperation,
    PatchOperationKind,
    SceneContext,
    StatePatch,
    SuccessTier,
    TimeScale,
    TurnIntent,
    TurnResolution,
)
from ai_rpg.db.repositories import WorldRepository, new_id
from ai_rpg.game.combat import SimpleCombatEngine
from ai_rpg.game.time import ability_modifier, action_time_cost, success_tier_from_roll
from ai_rpg.llm.adapter import RoutedLLMAdapter


class HybridActionEvaluator:
    def __init__(
        self,
        world_repository: WorldRepository,
        llm_adapter: RoutedLLMAdapter,
        combat_engine: SimpleCombatEngine,
        *,
        rng: random.Random | None = None,
    ):
        self.world_repository = world_repository
        self.llm_adapter = llm_adapter
        self.combat_engine = combat_engine
        self.rng = rng or random.Random()

    def resolve(self, intent: TurnIntent, context: SceneContext) -> TurnResolution:
        if intent.action_type == ActionType.LOOK:
            location_name = context.location.name if context.location else "Nowhere"
            nearby = ", ".join(entity.name for entity in context.nearby_entities) or "no one else is nearby"
            narration = f"{location_name}: {context.location.description if context.location else ''} Nearby: {nearby}."
            return TurnResolution(
                allowed=True,
                success_tier=SuccessTier.SUCCESS,
                narration=narration,
                patch=StatePatch.empty(context.save_id),
            )

        if intent.action_type == ActionType.MOVE:
            destination = next(
                (
                    place
                    for place in context.adjacent_places
                    if place.destination_id == intent.destination_id
                    or (
                        intent.destination_name
                        and intent.destination_name.lower() in place.destination_name.lower()
                    )
                ),
                None,
            )
            if destination is None:
                return self._denied(context.save_id, "You cannot travel there from here.")
            patch = StatePatch(
                save_id=context.save_id,
                operations=[
                    PatchOperation(
                        kind=PatchOperationKind.MOVE_ENTITY,
                        target_id=intent.actor_id,
                        data={"location_entity_id": destination.destination_id},
                    ),
                    PatchOperation(
                        kind=PatchOperationKind.ADVANCE_TIME,
                        data={"minutes": destination.travel_minutes},
                    ),
                    PatchOperation(
                        kind=PatchOperationKind.CREATE_EVENT,
                        data={
                            "event_id": new_id("event"),
                            "event_type": EventType.MOVEMENT.value,
                            "title": "Travel",
                            "description": f"You travel to {destination.destination_name}.",
                            "actor_entity_id": intent.actor_id,
                            "location_entity_id": destination.destination_id,
                        },
                    ),
                ],
            )
            response = self.llm_adapter.generate_structured(
                NarrationRequest(
                    system_prompt="Narrate the result of a successful travel action in a terse fantasy style.",
                    scene_context=context,
                    intent=intent,
                    resolution_hint=f"The player reaches {destination.destination_name} after a short journey.",
                    allowed_operations=[],
                )
            )
            return TurnResolution(
                allowed=True,
                success_tier=SuccessTier.SUCCESS,
                narration=response.narration,
                patch=patch,
                time_advance_minutes=destination.travel_minutes,
                time_scale=TimeScale.TRAVEL,
            )

        if intent.action_type == ActionType.TALK:
            target = next((entity for entity in context.nearby_entities if entity.id == intent.target_id), None)
            if target is None:
                return self._denied(context.save_id, "That person is not here.")
            player_stats = self.world_repository.get_entity_stats(intent.actor_id)
            charisma = player_stats.charisma if player_stats else 10
            diplomacy = player_stats.diplomacy if player_stats else 0
            natural = self.rng.randint(1, 20)
            modifier = ability_modifier(charisma) + diplomacy
            total = natural + modifier
            check = ActionCheck(
                stat="charisma",
                skill="diplomacy",
                difficulty=10,
                dice_roll={
                    "sides": 20,
                    "count": 1,
                    "rolls": [natural],
                    "modifier": modifier,
                    "total": total,
                },
                modifier=modifier,
                total=total,
            )
            success_tier = success_tier_from_roll(total, 10, natural)
            patch = StatePatch(
                save_id=context.save_id,
                operations=[
                    PatchOperation(
                        kind=PatchOperationKind.ADVANCE_TIME,
                        data={"minutes": action_time_cost(ActionType.TALK)},
                    ),
                    PatchOperation(
                        kind=PatchOperationKind.CREATE_EVENT,
                        data={
                            "event_id": new_id("event"),
                            "event_type": EventType.DIALOGUE.value,
                            "title": f"Conversation with {target.name}",
                            "description": intent.content or f"You speak with {target.name}.",
                            "actor_entity_id": intent.actor_id,
                            "target_entity_id": target.id,
                            "location_entity_id": context.location.id if context.location else None,
                        },
                    ),
                ],
            )
            messages: list[str] = []
            if target.name == "Mayor Elira" and success_tier in {SuccessTier.SUCCESS, SuccessTier.MIXED, SuccessTier.CRITICAL_SUCCESS}:
                quest = next((quest for quest in context.active_quests if quest.id.endswith("quest.clear_watchtower")), None)
                if quest is None:
                    patch.operations.append(
                        PatchOperation(
                            kind=PatchOperationKind.UPDATE_QUEST,
                            data={
                                "quest_id": f"{context.save_id}:quest.clear_watchtower",
                                "actor_entity_id": intent.actor_id,
                                "status": "active",
                                "notes": "Mayor Elira asked you to investigate the ruined watchtower.",
                                "progress": 1,
                            },
                        )
                    )
                    messages.append("Quest started: Scour the Watchtower")
            if target.name == "Ranger Tomas" and success_tier in {SuccessTier.SUCCESS, SuccessTier.CRITICAL_SUCCESS}:
                patch.operations.append(
                    PatchOperation(
                        kind=PatchOperationKind.ADD_BELIEF,
                        data={
                            "holder_entity_id": intent.actor_id,
                            "belief_key": "watchtower_goblins",
                            "belief_text": "Tomas is sure the tracks near the tower belong to goblins.",
                            "confidence": 0.9,
                        },
                    )
                )
                messages.append("You learn that Tomas believes goblins, not bandits, hold the tower.")
            response = self.llm_adapter.generate_structured(
                NarrationRequest(
                    system_prompt="Return terse JSON narration for a conversation in a frontier fantasy RPG.",
                    scene_context=context,
                    intent=intent,
                    resolution_hint=(
                        f"The player speaks with {target.name}. "
                        f"The outcome tier is {success_tier.value}. Keep it grounded in the local scene."
                    ),
                    allowed_operations=[],
                )
            )
            return TurnResolution(
                allowed=True,
                success_tier=success_tier,
                narration=response.narration,
                action_check=check,
                patch=patch,
                time_advance_minutes=action_time_cost(ActionType.TALK),
                time_scale=TimeScale.LOCAL,
                messages=messages,
            )

        if intent.action_type == ActionType.ATTACK:
            target = next((entity for entity in context.nearby_entities if entity.id == intent.target_id), None)
            if target is None:
                return self._denied(context.save_id, "There is nothing here by that name to attack.")
            if not target.is_hostile:
                return self._denied(context.save_id, f"{target.name} is not openly hostile.")
            return self.combat_engine.engage(
                context.save_id,
                context.location.id if context.location else "",
                intent.actor_id,
                target.id,
                intent,
            )

        if intent.action_type == ActionType.WAIT:
            patch = StatePatch(
                save_id=context.save_id,
                operations=[
                    PatchOperation(
                        kind=PatchOperationKind.ADVANCE_TIME,
                        data={"minutes": action_time_cost(ActionType.WAIT)},
                    )
                ],
            )
            return TurnResolution(
                allowed=True,
                success_tier=SuccessTier.SUCCESS,
                narration="You pause, listen to the world around you, and let a few minutes pass.",
                patch=patch,
                time_advance_minutes=action_time_cost(ActionType.WAIT),
                time_scale=TimeScale.LOCAL,
            )

        if intent.action_type in {ActionType.INVENTORY, ActionType.QUESTS}:
            return TurnResolution(
                allowed=True,
                success_tier=SuccessTier.SUCCESS,
                narration="",
                patch=StatePatch.empty(context.save_id),
            )

        return self._denied(context.save_id, "The game does not understand that action yet.")

    def _denied(self, save_id: str, message: str) -> TurnResolution:
        return TurnResolution(
            allowed=False,
            success_tier=SuccessTier.FAILURE,
            narration=message,
            patch=StatePatch.empty(save_id),
        )

