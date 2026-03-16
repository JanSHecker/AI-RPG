from __future__ import annotations

from ai_rpg.core.contracts import BeliefRecord, ContextBuilder, SceneContext, SceneEntity
from ai_rpg.db.repositories import WorldRepository


class DatabaseContextBuilder(ContextBuilder):
    def __init__(self, world_repository: WorldRepository):
        self.world_repository = world_repository

    def build(self, save_id: str, actor_id: str) -> SceneContext:
        actor = self.world_repository.get_entity(actor_id)
        if actor is None:
            raise ValueError(f"Unknown actor {actor_id}")
        actor_stats = self.world_repository.get_entity_stats(actor_id)
        location = self.world_repository.get_entity(actor.location_entity_id) if actor.location_entity_id else None
        nearby_entities = [
            entity
            for entity in self.world_repository.get_entities_in_location(save_id, actor.location_entity_id or "")
            if entity.id != actor_id
        ]
        relevant_holder_ids = [actor_id] + [entity.id for entity in nearby_entities]
        return SceneContext(
            save_id=save_id,
            actor_id=actor_id,
            current_time=self.world_repository.get_save_time(save_id),
            location=SceneEntity(
                id=location.id,
                name=location.name,
                entity_type=location.entity_type,
                description=location.description,
                is_hostile=location.is_hostile,
                is_player=location.is_player,
            )
            if location is not None
            else None,
            nearby_entities=nearby_entities,
            adjacent_places=self.world_repository.get_connected_places(save_id, actor.location_entity_id or ""),
            active_quests=self.world_repository.get_active_quests(save_id, actor_id),
            recent_events=self.world_repository.get_recent_events(save_id),
            visible_facts=self.world_repository.get_visible_facts(save_id, actor_id),
            relevant_beliefs=[BeliefRecord(**belief) for belief in self.world_repository.get_relevant_beliefs(save_id, relevant_holder_ids)],
            inventory=self.world_repository.get_inventory(save_id, actor_id),
            action_points=actor_stats.action_points if actor_stats is not None else 0,
            max_action_points=actor_stats.max_action_points if actor_stats is not None else 0,
        )
