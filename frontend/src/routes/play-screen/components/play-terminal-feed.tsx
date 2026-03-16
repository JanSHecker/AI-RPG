import { ScrollArea } from "../../../components/ui/scroll-area";
import type { TerminalEntry } from "../../../lib/types";
import { TerminalBlock } from "./terminal-block";

interface PlayTerminalFeedProps {
  isLoading: boolean;
  transcript: TerminalEntry[];
}

export function PlayTerminalFeed({
  isLoading,
  transcript,
}: PlayTerminalFeedProps) {
  return (
    <section className="play-section flex min-h-[68vh] flex-col xl:min-h-0">
      <div className="play-section-body flex-1 min-h-0 p-0">
        <ScrollArea className="h-[48vh] md:h-[56vh] xl:h-full">
          <div className="play-terminal-feed p-5">
            {isLoading && transcript.length === 0 ? (
              <div className="play-terminal-entry animate-pulseLine" data-kind="message">
                Establishing terminal link...
              </div>
            ) : (
              transcript.map((entry) => (
                <TerminalBlock key={entry.id} entry={entry} />
              ))
            )}
          </div>
        </ScrollArea>
      </div>
    </section>
  );
}
