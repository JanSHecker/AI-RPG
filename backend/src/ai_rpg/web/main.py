from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, PlainTextResponse
import uvicorn

from ai_rpg.game.turn_service import TurnRequestKind, TurnServiceResult, TurnViewKind
from ai_rpg.runtime import GameRuntime, build_runtime
from ai_rpg.web.schemas import (
    BootstrapResponse,
    CreateSaveRequest,
    CreateScenarioRequest,
    EncounterCombatant,
    EncounterSummary,
    GameSnapshot,
    PlayerStatus,
    SaveSummary,
    ScenarioSummary,
    TerminalEntry,
    TurnRequest,
    TurnResponse,
)


@lru_cache(maxsize=1)
def get_runtime() -> GameRuntime:
    return build_runtime()


def _entry(kind: str, content: str, *, title: str | None = None) -> TerminalEntry:
    return TerminalEntry(id=uuid4().hex[:12], kind=kind, title=title, content=content)


def _format_routes(context) -> str:
    if not context.adjacent_places:
        return "No nearby routes."
    return "\n".join(f"- {route.destination_name} ({route.travel_minutes} min)" for route in context.adjacent_places)


def _format_inventory(context) -> str:
    if not context.inventory:
        return "Inventory: empty"
    return "\n".join(f"- {item.item_name} x{item.quantity}" for item in context.inventory)


def _format_quests(context) -> str:
    if not context.active_quests:
        return "No active quests."
    return "\n".join(f"- {quest.title} [{quest.status.value}] {quest.notes}".strip() for quest in context.active_quests)


def _format_proposal(proposal) -> str:
    lines = [
        f"Action: {proposal.action_name}",
        f"Description: {proposal.description or proposal.raw_input}",
        f"Avoid Failure: {proposal.avoid_failure_percent:.1f}%",
        f"Clean Success: {proposal.clean_success_percent:.1f}%",
        f"AP Cost: {proposal.action_point_cost}",
    ]
    if proposal.target_name:
        lines.append(f"Target: {proposal.target_name}")
    if proposal.destination_name:
        lines.append(f"Destination: {proposal.destination_name}")
    if proposal.blocker_message:
        lines.append(f"Blocked: {proposal.blocker_message}")
    lines.append("Confirm: yes / do it / go ahead / confirm")
    lines.append("Cancel: no / cancel")
    return "\n".join(lines)


def _serialize_encounter(runtime: GameRuntime, encounter_id: str) -> EncounterSummary | None:
    encounter = runtime.combat_repository.get_encounter(encounter_id)
    if encounter is None:
        return None

    combatants: list[EncounterCombatant] = []
    active_entity_id: str | None = None
    for combatant in runtime.combat_repository.get_combatants(encounter_id):
        entity = runtime.world_repository.get_entity(combatant.entity_id)
        stats = runtime.world_repository.get_entity_stats(combatant.entity_id)
        is_active = encounter.active_combatant_id == combatant.id
        if is_active:
            active_entity_id = combatant.entity_id
        combatants.append(
            EncounterCombatant(
                entity_id=combatant.entity_id,
                name=entity.name if entity is not None else combatant.entity_id,
                current_hp=stats.hp if stats is not None else combatant.current_hp,
                max_hp=stats.max_hp if stats is not None else combatant.current_hp,
                is_player=bool(entity.is_player) if entity is not None else False,
                is_defeated=combatant.is_defeated,
                is_active=is_active,
            )
        )

    player_turn = any(combatant.is_player and combatant.is_active for combatant in combatants)
    return EncounterSummary(
        encounter_id=encounter.id,
        state=encounter.state,
        round_number=encounter.round_number,
        location_entity_id=encounter.location_entity_id,
        active_entity_id=active_entity_id,
        player_turn=player_turn,
        combatants=combatants,
    )


