from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ai_rpg.core.contracts import EncounterState, EntityType, EventType, QuestStatus
from ai_rpg.db.base import Base


def utcnow() -> datetime:
    return datetime.utcnow().replace(microsecond=0)


class Scenario(Base):
    __tablename__ = "scenarios"

    id: Mapped[str] = mapped_column(String(120), primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    is_builtin: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)


class Save(Base):
    __tablename__ = "saves"

    id: Mapped[str] = mapped_column(String(120), primary_key=True)
    scenario_id: Mapped[str] = mapped_column(ForeignKey("scenarios.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    player_entity_id: Mapped[str | None] = mapped_column(String(160), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)


class Entity(Base):
    __tablename__ = "entities"

    id: Mapped[str] = mapped_column(String(160), primary_key=True)
    scenario_id: Mapped[str | None] = mapped_column(ForeignKey("scenarios.id"), nullable=True, index=True)
    save_id: Mapped[str | None] = mapped_column(ForeignKey("saves.id"), nullable=True, index=True)
    source_template_id: Mapped[str | None] = mapped_column(String(160), nullable=True)
    entity_type: Mapped[EntityType] = mapped_column(
        Enum(EntityType, native_enum=False),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    location_entity_id: Mapped[str | None] = mapped_column(String(160), nullable=True, index=True)
    faction_entity_id: Mapped[str | None] = mapped_column(String(160), nullable=True)
    is_player: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_hostile: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    details: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)


class EntityStats(Base):
    __tablename__ = "entity_stats"

    id: Mapped[str] = mapped_column(String(160), primary_key=True)
    scenario_id: Mapped[str | None] = mapped_column(ForeignKey("scenarios.id"), nullable=True, index=True)
    save_id: Mapped[str | None] = mapped_column(ForeignKey("saves.id"), nullable=True, index=True)
    entity_id: Mapped[str] = mapped_column(ForeignKey("entities.id"), nullable=False, index=True)
    strength: Mapped[int] = mapped_column(Integer, default=10, nullable=False)
    dexterity: Mapped[int] = mapped_column(Integer, default=10, nullable=False)
    constitution: Mapped[int] = mapped_column(Integer, default=10, nullable=False)
    intelligence: Mapped[int] = mapped_column(Integer, default=10, nullable=False)
    wisdom: Mapped[int] = mapped_column(Integer, default=10, nullable=False)
    charisma: Mapped[int] = mapped_column(Integer, default=10, nullable=False)
    diplomacy: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    survival: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    stealth: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    melee: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    hp: Mapped[int] = mapped_column(Integer, default=10, nullable=False)
    max_hp: Mapped[int] = mapped_column(Integer, default=10, nullable=False)
    stamina: Mapped[int] = mapped_column(Integer, default=10, nullable=False)
    max_stamina: Mapped[int] = mapped_column(Integer, default=10, nullable=False)


class PlaceConnection(Base):
    __tablename__ = "place_connections"

    id: Mapped[str] = mapped_column(String(160), primary_key=True)
    scenario_id: Mapped[str | None] = mapped_column(ForeignKey("scenarios.id"), nullable=True, index=True)
    save_id: Mapped[str | None] = mapped_column(ForeignKey("saves.id"), nullable=True, index=True)
    source_template_id: Mapped[str | None] = mapped_column(String(160), nullable=True)
    from_place_id: Mapped[str] = mapped_column(String(160), nullable=False, index=True)
    to_place_id: Mapped[str] = mapped_column(String(160), nullable=False, index=True)
    travel_minutes: Mapped[int] = mapped_column(Integer, default=5, nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)


class Inventory(Base):
    __tablename__ = "inventories"

    id: Mapped[str] = mapped_column(String(160), primary_key=True)
    scenario_id: Mapped[str | None] = mapped_column(ForeignKey("scenarios.id"), nullable=True, index=True)
    save_id: Mapped[str | None] = mapped_column(ForeignKey("saves.id"), nullable=True, index=True)
    owner_entity_id: Mapped[str] = mapped_column(String(160), nullable=False, index=True)


class InventoryItem(Base):
    __tablename__ = "inventory_items"

    id: Mapped[str] = mapped_column(String(160), primary_key=True)
    scenario_id: Mapped[str | None] = mapped_column(ForeignKey("scenarios.id"), nullable=True, index=True)
    save_id: Mapped[str | None] = mapped_column(ForeignKey("saves.id"), nullable=True, index=True)
    inventory_id: Mapped[str] = mapped_column(String(160), nullable=False, index=True)
    item_entity_id: Mapped[str] = mapped_column(String(160), nullable=False, index=True)
    quantity: Mapped[int] = mapped_column(Integer, default=1, nullable=False)


class Quest(Base):
    __tablename__ = "quests"

    id: Mapped[str] = mapped_column(String(160), primary_key=True)
    scenario_id: Mapped[str | None] = mapped_column(ForeignKey("scenarios.id"), nullable=True, index=True)
    save_id: Mapped[str | None] = mapped_column(ForeignKey("saves.id"), nullable=True, index=True)
    source_template_id: Mapped[str | None] = mapped_column(String(160), nullable=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    giver_entity_id: Mapped[str | None] = mapped_column(String(160), nullable=True)
    target_entity_id: Mapped[str | None] = mapped_column(String(160), nullable=True)
    reward_text: Mapped[str] = mapped_column(Text, default="", nullable=False)


class QuestState(Base):
    __tablename__ = "quest_states"

    id: Mapped[str] = mapped_column(String(160), primary_key=True)
    scenario_id: Mapped[str | None] = mapped_column(ForeignKey("scenarios.id"), nullable=True, index=True)
    save_id: Mapped[str | None] = mapped_column(ForeignKey("saves.id"), nullable=True, index=True)
    quest_id: Mapped[str] = mapped_column(String(160), nullable=False, index=True)
    actor_entity_id: Mapped[str] = mapped_column(String(160), nullable=False, index=True)
    status: Mapped[QuestStatus] = mapped_column(Enum(QuestStatus, native_enum=False), nullable=False)
    progress: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    notes: Mapped[str] = mapped_column(Text, default="", nullable=False)


class Event(Base):
    __tablename__ = "events"

    id: Mapped[str] = mapped_column(String(160), primary_key=True)
    scenario_id: Mapped[str | None] = mapped_column(ForeignKey("scenarios.id"), nullable=True, index=True)
    save_id: Mapped[str | None] = mapped_column(ForeignKey("saves.id"), nullable=True, index=True)
    source_template_id: Mapped[str | None] = mapped_column(String(160), nullable=True)
    event_type: Mapped[EventType] = mapped_column(Enum(EventType, native_enum=False), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False, index=True)
    actor_entity_id: Mapped[str | None] = mapped_column(String(160), nullable=True)
    target_entity_id: Mapped[str | None] = mapped_column(String(160), nullable=True)
    location_entity_id: Mapped[str | None] = mapped_column(String(160), nullable=True)
    payload: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)


class ScheduledEvent(Base):
    __tablename__ = "scheduled_events"

    id: Mapped[str] = mapped_column(String(160), primary_key=True)
    scenario_id: Mapped[str | None] = mapped_column(ForeignKey("scenarios.id"), nullable=True, index=True)
    save_id: Mapped[str | None] = mapped_column(ForeignKey("saves.id"), nullable=True, index=True)
    source_template_id: Mapped[str | None] = mapped_column(String(160), nullable=True)
    event_type: Mapped[EventType] = mapped_column(Enum(EventType, native_enum=False), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    scheduled_for: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    actor_entity_id: Mapped[str | None] = mapped_column(String(160), nullable=True)
    target_entity_id: Mapped[str | None] = mapped_column(String(160), nullable=True)
    location_entity_id: Mapped[str | None] = mapped_column(String(160), nullable=True)
    processed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    payload: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)


class Fact(Base):
    __tablename__ = "facts"

    id: Mapped[str] = mapped_column(String(160), primary_key=True)
    scenario_id: Mapped[str | None] = mapped_column(ForeignKey("scenarios.id"), nullable=True, index=True)
    save_id: Mapped[str | None] = mapped_column(ForeignKey("saves.id"), nullable=True, index=True)
    source_template_id: Mapped[str | None] = mapped_column(String(160), nullable=True)
    subject_entity_id: Mapped[str | None] = mapped_column(String(160), nullable=True)
    fact_key: Mapped[str] = mapped_column(String(200), nullable=False)
    truth_text: Mapped[str] = mapped_column(Text, nullable=False)
    truth_value: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class FactVisibility(Base):
    __tablename__ = "fact_visibility"

    id: Mapped[str] = mapped_column(String(160), primary_key=True)
    scenario_id: Mapped[str | None] = mapped_column(ForeignKey("scenarios.id"), nullable=True, index=True)
    save_id: Mapped[str | None] = mapped_column(ForeignKey("saves.id"), nullable=True, index=True)
    source_template_id: Mapped[str | None] = mapped_column(String(160), nullable=True)
    fact_id: Mapped[str] = mapped_column(String(160), nullable=False, index=True)
    viewer_entity_id: Mapped[str | None] = mapped_column(String(160), nullable=True, index=True)
    viewer_role: Mapped[str | None] = mapped_column(String(80), nullable=True)


class Belief(Base):
    __tablename__ = "beliefs"

    id: Mapped[str] = mapped_column(String(160), primary_key=True)
    scenario_id: Mapped[str | None] = mapped_column(ForeignKey("scenarios.id"), nullable=True, index=True)
    save_id: Mapped[str | None] = mapped_column(ForeignKey("saves.id"), nullable=True, index=True)
    source_template_id: Mapped[str | None] = mapped_column(String(160), nullable=True)
    holder_entity_id: Mapped[str] = mapped_column(String(160), nullable=False, index=True)
    fact_id: Mapped[str | None] = mapped_column(String(160), nullable=True, index=True)
    belief_key: Mapped[str] = mapped_column(String(200), nullable=False)
    belief_text: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[float] = mapped_column(default=0.5, nullable=False)


class Relationship(Base):
    __tablename__ = "relationships"

    id: Mapped[str] = mapped_column(String(160), primary_key=True)
    scenario_id: Mapped[str | None] = mapped_column(ForeignKey("scenarios.id"), nullable=True, index=True)
    save_id: Mapped[str | None] = mapped_column(ForeignKey("saves.id"), nullable=True, index=True)
    source_template_id: Mapped[str | None] = mapped_column(String(160), nullable=True)
    source_entity_id: Mapped[str] = mapped_column(String(160), nullable=False, index=True)
    target_entity_id: Mapped[str] = mapped_column(String(160), nullable=False, index=True)
    attitude: Mapped[str] = mapped_column(String(80), default="neutral", nullable=False)
    score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    notes: Mapped[str] = mapped_column(Text, default="", nullable=False)


class CombatEncounter(Base):
    __tablename__ = "combat_encounters"

    id: Mapped[str] = mapped_column(String(160), primary_key=True)
    save_id: Mapped[str] = mapped_column(ForeignKey("saves.id"), nullable=False, index=True)
    location_entity_id: Mapped[str] = mapped_column(String(160), nullable=False, index=True)
    state: Mapped[EncounterState] = mapped_column(
        Enum(EncounterState, native_enum=False),
        default=EncounterState.ACTIVE,
        nullable=False,
    )
    started_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    round_number: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    active_combatant_id: Mapped[str | None] = mapped_column(String(160), nullable=True)
    notes: Mapped[str] = mapped_column(Text, default="", nullable=False)


class Combatant(Base):
    __tablename__ = "combatants"

    id: Mapped[str] = mapped_column(String(160), primary_key=True)
    encounter_id: Mapped[str] = mapped_column(ForeignKey("combat_encounters.id"), nullable=False, index=True)
    entity_id: Mapped[str] = mapped_column(String(160), nullable=False, index=True)
    initiative: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    turn_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    current_hp: Mapped[int] = mapped_column(Integer, default=10, nullable=False)
    is_defeated: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class WorldClock(Base):
    __tablename__ = "world_clock"

    id: Mapped[str] = mapped_column(String(160), primary_key=True)
    scenario_id: Mapped[str | None] = mapped_column(ForeignKey("scenarios.id"), nullable=True, index=True)
    save_id: Mapped[str | None] = mapped_column(ForeignKey("saves.id"), nullable=True, index=True)
    current_time: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)

