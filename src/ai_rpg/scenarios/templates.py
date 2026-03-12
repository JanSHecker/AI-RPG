from __future__ import annotations

from datetime import datetime, timedelta

from ai_rpg.core.contracts import EntityType, EventType, QuestStatus


DEFAULT_SCENARIO_ID = "scenario.frontier_fantasy"
DEFAULT_SCENARIO_NAME = "Frontier of Oakheart"
DEFAULT_SCENARIO_DESCRIPTION = (
    "A frontier village, a nearby ruin, and a handful of rumors that do not all agree."
)
DEFAULT_START_TIME = datetime(1365, 4, 14, 8, 0, 0)


def frontier_fantasy_template() -> dict:
    return {
        "scenario": {
            "id": DEFAULT_SCENARIO_ID,
            "name": DEFAULT_SCENARIO_NAME,
            "description": DEFAULT_SCENARIO_DESCRIPTION,
            "is_builtin": True,
        },
        "clock": DEFAULT_START_TIME,
        "entities": [
            {
                "id": "place.oakheart",
                "entity_type": EntityType.PLACE,
                "name": "Oakheart Village",
                "description": "A timber village built around a broad ancient oak.",
                "details": {"start": True},
            },
            {
                "id": "place.watchtower",
                "entity_type": EntityType.PLACE,
                "name": "Ruined Watchtower",
                "description": "A cracked stone tower overlooking the forest road.",
                "details": {},
            },
            {
                "id": "faction.oakheart_council",
                "entity_type": EntityType.FACTION,
                "name": "Oakheart Council",
                "description": "Village elders trying to hold the frontier together.",
                "details": {},
            },
            {
                "id": "npc.elira",
                "entity_type": EntityType.PERSON,
                "name": "Mayor Elira",
                "description": "Oakheart's practical mayor, tired but composed.",
                "location_entity_id": "place.oakheart",
                "faction_entity_id": "faction.oakheart_council",
                "details": {"role": "mayor"},
            },
            {
                "id": "npc.tomas",
                "entity_type": EntityType.PERSON,
                "name": "Ranger Tomas",
                "description": "A keen-eyed scout who trusts tracks more than gossip.",
                "location_entity_id": "place.oakheart",
                "details": {"role": "ranger"},
            },
            {
                "id": "npc.brenna",
                "entity_type": EntityType.PERSON,
                "name": "Smith Brenna",
                "description": "A blacksmith with soot on her sleeves and sharp opinions.",
                "location_entity_id": "place.oakheart",
                "details": {"role": "smith"},
            },
            {
                "id": "creature.goblin_scout",
                "entity_type": EntityType.CREATURE,
                "name": "Goblin Scout",
                "description": "A wiry goblin lurking in the broken tower.",
                "location_entity_id": "place.watchtower",
                "is_hostile": True,
                "details": {"role": "hostile"},
            },
            {
                "id": "item.healing_draught",
                "entity_type": EntityType.ITEM,
                "name": "Healing Draught",
                "description": "A bitter herbal tonic kept ready for emergencies.",
                "details": {"consumable": True},
            },
        ],
        "stats": [
            {
                "id": "stats.npc.elira",
                "entity_id": "npc.elira",
                "strength": 10,
                "dexterity": 10,
                "constitution": 11,
                "intelligence": 13,
                "wisdom": 12,
                "charisma": 14,
                "diplomacy": 3,
                "survival": 0,
                "stealth": 0,
                "melee": 0,
                "hp": 12,
                "max_hp": 12,
                "stamina": 10,
                "max_stamina": 10,
            },
            {
                "id": "stats.npc.tomas",
                "entity_id": "npc.tomas",
                "strength": 11,
                "dexterity": 14,
                "constitution": 11,
                "intelligence": 12,
                "wisdom": 14,
                "charisma": 10,
                "diplomacy": 1,
                "survival": 4,
                "stealth": 3,
                "melee": 2,
                "hp": 13,
                "max_hp": 13,
                "stamina": 12,
                "max_stamina": 12,
            },
            {
                "id": "stats.npc.brenna",
                "entity_id": "npc.brenna",
                "strength": 14,
                "dexterity": 10,
                "constitution": 13,
                "intelligence": 11,
                "wisdom": 10,
                "charisma": 11,
                "diplomacy": 0,
                "survival": 0,
                "stealth": 0,
                "melee": 2,
                "hp": 14,
                "max_hp": 14,
                "stamina": 11,
                "max_stamina": 11,
            },
            {
                "id": "stats.creature.goblin_scout",
                "entity_id": "creature.goblin_scout",
                "strength": 9,
                "dexterity": 14,
                "constitution": 10,
                "intelligence": 9,
                "wisdom": 10,
                "charisma": 8,
                "diplomacy": 0,
                "survival": 2,
                "stealth": 3,
                "melee": 2,
                "hp": 10,
                "max_hp": 10,
                "stamina": 8,
                "max_stamina": 8,
            },
        ],
        "connections": [
            {
                "id": "connection.oakheart.watchtower",
                "from_place_id": "place.oakheart",
                "to_place_id": "place.watchtower",
                "travel_minutes": 25,
                "description": "A muddy trail cutting through pines toward the old watchtower.",
            },
            {
                "id": "connection.watchtower.oakheart",
                "from_place_id": "place.watchtower",
                "to_place_id": "place.oakheart",
                "travel_minutes": 20,
                "description": "The downhill path back to Oakheart.",
            },
        ],
        "inventories": [
            {"id": "inventory.npc.brenna", "owner_entity_id": "npc.brenna"},
        ],
        "inventory_items": [
            {
                "id": "inventory-item.npc.brenna.healing_draught",
                "inventory_id": "inventory.npc.brenna",
                "item_entity_id": "item.healing_draught",
                "quantity": 1,
            },
        ],
        "quests": [
            {
                "id": "quest.clear_watchtower",
                "title": "Scour the Watchtower",
                "description": "Find out what has taken root in the ruined watchtower and make the road safe again.",
                "giver_entity_id": "npc.elira",
                "target_entity_id": "creature.goblin_scout",
                "reward_text": "Mayor Elira will owe you a favor and Brenna offers supplies.",
            },
        ],
        "quest_states": [
            {
                "id": "quest-state.elira.clear_watchtower",
                "quest_id": "quest.clear_watchtower",
                "actor_entity_id": "npc.elira",
                "status": QuestStatus.AVAILABLE,
                "progress": 0,
                "notes": "Elira needs someone trustworthy to investigate the ruins.",
            }
        ],
        "events": [
            {
                "id": "event.oakheart.rumor",
                "event_type": EventType.SYSTEM,
                "title": "An uneasy morning",
                "description": "Villagers whisper about trouble at the ruined watchtower.",
                "occurred_at": DEFAULT_START_TIME,
                "location_entity_id": "place.oakheart",
            }
        ],
        "scheduled_events": [
            {
                "id": "scheduled.goblin.raid",
                "event_type": EventType.SIMULATION,
                "description": "The goblin scout prepares to range closer to Oakheart if left alone.",
                "scheduled_for": DEFAULT_START_TIME + timedelta(minutes=45),
                "actor_entity_id": "creature.goblin_scout",
                "location_entity_id": "place.watchtower",
                "payload": {"kind": "goblin_patrol"},
            }
        ],
        "facts": [
            {
                "id": "fact.watchtower.goblins",
                "subject_entity_id": "place.watchtower",
                "fact_key": "watchtower_goblins",
                "truth_text": "A goblin scout is occupying the ruined watchtower.",
                "truth_value": True,
            },
            {
                "id": "fact.watchtower.seal",
                "subject_entity_id": "place.watchtower",
                "fact_key": "watchtower_old_seal",
                "truth_text": "An old warding seal lies hidden beneath the watchtower rubble.",
                "truth_value": True,
            },
        ],
        "fact_visibility": [
            {
                "id": "fact-visibility.watchtower.goblins.public",
                "fact_id": "fact.watchtower.goblins",
                "viewer_role": "all",
            },
            {
                "id": "fact-visibility.watchtower.seal.tomas",
                "fact_id": "fact.watchtower.seal",
                "viewer_entity_id": "npc.tomas",
            },
        ],
        "beliefs": [
            {
                "id": "belief.elira.bandits",
                "holder_entity_id": "npc.elira",
                "belief_key": "watchtower_raiders",
                "belief_text": "Bandits have probably moved into the watchtower.",
                "confidence": 0.65,
            },
            {
                "id": "belief.tomas.goblins",
                "holder_entity_id": "npc.tomas",
                "fact_id": "fact.watchtower.goblins",
                "belief_key": "watchtower_goblins",
                "belief_text": "The tracks around the tower belong to goblins, not bandits.",
                "confidence": 0.92,
            },
            {
                "id": "belief.brenna.seal",
                "holder_entity_id": "npc.brenna",
                "belief_key": "tower_bad_luck",
                "belief_text": "Something cursed sits under the tower stones.",
                "confidence": 0.4,
            },
        ],
        "relationships": [
            {
                "id": "relationship.elira.tomas",
                "source_entity_id": "npc.elira",
                "target_entity_id": "npc.tomas",
                "attitude": "trusting",
                "score": 2,
                "notes": "Elira relies on Tomas for scouting reports.",
            },
            {
                "id": "relationship.tomas.elira",
                "source_entity_id": "npc.tomas",
                "target_entity_id": "npc.elira",
                "attitude": "respectful",
                "score": 2,
                "notes": "Tomas thinks Elira listens, even under pressure.",
            },
        ],
    }


def empty_scenario_template(scenario_id: str, name: str, description: str) -> dict:
    return {
        "scenario": {
            "id": scenario_id,
            "name": name,
            "description": description,
            "is_builtin": False,
        },
        "clock": DEFAULT_START_TIME,
        "entities": [
            {
                "id": "place.unfinished",
                "entity_type": EntityType.PLACE,
                "name": "Unfinished Camp",
                "description": "A placeholder campsite for a scenario still under construction.",
                "details": {"start": True, "placeholder": True},
            }
        ],
        "stats": [],
        "connections": [],
        "inventories": [],
        "inventory_items": [],
        "quests": [],
        "quest_states": [],
        "events": [],
        "scheduled_events": [],
        "facts": [],
        "fact_visibility": [],
        "beliefs": [],
        "relationships": [],
    }

