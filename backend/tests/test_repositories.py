from __future__ import annotations

from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect


def test_scenario_clone_creates_player_places_and_action_points(save_repository, world_repository):
    save = save_repository.create_from_scenario("scenario.frontier_fantasy", "Clone Test", player_name="Aria")
    player = world_repository.get_player(save.id)
    player_stats = world_repository.get_entity_stats(player.id)
    assert player.name == "Aria"
    assert player.location_entity_id == f"{save.id}:place.oakheart"
    assert player_stats is not None
    assert player_stats.action_points == 100
    assert player_stats.max_action_points == 100

    watchtower = world_repository.get_entity(f"{save.id}:place.watchtower")
    assert watchtower is not None
    assert watchtower.name == "Ruined Watchtower"


def test_builtin_scenario_seeds_world_actions(action_repository):
    actions = action_repository.list_actions("scenario.frontier_fantasy")

    assert {action.handler_key for action in actions} >= {"travel", "talk", "rest", "attack_hostile"}
    assert {action.name for action in actions} >= {"Travel", "Talk", "Rest", "Attack"}


def test_alembic_upgrade_creates_schema(tmp_path):
    config = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
    db_path = tmp_path / "migration.db"
    config.set_main_option("sqlalchemy.url", f"sqlite:///{db_path}")
    command.upgrade(config, "head")

    engine = create_engine(f"sqlite:///{db_path}")
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    entity_stat_columns = {column["name"] for column in inspector.get_columns("entity_stats")}
    assert "entities" in tables
    assert "quests" in tables
    assert "scenario_actions" in tables
    assert "world_clock" in tables
    assert {"action_points", "max_action_points"} <= entity_stat_columns
