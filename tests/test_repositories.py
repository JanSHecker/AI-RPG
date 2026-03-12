from __future__ import annotations

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect


def test_scenario_clone_creates_player_and_places(save_repository, world_repository):
    save = save_repository.create_from_scenario("scenario.frontier_fantasy", "Clone Test", player_name="Aria")
    player = world_repository.get_player(save.id)
    assert player.name == "Aria"
    assert player.location_entity_id == f"{save.id}:place.oakheart"

    watchtower = world_repository.get_entity(f"{save.id}:place.watchtower")
    assert watchtower is not None
    assert watchtower.name == "Ruined Watchtower"


def test_alembic_upgrade_creates_schema(tmp_path):
    config = Config("alembic.ini")
    db_path = tmp_path / "migration.db"
    config.set_main_option("sqlalchemy.url", f"sqlite:///{db_path}")
    command.upgrade(config, "head")

    engine = create_engine(f"sqlite:///{db_path}")
    tables = inspect(engine).get_table_names()
    assert "entities" in tables
    assert "quests" in tables
    assert "world_clock" in tables
