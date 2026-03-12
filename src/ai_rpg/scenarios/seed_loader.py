from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

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
    Scenario,
    ScheduledEvent,
    WorldClock,
)
from ai_rpg.db.repositories import ScenarioRepository
from ai_rpg.db.session import session_scope
from ai_rpg.scenarios.templates import empty_scenario_template, frontier_fantasy_template


class ScenarioSeedLoader:
    def __init__(self, session_factory: sessionmaker[Session]):
        self.session_factory = session_factory
        self.scenario_repository = ScenarioRepository(session_factory)

    def ensure_builtin_scenarios(self) -> None:
        self._seed_template(frontier_fantasy_template())

    def create_empty_scenario(self, name: str, description: str = "") -> Scenario:
        scenario = self.scenario_repository.create_scenario(name=name, description=description)
        template = empty_scenario_template(scenario.id, name, description)
        self._seed_template(template)
        return self.scenario_repository.get(scenario.id)

    def _seed_template(self, template: dict) -> None:
        scenario_data = template["scenario"]
        self.scenario_repository.create_scenario(
            name=scenario_data["name"],
            description=scenario_data["description"],
            scenario_id=scenario_data["id"],
            is_builtin=scenario_data.get("is_builtin", False),
        )
        with session_scope(self.session_factory) as session:
            scenario_id = scenario_data["id"]
            exists = session.scalar(select(Entity).where(Entity.scenario_id == scenario_id).limit(1))
            if exists is not None:
                clock = session.scalar(select(WorldClock).where(WorldClock.scenario_id == scenario_id))
                if clock is not None:
                    clock.current_time = template["clock"]
                return

            self._insert_rows(session, Scenario, [scenario_data], scenario_id, is_meta=True)
            self._replace_clock(session, scenario_id, template["clock"])
            self._insert_rows(session, Entity, template["entities"], scenario_id)
            self._insert_rows(session, EntityStats, template["stats"], scenario_id)
            self._insert_rows(session, PlaceConnection, template["connections"], scenario_id)
            self._insert_rows(session, Inventory, template["inventories"], scenario_id)
            self._insert_rows(session, InventoryItem, template["inventory_items"], scenario_id)
            self._insert_rows(session, Quest, template["quests"], scenario_id)
            self._insert_rows(session, QuestState, template["quest_states"], scenario_id)
            self._insert_rows(session, Event, template["events"], scenario_id)
            self._insert_rows(session, ScheduledEvent, template["scheduled_events"], scenario_id)
            self._insert_rows(session, Fact, template["facts"], scenario_id)
            self._insert_rows(session, FactVisibility, template["fact_visibility"], scenario_id)
            self._insert_rows(session, Belief, template["beliefs"], scenario_id)
            self._insert_rows(session, Relationship, template["relationships"], scenario_id)

    def _replace_clock(self, session: Session, scenario_id: str, value) -> None:
        existing = session.scalar(select(WorldClock).where(WorldClock.scenario_id == scenario_id))
        if existing is None:
            session.add(WorldClock(id=f"clock:{scenario_id}", scenario_id=scenario_id, current_time=value))
        else:
            existing.current_time = value

    def _insert_rows(
        self,
        session: Session,
        model: type,
        rows: list[dict],
        scenario_id: str,
        *,
        is_meta: bool = False,
    ) -> None:
        for row in rows:
            data = dict(row)
            if not is_meta:
                data["scenario_id"] = scenario_id
            session.merge(model(**data))

