from __future__ import annotations

from ai_rpg.core.contracts import ActionType, PatchOperation, PatchOperationKind, StatePatch, TurnIntent


def _catalog_intent(text: str, actor_id: str, phase: str = "propose", **metadata):
    return TurnIntent(
        raw_input=text,
        actor_id=actor_id,
        action_type=ActionType.CATALOG,
        content=text,
        metadata={"phase": phase, **metadata},
    )


def test_paraphrased_inputs_produce_out_of_combat_proposals(save_id, world_repository, context_builder, evaluator):
    player = world_repository.get_player(save_id)
    context = context_builder.build(save_id, player.id)

    talk_resolution = evaluator.resolve(_catalog_intent("chat with mayor", player.id), context)
    travel_resolution = evaluator.resolve(_catalog_intent("head to watchtower", player.id), context)

    assert talk_resolution.awaiting_confirmation is True
    assert talk_resolution.proposal is not None
    assert talk_resolution.proposal.action_name == "Talk"
    assert talk_resolution.proposal.target_name == "Mayor Elira"
    assert talk_resolution.proposal.avoid_failure_percent > 0
    assert talk_resolution.proposal.clean_success_percent > 0
    assert travel_resolution.awaiting_confirmation is True
    assert travel_resolution.proposal is not None
    assert travel_resolution.proposal.action_name == "Travel"
    assert travel_resolution.proposal.destination_name == "Ruined Watchtower"
    assert travel_resolution.proposal.avoid_failure_percent == 100.0


def test_confirming_talk_spends_action_points_and_starts_quest(save_id, world_repository, context_builder, evaluator):
    player = world_repository.get_player(save_id)
    context = context_builder.build(save_id, player.id)
    proposal_resolution = evaluator.resolve(_catalog_intent("talk mayor", player.id), context)

    confirm_resolution = evaluator.resolve(
        _catalog_intent(
            proposal_resolution.proposal.raw_input,
            player.id,
            "confirm",
            proposal=proposal_resolution.proposal.model_dump(mode="json"),
        ),
        context,
    )

    assert confirm_resolution.allowed is True
    assert any(operation.kind == PatchOperationKind.UPDATE_QUEST for operation in confirm_resolution.patch.operations)
    assert any(operation.kind == PatchOperationKind.ADJUST_ACTION_POINTS for operation in confirm_resolution.patch.operations)

    world_repository.apply_patch(confirm_resolution.patch)
    updated = context_builder.build(save_id, player.id)
    assert updated.action_points == 90
    assert any(quest.title == "Scour the Watchtower" for quest in updated.active_quests)


def test_created_action_is_persisted_on_proposal_and_reused(save_id, world_repository, action_repository, context_builder, evaluator):
    player = world_repository.get_player(save_id)
    context = context_builder.build(save_id, player.id)

    first_resolution = evaluator.resolve(_catalog_intent("search the rubble for clues", player.id), context)

    assert first_resolution.awaiting_confirmation is True
    assert first_resolution.proposal is not None
    assert first_resolution.proposal.created_this_turn is True
    scenario_id = world_repository.get_save_scenario_id(save_id)
    saved_actions = action_repository.list_actions(scenario_id)
    assert any(action.name == "Search the Rubble" for action in saved_actions)

    second_resolution = evaluator.resolve(_catalog_intent("search rubble", player.id), context)

    assert second_resolution.awaiting_confirmation is True
    assert second_resolution.proposal is not None
    assert second_resolution.proposal.created_this_turn is False
    assert second_resolution.proposal.action_id == first_resolution.proposal.action_id


def test_insufficient_action_points_blocks_confirmation(save_id, world_repository, context_builder, evaluator):
    player = world_repository.get_player(save_id)
    world_repository.apply_patch(
        StatePatch(
            save_id=save_id,
            operations=[
                PatchOperation(
                    kind=PatchOperationKind.ADJUST_ACTION_POINTS,
                    target_id=player.id,
                    data={"set_to": 5},
                )
            ],
        )
    )
    context = context_builder.build(save_id, player.id)

    resolution = evaluator.resolve(_catalog_intent("talk mayor", player.id), context)

    assert resolution.awaiting_confirmation is True
    assert resolution.proposal is not None
    assert resolution.proposal.can_confirm_now is False
    assert resolution.proposal.blocker_message == "Not enough action points"


def test_llm_effect_actions_filter_disallowed_operations_and_spend_action_points(
    save_id,
    world_repository,
    context_builder,
    evaluator,
):
    player = world_repository.get_player(save_id)
    context = context_builder.build(save_id, player.id)
    proposal_resolution = evaluator.resolve(_catalog_intent("forbidden ritual", player.id), context)

    confirm_resolution = evaluator.resolve(
        _catalog_intent(
            proposal_resolution.proposal.raw_input,
            player.id,
            "confirm",
            proposal=proposal_resolution.proposal.model_dump(mode="json"),
        ),
        context,
    )

    assert confirm_resolution.allowed is True
    assert all(operation.kind != PatchOperationKind.START_COMBAT for operation in confirm_resolution.patch.operations)
    assert any(operation.kind == PatchOperationKind.CREATE_EVENT for operation in confirm_resolution.patch.operations)
    assert any(operation.kind == PatchOperationKind.ADJUST_ACTION_POINTS for operation in confirm_resolution.patch.operations)

    world_repository.apply_patch(confirm_resolution.patch)
    updated = context_builder.build(save_id, player.id)
    assert updated.action_points == 75
