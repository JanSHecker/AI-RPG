from __future__ import annotations

from datetime import timedelta
from typing import Any
from uuid import uuid4

from sqlalchemy import Select, desc, select
from sqlalchemy.orm import Session, sessionmaker

from ai_rpg.core.contracts import (
    EntityType,
    EventSummary,
    EventType,
    InventoryEntry,
    PatchOperationKind,
    QuestSnapshot,
    QuestStatus,
    SceneConnection,
    SceneEntity,
    SceneFact,
    StatePatch,
)
from ai_rpg.db.models import (
    Belief,
    Entity,
    EntityStats,
    Event,
    Fact,
    FactVisibility,
    Inventory,
    InventoryItem,
    PlaceConnection,
    Quest,
    QuestState,
    Relationship,
    Save,
    Scenario,
    ScheduledEvent,
    WorldClock,
    utcnow,
)
from ai_rpg.db.session import session_scope


def new_id(prefix: str) -> str:
    return f"{prefix}-{uuid4().hex[:12]}"


def clone_scoped_id(save_id: str, source_id: str | None) -> str | None:
    if source_id is None:
        return None
    return f"{save_id}:{source_id}"


class ScenarioRepository:
    def __init__(self, session_factory: sessionmaker[Session]):
        self.session_factory = session_factory

    def list_scenarios(self) -> list[Scenario]:
        with session_scope(self.session_factory) as session:
            stmt = select(Scenario).order_by(desc(Scenario.is_builtin), Scenario.name)
            return list(session.scalars(stmt))

    def get(self, scenario_id: str) -> Scenario | None:
        with session_scope(self.session_factory) as session:
            return session.get(Scenario, scenario_id)

    def create_scenario(
        self,
        name: str,
        description: str = "",
        *,
        scenario_id: str | None = None,
        is_builtin: bool = False,
    ) -> Scenario:
        with session_scope(self.session_factory) as session:
            actual_id = scenario_id or new_id("scenario")
            scenario = session.get(Scenario, actual_id)
            if scenario is None:
                scenario = Scenario(
                    id=actual_id,
                    name=name,
                    description=description,
                    is_builtin=is_builtin,
                )
                session.add(scenario)
            else:
                scenario.name = name
                scenario.description = description
                scenario.is_builtin = is_builtin
            clock = session.scalar(select(WorldClock).where(WorldClock.scenario_id == actual_id))
            if clock is None:
                session.add(
                    WorldClock(
                        id=f"clock:{actual_id}",
                        scenario_id=actual_id,
                        current_time=utcnow(),
                    )
                )
            session.flush()
            return scenario


