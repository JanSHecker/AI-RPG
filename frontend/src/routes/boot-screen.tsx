import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useDeferredValue, useState, useTransition } from 'react'
import { useNavigate } from 'react-router-dom'
import { Alert } from '../components/ui/alert'
import { Button } from '../components/ui/button'
import { Input } from '../components/ui/input'
import { Textarea } from '../components/ui/textarea'
import { ApiError, createSave, createScenario, getBootstrap } from '../lib/api'

type BootPanelId = 'new' | 'load' | 'scenario'

export function BootScreen() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [isRouting, startTransition] = useTransition()
  const [activePanel, setActivePanel] = useState<BootPanelId>('new')
  const [selectedScenarioId, setSelectedScenarioId] = useState('')
  const [saveName, setSaveName] = useState('New Adventure')
  const [playerName, setPlayerName] = useState('Wanderer')
  const [scenarioName, setScenarioName] = useState('')
  const [scenarioDescription, setScenarioDescription] = useState('')
  const [search, setSearch] = useState('')
  const deferredSearch = useDeferredValue(search)

  const bootstrapQuery = useQuery({
    queryKey: ['bootstrap'],
    queryFn: getBootstrap,
  })

  const createSaveMutation = useMutation({
    mutationFn: createSave,
    onSuccess: async (save) => {
      await queryClient.invalidateQueries({ queryKey: ['bootstrap'] })
      startTransition(() => {
        navigate(`/play/${save.id}`)
      })
    },
  })

  const createScenarioMutation = useMutation({
    mutationFn: createScenario,
    onSuccess: async (scenario) => {
      await queryClient.invalidateQueries({ queryKey: ['bootstrap'] })
      setSelectedScenarioId(scenario.id)
      setScenarioName('')
      setScenarioDescription('')
      setActivePanel('new')
    },
  })

  const saves =
    bootstrapQuery.data?.saves.filter((save) => {
      if (!deferredSearch.trim()) return true
      const haystack = `${save.name} ${save.scenario_name} ${save.player_name ?? ''}`.toLowerCase()
      return haystack.includes(deferredSearch.toLowerCase())
    }) ?? []

  const queryError = bootstrapQuery.error instanceof ApiError ? bootstrapQuery.error.message : null
  const createSaveError =
    createSaveMutation.error instanceof ApiError ? createSaveMutation.error.message : null
  const createScenarioError =
    createScenarioMutation.error instanceof ApiError ? createScenarioMutation.error.message : null
  const effectiveSelectedScenarioId =
    bootstrapQuery.data?.scenarios.some((scenario) => scenario.id === selectedScenarioId)
      ? selectedScenarioId
      : bootstrapQuery.data?.scenarios[0]?.id || ''
  const selectedScenario =
    bootstrapQuery.data?.scenarios.find((scenario) => scenario.id === effectiveSelectedScenarioId) ?? null
  const scenarioCount = bootstrapQuery.data?.scenarios.length ?? 0
  const saveCount = bootstrapQuery.data?.saves.length ?? 0

  const panelDetails: Record<
    BootPanelId,
    {
      description: string
      label: string
    }
  > = {
    new: {
      label: 'New Game',
      description: 'Choose a scenario, name the run, and enter the world.',
    },
    load: {
      label: 'Load Game',
      description: 'Resume any save without the extra frontpage clutter.',
    },
    scenario: {
      label: 'Create Scenario',
      description: 'Write a compact scenario shell and make it available immediately.',
    },
  }

  const navItems: Array<{ id: BootPanelId; label: string; meta: string }> = [
    { id: 'new', label: 'New Game', meta: `${scenarioCount || 0} scenarios` },
    { id: 'load', label: 'Load Game', meta: `${saveCount || 0} saves` },
    { id: 'scenario', label: 'Create Scenario', meta: 'authoring' },
  ]
  const alertClass = '!rounded-none !border-accent/35 !bg-black/80'
  const fieldClass = '!rounded-none !border-accent/30 !bg-black/80 !text-foreground placeholder:!text-muted/50'
  const buttonClass =
    '!rounded-none !border-accent/45 !bg-transparent !text-accent shadow-none hover:!border-accent hover:!bg-accent/10 hover:!text-accent'

  return (
    <div className="boot-shell">
      <div className="boot-frame">
        <aside className="boot-sidebar">
          <div>
            <p className="boot-kicker">AI-RPG</p>
            <h1 className="boot-title">Frontpage</h1>
            <p className="boot-copy">Start fresh, pick up an old run, or shape a new scenario.</p>

            <nav className="boot-nav" aria-label="Frontpage sections">
              {navItems.map((item) => {
                const isActive = activePanel === item.id
                return (
                  <button
                    key={item.id}
                    type="button"
                    className="boot-nav-button"
                    data-active={isActive}
                    aria-pressed={isActive}
                    onClick={() => setActivePanel(item.id)}
                  >
                    <span>{item.label}</span>
                    <span className="boot-nav-meta">{item.meta}</span>
                  </button>
                )
              })}
            </nav>
          </div>

          <div className="boot-sidebar-summary">
            <div className="boot-sidebar-stat">
              <span>Scenarios</span>
              <strong>{scenarioCount}</strong>
            </div>
            <div className="boot-sidebar-stat">
              <span>Saves</span>
              <strong>{saveCount}</strong>
            </div>
          </div>
        </aside>

        <main className="boot-panel">
          <header className="boot-panel-header">
            <p className="boot-kicker">Selection</p>
            <h2 className="boot-section-title">{panelDetails[activePanel].label}</h2>
            <p className="boot-copy">{panelDetails[activePanel].description}</p>
          </header>

          <div className="boot-panel-body">
            {queryError ? (
              <Alert variant="danger" className={alertClass}>
                {queryError}
              </Alert>
            ) : null}
            {bootstrapQuery.data?.configuration_warnings.map((warning) => (
              <Alert key={warning} className={alertClass}>
                {warning}
              </Alert>
            ))}

            {activePanel === 'new' ? (
              <div className="grid gap-5 xl:grid-cols-[minmax(0,1.1fr)_minmax(320px,0.9fr)]">
                <section className="boot-block">
                  <div className="boot-block-header">
                    <span>Scenario Library</span>
                    <span>{scenarioCount} available</span>
                  </div>
                  <div className="space-y-3">
                    {bootstrapQuery.isLoading ? (
                      <div className="boot-empty animate-pulseLine">Loading scenarios...</div>
                    ) : bootstrapQuery.data?.scenarios.length ? (
                      bootstrapQuery.data.scenarios.map((scenario) => {
                        const isActive = effectiveSelectedScenarioId === scenario.id
                        return (
                          <button
                            key={scenario.id}
                            type="button"
                            className="boot-list-item"
                            data-active={isActive}
                            onClick={() => setSelectedScenarioId(scenario.id)}
                          >
                            <div className="flex items-start justify-between gap-4">
                              <div>
                                <div className="boot-item-title">{scenario.name}</div>
                                <p className="mt-2 text-sm leading-6 text-muted">
                                  {scenario.description || 'No description yet.'}
                                </p>
                              </div>
                              <span className="boot-chip">{scenario.is_builtin ? 'Builtin' : 'Custom'}</span>
                            </div>
                          </button>
                        )
                      })
                    ) : (
                      <div className="boot-empty">No scenarios found. Create one from the left menu.</div>
                    )}
                  </div>
                </section>

                <section className="boot-block">
                  <div className="boot-block-header">
                    <span>Session Setup</span>
                    <span>{selectedScenario ? 'ready' : 'waiting'}</span>
                  </div>
                  <form
                    className="space-y-5"
                    onSubmit={(event) => {
                      event.preventDefault()
                      if (!effectiveSelectedScenarioId) return
                      createSaveMutation.mutate({
                        scenario_id: effectiveSelectedScenarioId,
                        save_name: saveName,
                        player_name: playerName,
                      })
                    }}
                  >
                    <div className="boot-selection">
                      <p className="boot-kicker">Selected Scenario</p>
                      <h3 className="mt-3 text-2xl uppercase tracking-[0.18em] text-foreground">
                        {selectedScenario?.name ?? 'None'}
                      </h3>
                      <p className="mt-3 text-sm leading-7 text-muted">
                        {selectedScenario?.description || 'Pick a scenario from the library to begin a new run.'}
                      </p>
                    </div>

                    <div className="grid gap-4 md:grid-cols-2">
                      <label className="space-y-2">
                        <span className="boot-kicker">Save Name</span>
                        <Input
                          className={fieldClass}
                          value={saveName}
                          onChange={(event) => setSaveName(event.target.value)}
                        />
                      </label>
                      <label className="space-y-2">
                        <span className="boot-kicker">Player Name</span>
                        <Input
                          className={fieldClass}
                          value={playerName}
                          onChange={(event) => setPlayerName(event.target.value)}
                        />
                      </label>
                    </div>

                    {createSaveError ? (
                      <Alert variant="danger" className={alertClass}>
                        {createSaveError}
                      </Alert>
                    ) : null}

                    <Button
                      type="submit"
                      className={`${buttonClass} w-full`}
                      disabled={!effectiveSelectedScenarioId || createSaveMutation.isPending || isRouting}
                    >
                      {createSaveMutation.isPending || isRouting ? 'Opening Console...' : 'Create Save And Enter'}
                    </Button>
                  </form>
                </section>
              </div>
            ) : null}

            {activePanel === 'load' ? (
              <section className="boot-block">
                <div className="boot-block-header">
                  <span>Saved Runs</span>
                  <span>{saves.length} shown</span>
                </div>
                <Input
                  className={fieldClass}
                  value={search}
                  onChange={(event) => setSearch(event.target.value)}
                  placeholder="Filter by save, scenario, or player..."
                />
                <div className="mt-4 space-y-3">
                  {bootstrapQuery.isLoading ? (
                    <div className="boot-empty animate-pulseLine">Loading saves...</div>
                  ) : saves.length ? (
                    saves.map((save) => (
                      <div key={save.id} className="boot-list-item">
                        <div className="flex flex-col gap-4 xl:flex-row xl:items-center xl:justify-between">
                          <div>
                            <p className="boot-kicker">{save.scenario_name}</p>
                            <div className="mt-3 text-xl uppercase tracking-[0.16em] text-foreground">{save.name}</div>
                            <p className="mt-2 text-sm leading-6 text-muted">
                              {save.player_name ? `${save.player_name} // ` : ''}
                              Updated {new Date(save.updated_at).toLocaleString()}
                            </p>
                          </div>
                          <Button className={buttonClass} onClick={() => navigate(`/play/${save.id}`)}>
                            Load Game
                          </Button>
                        </div>
                      </div>
                    ))
                  ) : (
                    <div className="boot-empty">No saves found. Start a new game from the left menu.</div>
                  )}
                </div>
              </section>
            ) : null}

            {activePanel === 'scenario' ? (
              <div className="grid gap-5 xl:grid-cols-[minmax(0,0.95fr)_minmax(280px,0.8fr)]">
                <section className="boot-block">
                  <div className="boot-block-header">
                    <span>Scenario Details</span>
                    <span>minimal scaffold</span>
                  </div>
                  <form
                    className="space-y-5"
                    onSubmit={(event) => {
                      event.preventDefault()
                      createScenarioMutation.mutate({
                        name: scenarioName || 'Untitled Scenario',
                        description: scenarioDescription,
                      })
                    }}
                  >
                    <label className="space-y-2">
                      <span className="boot-kicker">Scenario Name</span>
                      <Input
                        className={fieldClass}
                        value={scenarioName}
                        onChange={(event) => setScenarioName(event.target.value)}
                        placeholder="Untitled Scenario"
                      />
                    </label>
                    <label className="space-y-2">
                      <span className="boot-kicker">Description</span>
                      <Textarea
                        className={fieldClass}
                        value={scenarioDescription}
                        onChange={(event) => setScenarioDescription(event.target.value)}
                        placeholder="Describe the tone, location, or premise..."
                      />
                    </label>
                    {createScenarioError ? (
                      <Alert variant="danger" className={alertClass}>
                        {createScenarioError}
                      </Alert>
                    ) : null}
                    <Button
                      type="submit"
                      className={`${buttonClass} w-full`}
                      disabled={createScenarioMutation.isPending}
                    >
                      {createScenarioMutation.isPending ? 'Creating Scenario...' : 'Create Scenario'}
                    </Button>
                  </form>
                </section>

                <section className="boot-block">
                  <div className="boot-block-header">
                    <span>Current Library</span>
                    <span>{scenarioCount} total</span>
                  </div>
                  <div className="space-y-3">
                    {bootstrapQuery.data?.scenarios.map((scenario) => (
                      <div key={scenario.id} className="boot-list-item">
                        <div className="flex items-start justify-between gap-4">
                          <div>
                            <div className="boot-item-title">{scenario.name}</div>
                            <p className="mt-2 text-sm leading-6 text-muted">
                              {scenario.description || 'No description yet.'}
                            </p>
                          </div>
                          <span className="boot-chip">{scenario.is_builtin ? 'Builtin' : 'Custom'}</span>
                        </div>
                      </div>
                    ))}
                  </div>
                </section>
              </div>
            ) : null}
          </div>
        </main>
      </div>
    </div>
  )
}
