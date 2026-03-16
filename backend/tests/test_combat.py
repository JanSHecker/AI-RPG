from __future__ import annotations

from ai_rpg.core.contracts import ActionType, PatchOperation, PatchOperationKind, StatePatch, TurnIntent


def test_confirming_attack_proposal_creates_combat_damage(save_id, world_repository, context_builder, evaluator):
    player = world_repository.get_player(save_id)
    world_repository.apply_patch(
        StatePatch(
            save_id=save_id,
            operations=[
                PatchOperation(
                    kind=PatchOperationKind.MOVE_ENTITY,
                    target_id=player.id,
                    data={"location_entity_id": f"{save_id}:place.watchtower"},
                )
            ],
        )
    )
    context = context_builder.build(save_id, player.id)
    proposal = evaluator.resolve(
        TurnIntent(
            raw_input="swing at goblin",
            actor_id=player.id,
            action_type=ActionType.CATALOG,
            content="swing at goblin",
            metadata={"phase": "propose"},
        ),
        context,
    )
    goblin_before = world_repository.get_entity_stats(f"{save_id}:creature.goblin_scout").hp

    resolution = evaluator.resolve(
        TurnIntent(
            raw_input=proposal.proposal.raw_input,
            actor_id=player.id,
            action_type=ActionType.CATALOG,
            content=proposal.proposal.raw_input,
            metadata={
                "phase": "confirm",
                "proposal": proposal.proposal.model_dump(mode="json"),
            },
        ),
        context,
    )
    assert resolution.allowed is True
    assert resolution.encounter_id is not None

    world_repository.apply_patch(resolution.patch)
    goblin_after = world_repository.get_entity_stats(f"{save_id}:creature.goblin_scout").hp
    assert goblin_after < goblin_before
