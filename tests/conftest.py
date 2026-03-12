from __future__ import annotations

import os
from pathlib import Path

import pytest

from ai_rpg.core.config import Settings
from ai_rpg.db.combat_repo import CombatRepository
from ai_rpg.db.event_repo import EventRepository
from ai_rpg.db.repositories import SaveRepository, ScenarioRepository, WorldRepository
from ai_rpg.db.session import build_session_factory, create_schema
from ai_rpg.game.action_evaluator import HybridActionEvaluator
from ai_rpg.game.combat import SimpleCombatEngine
from ai_rpg.game.context_builder import DatabaseContextBuilder
from ai_rpg.game.intent_parser import IntentParser
from ai_rpg.game.simulation import SimpleSimulationEngine
from ai_rpg.llm.adapter import RoutedLLMAdapter
from ai_rpg.scenarios.seed_loader import ScenarioSeedLoader


class FixedRandom:
    def __init__(self, values: list[int]):
        self.values = list(values)

    def randint(self, start: int, end: int) -> int:
        if self.values:
            return self.values.pop(0)
        return end


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
def llm_settings(tmp_path: Path) -> Settings:
    return Settings(
        db_path=tmp_path / "unused.db",
        provider="openrouter",
        model="openrouter/auto",
        api_base="https://openrouter.ai/api/v1",
        api_key=None,
        debug=False,
    )


@pytest.fixture()
def llm_adapter(llm_settings: Settings):
    return RoutedLLMAdapter(llm_settings)


@pytest.fixture()
def combat_engine(world_repository: WorldRepository, combat_repository: CombatRepository):
    return SimpleCombatEngine(world_repository, combat_repository, rng=FixedRandom([18, 6, 17, 4, 3, 2]))


@pytest.fixture()
def simulation_engine(world_repository: WorldRepository, event_repository: EventRepository):
    return SimpleSimulationEngine(world_repository, event_repository)


@pytest.fixture()
def evaluator(
    world_repository: WorldRepository,
    llm_adapter: RoutedLLMAdapter,
    combat_engine: SimpleCombatEngine,
):
    return HybridActionEvaluator(world_repository, llm_adapter, combat_engine, rng=FixedRandom([18, 17, 5, 4]))

