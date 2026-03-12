from __future__ import annotations

from ai_rpg.core.contracts import ActionType, SceneContext, TurnIntent


class IntentParser:
    def parse(self, raw_input: str, actor_id: str, context: SceneContext) -> TurnIntent:
        text = raw_input.strip()
        lowered = text.lower()

        if not text:
            return TurnIntent(raw_input=text, actor_id=actor_id, action_type=ActionType.UNKNOWN)

        if text.startswith("/"):
            command = text[1:].split(maxsplit=1)[0].lower()
            return TurnIntent(
                raw_input=text,
                actor_id=actor_id,
                action_type=ActionType.COMMAND,
                command=command,
                content=text[1 + len(command) :].strip() or None,
            )

        if lowered in {"look", "l", "inspect"}:
            return TurnIntent(raw_input=text, actor_id=actor_id, action_type=ActionType.LOOK)

        if lowered in {"wait", "rest"}:
            return TurnIntent(raw_input=text, actor_id=actor_id, action_type=ActionType.WAIT)

        if lowered in {"inventory", "inv"}:
            return TurnIntent(raw_input=text, actor_id=actor_id, action_type=ActionType.INVENTORY)

        if lowered == "quests":
            return TurnIntent(raw_input=text, actor_id=actor_id, action_type=ActionType.QUESTS)

        for prefix in ("go to ", "go ", "travel to ", "travel ", "move to ", "move "):
            if lowered.startswith(prefix):
                destination_name = text[len(prefix) :].strip()
                destination = next(
                    (
                        place
                        for place in context.adjacent_places
                        if place.destination_name.lower() == destination_name.lower()
                        or destination_name.lower() in place.destination_name.lower()
                    ),
                    None,
                )
                return TurnIntent(
                    raw_input=text,
                    actor_id=actor_id,
                    action_type=ActionType.MOVE,
                    destination_id=destination.destination_id if destination else None,
                    destination_name=destination_name,
                )

        for prefix in ("talk to ", "talk ", "speak to ", "ask ", "ask about "):
            if lowered.startswith(prefix):
                target_name = text[len(prefix) :].strip()
                target = next(
                    (
                        entity
                        for entity in context.nearby_entities
                        if not entity.is_player
                        and (
                            entity.name.lower() == target_name.lower()
                            or target_name.lower() in entity.name.lower()
                        )
                    ),
                    None,
                )
                return TurnIntent(
                    raw_input=text,
                    actor_id=actor_id,
                    action_type=ActionType.TALK,
                    target_id=target.id if target else None,
                    target_name=target_name,
                    content=text,
                )

        for prefix in ("attack ", "strike ", "fight "):
            if lowered.startswith(prefix):
                target_name = text[len(prefix) :].strip()
                target = next(
                    (
                        entity
                        for entity in context.nearby_entities
                        if not entity.is_player
                        and (
                            entity.name.lower() == target_name.lower()
                            or target_name.lower() in entity.name.lower()
                        )
                    ),
                    None,
                )
                return TurnIntent(
                    raw_input=text,
                    actor_id=actor_id,
                    action_type=ActionType.ATTACK,
                    target_id=target.id if target else None,
                    target_name=target_name,
                    content=text,
                )

        if any(keyword in lowered for keyword in ("mayor", "ranger", "smith", "goblin")):
            target = next(
                (
                    entity
                    for entity in context.nearby_entities
                    if entity.name.lower() in lowered
                ),
                None,
            )
            return TurnIntent(
                raw_input=text,
                actor_id=actor_id,
                action_type=ActionType.TALK,
                target_id=target.id if target else None,
                target_name=target.name if target else text,
                content=text,
            )

        return TurnIntent(
            raw_input=text,
            actor_id=actor_id,
            action_type=ActionType.UNKNOWN,
            content=text,
        )

