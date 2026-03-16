from __future__ import annotations

from rich.console import Console
from rich.table import Table
import typer

from ai_rpg.cli.scenario_menu import choose_scenario, create_scenario_flow
from ai_rpg.db.repositories import SaveRepository, ScenarioRepository
from ai_rpg.game.play_loop import PlayLoop
from ai_rpg.runtime import build_runtime
from ai_rpg.scenarios.seed_loader import ScenarioSeedLoader


app = typer.Typer(add_completion=False, invoke_without_command=True)


def build_app(console: Console | None = None) -> tuple[Console, ScenarioRepository, SaveRepository, PlayLoop, ScenarioSeedLoader]:
    runtime = build_runtime()
    runtime.llm_adapter.ensure_configured()
    play_loop = PlayLoop(
        save_repository=runtime.save_repository,
        world_repository=runtime.world_repository,
        context_builder=runtime.context_builder,
        intent_parser=runtime.turn_service.intent_parser,
        action_evaluator=runtime.action_evaluator,
        combat_engine=runtime.combat_engine,
        simulation_engine=runtime.simulation_engine,
        console=console or Console(),
        turn_service=runtime.turn_service,
    )
    return play_loop.console, runtime.scenario_repository, runtime.save_repository, play_loop, runtime.seed_loader


@app.callback()
def main() -> None:
    try:
        console, scenario_repository, save_repository, play_loop, seed_loader = build_app()
    except RuntimeError as exc:
        Console().print(f"[bold red]{exc}[/]")
        raise typer.Exit(code=1)
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
