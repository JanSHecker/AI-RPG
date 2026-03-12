# AI-RPG

Terminal-first LLM RPG prototype with authoritative SQLite game state.

## Features

- Main menu with scenario and save management
- Authoritative world state stored in SQLite
- Built-in frontier fantasy scenario
- Natural-language input plus slash commands
- Hybrid action evaluation with d20 rolls, structured state patches, and optional LLM narration
- Shallow combat and world simulation systems with stable service boundaries

## Quick start

1. Install dependencies:

```bash
python3 -m pip install --user -e ".[dev]"
```

2. Run migrations:

```bash
python3 -m alembic upgrade head
```

3. Start the game:

```bash
python3 -m ai_rpg.cli.main
```

## Environment

Copy `.env.example` to `.env` or export the variables in your shell.

