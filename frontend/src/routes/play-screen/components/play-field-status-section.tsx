import type { GameSnapshot } from '../../../lib/types'
import { formatWorldTime } from '../utils'
import { StatMeter } from './stat-meter'

export function PlayFieldStatusSection({ snapshot }: { snapshot: GameSnapshot | undefined }) {
  return (
    <section className="play-section">
      <header className="play-section-header">
        <p className="play-section-title">Field Status</p>
        <p className="play-section-copy">Current player state and the location clock.</p>
      </header>
      <div className="play-section-body space-y-4">
        {snapshot ? (
          <>
            <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-1">
              <div>
                <p className="play-meta-label">Current Location</p>
                <p className="play-meta-value">{snapshot.scene_context.location?.name ?? 'Unknown'}</p>
              </div>
              <div>
                <p className="play-meta-label">World Time</p>
                <p className="play-meta-value">{formatWorldTime(snapshot.scene_context.current_time)}</p>
              </div>
            </div>
            <StatMeter label="Health" value={snapshot.player_status.hp} max={snapshot.player_status.max_hp} />
            <StatMeter label="Stamina" value={snapshot.player_status.stamina} max={snapshot.player_status.max_stamina} />
            <StatMeter
              label="Action Points"
              value={snapshot.player_status.action_points}
              max={snapshot.player_status.max_action_points}
            />
          </>
        ) : null}
      </div>
    </section>
  )
}
