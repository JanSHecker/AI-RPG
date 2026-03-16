from __future__ import annotations

from datetime import datetime

from ai_rpg.core.contracts import EventType, PatchOperation, PatchOperationKind, StatePatch, WorldEvent
from ai_rpg.db.event_repo import EventRepository
from ai_rpg.db.repositories import WorldRepository, new_id


class SimpleSimulationEngine:
    def __init__(self, world_repository: WorldRepository, event_repository: EventRepository):
        self.world_repository = world_repository
        self.event_repository = event_repository

    def advance(self, save_id: str, from_time: datetime, to_time: datetime) -> list[WorldEvent]:
        if to_time <= from_time:
            return []

        generated: list[WorldEvent] = []
        for scheduled in self.event_repository.due_events(save_id, to_time):
            payload = dict(scheduled.payload or {})
            if payload.get("kind") == "goblin_patrol" and scheduled.actor_entity_id:
                goblin = self.world_repository.get_entity(scheduled.actor_entity_id)
                goblin_stats = self.world_repository.get_entity_stats(scheduled.actor_entity_id)
                if goblin is not None and goblin_stats is not None and goblin_stats.hp > 0:
                    destination_id = goblin.location_entity_id
                    routes = self.world_repository.get_connected_places(save_id, goblin.location_entity_id or "")
                    if routes:
                        destination_id = routes[0].destination_id
                    patch = StatePatch(
                        save_id=save_id,
                        operations=[
                            PatchOperation(
                                kind=PatchOperationKind.MOVE_ENTITY,
                                target_id=goblin.id,
                                data={"location_entity_id": destination_id},
                            ),
                            PatchOperation(
                                kind=PatchOperationKind.CREATE_EVENT,
                                data={
                                    "event_id": new_id("event"),
                                    "event_type": EventType.SIMULATION.value,
                                    "title": "Goblin movement in the wilds",
                                    "description": "A goblin scout slips through the forest, emboldened by the passing hours.",
                                    "actor_entity_id": goblin.id,
                                    "location_entity_id": destination_id,
                                },
                            ),
                        ],
                    )
                    self.world_repository.apply_patch(patch)
                    event = WorldEvent(
                        id=new_id("world-event"),
                        event_type=EventType.SIMULATION,
                        title="Goblin movement in the wilds",
                        description="The frontier grows less safe the longer the watchtower is left alone.",
                        occurred_at=scheduled.scheduled_for,
                        actor_entity_id=goblin.id,
                        location_entity_id=destination_id,
                        metadata=payload,
                    )
                    self.event_repository.log_event(save_id, event)
                    generated.append(event)
            self.event_repository.mark_processed(scheduled.id)
        return generated
