from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from ai_rpg.cli.main import app


def test_cli_new_game_flow(tmp_path: Path):
    runner = CliRunner()
    db_path = tmp_path / "cli.db"
    result = runner.invoke(
        app,
        input="1\n1\nCLI Save\nAria\nexit\n4\n",
        env={"AI_RPG_DB_PATH": str(db_path), "AI_RPG_API_KEY": "test-key"},
    )

    assert result.exit_code == 0
    assert "Oakheart Village" in result.stdout


def test_cli_requires_api_key(tmp_path: Path):
    runner = CliRunner()
    db_path = tmp_path / "cli.db"
    result = runner.invoke(app, env={"AI_RPG_DB_PATH": str(db_path), "AI_RPG_API_KEY": ""})

    assert result.exit_code == 1
    assert "AI_RPG_API_KEY is required" in result.stdout
