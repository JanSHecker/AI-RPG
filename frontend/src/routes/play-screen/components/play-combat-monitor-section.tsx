import { Crosshair, ShieldAlert } from 'lucide-react'
import type { EncounterSummary } from '../../../lib/types'
import { PlayChip } from './play-chip'

export function PlayCombatMonitorSection({ encounter }: { encounter: EncounterSummary | null | undefined }) {
  if (!encounter) {
    return null
  }

  return (
    <section className="play-section">
      <header className="play-section-header">
        <p className="play-section-title">Combat Monitor</p>
        <p className="play-section-copy">Turn order and hit points from the persisted encounter state.</p>
      </header>
      <div className="play-section-body space-y-3">
        <div className="flex flex-wrap gap-2">
          <PlayChip variant="danger">Round {encounter.round_number}</PlayChip>
          <PlayChip variant={encounter.player_turn ? 'default' : 'muted'}>
            {encounter.player_turn ? 'Your Turn' : 'Enemy Turn'}
          </PlayChip>
        </div>
        {encounter.combatants.map((combatant) => (
          <div key={combatant.entity_id} className="play-entry" data-kind="panel">
            <div className="flex items-center justify-between gap-3">
              <div className="flex items-center gap-2">
                {combatant.is_player ? (
                  <ShieldAlert className="h-4 w-4 text-accent" />
                ) : (
                  <Crosshair className="h-4 w-4 text-danger" />
                )}
                <span>{combatant.name}</span>
              </div>
              <span className="play-inline-stat">
                {combatant.current_hp}/{combatant.max_hp}
              </span>
            </div>
          </div>
        ))}
      </div>
    </section>
  )
}
