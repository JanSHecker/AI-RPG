import { useEffect, useState } from 'react'
import { loadProposal, saveProposal } from '../../../lib/session'
import type { ActionProposal } from '../../../lib/types'

export function usePlayProposal(saveId: string) {
  const [pendingProposal, setPendingProposal] = useState<ActionProposal | null>(() => loadProposal(saveId))

  useEffect(() => {
    if (!saveId) return
    saveProposal(saveId, pendingProposal)
  }, [saveId, pendingProposal])

  return [pendingProposal, setPendingProposal] as const
}
