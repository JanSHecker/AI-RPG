from __future__ import annotations

from datetime import datetime, timedelta
import random

from ai_rpg.core.contracts import (
    ActionAttribute,
    ActionCheck,
    ActionProposal,
    ActionResolutionMode,
    ActionType,
    EventType,
    PatchOperation,
    PatchOperationKind,
    SceneContext,
    StatePatch,
    SuccessTier,
    TimeScale,
    TurnIntent,
    TurnResolution,
)
from ai_rpg.db.repositories import ScenarioActionRepository, WorldRepository, new_id
from ai_rpg.game.combat import SimpleCombatEngine
from ai_rpg.game.time import action_time_cost, calculate_outcome_chances, resolve_action_modifier, success_tier_from_roll


class HybridActionEvaluator:
    def __init__(
        self,
        world_repository: WorldRepository,
        action_repository: ScenarioActionRepository,
        llm_adapter,
        combat_engine: SimpleCombatEngine,
        *,
        rng: random.Random | None = None,
    ):
        self.world_repository = world_repository
        self.action_repository = action_repository
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

        if intent.action_type == ActionType.CATALOG:
            phase = str(intent.metadata.get("phase", "propose"))
            if phase == "confirm":
                return self._confirm_catalog_action(intent, context)
            return self._propose_catalog_action(intent, context)

        if intent.action_type == ActionType.MOVE:
            return self._execute_travel(
                context,
                destination_id=intent.destination_id,
                destination_name=intent.destination_name,
                action_point_cost=0,
            )

        if intent.action_type == ActionType.TALK:
            return self._execute_talk(
                context,
                target_id=intent.target_id,
                target_name=intent.target_name,
                raw_input=intent.content or intent.raw_input,
                action_point_cost=0,
            )

        if intent.action_type == ActionType.ATTACK:
            return self._execute_attack(
                context,
                target_id=intent.target_id,
                target_name=intent.target_name,
                raw_input=intent.content or intent.raw_input,
                action_point_cost=0,
            )

        if intent.action_type == ActionType.WAIT:
            return self._execute_rest(context, action_point_cost=0)

        if intent.action_type in {ActionType.INVENTORY, ActionType.QUESTS}:
            return TurnResolution(
                allowed=True,
                success_tier=SuccessTier.SUCCESS,
                narration="",
                patch=StatePatch.empty(context.save_id),
            )

        return self._denied(context.save_id, "The game does not understand that action yet.")

    def _propose_catalog_action(self, intent: TurnIntent, context: SceneContext) -> TurnResolution:
        scenario_id = self.world_repository.get_save_scenario_id(context.save_id)
        actions = self.action_repository.list_actions(scenario_id)
        if not actions:
            return self._denied(context.save_id, "No actions are available for this scenario.")

        try:
            decision = self.llm_adapter.match_or_create_action(
                raw_input=intent.raw_input,
                scene_context=context,
                actions=[self._serialize_action(action) for action in actions],
            )
        except Exception:
            return self._denied(context.save_id, "The game could not interpret that action right now.")

        created_this_turn = False
        action = None
        if decision.created_action is not None:
            action = self.action_repository.create_action(
                scenario_id,
                name=decision.created_action.name,
                description=decision.created_action.description,
                aliases=decision.created_action.aliases,
                relevant_attribute=decision.created_action.relevant_attribute,
                difficulty=max(0, decision.created_action.difficulty),
                action_point_cost=max(0, decision.created_action.action_point_cost),
                resolution_mode=ActionResolutionMode.LLM_EFFECTS,
                handler_key=None,
                created_by_llm=True,
            )
            created_this_turn = True
        elif decision.action_id:
            action = next((row for row in actions if row.id == decision.action_id), None)
            if action is None:
                action = self.action_repository.get(decision.action_id)

        if action is None:
            return self._denied(context.save_id, "The game could not match that action to anything usable.")

        proposal, error_message = self._build_action_proposal(action, intent.raw_input, context, created_this_turn)
        if proposal is None:
            return self._denied(context.save_id, error_message or "That action cannot be performed right now.")

        return TurnResolution(
            allowed=True,
            success_tier=SuccessTier.SUCCESS,
            narration="",
            patch=StatePatch.empty(context.save_id),
            proposal=proposal,
            awaiting_confirmation=True,
        )

    def _confirm_catalog_action(self, intent: TurnIntent, context: SceneContext) -> TurnResolution:
        try:
            proposal = ActionProposal.model_validate(intent.metadata["proposal"])
        except Exception:
            return self._denied(context.save_id, "The pending action could not be confirmed.")

        if not proposal.can_confirm_now:
            return self._denied(context.save_id, proposal.blocker_message or "That action cannot be confirmed right now.")
        if context.action_points < proposal.action_point_cost:
            return self._denied(context.save_id, "Not enough action points.")

        if proposal.resolution_mode == ActionResolutionMode.DETERMINISTIC:
            if proposal.handler_key == "travel":
                return self._execute_travel(
                    context,
                    destination_id=proposal.destination_id,
                    destination_name=proposal.destination_name,
                    action_point_cost=proposal.action_point_cost,
                )
            if proposal.handler_key == "talk":
                return self._execute_talk(
                    context,
                    target_id=proposal.target_id,
                    target_name=proposal.target_name,
                    raw_input=proposal.raw_input,
                    action_point_cost=proposal.action_point_cost,
                )
            if proposal.handler_key == "attack_hostile":
                return self._execute_attack(
                    context,
                    target_id=proposal.target_id,
                    target_name=proposal.target_name,
                    raw_input=proposal.raw_input,
                    action_point_cost=proposal.action_point_cost,
                )
            if proposal.handler_key == "rest":
                return self._execute_rest(context, action_point_cost=proposal.action_point_cost)
            return self._denied(context.save_id, "The proposed action has no deterministic handler.")

        return self._execute_llm_effect_action(context, proposal)

    def _build_action_proposal(self, action, raw_input: str, context: SceneContext, created_this_turn: bool) -> tuple[ActionProposal | None, str | None]:
        target_id = None
        target_name = None
        destination_id = None
        destination_name = None
        difficulty = action.difficulty

        if action.handler_key == "travel":
            destination = self._resolve_destination(context, raw_input, action.aliases)
            if destination is None:
                return None, "You cannot travel there from here."
            destination_id = destination.id
            destination_name = destination.name
            avoid_failure_percent = 100.0
            clean_success_percent = 100.0
        elif action.handler_key == "talk":
            target = self._resolve_target(context, raw_input, action.aliases)
            if target is None:
                return None, "That person is not here."
            target_id = target.id
            target_name = target.name
            avoid_failure_percent, clean_success_percent = self._calculate_generic_odds(context, action.relevant_attribute, difficulty)
        elif action.handler_key == "attack_hostile":
            target = self._resolve_target(context, raw_input, action.aliases)
            if target is None:
                return None, "There is nothing here by that name to attack."
            if not target.is_hostile:
                return None, f"{target.name} is not openly hostile."
            target_id = target.id
            target_name = target.name
            avoid_failure_percent, clean_success_percent, difficulty = self._calculate_attack_odds(context, target.id)
        elif action.handler_key == "rest":
            avoid_failure_percent = 100.0
            clean_success_percent = 100.0
        else:
            avoid_failure_percent, clean_success_percent = self._calculate_generic_odds(context, action.relevant_attribute, difficulty)

        can_confirm_now = context.action_points >= action.action_point_cost
        blocker_message = None if can_confirm_now else "Not enough action points"
        proposal = ActionProposal(
            action_id=action.id,
            action_name=action.name,
            raw_input=raw_input,
            description=action.description,
            relevant_attribute=action.relevant_attribute,
            difficulty=difficulty,
            action_point_cost=action.action_point_cost,
            avoid_failure_percent=avoid_failure_percent,
            clean_success_percent=clean_success_percent,
            resolution_mode=action.resolution_mode,
            handler_key=action.handler_key,
            target_id=target_id,
            target_name=target_name,
            destination_id=destination_id,
            destination_name=destination_name,
            can_confirm_now=can_confirm_now,
            blocker_message=blocker_message,
            created_this_turn=created_this_turn,
        )
        return proposal, None

    def _execute_travel(
        self,
        context: SceneContext,
        *,
        destination_id: str | None,
        destination_name: str | None,
        action_point_cost: int,
    ) -> TurnResolution:
        destination = next(
            (
                place
                for place in context.adjacent_places
                if place.destination_id == destination_id
                or (destination_name and destination_name.lower() in place.destination_name.lower())
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
                    target_id=context.actor_id,
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
                        "actor_entity_id": context.actor_id,
                        "location_entity_id": destination.destination_id,
                    },
                ),
            ],
        )
        resolution = TurnResolution(
            allowed=True,
            success_tier=SuccessTier.SUCCESS,
            narration=f"You set out and make your way to {destination.destination_name}.",
            patch=patch,
            time_advance_minutes=destination.travel_minutes,
            time_scale=TimeScale.TRAVEL,
        )
        return self._apply_action_point_cost(resolution, context.actor_id, action_point_cost)

    def _execute_talk(
        self,
        context: SceneContext,
        *,
        target_id: str | None,
        target_name: str | None,
        raw_input: str,
        action_point_cost: int,
    ) -> TurnResolution:
        target = next((entity for entity in context.nearby_entities if entity.id == target_id), None)
        if target is None and target_name:
            target = next((entity for entity in context.nearby_entities if target_name.lower() in entity.name.lower()), None)
        if target is None:
            return self._denied(context.save_id, "That person is not here.")

        player_stats = self.world_repository.get_entity_stats(context.actor_id)
        if player_stats is None:
            return self._denied(context.save_id, "The player has no usable stats.")
        stat_name, skill_name, modifier = resolve_action_modifier(player_stats, ActionAttribute.DIPLOMACY)
        natural = self.rng.randint(1, 20)
        total = natural + modifier
        check = ActionCheck(
            stat=stat_name,
            skill=skill_name,
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
                        "description": raw_input,
                        "actor_entity_id": context.actor_id,
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
                            "actor_entity_id": context.actor_id,
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
                        "holder_entity_id": context.actor_id,
                        "belief_key": "watchtower_goblins",
                        "belief_text": "Tomas is sure the tracks near the tower belong to goblins.",
                        "confidence": 0.9,
                    },
                )
            )
            messages.append("You learn that Tomas believes goblins, not bandits, hold the tower.")
        narration = f"You speak with {target.name}."
        if success_tier == SuccessTier.CRITICAL_FAILURE:
            narration = f"The conversation with {target.name} goes poorly."
        elif success_tier == SuccessTier.MIXED:
            narration = f"You get part of what you need from {target.name}, but not without friction."
        elif success_tier in {SuccessTier.SUCCESS, SuccessTier.CRITICAL_SUCCESS}:
            narration = f"The conversation with {target.name} moves in your favor."
        resolution = TurnResolution(
            allowed=True,
            success_tier=success_tier,
            narration=narration,
            action_check=check,
            patch=patch,
            messages=messages,
            time_advance_minutes=action_time_cost(ActionType.TALK),
            time_scale=TimeScale.LOCAL,
        )
        return self._apply_action_point_cost(resolution, context.actor_id, action_point_cost)

    def _execute_attack(
        self,
        context: SceneContext,
        *,
        target_id: str | None,
        target_name: str | None,
        raw_input: str,
        action_point_cost: int,
    ) -> TurnResolution:
        target = next((entity for entity in context.nearby_entities if entity.id == target_id), None)
        if target is None and target_name:
            target = next((entity for entity in context.nearby_entities if target_name.lower() in entity.name.lower()), None)
        if target is None:
            return self._denied(context.save_id, "There is nothing here by that name to attack.")
        if not target.is_hostile:
            return self._denied(context.save_id, f"{target.name} is not openly hostile.")
        resolution = self.combat_engine.engage(
            context.save_id,
            context.location.id if context.location else "",
            context.actor_id,
            target.id,
            TurnIntent(
                raw_input=raw_input,
                actor_id=context.actor_id,
                action_type=ActionType.ATTACK,
                target_id=target.id,
                target_name=target.name,
                content=raw_input,
            ),
        )
        return self._apply_action_point_cost(resolution, context.actor_id, action_point_cost)

    def _execute_rest(self, context: SceneContext, *, action_point_cost: int) -> TurnResolution:
        recovery_time = self._next_recovery_time(context.current_time)
        minutes = int((recovery_time - context.current_time).total_seconds() // 60)
        player_stats = self.world_repository.get_entity_stats(context.actor_id)
        if player_stats is None:
            return self._denied(context.save_id, "The player has no usable stats.")
        patch = StatePatch(
            save_id=context.save_id,
            operations=[
                PatchOperation(
                    kind=PatchOperationKind.ADVANCE_TIME,
                    data={"minutes": minutes},
                ),
                PatchOperation(
                    kind=PatchOperationKind.ADJUST_ACTION_POINTS,
                    target_id=context.actor_id,
                    data={"set_to": player_stats.max_action_points},
                ),
                PatchOperation(
                    kind=PatchOperationKind.CREATE_EVENT,
                    data={
                        "event_id": new_id("event"),
                        "event_type": EventType.SYSTEM.value,
                        "title": "Rest",
                        "description": "You end the day, recover, and wake ready to act again.",
                        "actor_entity_id": context.actor_id,
                        "location_entity_id": context.location.id if context.location else None,
                        "payload": {"recovery_time": recovery_time.isoformat()},
                    },
                ),
            ],
        )
        resolution = TurnResolution(
            allowed=True,
            success_tier=SuccessTier.SUCCESS,
            narration="You rest until the next morning and recover your strength.",
            patch=patch,
            time_advance_minutes=minutes,
            time_scale=TimeScale.LOCAL,
        )
        return self._apply_action_point_cost(resolution, context.actor_id, action_point_cost)

    def _execute_llm_effect_action(self, context: SceneContext, proposal: ActionProposal) -> TurnResolution:
        player_stats = self.world_repository.get_entity_stats(context.actor_id)
        if player_stats is None:
            return self._denied(context.save_id, "The player has no usable stats.")
        stat_name, skill_name, modifier = resolve_action_modifier(player_stats, proposal.relevant_attribute)
        natural = self.rng.randint(1, 20)
        total = natural + modifier
        success_tier = success_tier_from_roll(total, proposal.difficulty, natural)
        check = ActionCheck(
            stat=stat_name,
            skill=skill_name,
            difficulty=proposal.difficulty,
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
        try:
            response = self.llm_adapter.generate_out_of_combat_effects(
                proposal=proposal,
                scene_context=context,
                success_tier=success_tier,
            )
        except Exception:
            return self._denied(context.save_id, "The action could not be resolved right now.")

        allowed_kinds = {
            PatchOperationKind.ADVANCE_TIME,
            PatchOperationKind.CREATE_EVENT,
            PatchOperationKind.UPDATE_QUEST,
            PatchOperationKind.UPDATE_RELATIONSHIP,
            PatchOperationKind.ADD_BELIEF,
            PatchOperationKind.ADD_ITEM,
            PatchOperationKind.MOVE_ENTITY,
            PatchOperationKind.HEAL_ENTITY,
        }
        operations = []
        if proposal.action_point_cost > 0:
            operations.append(
                PatchOperation(
                    kind=PatchOperationKind.ADJUST_ACTION_POINTS,
                    target_id=context.actor_id,
                    data={"amount": -proposal.action_point_cost},
                )
            )
        operations.extend(operation for operation in response.operations if operation.kind in allowed_kinds)
        if not any(operation.kind == PatchOperationKind.CREATE_EVENT for operation in operations):
            operations.append(
                PatchOperation(
                    kind=PatchOperationKind.CREATE_EVENT,
                    data={
                        "event_id": new_id("event"),
                        "event_type": EventType.DISCOVERY.value,
                        "title": proposal.action_name,
                        "description": response.narration or proposal.raw_input,
                        "actor_entity_id": context.actor_id,
                        "location_entity_id": context.location.id if context.location else None,
                        "payload": {
                            "action_id": proposal.action_id,
                            "raw_input": proposal.raw_input,
                            "success_tier": success_tier.value,
                        },
                    },
                )
            )
        return TurnResolution(
            allowed=True,
            success_tier=success_tier,
            narration=response.narration or f"You attempt to {proposal.raw_input}.",
            action_check=check,
            patch=StatePatch(save_id=context.save_id, operations=operations),
        )

    def _apply_action_point_cost(self, resolution: TurnResolution, actor_id: str, action_point_cost: int) -> TurnResolution:
        if not resolution.allowed or action_point_cost <= 0:
            return resolution
        resolution.patch.operations.insert(
            0,
            PatchOperation(
                kind=PatchOperationKind.ADJUST_ACTION_POINTS,
                target_id=actor_id,
                data={"amount": -action_point_cost},
            ),
        )
        return resolution

    def _calculate_generic_odds(
        self,
        context: SceneContext,
        relevant_attribute: ActionAttribute,
        difficulty: int,
    ) -> tuple[float, float]:
        player_stats = self.world_repository.get_entity_stats(context.actor_id)
        if player_stats is None:
            return 0.0, 0.0
        _, _, modifier = resolve_action_modifier(player_stats, relevant_attribute)
        return calculate_outcome_chances(difficulty, modifier)

    def _calculate_attack_odds(self, context: SceneContext, target_id: str) -> tuple[float, float, int]:
        player_stats = self.world_repository.get_entity_stats(context.actor_id)
        target_stats = self.world_repository.get_entity_stats(target_id)
        if player_stats is None or target_stats is None:
            return 0.0, 0.0, 10
        _, _, modifier = resolve_action_modifier(player_stats, ActionAttribute.MELEE)
        difficulty = 10 + ((target_stats.dexterity - 10) // 2)
        avoid_failure_percent, clean_success_percent = calculate_outcome_chances(difficulty, modifier)
        return avoid_failure_percent, clean_success_percent, difficulty

    def _resolve_target(self, context: SceneContext, raw_input: str, aliases: list[str]) -> object | None:
        location_id = context.location.id if context.location else ""
        for candidate in self._candidate_terms(raw_input, aliases):
            target = self.world_repository.resolve_entity_by_name(context.save_id, location_id, candidate)
            if target is not None and target.id != context.actor_id:
                return target
        return None

    def _resolve_destination(self, context: SceneContext, raw_input: str, aliases: list[str]) -> object | None:
        location_id = context.location.id if context.location else ""
        for candidate in self._candidate_terms(raw_input, aliases):
            place = self.world_repository.resolve_place_by_name(context.save_id, location_id, candidate)
            if place is not None:
                return place
        return None

    def _candidate_terms(self, raw_input: str, aliases: list[str]) -> list[str]:
        candidates = [raw_input.strip()]
        lowered = raw_input.strip().lower()
        for alias in aliases:
            alias_lower = alias.lower()
            if lowered.startswith(alias_lower):
                remainder = raw_input[len(alias) :].strip()
                if remainder:
                    candidates.append(remainder)
        return [candidate for candidate in candidates if candidate]

    def _serialize_action(self, action) -> dict:
        return {
            "id": action.id,
            "name": action.name,
            "description": action.description,
            "aliases": list(action.aliases or []),
            "relevant_attribute": action.relevant_attribute.value,
            "difficulty": action.difficulty,
            "action_point_cost": action.action_point_cost,
            "resolution_mode": action.resolution_mode.value,
            "handler_key": action.handler_key,
            "created_by_llm": action.created_by_llm,
        }

    def _next_recovery_time(self, current_time: datetime) -> datetime:
        next_day = current_time.date() + timedelta(days=1)
        return datetime.combine(next_day, datetime.min.time()).replace(hour=8)

    def _denied(self, save_id: str, message: str) -> TurnResolution:
        return TurnResolution(
            allowed=False,
            success_tier=SuccessTier.FAILURE,
            narration=message,
            patch=StatePatch.empty(save_id),
        )
