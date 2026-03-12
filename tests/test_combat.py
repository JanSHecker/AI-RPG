from __future__ import annotations

from ai_rpg.core.contracts import PatchOperation, PatchOperationKind, StatePatch


def test_attacking_hostile_creates_combat_damage(save_id, world_repository, context_builder, parser, evaluator):
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
    intent = parser.parse("attack goblin", player.id, context)
    goblin_before = world_repository.get_entity_stats(f"{save_id}:creature.goblin_scout").hp

    resolution = evaluator.resolve(intent, context)
    assert resolution.allowed is True
    assert resolution.encounter_id is not None

    world_repository.apply_patch(resolution.patch)
    goblin_after = world_repository.get_entity_stats(f"{save_id}:creature.goblin_scout").hp
    assert goblin_after < goblin_before