class SaveRepository:
    def __init__(self, session_factory: sessionmaker[Session]):
        self.session_factory = session_factory

    def list_saves(self) -> list[Save]:
        with session_scope(self.session_factory) as session:
            stmt = select(Save).order_by(desc(Save.updated_at))
            return list(session.scalars(stmt))

    def get(self, save_id: str) -> Save | None:
        with session_scope(self.session_factory) as session:
            return session.get(Save, save_id)

    def create_from_scenario(
        self,
        scenario_id: str,
        save_name: str,
        *,
        player_name: str = "Wanderer",
    ) -> Save:
        save_id = new_id("save")
        with session_scope(self.session_factory) as session:
            scenario = session.get(Scenario, scenario_id)
            if scenario is None:
                raise ValueError(f"Unknown scenario: {scenario_id}")

            save = Save(id=save_id, scenario_id=scenario_id, name=save_name)
            session.add(save)
            session.flush()

            self._clone_table(session, Entity, scenario_id, save_id, self._clone_entity)
            self._clone_table(session, EntityStats, scenario_id, save_id, self._clone_entity_stats)
            self._clone_table(session, PlaceConnection, scenario_id, save_id, self._clone_place_connection)
            self._clone_table(session, Inventory, scenario_id, save_id, self._clone_inventory)
            self._clone_table(session, InventoryItem, scenario_id, save_id, self._clone_inventory_item)
            self._clone_table(session, Quest, scenario_id, save_id, self._clone_quest)
            self._clone_table(session, QuestState, scenario_id, save_id, self._clone_quest_state)
            self._clone_table(session, Event, scenario_id, save_id, self._clone_event)
            self._clone_table(session, ScheduledEvent, scenario_id, save_id, self._clone_scheduled_event)
            self._clone_table(session, Fact, scenario_id, save_id, self._clone_fact)
            self._clone_table(session, FactVisibility, scenario_id, save_id, self._clone_fact_visibility)
            self._clone_table(session, Belief, scenario_id, save_id, self._clone_belief)
            self._clone_table(session, Relationship, scenario_id, save_id, self._clone_relationship)

            clock = session.scalar(select(WorldClock).where(WorldClock.scenario_id == scenario_id))
            clock_time = clock.current_time if clock else utcnow()
            session.add(WorldClock(id=f"clock:{save_id}", save_id=save_id, current_time=clock_time))

            start_place = None
            place_stmt = select(Entity).where(
                Entity.save_id == save_id,
                Entity.entity_type == EntityType.PLACE,
            )
            for place in session.scalars(place_stmt):
                if (place.details or {}).get("start"):
                    start_place = place
                    break
                if start_place is None:
                    start_place = place
            if start_place is None:
                raise ValueError("Scenario has no place to start from.")

            player_entity = Entity(
                id=f"{save_id}:player",
                save_id=save_id,
                entity_type=EntityType.PLAYER,
                name=player_name,
                description="A determined adventurer.",
                location_entity_id=start_place.id,
                is_player=True,
                details={"origin": "player"},
            )
            session.add(player_entity)
            session.add(
                EntityStats(
                    id=f"{save_id}:player:stats",
                    save_id=save_id,
                    entity_id=player_entity.id,
                    strength=12,
                    dexterity=12,
                    constitution=12,
                    intelligence=11,
                    wisdom=11,
                    charisma=12,
                    diplomacy=2,
                    survival=1,
                    stealth=1,
                    melee=2,
                    hp=16,
                    max_hp=16,
                    stamina=12,
                    max_stamina=12,
                )
            )
            session.add(Inventory(id=f"{save_id}:player:inventory", save_id=save_id, owner_entity_id=player_entity.id))
            save.player_entity_id = player_entity.id
            session.add(
                Event(
                    id=f"{save_id}:event:intro",
                    save_id=save_id,
                    event_type=EventType.SYSTEM,
                    title="A new journey begins",
                    description=f"{player_name} arrives in {start_place.name} seeking purpose.",
                    occurred_at=clock_time,
                    actor_entity_id=player_entity.id,
                    location_entity_id=start_place.id,
                )
            )
            session.flush()
            return save

    def _clone_table(
        self,
        session: Session,
        model: type,
        scenario_id: str,
        save_id: str,
        clone_fn,
    ) -> None:
        stmt = select(model).where(getattr(model, "scenario_id") == scenario_id)
        for row in session.scalars(stmt):
            session.add(clone_fn(row, save_id))

    def _clone_entity(self, row: Entity, save_id: str) -> Entity:
        return Entity(
            id=clone_scoped_id(save_id, row.id),
            save_id=save_id,
            source_template_id=row.id,
            entity_type=row.entity_type,
            name=row.name,
            description=row.description,
            location_entity_id=clone_scoped_id(save_id, row.location_entity_id),
            faction_entity_id=clone_scoped_id(save_id, row.faction_entity_id),
            is_player=row.is_player,
            is_hostile=row.is_hostile,
            details=dict(row.details or {}),
        )

    def _clone_entity_stats(self, row: EntityStats, save_id: str) -> EntityStats:
        return EntityStats(
            id=clone_scoped_id(save_id, row.id),
            save_id=save_id,
            entity_id=clone_scoped_id(save_id, row.entity_id),
            strength=row.strength,
            dexterity=row.dexterity,
            constitution=row.constitution,
            intelligence=row.intelligence,
            wisdom=row.wisdom,
            charisma=row.charisma,
            diplomacy=row.diplomacy,
            survival=row.survival,
            stealth=row.stealth,
            melee=row.melee,
            hp=row.hp,
            max_hp=row.max_hp,
            stamina=row.stamina,
            max_stamina=row.max_stamina,
        )

    def _clone_place_connection(self, row: PlaceConnection, save_id: str) -> PlaceConnection:
        return PlaceConnection(
            id=clone_scoped_id(save_id, row.id),
            save_id=save_id,
            source_template_id=row.id,
            from_place_id=clone_scoped_id(save_id, row.from_place_id),
            to_place_id=clone_scoped_id(save_id, row.to_place_id),
            travel_minutes=row.travel_minutes,
            description=row.description,
        )

    def _clone_inventory(self, row: Inventory, save_id: str) -> Inventory:
        return Inventory(
            id=clone_scoped_id(save_id, row.id),
            save_id=save_id,
            owner_entity_id=clone_scoped_id(save_id, row.owner_entity_id),
        )

    def _clone_inventory_item(self, row: InventoryItem, save_id: str) -> InventoryItem:
        return InventoryItem(
            id=clone_scoped_id(save_id, row.id),
            save_id=save_id,
            inventory_id=clone_scoped_id(save_id, row.inventory_id),
            item_entity_id=clone_scoped_id(save_id, row.item_entity_id),
            quantity=row.quantity,
        )

    def _clone_quest(self, row: Quest, save_id: str) -> Quest:
        return Quest(
            id=clone_scoped_id(save_id, row.id),
            save_id=save_id,
            source_template_id=row.id,
            title=row.title,
            description=row.description,
            giver_entity_id=clone_scoped_id(save_id, row.giver_entity_id),
            target_entity_id=clone_scoped_id(save_id, row.target_entity_id),
            reward_text=row.reward_text,
        )

    def _clone_quest_state(self, row: QuestState, save_id: str) -> QuestState:
        return QuestState(
            id=clone_scoped_id(save_id, row.id),
            save_id=save_id,
            quest_id=clone_scoped_id(save_id, row.quest_id),
            actor_entity_id=clone_scoped_id(save_id, row.actor_entity_id),
            status=row.status,
            progress=row.progress,
            notes=row.notes,
        )

    def _clone_event(self, row: Event, save_id: str) -> Event:
        return Event(
            id=clone_scoped_id(save_id, row.id),
            save_id=save_id,
            source_template_id=row.id,
            event_type=row.event_type,
            title=row.title,
            description=row.description,
            occurred_at=row.occurred_at,
            actor_entity_id=clone_scoped_id(save_id, row.actor_entity_id),
            target_entity_id=clone_scoped_id(save_id, row.target_entity_id),
            location_entity_id=clone_scoped_id(save_id, row.location_entity_id),
            payload=dict(row.payload or {}),
        )

    def _clone_scheduled_event(self, row: ScheduledEvent, save_id: str) -> ScheduledEvent:
        return ScheduledEvent(
            id=clone_scoped_id(save_id, row.id),
            save_id=save_id,
            source_template_id=row.id,
            event_type=row.event_type,
            description=row.description,
            scheduled_for=row.scheduled_for,
            actor_entity_id=clone_scoped_id(save_id, row.actor_entity_id),
            target_entity_id=clone_scoped_id(save_id, row.target_entity_id),
            location_entity_id=clone_scoped_id(save_id, row.location_entity_id),
            processed=row.processed,
            payload=dict(row.payload or {}),
        )

    def _clone_fact(self, row: Fact, save_id: str) -> Fact:
        return Fact(
            id=clone_scoped_id(save_id, row.id),
            save_id=save_id,
            source_template_id=row.id,
            subject_entity_id=clone_scoped_id(save_id, row.subject_entity_id),
            fact_key=row.fact_key,
            truth_text=row.truth_text,
            truth_value=row.truth_value,
        )

    def _clone_fact_visibility(self, row: FactVisibility, save_id: str) -> FactVisibility:
        return FactVisibility(
            id=clone_scoped_id(save_id, row.id),
            save_id=save_id,
            source_template_id=row.id,
            fact_id=clone_scoped_id(save_id, row.fact_id),
            viewer_entity_id=clone_scoped_id(save_id, row.viewer_entity_id),
            viewer_role=row.viewer_role,
        )

    def _clone_belief(self, row: Belief, save_id: str) -> Belief:
        return Belief(
            id=clone_scoped_id(save_id, row.id),
            save_id=save_id,
            source_template_id=row.id,
            holder_entity_id=clone_scoped_id(save_id, row.holder_entity_id),
            fact_id=clone_scoped_id(save_id, row.fact_id),
            belief_key=row.belief_key,
            belief_text=row.belief_text,
            confidence=row.confidence,
        )

    def _clone_relationship(self, row: Relationship, save_id: str) -> Relationship:
        return Relationship(
            id=clone_scoped_id(save_id, row.id),
            save_id=save_id,
            source_template_id=row.id,
            source_entity_id=clone_scoped_id(save_id, row.source_entity_id),
            target_entity_id=clone_scoped_id(save_id, row.target_entity_id),
            attitude=row.attitude,
            score=row.score,
            notes=row.notes,
        )


