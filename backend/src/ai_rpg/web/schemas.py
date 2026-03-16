from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from ai_rpg.core.contracts import ActionProposal, EncounterState, EventSummary, SceneContext


class WebModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ScenarioSummary(WebModel):
    id: str
    name: str
    description: str = ""
    is_builtin: bool = False


class SaveSummary(WebModel):
    id: str
    name: str
    scenario_id: str
    scenario_name: str
    player_name: str | None = None
    updated_at: datetime


class PlayerStatus(WebModel):
    entity_id: str
    name: str
    hp: int
    max_hp: int
    stamina: int
    max_stamina: int
    action_points: int
    max_action_points: int


class EncounterCombatant(WebModel):
    entity_id: str
    name: str
    current_hp: int
    max_hp: int
    is_player: bool
    is_defeated: bool
    is_active: bool


class EncounterSummary(WebModel):
    encounter_id: str
    state: EncounterState
    round_number: int
    location_entity_id: str
    active_entity_id: str | None = None
    player_turn: bool = False
    combatants: list[EncounterCombatant] = Field(default_factory=list)


class TerminalEntry(WebModel):
    id: str
    kind: Literal["system", "input", "narration", "message", "panel"]
    title: str | None = None
    content: str


class GameSnapshot(WebModel):
    save_id: str
    save_name: str
    scenario_id: str
    scenario_name: str
    player_name: str
    scene_context: SceneContext
    player_status: PlayerStatus
    recent_events: list[EventSummary] = Field(default_factory=list)
    active_encounter: EncounterSummary | None = None
    configuration_warnings: list[str] = Field(default_factory=list)
    seed_entries: list[TerminalEntry] = Field(default_factory=list)


class BootstrapResponse(WebModel):
    scenarios: list[ScenarioSummary] = Field(default_factory=list)
    saves: list[SaveSummary] = Field(default_factory=list)
    configuration_warnings: list[str] = Field(default_factory=list)


class CreateScenarioRequest(WebModel):
    name: str
    description: str = ""


class CreateSaveRequest(WebModel):
    scenario_id: str
    save_name: str
    player_name: str = "Wanderer"


class TurnRequest(WebModel):
    kind: Literal["input", "confirm", "cancel"]
    raw_input: str | None = None
    proposal: ActionProposal | None = None


class TurnResponse(WebModel):
    snapshot: GameSnapshot
    terminal_entries: list[TerminalEntry] = Field(default_factory=list)
    pending_proposal: ActionProposal | None = None
    exit_to_menu: bool = False
