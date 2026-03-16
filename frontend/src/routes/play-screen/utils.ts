import type { ActionProposal, TerminalEntry } from '../../lib/types'

const proposalEntryTitle = 'Proposed Action'
const controlInputs = new Set(['yes', 'do it', 'go ahead', 'confirm', 'no', 'cancel'])
const confirmInputs = new Set(['yes', 'do it', 'go ahead', 'confirm'])

export function formatActionDetails(proposal: ActionProposal): string {
  const lines = [
    `Matched: ${proposal.action_name}`,
    `Description: ${proposal.description || proposal.raw_input}`,
    `Avoid Failure: ${proposal.avoid_failure_percent.toFixed(1)}%`,
    `Clean Success: ${proposal.clean_success_percent.toFixed(1)}%`,
    `AP Cost: ${proposal.action_point_cost}`,
  ]

  if (proposal.target_name) {
    lines.push(`Target: ${proposal.target_name}`)
  }

  if (proposal.destination_name) {
    lines.push(`Destination: ${proposal.destination_name}`)
  }

  if (proposal.blocker_message) {
    lines.push(`Blocked: ${proposal.blocker_message}`)
  }

  return lines.join('\n')
}

function sanitizeProposalDetails(details: string): string {
  return details
    .split('\n')
    .map((line) => line.trim())
    .filter((line) => line.length > 0 && !line.startsWith('Confirm:') && !line.startsWith('Cancel:'))
    .map((line) => (line.startsWith('Action: ') ? `Matched: ${line.slice('Action: '.length)}` : line))
    .join('\n')
}

export function makeTerminalEntry(
  kind: TerminalEntry['kind'],
  content: string,
  title: string | null = null,
  options: { details?: string | null } = {},
): TerminalEntry {
  return {
    id: `local-${globalThis.crypto?.randomUUID?.() ?? `${Date.now()}-${Math.random().toString(16).slice(2)}`}`,
    kind,
    title,
    content,
    details: options.details ?? null,
  }
}

export function makeActionEntry(rawInput: string, proposal?: ActionProposal | null): TerminalEntry {
  return makeTerminalEntry('input', rawInput, 'Action', {
    details: proposal ? formatActionDetails(proposal) : null,
  })
}

export function isProposalEntry(entry: TerminalEntry) {
  return entry.kind === 'panel' && entry.title === proposalEntryTitle
}

export function isControlInput(rawInput: string | undefined) {
  return controlInputs.has((rawInput ?? '').trim().toLowerCase())
}

function isLegacyInputEntry(entry: TerminalEntry) {
  return entry.kind === 'input' && entry.title === 'Input'
}

export function normalizeTranscriptEntries(entries: TerminalEntry[]): TerminalEntry[] {
  const normalized: TerminalEntry[] = []

  for (let index = 0; index < entries.length; index += 1) {
    const entry = entries[index]

    if (entry.title === 'Action') {
      normalized.push(entry)
      continue
    }

    if (isLegacyInputEntry(entry)) {
      const rawInput = entry.content.trim()
      const proposalEntry = entries[index + 1]

      if (proposalEntry && isProposalEntry(proposalEntry)) {
        const confirmationEntry = entries[index + 2]
        if (
          confirmationEntry &&
          isLegacyInputEntry(confirmationEntry) &&
          confirmInputs.has(confirmationEntry.content.trim().toLowerCase())
        ) {
          normalized.push(makeTerminalEntry('input', rawInput, 'Action', { details: sanitizeProposalDetails(proposalEntry.content) }))
          index += 2
        } else {
          index += 1
        }
        continue
      }

      if (!isControlInput(rawInput)) {
        normalized.push(makeActionEntry(rawInput))
      }
      continue
    }

    if (isProposalEntry(entry)) {
      continue
    }

    normalized.push(entry)
  }

  return normalized
}

export function formatWorldTime(value: string | undefined): string {
  return value ? new Date(value).toLocaleString() : 'Syncing...'
}
