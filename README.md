# AI-RPG

Web-first LLM RPG with a React terminal-style frontend, FastAPI backend, and authoritative SQLite game state.

## Repository layout

- `frontend/` contains the Vite/React client.
- `backend/` contains the FastAPI app, gameplay engine, migrations, and backend tests.
- The repo root keeps shared docs plus the helper scripts that start each side together.

## Features

- React + TypeScript frontend with a high-contrast black/cyan terminal aesthetic
- FastAPI backend that reuses the existing Python gameplay engine and repositories
- Built-in frontier fantasy scenario plus simple scenario scaffolding
- Main menu for new game, load game, and scenario creation
- Freeform action proposals with confirm/cancel flow
- Slash commands, inventory, quests, map, and persisted combat state
- Legacy CLI kept in-repo as a temporary fallback

## Quick start

1. Install the Python dependencies:

```bash
cd backend
python3 -m pip install --user -e ".[dev]"
cd ..
```

2. Install the frontend dependencies:

```bash
cd frontend
npm install
cd ..
```

3. Copy `.env.example` to `.env` and set your provider values.

4. Start the FastAPI backend:

```bash
cd backend
python3 -m ai_rpg.web.main
```

5. In another terminal, start the React frontend:

```bash
cd frontend
npm run dev
```

6. Open the frontend at [http://localhost:5173](http://localhost:5173).

Freeform action matching uses your configured provider. If `AI_RPG_API_KEY` is missing, the UI will warn you and freeform action proposals will be unavailable until you configure it.

## Production-style frontend serving

To build the frontend so FastAPI serves the static files directly:

```bash
cd frontend
npm run build
cd ..
cd backend
python3 -m ai_rpg.web.main
```

Then open [http://localhost:8000](http://localhost:8000).

## Testing

Backend:

```bash
cd backend
python3 -m pytest -s -q
```

Frontend unit/integration:

```bash
cd frontend
npm run test
```

Frontend production build:

```bash
cd frontend
npm run build
```

Playwright end-to-end:

```bash
cd frontend
npx playwright install chromium
npx playwright test
```

## Legacy CLI

The terminal UI still exists as a fallback while parity is maintained:

```bash
cd backend
python3 -m ai_rpg.cli.main
```