def _build_seed_entries(snapshot: GameSnapshot) -> list[TerminalEntry]:
    context = snapshot.scene_context
    entries = [
        _entry(
            "system",
            f"{context.current_time}",
            title=f"{context.location.name if context.location else 'Unknown'}{' [combat]' if snapshot.active_encounter else ''}",
        )
    ]
    if context.location and context.location.description:
        entries.append(_entry("narration", context.location.description))

    status_lines: list[str] = []
    if context.nearby_entities:
        status_lines.append("Nearby: " + ", ".join(entity.name for entity in context.nearby_entities))
    if context.adjacent_places:
        status_lines.append("Routes: " + ", ".join(place.destination_name for place in context.adjacent_places))
    status_lines.append(f"Action Points: {context.action_points}/{context.max_action_points}")
    entries.append(_entry("message", "\n".join(status_lines)))

    if snapshot.active_encounter is not None:
        combat_lines = [
            f"Round: {snapshot.active_encounter.round_number}",
            f"Active: {snapshot.active_encounter.active_entity_id or 'Unknown'}",
        ]
        combat_lines.extend(
            f"- {combatant.name}: {combatant.current_hp}/{combatant.max_hp}{' (active)' if combatant.is_active else ''}{' [down]' if combatant.is_defeated else ''}"
            for combatant in snapshot.active_encounter.combatants
        )
        entries.append(_entry("panel", "\n".join(combat_lines), title="Combat"))
    return entries


def _build_snapshot(runtime: GameRuntime, save_id: str) -> GameSnapshot:
    save = runtime.save_repository.get(save_id)
    if save is None or save.player_entity_id is None:
        raise HTTPException(status_code=404, detail="Unknown save.")

    state = runtime.turn_service.get_state(save_id)
    scenario = runtime.scenario_repository.get(save.scenario_id)
    player = runtime.world_repository.get_entity(state.player_id)
    player_stats = runtime.world_repository.get_entity_stats(state.player_id)
    if player is None or player_stats is None:
        raise HTTPException(status_code=500, detail="Player state is incomplete.")

    active_encounter = None
    if state.active_encounter_id is not None:
        active_encounter = _serialize_encounter(runtime, state.active_encounter_id)

    snapshot = GameSnapshot(
        save_id=save.id,
        save_name=save.name,
        scenario_id=save.scenario_id,
        scenario_name=scenario.name if scenario is not None else save.scenario_id,
        player_name=player.name,
        scene_context=state.context,
        player_status=PlayerStatus(
            entity_id=player.id,
            name=player.name,
            hp=player_stats.hp,
            max_hp=player_stats.max_hp,
            stamina=player_stats.stamina,
            max_stamina=player_stats.max_stamina,
            action_points=player_stats.action_points,
            max_action_points=player_stats.max_action_points,
        ),
        recent_events=runtime.world_repository.get_recent_events(save_id, limit=10),
        active_encounter=active_encounter,
        configuration_warnings=runtime.turn_service.configuration_warnings(),
        seed_entries=[],
    )
    return snapshot.model_copy(update={"seed_entries": _build_seed_entries(snapshot)})


def _build_save_summary(runtime: GameRuntime, save) -> SaveSummary:
    scenario = runtime.scenario_repository.get(save.scenario_id)
    player_name = None
    if save.player_entity_id:
        player = runtime.world_repository.get_entity(save.player_entity_id)
        player_name = player.name if player is not None else None
    return SaveSummary(
        id=save.id,
        name=save.name,
        scenario_id=save.scenario_id,
        scenario_name=scenario.name if scenario is not None else save.scenario_id,
        player_name=player_name,
        updated_at=save.updated_at,
    )


def _build_turn_entries(runtime: GameRuntime, result: TurnServiceResult) -> list[TerminalEntry]:
    entries: list[TerminalEntry] = []
    snapshot = _build_snapshot(runtime, result.state.save_id)
    if result.view_kind == TurnViewKind.SCENE:
        entries.extend(snapshot.seed_entries)
    elif result.view_kind == TurnViewKind.INVENTORY:
        entries.append(_entry("panel", _format_inventory(result.state.context), title="Inventory"))
    elif result.view_kind == TurnViewKind.QUESTS:
        entries.append(_entry("panel", _format_quests(result.state.context), title="Quests"))
    elif result.view_kind == TurnViewKind.MAP:
        entries.append(_entry("panel", _format_routes(result.state.context), title="Nearby Routes"))
    elif result.view_kind == TurnViewKind.DEBUG and result.debug_payload is not None:
        entries.append(_entry("panel", result.debug_payload, title="Debug"))

    if result.narration:
        entries.append(_entry("narration", result.narration))
    for message in result.messages:
        entries.append(_entry("message", message))
    if result.pending_proposal is not None:
        entries.append(_entry("panel", _format_proposal(result.pending_proposal), title="Proposed Action"))
    return entries


