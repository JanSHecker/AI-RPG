from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import json

from ai_rpg.core.contracts import ActionProposal, ActionType, SceneContext, TurnIntent
from ai_rpg.db.combat_repo import CombatRepository
from ai_rpg.db.repositories import SaveRepository, WorldRepository
from ai_rpg.game.action_evaluator import HybridActionEvaluator
from ai_rpg.game.combat import SimpleCombatEngine
from ai_rpg.game.context_builder import DatabaseContextBuilder
from ai_rpg.game.intent_parser import IntentParser
from ai_rpg.game.simulation import SimpleSimulationEngine


class TurnRequestKind(str, Enum):
    INPUT = "input"
    CONFIRM = "confirm"
    CANCEL = "cancel"


class TurnViewKind(str, Enum):
    NONE = "none"
    SCENE = "scene"
    INVENTORY = "inventory"
    QUESTS = "quests"
    MAP = "map"
    DEBUG = "debug"


@dataclass(slots=True)
class TurnState:
    save_id: str
    player_id: str
    context: SceneContext
    active_encounter_id: str | None


@dataclass(slots=True)
class TurnServiceResult:
    state: TurnState
    pending_proposal: ActionProposal | None = None
    exit_to_menu: bool = False
    narration: str = ""
    messages: list[str] = field(default_factory=list)
    view_kind: TurnViewKind = TurnViewKind.NONE
    debug_payload: str | None = None


