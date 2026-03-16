from __future__ import annotations

from pathlib import Path

from ai_rpg.core.config import Settings
from ai_rpg.core.contracts import ActionProposal
from ai_rpg.runtime import build_runtime
from ai_rpg.game.turn_service import TurnRequestKind, TurnViewKind


def _settings_for(database_url: str) -> Settings:
    return Settings(
        db_path=Path(database_url.removeprefix("sqlite:///")),
        provider="test",
        model="test-model",
        api_base="http://example.invalid",
        api_key="test-key",
        debug=False,
    )


def test_turn_service_proposes_and_confirms_action(database_url, session_factory, llm_adapter):
    runtime = build_runtime(settings=_settings_for(database_url), session_factory=session_factory, llm_adapter=llm_adapter)
    save = runtime.save_repository.create_from_scenario("scenario.frontier_fantasy", "Service Save", player_name="Aria")

    proposal_result = runtime.turn_service.process(save.id, kind=TurnRequestKind.INPUT, raw_input="talk mayor")

    assert proposal_result.pending_proposal is not None
    assert proposal_result.pending_proposal.action_name == "Talk"

    confirm_result = runtime.turn_service.process(
        save.id,
        kind=TurnRequestKind.CONFIRM,
        pending_proposal=proposal_result.pending_proposal,
    )

    assert confirm_result.pending_proposal is None
    assert confirm_result.state.context.action_points == 90


def test_turn_service_keeps_pending_proposal_for_slash_commands(database_url, session_factory, llm_adapter):
    runtime = build_runtime(settings=_settings_for(database_url), session_factory=session_factory, llm_adapter=llm_adapter)
    save = runtime.save_repository.create_from_scenario("scenario.frontier_fantasy", "Command Save", player_name="Aria")

    proposal_result = runtime.turn_service.process(save.id, kind=TurnRequestKind.INPUT, raw_input="talk mayor")
    proposal = proposal_result.pending_proposal

    command_result = runtime.turn_service.process(
        save.id,
        kind=TurnRequestKind.INPUT,
        raw_input="/inventory",
        pending_proposal=proposal,
    )

    assert isinstance(command_result.pending_proposal, ActionProposal)
    assert command_result.pending_proposal.action_name == proposal.action_name
    assert command_result.view_kind == TurnViewKind.INVENTORY


def test_turn_service_derives_active_combat_from_persisted_encounter(database_url, session_factory, llm_adapter):
    runtime = build_runtime(settings=_settings_for(database_url), session_factory=session_factory, llm_adapter=llm_adapter)
    save = runtime.save_repository.create_from_scenario("scenario.frontier_fantasy", "Combat Save", player_name="Aria")

    travel_result = runtime.turn_service.process(save.id, kind=TurnRequestKind.INPUT, raw_input="head to watchtower")
    travel_confirm = runtime.turn_service.process(
        save.id,
        kind=TurnRequestKind.CONFIRM,
        pending_proposal=travel_result.pending_proposal,
    )
    assert travel_confirm.state.context.location is not None
    assert travel_confirm.state.context.location.name == "Ruined Watchtower"

    proposal_result = runtime.turn_service.process(save.id, kind=TurnRequestKind.INPUT, raw_input="attack goblin")
    combat_result = runtime.turn_service.process(
        save.id,
        kind=TurnRequestKind.CONFIRM,
        pending_proposal=proposal_result.pending_proposal,
    )

    assert combat_result.state.active_encounter_id is not None
    assert combat_result.state.context.location is not None
