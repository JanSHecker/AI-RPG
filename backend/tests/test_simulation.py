from __future__ import annotations

from ai_rpg.core.contracts import PatchOperation, PatchOperationKind, StatePatch


def test_simulation_advances_due_events(save_id, world_repository, simulation_engine):
    before = world_repository.get_save_time(save_id)
    world_repository.apply_patch(
        StatePatch(
            save_id=save_id,
            operations=[
                PatchOperation(
                    kind=PatchOperationKind.ADVANCE_TIME,
                    data={"minutes": 50},
                )
            ],
        )
    )
    after = world_repository.get_save_time(save_id)
    events = simulation_engine.advance(save_id, before, after)
    goblin = world_repository.get_entity(f"{save_id}:creature.goblin_scout")

    assert events
    assert events[0].event_type.value == "simulation"
    assert goblin.location_entity_id == f"{save_id}:place.oakheart"

