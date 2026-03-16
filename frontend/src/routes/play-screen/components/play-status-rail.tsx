import type { GameSnapshot } from '../../../lib/types'
import { PlayCombatMonitorSection } from './play-combat-monitor-section'
import { PlayFieldStatusSection } from './play-field-status-section'
import { PlayWorldPanelsSection } from './play-world-panels-section'

export function PlayStatusRail({ snapshot }: { snapshot: GameSnapshot | undefined }) {
  return (
    <aside className="play-rail play-rail-stretch" data-testid="play-status-rail">
      <PlayFieldStatusSection snapshot={snapshot} />
      <PlayCombatMonitorSection encounter={snapshot?.active_encounter} />
      <PlayWorldPanelsSection snapshot={snapshot} />
    </aside>
  )
}
