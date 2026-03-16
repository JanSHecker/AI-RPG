from __future__ import annotations

from pathlib import Path

import pytest

from ai_rpg.core.contracts import (
    ActionAttribute,
    ActionDraft,
    ActionMatchDecision,
    NarrationResponse,
    PatchOperation,
    PatchOperationKind,
)
from ai_rpg.db.combat_repo import CombatRepository
from ai_rpg.db.event_repo import EventRepository
from ai_rpg.db.repositories import (
    SaveRepository,
    ScenarioActionRepository,
    ScenarioRepository,
    WorldRepository,
)
from ai_rpg.db.session import build_session_factory, create_schema
from ai_rpg.game.action_evaluator import HybridActionEvaluator
from ai_rpg.game.combat import SimpleCombatEngine
from ai_rpg.game.context_builder import DatabaseContextBuilder
from ai_rpg.game.intent_parser import IntentParser
from ai_rpg.game.simulation import SimpleSimulationEngine
from ai_rpg.scenarios.seed_loader import ScenarioSeedLoader


class FixedRandom:
    def __init__(self, values: list[int]):
        self.values = list(values)

    def randint(self, start: int, end: int) -> int:
        if self.values:
            return self.values.pop(0)
        return end


class FakeLLMAdapter:
    def ensure_configured(self) -> None:
        return None

    def match_or_create_action(self, *, raw_input: str, scene_context, actions: list[dict]) -> ActionMatchDecision:
        lowered = raw_input.strip().lower()

        if "search" in lowered and "rubble" in lowered:
            existing = next(
                (
                    action
                    for action in actions
                    if action["name"].lower() == "search the rubble"
                    or any(alias.lower() == "search the rubble" for alias in action["aliases"])
                ),
                None,
            )
            if existing is not None:
                return ActionMatchDecision(action_id=existing["id"], confidence=0.99)
            return ActionMatchDecision(
                created_action=ActionDraft(
                    name="Search the Rubble",
                    description="Pick through rubble or debris for clues and salvage.",
                    aliases=["search the rubble", "search rubble", "look for clues"],
                    relevant_attribute=ActionAttribute.SURVIVAL,
                    difficulty=12,
                    action_point_cost=15,
                )
            )

        if "forbidden" in lowered:
            existing = next((action for action in actions if action["name"].lower() == "forbidden ritual"), None)
            if existing is not None:
                return ActionMatchDecision(action_id=existing["id"], confidence=0.99)
            return ActionMatchDecision(
                created_action=ActionDraft(
                    name="Forbidden Ritual",
                    description="Attempt a dangerous improvisational rite.",
                    aliases=["forbidden ritual"],
                    relevant_attribute=ActionAttribute.INTELLIGENCE,
                    difficulty=14,
                    action_point_cost=25,
                )
            )

        normalized = f" {lowered} "
        for action in actions:
            for alias in action["aliases"]:
                alias_lower = alias.lower()
                if lowered == alias_lower or lowered.startswith(f"{alias_lower} ") or f" {alias_lower} " in normalized:
                    return ActionMatchDecision(action_id=action["id"], confidence=0.95)

        return ActionMatchDecision(
            created_action=ActionDraft(
                name="Study the Scene",
                description="Take a closer, deliberate look at the current situation.",
                aliases=[lowered],
                relevant_attribute=ActionAttribute.WISDOM,
                difficulty=10,
                action_point_cost=5,
            )
        )

    def generate_out_of_combat_effects(self, *, proposal, scene_context, success_tier) -> NarrationResponse:
        lowered = proposal.raw_input.lower()
        if "forbidden" in lowered:
            return NarrationResponse(
                narration="You begin a dangerous ritual.",
                operations=[
                    PatchOperation(
                        kind=PatchOperationKind.START_COMBAT,
                        data={"reason": "This should be filtered out."},
                    )
                ],
            )
        return NarrationResponse(
            narration=f"You follow through on '{proposal.raw_input}'.",
            operations=[
                PatchOperation(
                    kind=PatchOperationKind.CREATE_EVENT,
                    data={
                        "event_type": "discovery",
                        "title": proposal.action_name,
                        "description": f"{proposal.action_name} resolves with {success_tier.value}.",
                        "actor_entity_id": scene_context.actor_id,
                        "location_entity_id": scene_context.location.id if scene_context.location else None,
                        "payload": {
                            "action_id": proposal.action_id,
                            "success_tier": success_tier.value,
                        },
                    },
                )
            ],
        )


@pytest.fixture()
def database_url(tmp_path: Path) -> str:
    return f"sqlite:///{tmp_path / 'test.db'}"


@pytest.fixture()
def session_factory(database_url: str):
    create_schema(database_url)
    factory = build_session_factory(database_url)
    ScenarioSeedLoader(factory).ensure_builtin_scenarios()
    return factory


@pytest.fixture()
def scenario_repository(session_factory):
    return ScenarioRepository(session_factory)


@pytest.fixture()
def action_repository(session_factory):
    return ScenarioActionRepository(session_factory)


@pytest.fixture()
def save_repository(session_factory):
    return SaveRepository(session_factory)


@pytest.fixture()
def world_repository(session_factory):
    return WorldRepository(session_factory)


@pytest.fixture()
def event_repository(session_factory):
    return EventRepository(session_factory)


@pytest.fixture()
def combat_repository(session_factory):
    return CombatRepository(session_factory)


@pytest.fixture()
def save_id(save_repository: SaveRepository) -> str:
    save = save_repository.create_from_scenario("scenario.frontier_fantasy", "Test Save", player_name="Aria")
    return save.id


@pytest.fixture()
def context_builder(world_repository: WorldRepository):
    return DatabaseContextBuilder(world_repository)


@pytest.fixture()
def parser():
    return IntentParser()


@pytest.fixture()
def llm_adapter():
    return FakeLLMAdapter()


@pytest.fixture()
def combat_engine(world_repository: WorldRepository, combat_repository: CombatRepository):
    return SimpleCombatEngine(world_repository, combat_repository, rng=FixedRandom([18, 6, 17, 4, 3, 2]))


@pytest.fixture()
def simulation_engine(world_repository: WorldRepository, event_repository: EventRepository):
    return SimpleSimulationEngine(world_repository, event_repository)


@pytest.fixture()
def evaluator(
    world_repository: WorldRepository,
    action_repository: ScenarioActionRepository,
    llm_adapter: FakeLLMAdapter,
    combat_engine: SimpleCombatEngine,
):
    return HybridActionEvaluator(
        world_repository,
        action_repository,
        llm_adapter,
        combat_engine,
        rng=FixedRandom([18, 17, 5, 4, 16, 14, 12, 10]),
    )
