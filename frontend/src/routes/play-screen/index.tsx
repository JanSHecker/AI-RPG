import { useQuery } from '@tanstack/react-query'
import { useNavigate, useParams } from 'react-router-dom'
import { getSaveSnapshot } from '../../lib/api'
import { MissingSaveState } from './components/missing-save-state'
import { PlayCommandPanel } from './components/play-command-panel'
import { PlayStatusRail } from './components/play-status-rail'
import { PlayTerminalFeed } from './components/play-terminal-feed'
import { usePlayProposal } from './hooks/use-play-proposal'
import { usePlayRuntime } from './hooks/use-play-runtime'
import { usePlayTranscript } from './hooks/use-play-transcript'
import { usePlayTurnMutation } from './hooks/use-play-turn-mutation'

function PlayScreenView({ saveId }: { saveId: string }) {
  const navigate = useNavigate()

  const snapshotQuery = useQuery({
    enabled: Boolean(saveId),
    queryKey: ['snapshot', saveId],
    queryFn: () => getSaveSnapshot(saveId),
  })

  const [transcript, setTranscript] = usePlayTranscript(saveId, snapshotQuery.data)
  const [pendingProposal, setPendingProposal] = usePlayProposal(saveId)

  usePlayRuntime({
    saveId,
    snapshot: snapshotQuery.data,
    pendingProposal,
    transcript,
  })

  const { dispatchTurn, turnMutation } = usePlayTurnMutation({
    saveId,
    pendingProposal,
    setTranscript,
    setPendingProposal,
    exitToMenu: () => navigate('/'),
  })

  return (
    <div className="play-shell">
      <div className="play-frame">
        <main className="play-stage">
          <PlayTerminalFeed
            isLoading={snapshotQuery.isLoading}
            transcript={transcript}
            onNavigateBack={() => navigate('/')}
          />
          <PlayCommandPanel
            snapshot={snapshotQuery.data}
            snapshotError={snapshotQuery.error}
            pendingProposal={pendingProposal}
            isPending={turnMutation.isPending}
            onDispatchTurn={dispatchTurn}
          />
        </main>

        <PlayStatusRail snapshot={snapshotQuery.data} />
      </div>
    </div>
  )
}

export function PlayScreen() {
  const { saveId = '' } = useParams()

  if (!saveId) {
    return <MissingSaveState />
  }

  return <PlayScreenView key={saveId} saveId={saveId} />
}
