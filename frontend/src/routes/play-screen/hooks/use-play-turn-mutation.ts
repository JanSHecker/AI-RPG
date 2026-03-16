import { useMutation, useQueryClient } from '@tanstack/react-query'
import type { Dispatch, SetStateAction } from 'react'
import { startTransition } from 'react'
import { ApiError, processTurn } from '../../../lib/api'
import type { ActionProposal, TerminalEntry, TurnRequest, TurnResponse } from '../../../lib/types'
import { isControlInput, isProposalEntry, makeActionEntry, makeTerminalEntry } from '../utils'

interface UsePlayTurnMutationOptions {
  saveId: string
  pendingProposal: ActionProposal | null
  setTranscript: Dispatch<SetStateAction<TerminalEntry[]>>
  setPendingProposal: Dispatch<SetStateAction<ActionProposal | null>>
  exitToMenu: () => void
}

const discardedActionMessage = 'You set the action aside.'

function buildTranscriptEntries(request: TurnRequest, response: TurnResponse): TerminalEntry[] {
  const entries = response.terminal_entries.filter((entry) => {
    if (response.pending_proposal && isProposalEntry(entry)) {
      return false
    }

    if (request.kind === 'cancel' && entry.kind === 'message' && entry.content === discardedActionMessage) {
      return false
    }

    return true
  })

  if (request.kind === 'confirm') {
    if (request.proposal && response.pending_proposal === null) {
      return [makeActionEntry(request.proposal.raw_input, request.proposal), ...entries]
    }

    return entries
  }

  if (request.kind === 'input' && request.raw_input && response.pending_proposal === null && !isControlInput(request.raw_input)) {
    return [makeActionEntry(request.raw_input), ...entries]
  }

  return entries
}

export function usePlayTurnMutation({
  saveId,
  pendingProposal,
  setTranscript,
  setPendingProposal,
  exitToMenu,
}: UsePlayTurnMutationOptions) {
  const queryClient = useQueryClient()
  const turnMutation = useMutation({
    mutationFn: ({ request }: { request: TurnRequest }) => processTurn(saveId, request),
    onSuccess: (response, variables) => {
      queryClient.setQueryData(['snapshot', saveId], response.snapshot)
      startTransition(() => {
        setTranscript((current) => [...current, ...buildTranscriptEntries(variables.request, response)])
        setPendingProposal(response.pending_proposal)
      })
      if (response.exit_to_menu) {
        startTransition(() => {
          exitToMenu()
        })
      }
    },
    onError: (error) => {
      const message = error instanceof ApiError ? error.message : 'The terminal link went dark for a moment.'
      startTransition(() => {
        setTranscript((current) => [...current, makeTerminalEntry('message', message, 'Error')])
      })
    },
  })

  function dispatchTurn(request: TurnRequest) {
    if (!saveId) return
    turnMutation.mutate({ request: { ...request, proposal: request.proposal ?? pendingProposal } })
  }

  return {
    dispatchTurn,
    turnMutation,
  }
}
