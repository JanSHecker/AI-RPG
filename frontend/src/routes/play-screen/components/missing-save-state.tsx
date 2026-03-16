import { Alert } from '../../../components/ui/alert'
import { playScreenClassNames } from '../constants'

export function MissingSaveState() {
  return (
    <div className="play-shell">
      <div className="play-frame !grid-cols-1">
        <section className="play-section">
          <div className="play-section-body">
            <Alert variant="danger" className={playScreenClassNames.alert}>
              No save id was provided.
            </Alert>
          </div>
        </section>
      </div>
    </div>
  )
}
