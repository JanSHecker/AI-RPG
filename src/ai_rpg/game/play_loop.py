from __future__ import annotations

import json

from rich.console import Console
from rich.table import Table

from ai_rpg.core.contracts import ActionType
from ai_rpg.db.repositories import SaveRepository, WorldRepository
from ai_rpg.game.action_evaluator import HybridActionEvaluator
from ai_rpg.game.combat import SimpleCombatEngine
from ai_rpg.game.context_builder import DatabaseContextBuilder
from ai_rpg.game.intent_parser import IntentParser
from ai_rpg.game.simulation import SimpleSimulationEngine


class PlayLoop:
    def __init__(
        self,
        save_repository: SaveRepository,
        world_repository: WorldRepository,
        context_builder: DatabaseContextBuilder,
        intent_parser: IntentParser,
        action_evaluator: HybridActionEvaluator,
        combat_engine: SimpleCombatEngine,
        simulation_engine: SimpleSimulationEngine,
        *,
        console: Console | None = None,
    ):
        self.save_repository = save_repository
        self.world_repository = world_repository
        self.context_builder = context_builder
        self.intent_parser = intent_parser
        self.action_evaluator = action_evaluator
        self.combat_engine = combat_engine
        self.simulation_engine = simulation_engine
        self.console = console or Console()

    def run(self, save_id: str) -> None:
        save = self.save_repository.get(save_id)
        if save is None or save.player_entity_id is None:
            raise ValueError(f"Save {save_id} is missing.")
        player_id = save.player_entity_id
        active_encounter_id: str | None = None

        while True:
            context = self.context_builder.build(save_id, player_id)
            self._render_scene(context, active_encounter_id)
            raw_input = self.console.input("\n[bold green]> [/]")
            if raw_input.strip().lower() in {"quit", "exit", "/exit"}:
                self.console.print("Returning to the main menu.")
                return
            intent = self.intent_parser.parse(raw_input, player_id, context)
            if intent.action_type == ActionType.COMMAND:
                if self._handle_command(intent.command or "", context):
                    return
                continue

            if active_encounter_id:
                resolution = self.combat_engine.resolve_turn_for_entity(active_encounter_id, player_id, intent)
            else:
                resolution = self.action_evaluator.resolve(intent, context)

            before_time = self.world_repository.get_save_time(save_id)
            if resolution.patch.operations:
                self.world_repository.apply_patch(resolution.patch)
            after_time = self.world_repository.get_save_time(save_id)
            if after_time > before_time:
                self.simulation_engine.advance(save_id, before_time, after_time)

            self.console.print(f"\n[bold cyan]{resolution.narration}[/]")
            for message in resolution.messages:
                self.console.print(f"[yellow]{message}[/]")

            if intent.action_type == ActionType.INVENTORY:
                self._render_inventory(context)
            if intent.action_type == ActionType.QUESTS:
                self._render_quests(context)

            active_encounter_id = resolution.encounter_id if resolution.enter_combat else None

    def _handle_command(self, command: str, context) -> bool:
        if command == "help":
            self.console.print("/help, /look, /inventory, /quests, /map, /save, /debug, /exit")
        elif command == "look":
            self._render_scene(context, None)
        elif command == "inventory":
            self._render_inventory(context)
        elif command == "quests":
            self._render_quests(context)
        elif command == "map":
            table = Table(title="Nearby Routes")
            table.add_column("Destination")
            table.add_column("Travel")
            for route in context.adjacent_places:
                table.add_row(route.destination_name, f"{route.travel_minutes} min")
            self.console.print(table)
        elif command == "save":
            self.console.print("The world is already persisted after every resolved action.")
        elif command == "debug":
            self.console.print(json.dumps(context.model_dump(mode="json"), indent=2, default=str))
        elif command in {"exit", "load"}:
            return True
        else:
            self.console.print(f"Unknown command: /{command}")
        return False

    def _render_scene(self, context, active_encounter_id: str | None) -> None:
        location_name = context.location.name if context.location else "Unknown"
        header = f"[bold magenta]{location_name}[/] - {context.current_time}"
        if active_encounter_id:
            header += " [red](combat)[/]"
        self.console.print(f"\n{header}")
        if context.location:
            self.console.print(context.location.description)
        if context.nearby_entities:
            nearby = ", ".join(entity.name for entity in context.nearby_entities)
            self.console.print(f"Nearby: {nearby}")
        if context.adjacent_places:
            destinations = ", ".join(place.destination_name for place in context.adjacent_places)
            self.console.print(f"Routes: {destinations}")

    def _render_inventory(self, context) -> None:
        if not context.inventory:
            self.console.print("Inventory: empty")
            return
        table = Table(title="Inventory")
        table.add_column("Item")
        table.add_column("Qty")
        for item in context.inventory:
            table.add_row(item.item_name, str(item.quantity))
        self.console.print(table)

    def _render_quests(self, context) -> None:
        if not context.active_quests:
            self.console.print("No active quests.")
            return
        table = Table(title="Quests")
        table.add_column("Title")
        table.add_column("Status")
        table.add_column("Notes")
        for quest in context.active_quests:
            table.add_row(quest.title, quest.status.value, quest.notes)
        self.console.print(table)

