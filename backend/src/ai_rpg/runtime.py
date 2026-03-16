from __future__ import annotations

from dataclasses import dataclass

from ai_rpg.core.config import Settings, load_settings
from ai_rpg.db.combat_repo import CombatRepository
from ai_rpg.db.event_repo import EventRepository
from ai_rpg.db.repositories import SaveRepository, ScenarioActionRepository, ScenarioRepository, WorldRepository
from ai_rpg.db.session import build_session_factory, create_schema
from ai_rpg.game.action_evaluator import HybridActionEvaluator
from ai_rpg.game.combat import SimpleCombatEngine
from ai_rpg.game.context_builder import DatabaseContextBuilder
from ai_rpg.game.intent_parser import IntentParser
from ai_rpg.game.simulation import SimpleSimulationEngine
from ai_rpg.game.turn_service import TurnService
from ai_rpg.llm.adapter import RoutedLLMAdapter
from ai_rpg.scenarios.seed_loader import ScenarioSeedLoader


@dataclass(slots=True)
class GameRuntime:
    settings: Settings
    scenario_repository: ScenarioRepository
    action_repository: ScenarioActionRepository
    save_repository: SaveRepository
    world_repository: WorldRepository
    event_repository: EventRepository
    combat_repository: CombatRepository
    seed_loader: ScenarioSeedLoader
    llm_adapter: object
    context_builder: DatabaseContextBuilder
    combat_engine: SimpleCombatEngine
    simulation_engine: SimpleSimulationEngine
    action_evaluator: HybridActionEvaluator
    turn_service: TurnService


def build_runtime(
    settings: Settings | None = None,
    *,
    llm_adapter: object | None = None,
    session_factory=None,
) -> GameRuntime:
    settings = settings or load_settings()
    if session_factory is None:
        create_schema(settings.database_url)
        session_factory = build_session_factory(settings.database_url)

    scenario_repository = ScenarioRepository(session_factory)
    action_repository = ScenarioActionRepository(session_factory)
    save_repository = SaveRepository(session_factory)
    world_repository = WorldRepository(session_factory)
    event_repository = EventRepository(session_factory)
    combat_repository = CombatRepository(session_factory)
    seed_loader = ScenarioSeedLoader(session_factory)
    seed_loader.ensure_builtin_scenarios()

    actual_llm_adapter = llm_adapter or RoutedLLMAdapter(settings)
    context_builder = DatabaseContextBuilder(world_repository)
    combat_engine = SimpleCombatEngine(world_repository, combat_repository)
    simulation_engine = SimpleSimulationEngine(world_repository, event_repository)
    action_evaluator = HybridActionEvaluator(world_repository, action_repository, actual_llm_adapter, combat_engine)
    turn_service = TurnService(
        settings=settings,
        save_repository=save_repository,
        world_repository=world_repository,
        context_builder=context_builder,
        intent_parser=IntentParser(),
        action_evaluator=action_evaluator,
        combat_engine=combat_engine,
        simulation_engine=simulation_engine,
        combat_repository=combat_repository,
    )
    return GameRuntime(
        settings=settings,
        scenario_repository=scenario_repository,
        action_repository=action_repository,
        save_repository=save_repository,
        world_repository=world_repository,
        event_repository=event_repository,
        combat_repository=combat_repository,
        seed_loader=seed_loader,
        llm_adapter=actual_llm_adapter,
        context_builder=context_builder,
        combat_engine=combat_engine,
        simulation_engine=simulation_engine,
        action_evaluator=action_evaluator,
        turn_service=turn_service,
    )
