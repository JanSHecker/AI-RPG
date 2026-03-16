from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from ai_rpg.core.config import Settings
from ai_rpg.runtime import build_runtime
from ai_rpg.web.main import create_app


def _settings_for(database_url: str, *, api_key: str | None = None) -> Settings:
    return Settings(
        db_path=Path(database_url.removeprefix("sqlite:///")),
        provider="test",
        model="test-model",
        api_base="http://example.invalid",
        api_key=api_key,
        debug=False,
    )


def test_bootstrap_lists_scenarios_and_configuration_warning(database_url, session_factory, llm_adapter):
    runtime = build_runtime(settings=_settings_for(database_url, api_key=None), session_factory=session_factory, llm_adapter=llm_adapter)
    client = TestClient(create_app(runtime=runtime))

    response = client.get("/api/bootstrap")

    assert response.status_code == 200
    payload = response.json()
    assert any(scenario["id"] == "scenario.frontier_fantasy" for scenario in payload["scenarios"])
    assert payload["configuration_warnings"]


def test_web_api_create_snapshot_and_turn_flow(database_url, session_factory, llm_adapter):
    runtime = build_runtime(settings=_settings_for(database_url), session_factory=session_factory, llm_adapter=llm_adapter)
    client = TestClient(create_app(runtime=runtime))

    scenario_response = client.post(
        "/api/scenarios",
        json={"name": "Browser Frontier", "description": "A web-first scenario."},
    )
    assert scenario_response.status_code == 201
    scenario_id = scenario_response.json()["id"]

    save_response = client.post(
        "/api/saves",
        json={"scenario_id": "scenario.frontier_fantasy", "save_name": "Web Save", "player_name": "Aria"},
    )
    assert save_response.status_code == 201
    save_id = save_response.json()["id"]

    snapshot_response = client.get(f"/api/saves/{save_id}")
    assert snapshot_response.status_code == 200
    assert snapshot_response.json()["save_id"] == save_id

    proposal_response = client.post(
        f"/api/saves/{save_id}/turn",
        json={"kind": "input", "raw_input": "talk mayor"},
    )
    assert proposal_response.status_code == 200
    proposal_payload = proposal_response.json()
    assert proposal_payload["pending_proposal"]["action_name"] == "Talk"
    assert any(entry["title"] == "Proposed Action" for entry in proposal_payload["terminal_entries"])

    confirm_response = client.post(
        f"/api/saves/{save_id}/turn",
        json={"kind": "confirm", "proposal": proposal_payload["pending_proposal"]},
    )
    assert confirm_response.status_code == 200
    confirm_payload = confirm_response.json()
    assert confirm_payload["pending_proposal"] is None
    assert confirm_payload["snapshot"]["player_status"]["action_points"] == 90
