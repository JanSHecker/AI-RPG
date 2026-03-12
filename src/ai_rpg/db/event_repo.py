from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from ai_rpg.core.contracts import EventType, WorldEvent
from ai_rpg.db.models import Event, ScheduledEvent
from ai_rpg.db.repositories import new_id
from ai_rpg.db.session import session_scope


class EventRepository:
    def __init__(self, session_factory: sessionmaker[Session]):
        self.session_factory = session_factory

    def log_event(self, save_id: str, event: WorldEvent) -> None:
        with session_scope(self.session_factory) as session:
            session.add(
                Event(
                    id=event.id,
                    save_id=save_id,
                    event_type=event.event_type,
                    title=event.title,
                    description=event.description,
                    occurred_at=event.occurred_at,
                    actor_entity_id=event.actor_entity_id,
                    target_entity_id=event.target_entity_id,
                    location_entity_id=event.location_entity_id,
                    payload=dict(event.metadata),
                )
            )

    def schedule_event(
        self,
        save_id: str,
        *,
        event_type: EventType,
        description: str,
        scheduled_for: datetime,
        actor_entity_id: str | None = None,
        target_entity_id: str | None = None,
        location_entity_id: str | None = None,
        payload: dict | None = None,
    ) -> str:
        event_id = new_id("scheduled")
        with session_scope(self.session_factory) as session:
            session.add(
                ScheduledEvent(
                    id=event_id,
                    save_id=save_id,
                    event_type=event_type,
                    description=description,
                    scheduled_for=scheduled_for,
                    actor_entity_id=actor_entity_id,
                    target_entity_id=target_entity_id,
                    location_entity_id=location_entity_id,
                    payload=payload or {},
                )
            )
        return event_id

    def due_events(self, save_id: str, up_to: datetime) -> list[ScheduledEvent]:
        with session_scope(self.session_factory) as session:
            stmt = select(ScheduledEvent).where(
                ScheduledEvent.save_id == save_id,
                ScheduledEvent.processed == False,  # noqa: E712
                ScheduledEvent.scheduled_for <= up_to,
            )
            return list(session.scalars(stmt))

    def mark_processed(self, scheduled_event_id: str) -> None:
        with session_scope(self.session_factory) as session:
            scheduled_event = session.get(ScheduledEvent, scheduled_event_id)
            if scheduled_event is not None:
                scheduled_event.processed = True

