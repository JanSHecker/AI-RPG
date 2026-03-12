from __future__ import annotations

from rich.console import Console
from rich.table import Table
import typer

from ai_rpg.core.config import load_settings
from ai_rpg.db.combat_repo import CombatRepository
from ai_rpg.db.event_repo import EventRepository
from ai_rpg.db.repositories import SaveRepository, ScenarioRepository, WorldRepository
from ai_rpg.db.session import build_session_factory, create_schema
from ai_rpg.game.action_evaluator import HybridActionEvaluator
from ai_rpg.game.combat import SimpleCombatEngine
from ai_rpg.game.context_builder import DatabaseContextBuilder
from ai_rpg.game.intent_parser import IntentParser
from ai_rpg.game.play_loop import PlayLoop
from ai_rpg.game.simulation import SimpleSimulationEngine
from ai_rpg.llm.adapter import RoutedLLMAdapter
from ai_rpg.scenarios.seed_loader import ScenarioSeedLoader
from ai_rpg.cli.scenario_menu import choose_scenario, create_scenario_flow


app = typer.Typer(add_completion=False, invoke_without_command=True)


def build_app(console: Console | None = None) -> tuple[Console, ScenarioRepository, SaveRepository, PlayLoop, ScenarioSeedLoader]:
    settings = load_settings()
    create_schema(settings.database_url)
    session_factory = build_session_factory(settings.database_url)

    scenario_repository = ScenarioRepository(session_factory)
    save_repository = SaveRepository(session_factory)
    world_repository = WorldRepository(session_factory)
    event_repository = EventRepository(session_factory)
    combat_repository = CombatRepository(session_factory)
    seed_loader = ScenarioSeedLoader(session_factory)
    seed_loader.ensure_builtin_scenarios()

    llm_adapter = RoutedLLMAdapter(settings)
    context_builder = DatabaseContextBuilder(world_repository)
    combat_engine = SimpleCombatEngine(world_repository, combat_repository)
    simulation_engine = SimpleSimulationEngine(world_repository, event_repository)
    action_evaluator = HybridActionEvaluator(world_repository, llm_adapter, combat_engine)
    play_loop = PlayLoop(
        save_repository=save_repository,
        world_repository=world_repository,
        context_builder=context_builder,
        intent_parser=IntentParser(),
        action_evaluator=action_evaluator,
        combat_engine=combat_engine,
        simulation_engine=simulation_engine,
        console=console or Console(),
    )
    return play_loop.console, scenario_repository, save_repository, play_loop, seed_loader


@app.callback()
def main() -> None:
    console, scenario_repository, save_repository, play_loop, seed_loader = build_app()
    while True:
        console.print("\n[bold]AI-RPG[/]")
        console.print("1. New Game")
        console.print("2. Load Game")
        console.print("3. Create Scenario")
        console.print("4. Quit")
        choice = console.input("Select an option: ").strip()
        if choice == "1":
            scenario_id = choose_scenario(console, scenario_repository)
            if scenario_id is None:
                console.print("Invalid scenario selection.")
                continue
            save_name = console.input("Save name: ").strip() or "New Adventure"
            player_name = console.input("Player name: ").strip() or "Wanderer"
            save = save_repository.create_from_scenario(scenario_id, save_name, player_name=player_name)
            play_loop.run(save.id)
        elif choice == "2":
            saves = save_repository.list_saves()
            if not saves:
                console.print("No saves available.")
                continue
            table = Table(title="Save Slots")
            table.add_column("#")
            table.add_column("Name")
            table.add_column("Scenario")
            for index, save in enumerate(saves, start=1):
                table.add_row(str(index), save.name, save.scenario_id)
            console.print(table)
            selection = console.input("Load save #: ").strip()
            if not selection.isdigit():
                console.print("Invalid save selection.")
                continue
            index = int(selection) - 1
            if index < 0 or index >= len(saves):
                console.print("Invalid save selection.")
                continue
            play_loop.run(saves[index].id)
        elif choice == "3":
            create_scenario_flow(console, seed_loader)
        elif choice == "4":
            console.print("Farewell.")
            break
        else:
            console.print("Choose 1-4.")


def run() -> None:
    app()


if __name__ == "__main__":
    run()