class TurnService:
    def __init__(
        self,
        *,
        settings,
        save_repository: SaveRepository,
        world_repository: WorldRepository,
        context_builder: DatabaseContextBuilder,
        intent_parser: IntentParser,
        action_evaluator: HybridActionEvaluator,
        combat_engine: SimpleCombatEngine,
        simulation_engine: SimpleSimulationEngine,
        combat_repository: CombatRepository,
    ):
        self.settings = settings
        self.save_repository = save_repository
        self.world_repository = world_repository
        self.context_builder = context_builder
        self.intent_parser = intent_parser
        self.action_evaluator = action_evaluator
        self.combat_engine = combat_engine
        self.simulation_engine = simulation_engine
        self.combat_repository = combat_repository

    def get_state(self, save_id: str) -> TurnState:
        save = self.save_repository.get(save_id)
        if save is None or save.player_entity_id is None:
            raise ValueError(f"Save {save_id} is missing.")
        player_id = save.player_entity_id
        context = self.context_builder.build(save_id, player_id)
        active_encounter = self.combat_repository.find_active_encounter_for_entity(save_id, player_id)
        return TurnState(
            save_id=save_id,
            player_id=player_id,
            context=context,
            active_encounter_id=active_encounter.id if active_encounter is not None else None,
        )

    def configuration_warnings(self) -> list[str]:
        warnings: list[str] = []
        if not getattr(self.settings, "api_key", None):
            warnings.append("AI_RPG_API_KEY is not configured. Freeform action matching may be unavailable.")
        return warnings

    def process(
        self,
        save_id: str,
        *,
        kind: TurnRequestKind,
        raw_input: str | None = None,
        pending_proposal: ActionProposal | None = None,
    ) -> TurnServiceResult:
        if kind == TurnRequestKind.CANCEL:
            state = self.get_state(save_id)
            if pending_proposal is None:
                return TurnServiceResult(state=state, messages=["There is no pending action to cancel."])
            return TurnServiceResult(state=state, messages=["You set the action aside."])

        state = self.get_state(save_id)
        context = state.context

        if kind == TurnRequestKind.CONFIRM:
            return self._confirm_pending_action(state, pending_proposal)

        text = raw_input or ""
        lowered = text.strip().lower()

        if pending_proposal is not None and lowered in {"yes", "do it", "go ahead", "confirm"}:
            return self._confirm_pending_action(state, pending_proposal)
        if pending_proposal is not None and lowered in {"no", "cancel"}:
            return TurnServiceResult(state=state, messages=["You set the action aside."])
        if pending_proposal is None and lowered in {"yes", "do it", "go ahead", "confirm"}:
            return TurnServiceResult(state=state, messages=["There is no pending action to confirm."])
        if pending_proposal is None and lowered in {"no", "cancel"}:
            return TurnServiceResult(state=state, messages=["There is no pending action to cancel."])

        if lowered in {"quit", "exit", "/exit"}:
            return TurnServiceResult(state=state, exit_to_menu=True, messages=["Returning to the main menu."])

        if text.startswith("/"):
            intent = self.intent_parser.parse(text, state.player_id, context)
            if intent.action_type == ActionType.COMMAND:
                result = self._handle_command(state, intent.command or "")
                if pending_proposal is not None and not result.exit_to_menu:
                    return TurnServiceResult(
                        state=result.state,
                        pending_proposal=pending_proposal,
                        exit_to_menu=result.exit_to_menu,
                        narration=result.narration,
                        messages=result.messages,
                        view_kind=result.view_kind,
                        debug_payload=result.debug_payload,
                    )
                return result

        if not text.strip():
            return TurnServiceResult(state=state, messages=["Enter an action."])

        if state.active_encounter_id:
            intent = self.intent_parser.parse(text, state.player_id, context)
            resolution = self.combat_engine.resolve_turn_for_entity(state.active_encounter_id, state.player_id, intent)
            return self._finalize_resolution(state.save_id, resolution)

        resolution = self.action_evaluator.resolve(
            TurnIntent(
                raw_input=text,
                actor_id=state.player_id,
                action_type=ActionType.CATALOG,
                content=text,
                metadata={"phase": "propose"},
            ),
            context,
        )
        return self._finalize_resolution(state.save_id, resolution)

    def _confirm_pending_action(self, state: TurnState, proposal: ActionProposal | None) -> TurnServiceResult:
        if proposal is None:
            return TurnServiceResult(state=state, messages=["There is no pending action to confirm."])
        if not proposal.can_confirm_now:
            return TurnServiceResult(
                state=state,
                pending_proposal=proposal,
                messages=[proposal.blocker_message or "That action cannot be confirmed."],
            )

        resolution = self.action_evaluator.resolve(
            TurnIntent(
                raw_input=proposal.raw_input,
                actor_id=state.player_id,
                action_type=ActionType.CATALOG,
                content=proposal.raw_input,
                metadata={
                    "phase": "confirm",
                    "proposal": proposal.model_dump(mode="json"),
                },
            ),
            state.context,
        )
        return self._finalize_resolution(state.save_id, resolution)

    def _handle_command(self, state: TurnState, command: str) -> TurnServiceResult:
        if command == "help":
            return TurnServiceResult(
                state=state,
                messages=["/help, /look, /inventory, /quests, /map, /save, /debug, /exit"],
            )
        if command == "look":
            return TurnServiceResult(state=state, view_kind=TurnViewKind.SCENE)
        if command == "inventory":
            return TurnServiceResult(state=state, view_kind=TurnViewKind.INVENTORY)
        if command == "quests":
            return TurnServiceResult(state=state, view_kind=TurnViewKind.QUESTS)
        if command == "map":
            return TurnServiceResult(state=state, view_kind=TurnViewKind.MAP)
        if command == "save":
            return TurnServiceResult(
                state=state,
                messages=["The world is already persisted after every resolved action."],
            )
        if command == "debug":
            return TurnServiceResult(
                state=state,
                view_kind=TurnViewKind.DEBUG,
                debug_payload=json.dumps(state.context.model_dump(mode="json"), indent=2, default=str),
            )
        if command in {"exit", "load"}:
            return TurnServiceResult(state=state, exit_to_menu=True, messages=["Returning to the main menu."])
        return TurnServiceResult(state=state, messages=[f"Unknown command: /{command}"])

    def _finalize_resolution(self, save_id: str, resolution) -> TurnServiceResult:
        before_time = self.world_repository.get_save_time(save_id)
        if resolution.patch.operations:
            self.world_repository.apply_patch(resolution.patch)
        after_time = self.world_repository.get_save_time(save_id)
        if after_time > before_time:
            self.simulation_engine.advance(save_id, before_time, after_time)

        state = self.get_state(save_id)
        return TurnServiceResult(
            state=state,
            pending_proposal=resolution.proposal if resolution.awaiting_confirmation else None,
            narration=resolution.narration,
            messages=list(resolution.messages),
        )
