import { Package2, ScrollText } from 'lucide-react'
import { ScrollArea } from '../../../components/ui/scroll-area'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../../../components/ui/tabs'
import type { GameSnapshot } from '../../../lib/types'
import { playScreenClassNames } from '../constants'

export function PlayWorldPanelsSection({ snapshot }: { snapshot: GameSnapshot | undefined }) {
  return (
    <section className="play-section play-section-fill play-world-panel" data-testid="play-world-panels">
      <header className="play-section-header">
        <p className="play-section-title">World Panels</p>
        <p className="play-section-copy">Events, inventory, quests, and nearby routes.</p>
      </header>
      <div className="play-section-body play-section-body-fill p-0">
        <Tabs defaultValue="events" className="flex h-full min-h-0 flex-col">
          <TabsList className={playScreenClassNames.tabList}>
            <TabsTrigger className={playScreenClassNames.tabTrigger} value="events">
              Events
            </TabsTrigger>
            <TabsTrigger className={playScreenClassNames.tabTrigger} value="inventory">
              Inventory
            </TabsTrigger>
            <TabsTrigger className={playScreenClassNames.tabTrigger} value="quests">
              Quests
            </TabsTrigger>
            <TabsTrigger className={playScreenClassNames.tabTrigger} value="map">
              Map
            </TabsTrigger>
          </TabsList>

          <TabsContent className={playScreenClassNames.tabContent} value="events">
            <ScrollArea className="h-full">
              <div className="space-y-3 p-4">
                {snapshot?.recent_events.length ? (
                  snapshot.recent_events.map((event) => (
                    <div key={event.id} className="play-entry" data-kind="message">
                      <div className="play-entry-title">{event.title}</div>
                      <p>{event.description}</p>
                    </div>
                  ))
                ) : (
                  <div className="play-entry" data-kind="message">
                    No recent events yet.
                  </div>
                )}
              </div>
            </ScrollArea>
          </TabsContent>

          <TabsContent className={playScreenClassNames.tabContent} value="inventory">
            <ScrollArea className="h-full">
              <div className="space-y-3 p-4">
                {snapshot?.scene_context.inventory.length ? (
                  snapshot.scene_context.inventory.map((item) => (
                    <div key={item.item_entity_id} className="play-entry" data-kind="panel">
                      <div className="flex items-center justify-between gap-3">
                        <div className="flex items-center gap-2">
                          <Package2 className="h-4 w-4 text-accent" />
                          <span>{item.item_name}</span>
                        </div>
                        <span className="play-inline-stat">x{item.quantity}</span>
                      </div>
                    </div>
                  ))
                ) : (
                  <div className="play-entry" data-kind="message">
                    Inventory: empty
                  </div>
                )}
              </div>
            </ScrollArea>
          </TabsContent>

          <TabsContent className={playScreenClassNames.tabContent} value="quests">
            <ScrollArea className="h-full">
              <div className="space-y-3 p-4">
                {snapshot?.scene_context.active_quests.length ? (
                  snapshot.scene_context.active_quests.map((quest) => (
                    <div key={quest.id} className="play-entry" data-kind="panel">
                      <div className="play-entry-title">{quest.status}</div>
                      <p className="text-foreground">{quest.title}</p>
                      <p className="mt-2 text-muted">{quest.notes || quest.description}</p>
                    </div>
                  ))
                ) : (
                  <div className="play-entry" data-kind="message">
                    No active quests.
                  </div>
                )}
              </div>
            </ScrollArea>
          </TabsContent>

          <TabsContent className={playScreenClassNames.tabContent} value="map">
            <ScrollArea className="h-full">
              <div className="space-y-3 p-4">
                {snapshot?.scene_context.adjacent_places.length ? (
                  snapshot.scene_context.adjacent_places.map((route) => (
                    <div key={route.destination_id} className="play-entry" data-kind="panel">
                      <div className="flex items-center justify-between gap-3">
                        <div className="flex items-center gap-2">
                          <ScrollText className="h-4 w-4 text-accent" />
                          <span>{route.destination_name}</span>
                        </div>
                        <span className="play-inline-stat">{route.travel_minutes} min</span>
                      </div>
                    </div>
                  ))
                ) : (
                  <div className="play-entry" data-kind="message">
                    No routes from here.
                  </div>
                )}
              </div>
            </ScrollArea>
          </TabsContent>
        </Tabs>
      </div>
    </section>
  )
}
