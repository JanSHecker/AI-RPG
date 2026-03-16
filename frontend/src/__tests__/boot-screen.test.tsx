import { fireEvent, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { BootScreen } from '../routes/boot-screen'
import { jsonResponse, renderRoute } from './test-utils'

describe('BootScreen', () => {
  const fetchMock = vi.fn()

  beforeEach(() => {
    vi.stubGlobal('fetch', fetchMock)
  })

  afterEach(() => {
    fetchMock.mockReset()
    vi.unstubAllGlobals()
  })

  it('renders bootstrap data and can create a save from the selected scenario', async () => {
    fetchMock.mockImplementation((input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input)
      if (url.endsWith('/api/bootstrap')) {
        return Promise.resolve(
          jsonResponse({
            scenarios: [
              {
                id: 'scenario.frontier_fantasy',
                name: 'Frontier Fantasy',
                description: 'The default frontier scenario.',
                is_builtin: true,
              },
            ],
            saves: [
              {
                id: 'save-1',
                name: 'Existing Save',
                scenario_id: 'scenario.frontier_fantasy',
                scenario_name: 'Frontier Fantasy',
                player_name: 'Aria',
                updated_at: '2026-03-12T10:00:00',
              },
            ],
            configuration_warnings: [],
          }),
        )
      }

      if (url.endsWith('/api/saves') && init?.method === 'POST') {
        return Promise.resolve(
          jsonResponse({
            id: 'save-2',
            name: 'New Adventure',
            scenario_id: 'scenario.frontier_fantasy',
            scenario_name: 'Frontier Fantasy',
            player_name: 'Wanderer',
            updated_at: '2026-03-12T10:05:00',
          }, 201),
        )
      }

      throw new Error(`Unexpected fetch: ${url}`)
    })

    renderRoute('/', '/', <BootScreen />)

    expect(await screen.findByRole('button', { name: /new game/i })).toBeInTheDocument()
    expect((await screen.findAllByText('The default frontier scenario.')).length).toBeGreaterThanOrEqual(1)
    expect(screen.getAllByText('Frontier Fantasy').length).toBeGreaterThanOrEqual(1)

    fireEvent.click(screen.getByRole('button', { name: /load game/i }))
    expect(await screen.findByText('Existing Save')).toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: /new game/i }))

    fireEvent.click(screen.getByRole('button', { name: /create save and enter/i }))

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(
        expect.stringContaining('/api/saves'),
        expect.objectContaining({ method: 'POST' }),
      )
    })
  })
})
