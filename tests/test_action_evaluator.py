from __future__ import annotations


def test_talking_to_elira_starts_quest(save_id, world_repository, context_builder, parser, evaluator):
    player = world_repository.get_player(save_id)
    context = context_builder.build(save_id, player.id)
    intent = parser.parse("talk mayor", player.id, context)
    resolution = evaluator.resolve(intent, context)

    assert resolution.allowed is True
    assert any(operation.kind.value == "update_quest" for operation in resolution.patch.operations)

    world_repository.apply_patch(resolution.patch)
    updated = context_builder.build(save_id, player.id)
    assert any(quest.title == "Scour the Watchtower" for quest in updated.active_quests)

