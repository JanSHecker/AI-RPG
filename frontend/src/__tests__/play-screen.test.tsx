import { fireEvent, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { PlayScreen } from '../routes/play-screen'
import { jsonResponse, renderRoute } from './test-utils'

const snapshotPayload = {
  save_id: 'save-1',
  save_name: 'Web Save',
  scenario_id: 'scenario.frontier_fantasy',
  scenario_name: 'Frontier Fantasy',
  player_name: 'Aria',
  scene_context: {
    save_id: 'save-1',
    actor_id: 'save-1:player',
    current_time: '2026-03-12T10:00:00',
    location: {
      id: 'save-1:place.oakheart',
      name: 'Oakheart Village',
      entity_type: 'place',
      description: 'A quiet village surrounded by pines.',
      is_hostile: false,
      is_player: false,
      attitude: 0,
    },
    nearby_entities: [],
    adjacent_places: [],
    active_quests: [],
    recent_events: [],
    visible_facts: [],
    relevant_beliefs: [],
    inventory: [],
    action_points: 100,
    max_action_points: 100,
  },
  player_status: {
    entity_id: 'save-1:player',
    name: 'Aria',
    hp: 16,
    max_hp: 16,
    stamina: 12,
    max_stamina: 12,
    action_points: 100,
    max_action_points: 100,
  },
  recent_events: [],
  active_encounter: null,
  configuration_warnings: [],
  seed_entries: [
    {
      id: 'seed-1',
      kind: 'system',
      title: 'Oakheart Village',
      content: '2026-03-12T10:00:00',
    },
  ],
}

describe('PlayScreen', () => {
  const fetchMock = vi.fn()

  beforeEach(() => {
    vi.stubGlobal('fetch', fetchMock)
    window.sessionStorage.clear()
  })

  afterEach(() => {
    fetchMock.mockReset()
    vi.unstubAllGlobals()
  })

  it('keeps pending proposals out of the transcript and logs a confirmed action as one item', async () => {
    fetchMock.mockImplementation((input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input)
      if (url.endsWith('/api/saves/save-1') && !init?.method) {
        return Promise.resolve(jsonResponse(snapshotPayload))
      }

      if (url.endsWith('/api/saves/save-1/turn') && init?.method === 'POST') {
        const body = JSON.parse(String(init.body ?? '{}'))

        if (body.kind === 'confirm') {
          return Promise.resolve(
            jsonResponse({
              snapshot: snapshotPayload,
              terminal_entries: [
                {
                  id: 'turn-2',
                  kind: 'narration',
                  title: null,
                  content: 'Mayor Elra leans in and shares what she knows.',
                },
              ],
              pending_proposal: null,
              exit_to_menu: false,
            }),
          )
        }

        return Promise.resolve(
          jsonResponse({
            snapshot: snapshotPayload,
            terminal_entries: [
              {
                id: 'turn-1',
                kind: 'panel',
                title: 'Proposed Action',
                content: 'Action: Talk',
              },
            ],
            pending_proposal: {
              action_id: 'action.talk',
              action_name: 'Talk',
              raw_input: 'talk mayor',
              description: 'Speak to someone nearby.',
              relevant_attribute: 'charisma',
              difficulty: 10,
              action_point_cost: 10,
              avoid_failure_percent: 90,
              clean_success_percent: 65,
              resolution_mode: 'deterministic',
              handler_key: 'talk',
              target_id: 'npc.mayor',
              target_name: 'Mayor Elra',
              destination_id: null,
              destination_name: null,
              can_confirm_now: true,
              blocker_message: null,
              created_this_turn: false,
            },
            exit_to_menu: false,
          }),
        )
      }

      throw new Error(`Unexpected fetch: ${url}`)
    })

    renderRoute('/play/save-1', '/play/:saveId', <PlayScreen />)

    expect((await screen.findAllByText('Oakheart Village')).length).toBeGreaterThanOrEqual(1)
    expect((await screen.findByText('2026-03-12T10:00:00')).closest('article')).toHaveClass('play-terminal-entry')
    expect(screen.getByTestId('play-terminal-panel')).toContainElement(screen.getByRole('button', { name: /^back$/i }))
    expect(screen.queryByText('Live Session')).not.toBeInTheDocument()
    expect(screen.queryByText('Quick Actions')).not.toBeInTheDocument()
    expect(screen.getByTestId('play-status-rail')).toHaveClass('play-rail-stretch')
    expect(screen.getByTestId('play-world-panels')).toHaveClass('play-section-fill')

    fireEvent.change(screen.getByPlaceholderText(/type a freeform action/i), {
      target: { value: 'talk mayor' },
    })
    fireEvent.submit(screen.getByRole('button', { name: /transmit/i }).closest('form')!)

    expect(await screen.findByText(/pending proposal/i)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /confirm/i })).toBeInTheDocument()
    expect(screen.queryByText('talk mayor')).not.toBeInTheDocument()
    expect(screen.queryByText('Proposed Action')).not.toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: /^confirm$/i }))

    expect(await screen.findByText('Action')).toBeInTheDocument()
    expect(await screen.findByText('talk mayor')).toBeInTheDocument()
    expect(screen.getByText(/proposed action details/i)).toBeInTheDocument()
    expect(screen.queryByText(/^Input$/)).not.toBeInTheDocument()
    expect(await screen.findByText('Mayor Elra leans in and shares what she knows.')).toBeInTheDocument()

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledTimes(3)
    })
  })
})
