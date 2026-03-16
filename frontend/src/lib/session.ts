import type { ActionProposal, TerminalEntry } from './types'

const transcriptKey = (saveId: string) => `ai-rpg:transcript:${saveId}`
const proposalKey = (saveId: string) => `ai-rpg:proposal:${saveId}`

function parseJson<T>(raw: string | null): T | null {
  if (!raw) return null
  try {
    return JSON.parse(raw) as T
  } catch {
    return null
  }
}

export function loadTranscript(saveId: string): TerminalEntry[] | null {
  if (typeof window === 'undefined') return null
  return parseJson<TerminalEntry[]>(window.sessionStorage.getItem(transcriptKey(saveId)))
}

export function saveTranscript(saveId: string, entries: TerminalEntry[]) {
  if (typeof window === 'undefined') return
  window.sessionStorage.setItem(transcriptKey(saveId), JSON.stringify(entries))
}

export function loadProposal(saveId: string): ActionProposal | null {
  if (typeof window === 'undefined') return null
  return parseJson<ActionProposal>(window.sessionStorage.getItem(proposalKey(saveId)))
}

export function saveProposal(saveId: string, proposal: ActionProposal | null) {
  if (typeof window === 'undefined') return
  if (proposal === null) {
    window.sessionStorage.removeItem(proposalKey(saveId))
    return
  }
  window.sessionStorage.setItem(proposalKey(saveId), JSON.stringify(proposal))
}