def create_app(runtime: GameRuntime | None = None) -> FastAPI:
    actual_runtime = runtime

    def resolve_runtime() -> GameRuntime:
        return actual_runtime or get_runtime()

    app = FastAPI(title="AI-RPG Web")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    router = APIRouter(prefix="/api")

    @router.get("/bootstrap", response_model=BootstrapResponse)
    def bootstrap() -> BootstrapResponse:
        runtime = resolve_runtime()
        scenarios = [
            ScenarioSummary(
                id=scenario.id,
                name=scenario.name,
                description=scenario.description,
                is_builtin=scenario.is_builtin,
            )
            for scenario in runtime.scenario_repository.list_scenarios()
        ]
        saves = [_build_save_summary(runtime, save) for save in runtime.save_repository.list_saves()]
        return BootstrapResponse(
            scenarios=scenarios,
            saves=saves,
            configuration_warnings=runtime.turn_service.configuration_warnings(),
        )

    @router.post("/scenarios", response_model=ScenarioSummary, status_code=201)
    def create_scenario(payload: CreateScenarioRequest) -> ScenarioSummary:
        runtime = resolve_runtime()
        scenario = runtime.seed_loader.create_empty_scenario(name=payload.name, description=payload.description)
        if scenario is None:
            raise HTTPException(status_code=500, detail="Scenario could not be created.")
        return ScenarioSummary(
            id=scenario.id,
            name=scenario.name,
            description=scenario.description,
            is_builtin=scenario.is_builtin,
        )

    @router.post("/saves", response_model=SaveSummary, status_code=201)
    def create_save(payload: CreateSaveRequest) -> SaveSummary:
        runtime = resolve_runtime()
        try:
            save = runtime.save_repository.create_from_scenario(
                payload.scenario_id,
                payload.save_name,
                player_name=payload.player_name,
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return _build_save_summary(runtime, save)

    @router.get("/saves/{save_id}", response_model=GameSnapshot)
    def get_save_snapshot(save_id: str) -> GameSnapshot:
        runtime = resolve_runtime()
        return _build_snapshot(runtime, save_id)

    @router.post("/saves/{save_id}/turn", response_model=TurnResponse)
    def process_turn(save_id: str, payload: TurnRequest) -> TurnResponse:
        runtime = resolve_runtime()
        if runtime.save_repository.get(save_id) is None:
            raise HTTPException(status_code=404, detail="Unknown save.")
        result = runtime.turn_service.process(
            save_id,
            kind=TurnRequestKind(payload.kind),
            raw_input=payload.raw_input,
            pending_proposal=payload.proposal,
        )
        return TurnResponse(
            snapshot=_build_snapshot(runtime, save_id),
            terminal_entries=_build_turn_entries(runtime, result),
            pending_proposal=result.pending_proposal,
            exit_to_menu=result.exit_to_menu,
        )

    app.include_router(router)

    frontend_dist = Path(__file__).resolve().parents[4] / "frontend" / "dist"

    @app.get("/{full_path:path}", include_in_schema=False)
    def serve_frontend(full_path: str):
        if frontend_dist.exists():
            candidate = frontend_dist / full_path
            if full_path and candidate.is_file():
                return FileResponse(candidate)
            index_file = frontend_dist / "index.html"
            if index_file.exists():
                return FileResponse(index_file)
        return PlainTextResponse(
            "Frontend assets are not built. Run the Vite dev server from ../frontend or build the frontend.",
            status_code=200,
        )

    return app


app = create_app()


def run() -> None:
    uvicorn.run("ai_rpg.web.main:app", host="127.0.0.1", port=8000, reload=False)


if __name__ == "__main__":
    run()
