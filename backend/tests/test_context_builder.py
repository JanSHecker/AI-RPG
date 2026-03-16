from __future__ import annotations


def test_context_builder_surfaces_public_facts_and_local_beliefs(save_id, world_repository, context_builder):
    player = world_repository.get_player(save_id)
    context = context_builder.build(save_id, player.id)

    fact_keys = {fact.fact_key for fact in context.visible_facts}
    belief_keys = {belief.belief_key for belief in context.relevant_beliefs}

    assert context.location.name == "Oakheart Village"
    assert "watchtower_goblins" in fact_keys
    assert "watchtower_old_seal" not in fact_keys
    assert "watchtower_raiders" in belief_keys
    assert context.action_points == 100
    assert context.max_action_points == 100
