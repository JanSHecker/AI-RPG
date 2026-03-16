from __future__ import annotations

from rich.console import Console
from rich.table import Table

from ai_rpg.core.contracts import ActionProposal
from ai_rpg.db.repositories import SaveRepository, WorldRepository
from ai_rpg.game.action_evaluator import HybridActionEvaluator
from ai_rpg.game.combat import SimpleCombatEngine
from ai_rpg.game.context_builder import DatabaseContextBuilder
from ai_rpg.game.intent_parser import IntentParser
from ai_rpg.game.simulation import SimpleSimulationEngine
from ai_rpg.game.turn_service import TurnRequestKind, TurnService, TurnViewKind


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
        turn_service: TurnService | None = None,
    ):
        self.save_repository = save_repository
        self.world_repository = world_repository
        self.context_builder = context_builder
        self.intent_parser = intent_parser
        self.action_evaluator = action_evaluator
        self.combat_engine = combat_engine
        self.simulation_engine = simulation_engine
        self.console = console or Console()
        self.turn_service = turn_service or TurnService(
            settings=type("SettingsProxy", (), {"api_key": None})(),
            save_repository=save_repository,
            world_repository=world_repository,
            context_builder=context_builder,
            intent_parser=intent_parser,
            action_evaluator=action_evaluator,
            combat_engine=combat_engine,
            simulation_engine=simulation_engine,
            combat_repository=combat_engine.combat_repository,
        )

    def run(self, save_id: str) -> None:
        save = self.save_repository.get(save_id)
        if save is None or save.player_entity_id is None:
            raise ValueError(f"Save {save_id} is missing.")
        pending_proposal: ActionProposal | None = None

        while True:
            state = self.turn_service.get_state(save_id)
            self._render_scene(state.context, state.active_encounter_id)
            if pending_proposal is not None:
                self._render_action_proposal(pending_proposal)

            raw_input = self.console.input("\n[bold green]> [/]")
            result = self.turn_service.process(
                save_id,
                kind=TurnRequestKind.INPUT,
                raw_input=raw_input,
                pending_proposal=pending_proposal,
            )
            pending_proposal = result.pending_proposal

            if result.narration:
                self.console.print(f"\n[bold cyan]{result.narration}[/]")
            for message in result.messages:
                self.console.print(f"[yellow]{message}[/]")

            if result.view_kind == TurnViewKind.SCENE:
                self._render_scene(result.state.context, result.state.active_encounter_id)
            elif result.view_kind == TurnViewKind.INVENTORY:
                self._render_inventory(result.state.context)
            elif result.view_kind == TurnViewKind.QUESTS:
                self._render_quests(result.state.context)
            elif result.view_kind == TurnViewKind.MAP:
                self._render_map(result.state.context)
            elif result.view_kind == TurnViewKind.DEBUG and result.debug_payload is not None:
                self.console.print(result.debug_payload)

            if result.pending_proposal is not None:
                self._render_action_proposal(pending_proposal)

            if result.exit_to_menu:
                return

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
        self.console.print(f"Action Points: {context.action_points}/{context.max_action_points}")

    def _render_map(self, context) -> None:
        table = Table(title="Nearby Routes")
        table.add_column("Destination")
        table.add_column("Travel")
        for route in context.adjacent_places:
            table.add_row(route.destination_name, f"{route.travel_minutes} min")
        self.console.print(table)

    def _render_action_proposal(self, proposal: ActionProposal) -> None:
        table = Table(title="Proposed Action")
        table.add_column("Field")
        table.add_column("Value")
        table.add_row("Action", proposal.action_name)
        table.add_row("Description", proposal.description or proposal.raw_input)
        table.add_row("Avoid Failure", f"{proposal.avoid_failure_percent:.1f}%")
        table.add_row("Clean Success", f"{proposal.clean_success_percent:.1f}%")
        table.add_row("AP Cost", str(proposal.action_point_cost))
        if proposal.target_name:
            table.add_row("Target", proposal.target_name)
        if proposal.destination_name:
            table.add_row("Destination", proposal.destination_name)
        if proposal.created_this_turn:
            table.add_row("New Action", "Learned this turn")
        if proposal.blocker_message:
            table.add_row("Blocked", proposal.blocker_message)
        table.add_row("Confirm", "yes / do it / go ahead / confirm")
        table.add_row("Cancel", "no / cancel")
        self.console.print(table)

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
