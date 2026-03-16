import type { TerminalEntry } from '../../../lib/types'

export function TerminalBlock({ entry }: { entry: TerminalEntry }) {
  return (
    <article className="play-terminal-entry" data-has-details={entry.details ? 'true' : undefined} data-kind={entry.kind}>
      {entry.title ? <div className="play-entry-title">{entry.title}</div> : null}
      <pre className="whitespace-pre-wrap break-words font-inherit text-inherit">{entry.content}</pre>
      {entry.details ? (
        <details className="play-terminal-details">
          <summary className="play-terminal-details-toggle">Proposed action details</summary>
          <pre className="play-terminal-details-body">{entry.details}</pre>
        </details>
      ) : null}
    </article>
  )
}
