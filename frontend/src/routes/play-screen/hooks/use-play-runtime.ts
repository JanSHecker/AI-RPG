import { useEffect } from 'react'
import type { ActionProposal, GameSnapshot, TerminalEntry } from '../../../lib/types'

declare global {
  interface Window {
    render_game_to_text?: () => string
    advanceTime?: (ms: number) => number
  }
}

interface UsePlayRuntimeOptions {
  saveId: string
  snapshot: GameSnapshot | undefined
  pendingProposal: ActionProposal | null
  transcript: TerminalEntry[]
}

export function usePlayRuntime({ saveId, snapshot, pendingProposal, transcript }: UsePlayRuntimeOptions) {
  useEffect(() => {
    window.render_game_to_text = () =>
      JSON.stringify(
        {
          saveId,
          location: snapshot?.scene_context.location?.name ?? null,
          actionPoints: snapshot?.player_status.action_points ?? null,
          activeEncounter: snapshot?.active_encounter
            ? {
                round: snapshot.active_encounter.round_number,
                combatants: snapshot.active_encounter.combatants.map((combatant) => ({
                  name: combatant.name,
                  hp: combatant.current_hp,
                  maxHp: combatant.max_hp,
                  active: combatant.is_active,
                })),
              }
            : null,
          pendingProposal: pendingProposal?.action_name ?? null,
          transcriptTail: transcript.slice(-6),
        },
        null,
        2,
      )
    window.advanceTime = (ms: number) => ms
    return () => {
      delete window.render_game_to_text
      delete window.advanceTime
    }
  }, [saveId, snapshot, pendingProposal, transcript])
}
