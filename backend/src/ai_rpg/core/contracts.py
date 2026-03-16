from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Protocol

from pydantic import BaseModel, ConfigDict, Field


class EntityType(str, Enum):
    PLAYER = "player"
    PERSON = "person"
    PLACE = "place"
    ITEM = "item"
    FACTION = "faction"
    CREATURE = "creature"


class QuestStatus(str, Enum):
    AVAILABLE = "available"
    ACTIVE = "active"
    COMPLETED = "completed"
    FAILED = "failed"


class EventType(str, Enum):
    SYSTEM = "system"
    DIALOGUE = "dialogue"
    MOVEMENT = "movement"
    COMBAT = "combat"
    QUEST = "quest"
    DISCOVERY = "discovery"
    SIMULATION = "simulation"


class SuccessTier(str, Enum):
    CRITICAL_FAILURE = "critical_failure"
    FAILURE = "failure"
    MIXED = "mixed"
    SUCCESS = "success"
    CRITICAL_SUCCESS = "critical_success"


class ActionType(str, Enum):
    LOOK = "look"
    TALK = "talk"
    MOVE = "move"
    ATTACK = "attack"
    WAIT = "wait"
    INVENTORY = "inventory"
    QUESTS = "quests"
    COMMAND = "command"
    CATALOG = "catalog"
    UNKNOWN = "unknown"


class ActionResolutionMode(str, Enum):
    DETERMINISTIC = "deterministic"
    LLM_EFFECTS = "llm_effects"


class ActionAttribute(str, Enum):
    STRENGTH = "strength"
    DEXTERITY = "dexterity"
    CONSTITUTION = "constitution"
    INTELLIGENCE = "intelligence"
    WISDOM = "wisdom"
    CHARISMA = "charisma"
    DIPLOMACY = "diplomacy"
    SURVIVAL = "survival"
    STEALTH = "stealth"
    MELEE = "melee"


class TimeScale(str, Enum):
    LOCAL = "local"
    TRAVEL = "travel"
    COMBAT = "combat"


class EncounterState(str, Enum):
    ACTIVE = "active"
    WON = "won"
    LOST = "lost"
    ESCAPED = "escaped"


class PatchOperationKind(str, Enum):
    MOVE_ENTITY = "move_entity"
    CREATE_EVENT = "create_event"
    UPDATE_QUEST = "update_quest"
    ADVANCE_TIME = "advance_time"
    ADJUST_ACTION_POINTS = "adjust_action_points"
    UPDATE_RELATIONSHIP = "update_relationship"
    DAMAGE_ENTITY = "damage_entity"
    HEAL_ENTITY = "heal_entity"
    ADD_BELIEF = "add_belief"
    START_COMBAT = "start_combat"
    END_COMBAT = "end_combat"
    ADD_ITEM = "add_item"


