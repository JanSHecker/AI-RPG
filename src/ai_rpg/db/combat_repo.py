from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from ai_rpg.core.contracts import EncounterState
from ai_rpg.db.models import CombatEncounter, Combatant, EntityStats, WorldClock, utcnow
from ai_rpg.db.repositories import new_id
from ai_rpg.db.session import session_scope


class CombatRepository:
    def __init__(self, session_factory: sessionmaker[Session]):
        self.session_factory = session_factory

    def create_encounter(self, save_id: str, location_entity_id: str, entity_ids: list[str]) -> str:
        encounter_id = new_id("encounter")
        with session_scope(self.session_factory) as session:
            clock = session.scalar(select(WorldClock).where(WorldClock.save_id == save_id))
            started_at = clock.current_time if clock else utcnow()
            encounter = CombatEncounter(
                id=encounter_id,
                save_id=save_id,
                location_entity_id=location_entity_id,
                started_at=started_at,
                state=EncounterState.ACTIVE,
            )
            session.add(encounter)
            for order, entity_id in enumerate(entity_ids):
                stats = session.scalar(select(EntityStats).where(EntityStats.entity_id == entity_id))
                session.add(
                    Combatant(
                        id=new_id("combatant"),
                        encounter_id=encounter_id,
                        entity_id=entity_id,
                        turn_order=order,
                        initiative=0,
                        current_hp=stats.hp if stats else 10,
                        is_defeated=False,
                    )
                )
            session.flush()
            active = session.scalar(
                select(Combatant)
                .where(Combatant.encounter_id == encounter_id)
                .order_by(Combatant.turn_order)
            )
            encounter.active_combatant_id = active.id if active else None
        return encounter_id

    def get_encounter(self, encounter_id: str) -> CombatEncounter | None:
        with session_scope(self.session_factory) as session:
            return session.get(CombatEncounter, encounter_id)

    def get_combatants(self, encounter_id: str) -> list[Combatant]:
        with session_scope(self.session_factory) as session:
            stmt = (
                select(Combatant)
                .where(Combatant.encounter_id == encounter_id)
                .order_by(Combatant.turn_order, Combatant.entity_id)
            )
            return list(session.scalars(stmt))

    def set_initiative(self, encounter_id: str, order: list[tuple[str, int]]) -> None:
        with session_scope(self.session_factory) as session:
            for turn_order, (combatant_id, initiative) in enumerate(order):
                combatant = session.get(Combatant, combatant_id)
                if combatant is None:
                    continue
                combatant.turn_order = turn_order
                combatant.initiative = initiative
            first = session.scalar(
                select(Combatant)
                .where(Combatant.encounter_id == encounter_id, Combatant.is_defeated == False)  # noqa: E712
                .order_by(Combatant.turn_order)
            )
            encounter = session.get(CombatEncounter, encounter_id)
            if encounter is not None:
                encounter.active_combatant_id = first.id if first else None

    def mark_defeated(self, encounter_id: str, entity_id: str) -> None:
        with session_scope(self.session_factory) as session:
            stmt = select(Combatant).where(
                Combatant.encounter_id == encounter_id,
                Combatant.entity_id == entity_id,
            )
            combatant = session.scalar(stmt)
            if combatant is not None:
                combatant.is_defeated = True
                combatant.current_hp = 0

    def advance_turn(self, encounter_id: str) -> str | None:
        with session_scope(self.session_factory) as session:
            encounter = session.get(CombatEncounter, encounter_id)
            if encounter is None:
                return None
            combatants = list(
                session.scalars(
                    select(Combatant)
                    .where(Combatant.encounter_id == encounter_id, Combatant.is_defeated == False)  # noqa: E712
                    .order_by(Combatant.turn_order)
                )
            )
            if not combatants:
                encounter.state = EncounterState.WON
                encounter.ended_at = utcnow()
                encounter.active_combatant_id = None
                return None
            if encounter.active_combatant_id is None:
                encounter.active_combatant_id = combatants[0].id
                return encounter.active_combatant_id
            ids = [combatant.id for combatant in combatants]
            if encounter.active_combatant_id not in ids:
                encounter.active_combatant_id = combatants[0].id
                return encounter.active_combatant_id
            index = ids.index(encounter.active_combatant_id)
            next_index = (index + 1) % len(ids)
            if next_index == 0:
                encounter.round_number += 1
            encounter.active_combatant_id = ids[next_index]
            return encounter.active_combatant_id

    def complete_encounter(self, encounter_id: str, state: EncounterState) -> None:
        with session_scope(self.session_factory) as session:
            encounter = session.get(CombatEncounter, encounter_id)
            if encounter is not None:
                encounter.state = state
                encounter.ended_at = utcnow()
