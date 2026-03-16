# Subagent Handoff Notes

This repository is structured so the orchestrator can keep shared contracts stable while future work is split into isolated branches or worktrees.

## Contract freeze

Do not change these interfaces without orchestrator review:

- `ContextBuilder.build(save_id, actor_id) -> SceneContext`
- `ActionEvaluator.resolve(intent, context) -> TurnResolution`
- `CombatEngine.start_encounter(...) -> encounter_id`
- `CombatEngine.resolve_turn(encounter_id, combatant_id, intent) -> TurnResolution`
- `SimulationEngine.advance(save_id, from_time, to_time) -> list[WorldEvent]`
- `LLMAdapter.generate_structured(request) -> NarrationResponse`

The shared DTOs live in `backend/src/ai_rpg/core/contracts.py`.

## Ownership split

- Orchestrator branch: `backend/src/ai_rpg/cli`, `backend/src/ai_rpg/game/action_evaluator.py`, `backend/src/ai_rpg/game/context_builder.py`, `backend/src/ai_rpg/llm`, migrations, and cross-system tests.
- Combat branch: `backend/src/ai_rpg/game/combat.py`, `backend/src/ai_rpg/game/combat_rules.py`, `backend/src/ai_rpg/db/combat_repo.py`, and combat tests.
- Simulation branch: `backend/src/ai_rpg/game/simulation.py`, `backend/src/ai_rpg/game/time.py`, `backend/src/ai_rpg/db/event_repo.py`, and simulation tests.
- Scenario branch: `backend/src/ai_rpg/scenarios`, `backend/src/ai_rpg/cli/scenario_menu.py`, and scenario tests.

## Merge order

1. Keep migrations and contracts on the orchestrator branch.
2. Merge scenario tooling first if test fixtures need seed changes.
3. Merge simulation before deeper combat integration so time/event behavior is stable.
4. Merge combat after simulation unless combat stays interface-local.
5. Finish with orchestrator-led integration and end-to-end test updates.
