import { startTransition, useEffect, useState } from 'react'
import { loadTranscript, saveTranscript } from '../../../lib/session'
import type { GameSnapshot, TerminalEntry } from '../../../lib/types'
import { normalizeTranscriptEntries } from '../utils'

export function usePlayTranscript(saveId: string, snapshot: GameSnapshot | undefined) {
  const [transcript, setTranscript] = useState<TerminalEntry[]>(() => normalizeTranscriptEntries(loadTranscript(saveId) ?? []))

  useEffect(() => {
    if (snapshot && transcript.length === 0) {
      startTransition(() => {
        setTranscript(normalizeTranscriptEntries(snapshot.seed_entries))
      })
    }
  }, [snapshot, transcript.length])

  useEffect(() => {
    if (!saveId) return
    saveTranscript(saveId, transcript)
  }, [saveId, transcript])

  return [transcript, setTranscript] as const
}