class WorldRepository:
    def __init__(self, session_factory: sessionmaker[Session]):
        self.session_factory = session_factory

    def get_save_time(self, save_id: str):
        with session_scope(self.session_factory) as session:
            clock = session.scalar(select(WorldClock).where(WorldClock.save_id == save_id))
            if clock is None:
                raise ValueError(f"Missing world clock for save {save_id}")
            return clock.current_time

    def get_player(self, save_id: str) -> Entity:
        with session_scope(self.session_factory) as session:
            save = session.get(Save, save_id)
            if save is None or save.player_entity_id is None:
                raise ValueError(f"Save {save_id} has no player.")
            player = session.get(Entity, save.player_entity_id)
            if player is None:
                raise ValueError(f"Player entity missing for save {save_id}")
            return player

    def get_entity(self, entity_id: str) -> Entity | None:
        with session_scope(self.session_factory) as session:
            return session.get(Entity, entity_id)

    def get_entity_stats(self, entity_id: str) -> EntityStats | None:
        with session_scope(self.session_factory) as session:
            stmt = select(EntityStats).where(EntityStats.entity_id == entity_id)
            return session.scalar(stmt)

    def resolve_entity_by_name(self, save_id: str, location_entity_id: str, name: str) -> Entity | None:
        lowered = name.strip().lower()
        with session_scope(self.session_factory) as session:
            stmt = select(Entity).where(
                Entity.save_id == save_id,
                Entity.location_entity_id == location_entity_id,
            )
            for entity in session.scalars(stmt):
                if entity.name.lower() == lowered or lowered in entity.name.lower():
                    return entity
            return None

    def resolve_place_by_name(self, save_id: str, from_place_id: str, name: str) -> Entity | None:
        lowered = name.strip().lower()
        with session_scope(self.session_factory) as session:
            stmt = (
                select(Entity)
                .join(PlaceConnection, PlaceConnection.to_place_id == Entity.id)
                .where(
                    Entity.save_id == save_id,
                    PlaceConnection.save_id == save_id,
                    PlaceConnection.from_place_id == from_place_id,
                )
            )
            for entity in session.scalars(stmt):
                if entity.name.lower() == lowered or lowered in entity.name.lower():
                    return entity
            return None

    def get_entities_in_location(self, save_id: str, location_entity_id: str) -> list[SceneEntity]:
        with session_scope(self.session_factory) as session:
            stmt = (
                select(Entity, Relationship.score)
                .outerjoin(
                    Relationship,
                    (Relationship.source_entity_id == location_entity_id)
                    & (Relationship.target_entity_id == Entity.id)
                    & (Relationship.save_id == save_id),
                )
                .where(
                    Entity.save_id == save_id,
                    Entity.location_entity_id == location_entity_id,
                )
                .order_by(Entity.name)
            )
            return [
                SceneEntity(
                    id=entity.id,
                    name=entity.name,
                    entity_type=entity.entity_type,
                    description=entity.description,
                    is_hostile=entity.is_hostile,
                    is_player=entity.is_player,
                    attitude=score or 0,
                )
                for entity, score in session.execute(stmt)
            ]

    def get_connected_places(self, save_id: str, from_place_id: str) -> list[SceneConnection]:
        with session_scope(self.session_factory) as session:
            stmt = (
                select(PlaceConnection, Entity)
                .join(Entity, Entity.id == PlaceConnection.to_place_id)
                .where(
                    PlaceConnection.save_id == save_id,
                    PlaceConnection.from_place_id == from_place_id,
                )
                .order_by(Entity.name)
            )
            return [
                SceneConnection(
                    destination_id=entity.id,
                    destination_name=entity.name,
                    travel_minutes=connection.travel_minutes,
                    description=connection.description,
                )
                for connection, entity in session.execute(stmt)
            ]

    def get_active_quests(self, save_id: str, actor_entity_id: str) -> list[QuestSnapshot]:
        with session_scope(self.session_factory) as session:
            stmt = (
                select(QuestState, Quest)
                .join(Quest, Quest.id == QuestState.quest_id)
                .where(
                    QuestState.save_id == save_id,
                    QuestState.actor_entity_id == actor_entity_id,
                    QuestState.status.in_([QuestStatus.ACTIVE, QuestStatus.AVAILABLE]),
                )
                .order_by(Quest.title)
            )
            return [
                QuestSnapshot(
                    id=quest.id,
                    title=quest.title,
                    description=quest.description,
                    status=state.status,
                    notes=state.notes,
                )
                for state, quest in session.execute(stmt)
            ]

    def get_recent_events(self, save_id: str, limit: int = 5) -> list[EventSummary]:
        with session_scope(self.session_factory) as session:
            stmt = (
                select(Event)
                .where(Event.save_id == save_id)
                .order_by(desc(Event.occurred_at))
                .limit(limit)
            )
            return [
                EventSummary(
                    id=event.id,
                    event_type=event.event_type,
                    title=event.title,
                    description=event.description,
                    occurred_at=event.occurred_at,
                )
                for event in session.scalars(stmt)
            ]

    def get_visible_facts(self, save_id: str, viewer_entity_id: str) -> list[SceneFact]:
        with session_scope(self.session_factory) as session:
            stmt = (
                select(Fact)
                .join(FactVisibility, FactVisibility.fact_id == Fact.id)
                .where(
                    Fact.save_id == save_id,
                    FactVisibility.save_id == save_id,
                    ((FactVisibility.viewer_entity_id == viewer_entity_id) | (FactVisibility.viewer_role == "all")),
                )
                .order_by(Fact.fact_key)
            )
            return [
                SceneFact(
                    id=fact.id,
                    fact_key=fact.fact_key,
                    text=fact.truth_text,
                    subject_entity_id=fact.subject_entity_id,
                )
                for fact in session.scalars(stmt)
            ]

    def get_relevant_beliefs(self, save_id: str, holder_ids: list[str]) -> list[dict[str, Any]]:
        if not holder_ids:
            return []
        with session_scope(self.session_factory) as session:
            stmt = (
                select(Belief)
                .where(Belief.save_id == save_id, Belief.holder_entity_id.in_(holder_ids))
                .order_by(Belief.confidence.desc())
            )
            return [
                {
                    "id": belief.id,
                    "holder_entity_id": belief.holder_entity_id,
                    "belief_key": belief.belief_key,
                    "belief_text": belief.belief_text,
                    "confidence": belief.confidence,
                    "fact_id": belief.fact_id,
                }
                for belief in session.scalars(stmt)
            ]

    def get_inventory(self, save_id: str, owner_entity_id: str) -> list[InventoryEntry]:
        with session_scope(self.session_factory) as session:
            inventory = session.scalar(
                select(Inventory).where(
                    Inventory.save_id == save_id,
                    Inventory.owner_entity_id == owner_entity_id,
                )
            )
            if inventory is None:
                return []
            stmt = (
                select(InventoryItem, Entity)
                .join(Entity, Entity.id == InventoryItem.item_entity_id)
                .where(
                    InventoryItem.save_id == save_id,
                    InventoryItem.inventory_id == inventory.id,
                )
                .order_by(Entity.name)
            )
            return [
                InventoryEntry(item_entity_id=item.id, item_name=item.name, quantity=entry.quantity)
                for entry, item in session.execute(stmt)
            ]

    def find_relationship(self, save_id: str, source_entity_id: str, target_entity_id: str) -> Relationship | None:
        with session_scope(self.session_factory) as session:
            stmt = select(Relationship).where(
                Relationship.save_id == save_id,
                Relationship.source_entity_id == source_entity_id,
                Relationship.target_entity_id == target_entity_id,
            )
            return session.scalar(stmt)

    def apply_patch(self, patch: StatePatch) -> None:
        with session_scope(self.session_factory) as session:
            for operation in patch.operations:
                if operation.kind == PatchOperationKind.MOVE_ENTITY:
                    entity = session.get(Entity, operation.target_id)
                    if entity is None:
                        raise ValueError(f"Cannot move missing entity {operation.target_id}")
                    entity.location_entity_id = operation.data["location_entity_id"]
                elif operation.kind == PatchOperationKind.CREATE_EVENT:
                    session.add(
                        Event(
                            id=operation.data.get("event_id", new_id("event")),
                            save_id=patch.save_id,
                            event_type=EventType(operation.data["event_type"]),
                            title=operation.data["title"],
                            description=operation.data["description"],
                            occurred_at=operation.data.get("occurred_at", utcnow()),
                            actor_entity_id=operation.data.get("actor_entity_id"),
                            target_entity_id=operation.data.get("target_entity_id"),
                            location_entity_id=operation.data.get("location_entity_id"),
                            payload=dict(operation.data.get("payload", {})),
                        )
                    )
                elif operation.kind == PatchOperationKind.UPDATE_QUEST:
                    stmt = select(QuestState).where(
                        QuestState.save_id == patch.save_id,
                        QuestState.quest_id == operation.data["quest_id"],
                        QuestState.actor_entity_id == operation.data["actor_entity_id"],
                    )
                    quest_state = session.scalar(stmt)
                    if quest_state is None:
                        quest_state = QuestState(
                            id=new_id("quest-state"),
                            save_id=patch.save_id,
                            quest_id=operation.data["quest_id"],
                            actor_entity_id=operation.data["actor_entity_id"],
                            status=QuestStatus(operation.data["status"]),
                            notes=operation.data.get("notes", ""),
                            progress=operation.data.get("progress", 0),
                        )
                        session.add(quest_state)
                    else:
                        quest_state.status = QuestStatus(operation.data["status"])
                        quest_state.notes = operation.data.get("notes", quest_state.notes)
                        quest_state.progress = operation.data.get("progress", quest_state.progress)
                elif operation.kind == PatchOperationKind.ADVANCE_TIME:
                    clock = session.scalar(select(WorldClock).where(WorldClock.save_id == patch.save_id))
                    if clock is None:
                        raise ValueError(f"Missing world clock for save {patch.save_id}")
                    clock.current_time = clock.current_time + timedelta(minutes=operation.data.get("minutes", 0))
                elif operation.kind == PatchOperationKind.UPDATE_RELATIONSHIP:
                    stmt = select(Relationship).where(
                        Relationship.save_id == patch.save_id,
                        Relationship.source_entity_id == operation.data["source_entity_id"],
                        Relationship.target_entity_id == operation.data["target_entity_id"],
                    )
                    relationship = session.scalar(stmt)
                    if relationship is None:
                        relationship = Relationship(
                            id=new_id("relationship"),
                            save_id=patch.save_id,
                            source_entity_id=operation.data["source_entity_id"],
                            target_entity_id=operation.data["target_entity_id"],
                            attitude=operation.data.get("attitude", "neutral"),
                            score=operation.data.get("score_delta", 0),
                            notes=operation.data.get("notes", ""),
                        )
                        session.add(relationship)
                    else:
                        relationship.score = relationship.score + operation.data.get("score_delta", 0)
                        if "attitude" in operation.data:
                            relationship.attitude = operation.data["attitude"]
                        if "notes" in operation.data:
                            relationship.notes = operation.data["notes"]
                elif operation.kind in {PatchOperationKind.DAMAGE_ENTITY, PatchOperationKind.HEAL_ENTITY}:
                    stmt = select(EntityStats).where(EntityStats.entity_id == operation.target_id)
                    stats = session.scalar(stmt)
                    if stats is None:
                        raise ValueError(f"Missing stats for entity {operation.target_id}")
                    delta = operation.data.get("amount", 0)
                    if operation.kind == PatchOperationKind.DAMAGE_ENTITY:
                        stats.hp = max(0, stats.hp - delta)
                    else:
                        stats.hp = min(stats.max_hp, stats.hp + delta)
                elif operation.kind == PatchOperationKind.ADD_BELIEF:
                    session.add(
                        Belief(
                            id=operation.data.get("belief_id", new_id("belief")),
                            save_id=patch.save_id,
                            holder_entity_id=operation.data["holder_entity_id"],
                            fact_id=operation.data.get("fact_id"),
                            belief_key=operation.data["belief_key"],
                            belief_text=operation.data["belief_text"],
                            confidence=operation.data.get("confidence", 0.5),
                        )
                    )
                elif operation.kind == PatchOperationKind.ADD_ITEM:
                    inventory = session.scalar(
                        select(Inventory).where(
                            Inventory.save_id == patch.save_id,
                            Inventory.owner_entity_id == operation.data["owner_entity_id"],
                        )
                    )
                    if inventory is None:
                        inventory = Inventory(
                            id=new_id("inventory"),
                            save_id=patch.save_id,
                            owner_entity_id=operation.data["owner_entity_id"],
                        )
                        session.add(inventory)
                        session.flush()
                    stmt = select(InventoryItem).where(
                        InventoryItem.save_id == patch.save_id,
                        InventoryItem.inventory_id == inventory.id,
                        InventoryItem.item_entity_id == operation.data["item_entity_id"],
                    )
                    item = session.scalar(stmt)
                    if item is None:
                        item = InventoryItem(
                            id=new_id("inventory-item"),
                            save_id=patch.save_id,
                            inventory_id=inventory.id,
                            item_entity_id=operation.data["item_entity_id"],
                            quantity=operation.data.get("quantity", 1),
                        )
                        session.add(item)
                    else:
                        item.quantity += operation.data.get("quantity", 1)
                else:
                    raise ValueError(f"Unsupported patch operation: {operation.kind}")

    def base_query(self, model: type, *, save_id: str) -> Select[Any]:
        return select(model).where(getattr(model, "save_id") == save_id)
