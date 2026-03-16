export interface ScenarioSummary {
  id: string
  name: string
  description: string
  is_builtin: boolean
}

export interface SaveSummary {
  id: string
  name: string
  scenario_id: string
  scenario_name: string
  player_name: string | null
  updated_at: string
}

export interface SceneEntity {
  id: string
  name: string
  entity_type: string
  description: string
  is_hostile: boolean
  is_player: boolean
  attitude: number
}

export interface SceneConnection {
  destination_id: string
  destination_name: string
  travel_minutes: number
  description: string
}

export interface QuestSnapshot {
  id: string
  title: string
  description: string
  status: string
  notes: string
}

export interface InventoryEntry {
  item_entity_id: string
  item_name: string
  quantity: number
}

export interface EventSummary {
  id: string
  event_type: string
  title: string
  description: string
  occurred_at: string
}

export interface SceneContext {
  save_id: string
  actor_id: string
  current_time: string
  location: SceneEntity | null
  nearby_entities: SceneEntity[]
  adjacent_places: SceneConnection[]
  active_quests: QuestSnapshot[]
  recent_events: EventSummary[]
  visible_facts: Array<Record<string, unknown>>
  relevant_beliefs: Array<Record<string, unknown>>
  inventory: InventoryEntry[]
  action_points: number
  max_action_points: number
}

export interface PlayerStatus {
  entity_id: string
  name: string
  hp: number
  max_hp: number
  stamina: number
  max_stamina: number
  action_points: number
  max_action_points: number
}

export interface EncounterCombatant {
  entity_id: string
  name: string
  current_hp: number
  max_hp: number
  is_player: boolean
  is_defeated: boolean
  is_active: boolean
}

export interface EncounterSummary {
  encounter_id: string
  state: string
  round_number: number
  location_entity_id: string
  active_entity_id: string | null
  player_turn: boolean
  combatants: EncounterCombatant[]
}

export interface TerminalEntry {
  id: string
  kind: 'system' | 'input' | 'narration' | 'message' | 'panel'
  title: string | null
  content: string
  details?: string | null
}

export interface ActionProposal {
  action_id: string
  action_name: string
  raw_input: string
  description: string
  relevant_attribute: string
  difficulty: number
  action_point_cost: number
  avoid_failure_percent: number
  clean_success_percent: number
  resolution_mode: string
  handler_key: string | null
  target_id: string | null
  target_name: string | null
  destination_id: string | null
  destination_name: string | null
  can_confirm_now: boolean
  blocker_message: string | null
  created_this_turn: boolean
}

export interface GameSnapshot {
  save_id: string
  save_name: string
  scenario_id: string
  scenario_name: string
  player_name: string
  scene_context: SceneContext
  player_status: PlayerStatus
  recent_events: EventSummary[]
  active_encounter: EncounterSummary | null
  configuration_warnings: string[]
  seed_entries: TerminalEntry[]
}

export interface BootstrapResponse {
  scenarios: ScenarioSummary[]
  saves: SaveSummary[]
  configuration_warnings: string[]
}

export interface TurnResponse {
  snapshot: GameSnapshot
  terminal_entries: TerminalEntry[]
  pending_proposal: ActionProposal | null
  exit_to_menu: boolean
}

export interface TurnRequest {
  kind: 'input' | 'confirm' | 'cancel'
  raw_input?: string
  proposal?: ActionProposal | null
}
