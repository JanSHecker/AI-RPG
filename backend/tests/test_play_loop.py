from __future__ import annotations

from io import StringIO

from rich.console import Console

from ai_rpg.core.contracts import PatchOperation, PatchOperationKind, StatePatch
from ai_rpg.game.play_loop import PlayLoop


class ScriptedConsole(Console):
    __slots__ = ("_stream", "_inputs")

    def __init__(self, inputs: list[str]):
        stream = StringIO()
        object.__setattr__(self, "_stream", stream)
        object.__setattr__(self, "_inputs", iter(inputs))
        super().__init__(file=stream, force_terminal=False, color_system=None, width=120)

    def input(self, prompt: str = "") -> str:  # type: ignore[override]
        self.print(prompt, end="")
        return next(self._inputs)

    def export_text(self) -> str:
        return self._stream.getvalue()


def _build_loop(
    save_repository,
    world_repository,
    context_builder,
    parser,
    evaluator,
    combat_engine,
    simulation_engine,
    console,
) -> PlayLoop:
    return PlayLoop(
        save_repository=save_repository,
        world_repository=world_repository,
        context_builder=context_builder,
        intent_parser=parser,
        action_evaluator=evaluator,
        combat_engine=combat_engine,
        simulation_engine=simulation_engine,
        console=console,
    )


def test_play_loop_renders_proposal_and_confirms_action(
    save_id,
    save_repository,
    world_repository,
    context_builder,
    parser,
    evaluator,
    combat_engine,
    simulation_engine,
):
    console = ScriptedConsole(["talk mayor", "yes", "/exit"])
    loop = _build_loop(
        save_repository,
        world_repository,
        context_builder,
        parser,
        evaluator,
        combat_engine,
        simulation_engine,
        console,
    )

    loop.run(save_id)

    output = console.export_text()
    player = world_repository.get_player(save_id)
    updated_context = context_builder.build(save_id, player.id)
    assert "Proposed Action" in output
    assert "Avoid Failure" in output
    assert "AP Cost" in output
    assert updated_context.action_points == 90


def test_play_loop_new_normal_input_replaces_pending_proposal(
    save_id,
    save_repository,
    world_repository,
    context_builder,
    parser,
    evaluator,
    combat_engine,
    simulation_engine,
):
    console = ScriptedConsole(["talk mayor", "head to watchtower", "/exit"])
    loop = _build_loop(
        save_repository,
        world_repository,
        context_builder,
        parser,
        evaluator,
        combat_engine,
        simulation_engine,
        console,
    )

    loop.run(save_id)

    output = console.export_text()
    player = world_repository.get_player(save_id)
    updated_context = context_builder.build(save_id, player.id)
    assert "Talk" in output
    assert "Travel" in output
    assert updated_context.location.name == "Oakheart Village"
    assert updated_context.action_points == 100


def test_active_combat_turn_bypasses_catalog_proposal_flow(
    save_id,
    save_repository,
    world_repository,
    context_builder,
    parser,
    evaluator,
    combat_engine,
    simulation_engine,
):
    player = world_repository.get_player(save_id)
    world_repository.apply_patch(
        StatePatch(
            save_id=save_id,
            operations=[
                PatchOperation(
                    kind=PatchOperationKind.MOVE_ENTITY,
                    target_id=player.id,
                    data={"location_entity_id": f"{save_id}:place.watchtower"},
                )
            ],
        )
    )
    console = ScriptedConsole(["swing at goblin", "yes", "attack goblin", "/exit"])
    loop = _build_loop(
        save_repository,
        world_repository,
        context_builder,
        parser,
        evaluator,
        combat_engine,
        simulation_engine,
        console,
    )

    loop.run(save_id)

    goblin_stats = world_repository.get_entity_stats(f"{save_id}:creature.goblin_scout")
    output = console.export_text()
    assert goblin_stats is not None
    assert goblin_stats.hp == 5
    assert output.count("Proposed Action") == 2
