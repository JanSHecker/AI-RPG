from __future__ import annotations

from rich.console import Console
from rich.table import Table

from ai_rpg.db.repositories import ScenarioRepository
from ai_rpg.scenarios.seed_loader import ScenarioSeedLoader


def choose_scenario(console: Console, scenario_repository: ScenarioRepository) -> str | None:
    scenarios = scenario_repository.list_scenarios()
    if not scenarios:
        console.print("No scenarios available.")
        return None
    table = Table(title="Scenarios")
    table.add_column("#")
    table.add_column("Name")
    table.add_column("ID")
    table.add_column("Description")
    for index, scenario in enumerate(scenarios, start=1):
        table.add_row(str(index), scenario.name, scenario.id, scenario.description)
    console.print(table)
    choice = console.input("Choose a scenario by number: ").strip()
    if not choice.isdigit():
        return None
    index = int(choice) - 1
    if index < 0 or index >= len(scenarios):
        return None
    return scenarios[index].id


def create_scenario_flow(console: Console, seed_loader: ScenarioSeedLoader) -> None:
    name = console.input("Scenario name: ").strip() or "Untitled Scenario"
    description = console.input("Scenario description: ").strip()
    scenario = seed_loader.create_empty_scenario(name=name, description=description)
    console.print(f"Created scenario scaffold: {scenario.name} ({scenario.id})")

