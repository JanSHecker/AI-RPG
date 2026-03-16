import { useDeferredValue, useState } from "react";
import { Alert } from "../../../components/ui/alert";
import { Button } from "../../../components/ui/button";
import { Input } from "../../../components/ui/input";
import { ApiError } from "../../../lib/api";
import type {
  ActionProposal,
  GameSnapshot,
  TurnRequest,
} from "../../../lib/types";
import { playScreenClassNames } from "../constants";

interface PlayCommandPanelProps {
  snapshot: GameSnapshot | undefined;
  snapshotError: unknown;
  pendingProposal: ActionProposal | null;
  isPending: boolean;
  onDispatchTurn: (request: TurnRequest) => void;
}

export function PlayCommandPanel({
  snapshot,
  snapshotError,
  pendingProposal,
  isPending,
  onDispatchTurn,
}: PlayCommandPanelProps) {
  const [input, setInput] = useState("");
  const deferredInput = useDeferredValue(input);

  return (
    <section className="play-section">
      <div className="play-section-body space-y-4">
        {snapshotError instanceof ApiError ? (
          <Alert variant="danger" className={playScreenClassNames.alert}>
            {snapshotError.message}
          </Alert>
        ) : null}

        {snapshot?.configuration_warnings.map((warning) => (
          <Alert key={warning} className={playScreenClassNames.alert}>
            {warning}
          </Alert>
        ))}

        {pendingProposal ? (
          <div className="play-callout">
            Pending proposal:{" "}
            <span className="text-accent">{pendingProposal.action_name}</span>.
            Confirm, cancel, or replace it with a fresh out-of-combat action.
          </div>
        ) : null}

        {pendingProposal ? (
          <div className="flex flex-wrap gap-2">
            <Button
              size="sm"
              className={`${playScreenClassNames.primaryButton} !h-10`}
              onClick={() =>
                onDispatchTurn({ kind: "confirm", proposal: pendingProposal })
              }
            >
              Confirm
            </Button>
            <Button
              size="sm"
              className={`${playScreenClassNames.dangerButton} !h-10`}
              onClick={() =>
                onDispatchTurn({ kind: "cancel", proposal: pendingProposal })
              }
            >
              Cancel
            </Button>
          </div>
        ) : null}

        <form
          className="grid w-full gap-3 md:grid-cols-[minmax(0,1fr)_auto]"
          onSubmit={(event) => {
            event.preventDefault();
            const trimmed = input.trim();
            if (!trimmed) return;
            onDispatchTurn({
              kind: "input",
              raw_input: trimmed,
              proposal: pendingProposal,
            });
            setInput("");
          }}
        >
          <Input
            className={playScreenClassNames.field}
            value={input}
            onChange={(event) => setInput(event.target.value)}
            autoFocus
            placeholder="Type a freeform action or a slash command..."
          />
          <Button
            type="submit"
            className={`${playScreenClassNames.primaryButton} !h-11`}
            disabled={!deferredInput.trim() || isPending}
          >
            {isPending ? "Processing..." : "Transmit"}
          </Button>
        </form>
      </div>
    </section>
  );
}