class SceneEntity(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    name: str
    entity_type: EntityType
    description: str = ""
    is_hostile: bool = False
    is_player: bool = False
    attitude: int = 0


class SceneConnection(BaseModel):
    model_config = ConfigDict(extra="forbid")

    destination_id: str
    destination_name: str
    travel_minutes: int
    description: str = ""


class SceneFact(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    fact_key: str
    text: str
    subject_entity_id: str | None = None


class BeliefRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    holder_entity_id: str
    belief_key: str
    belief_text: str
    confidence: float = 0.5
    fact_id: str | None = None


class QuestSnapshot(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    title: str
    description: str
    status: QuestStatus
    notes: str = ""


class EventSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    event_type: EventType
    title: str
    description: str
    occurred_at: datetime


class InventoryEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    item_entity_id: str
    item_name: str
    quantity: int = 1


class DiceRoll(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sides: int
    count: int = 1
    rolls: list[int]
    modifier: int = 0
    total: int


class ActionCheck(BaseModel):
    model_config = ConfigDict(extra="forbid")

    stat: str
    skill: str | None = None
    difficulty: int = 10
    dice_roll: DiceRoll
    modifier: int = 0
    total: int


class PatchOperation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: PatchOperationKind
    target_id: str | None = None
    data: dict[str, Any] = Field(default_factory=dict)


class StatePatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    save_id: str
    operations: list[PatchOperation] = Field(default_factory=list)

    @classmethod
    def empty(cls, save_id: str) -> "StatePatch":
        return cls(save_id=save_id, operations=[])


class WorldEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    event_type: EventType
    title: str
    description: str
    occurred_at: datetime
    actor_entity_id: str | None = None
    target_entity_id: str | None = None
    location_entity_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class SceneContext(BaseModel):
    model_config = ConfigDict(extra="forbid")

    save_id: str
    actor_id: str
    current_time: datetime
    location: SceneEntity | None = None
    nearby_entities: list[SceneEntity] = Field(default_factory=list)
    adjacent_places: list[SceneConnection] = Field(default_factory=list)
    active_quests: list[QuestSnapshot] = Field(default_factory=list)
    recent_events: list[EventSummary] = Field(default_factory=list)
    visible_facts: list[SceneFact] = Field(default_factory=list)
    relevant_beliefs: list[BeliefRecord] = Field(default_factory=list)
    inventory: list[InventoryEntry] = Field(default_factory=list)
    action_points: int = 0
    max_action_points: int = 0


class TurnIntent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    raw_input: str
    action_type: ActionType
    actor_id: str
    command: str | None = None
    target_id: str | None = None
    target_name: str | None = None
    destination_id: str | None = None
    destination_name: str | None = None
    content: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class ActionDraft(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    description: str = ""
    aliases: list[str] = Field(default_factory=list)
    relevant_attribute: ActionAttribute
    difficulty: int = 10
    action_point_cost: int = 0


class ActionMatchDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")

    action_id: str | None = None
    confidence: float | None = None
    created_action: ActionDraft | None = None


class ActionProposal(BaseModel):
    model_config = ConfigDict(extra="forbid")

    action_id: str
    action_name: str
    raw_input: str
    description: str = ""
    relevant_attribute: ActionAttribute
    difficulty: int = 10
    action_point_cost: int = 0
    avoid_failure_percent: float = 0.0
    clean_success_percent: float = 0.0
    resolution_mode: ActionResolutionMode
    handler_key: str | None = None
    target_id: str | None = None
    target_name: str | None = None
    destination_id: str | None = None
    destination_name: str | None = None
    can_confirm_now: bool = True
    blocker_message: str | None = None
    created_this_turn: bool = False


class NarrationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    system_prompt: str
    scene_context: SceneContext
    intent: TurnIntent
    resolution_hint: str
    allowed_operations: list[PatchOperationKind] = Field(default_factory=list)


class NarrationResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    narration: str
    operations: list[PatchOperation] = Field(default_factory=list)
    spoken_dialogue: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class TurnResolution(BaseModel):
    model_config = ConfigDict(extra="forbid")

    allowed: bool
    success_tier: SuccessTier
    narration: str
    action_check: ActionCheck | None = None
    patch: StatePatch
    generated_events: list[WorldEvent] = Field(default_factory=list)
    time_advance_minutes: int = 0
    time_scale: TimeScale = TimeScale.LOCAL
    enter_combat: bool = False
    encounter_id: str | None = None
    messages: list[str] = Field(default_factory=list)
    proposal: ActionProposal | None = None
    awaiting_confirmation: bool = False


class ContextBuilder(Protocol):
    def build(self, save_id: str, actor_id: str) -> SceneContext:
        ...


class ActionEvaluator(Protocol):
    def resolve(self, intent: TurnIntent, context: SceneContext) -> TurnResolution:
        ...


class CombatEngine(Protocol):
    def start_encounter(
        self,
        save_id: str,
        location_entity_id: str,
        actor_ids: list[str],
    ) -> str:
        ...

    def resolve_turn(
        self,
        encounter_id: str,
        combatant_id: str,
        intent: TurnIntent,
    ) -> TurnResolution:
        ...


class SimulationEngine(Protocol):
    def advance(
        self,
        save_id: str,
        from_time: datetime,
        to_time: datetime,
    ) -> list[WorldEvent]:
        ...


class LLMAdapter(Protocol):
    def generate_structured(self, request: NarrationRequest) -> NarrationResponse:
        ...
