import type {
  BootstrapResponse,
  GameSnapshot,
  SaveSummary,
  ScenarioSummary,
  TurnRequest,
  TurnResponse,
} from './types'

const API_BASE = import.meta.env.VITE_API_BASE ?? '/api'

export class ApiError extends Error {
  status: number

  constructor(message: string, status: number) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: {
      'Content-Type': 'application/json',
      ...(init?.headers ?? {}),
    },
    ...init,
  })

  if (!response.ok) {
    let detail = response.statusText
    try {
      const payload = (await response.json()) as { detail?: string }
      detail = payload.detail ?? detail
    } catch {
      // Ignore JSON parsing failures for non-JSON responses.
    }
    throw new ApiError(detail, response.status)
  }

  return (await response.json()) as T
}

export function getBootstrap() {
  return request<BootstrapResponse>('/bootstrap')
}

export function createScenario(payload: { name: string; description: string }) {
  return request<ScenarioSummary>('/scenarios', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export function createSave(payload: {
  scenario_id: string
  save_name: string
  player_name: string
}) {
  return request<SaveSummary>('/saves', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export function getSaveSnapshot(saveId: string) {
  return request<GameSnapshot>(`/saves/${saveId}`)
}

export function processTurn(saveId: string, payload: TurnRequest) {
  return request<TurnResponse>(`/saves/${saveId}/turn`, {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}
