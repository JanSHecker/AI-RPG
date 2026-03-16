from __future__ import annotations

from ai_rpg.core.config import Settings
from ai_rpg.core.contracts import (
    ActionDraft,
    ActionMatchDecision,
    ActionProposal,
    NarrationRequest,
    NarrationResponse,
    PatchOperationKind,
    SuccessTier,
)
from ai_rpg.llm.openai_compatible import OpenAICompatibleClient


def validate_allowed_operations(kinds: list[PatchOperationKind], response: NarrationResponse) -> NarrationResponse:
    allowed = set(kinds)
    filtered = [operation for operation in response.operations if operation.kind in allowed]
    return response.model_copy(update={"operations": filtered})


class RoutedLLMAdapter:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.client = OpenAICompatibleClient(settings)

    def ensure_configured(self) -> None:
        if not self.settings.api_key:
            raise RuntimeError("AI_RPG_API_KEY is required for normal gameplay actions.")

    def generate_structured(self, request: NarrationRequest) -> NarrationResponse:
        self.ensure_configured()
        data = self.client.create_completion(
            system_prompt=request.system_prompt,
            user_payload={
                "intent": request.intent.model_dump(mode="json"),
                "scene_context": request.scene_context.model_dump(mode="json"),
                "resolution_hint": request.resolution_hint,
                "allowed_operations": [kind.value for kind in request.allowed_operations],
            },
        )
        response = NarrationResponse.model_validate(data)
        return validate_allowed_operations(request.allowed_operations, response)

    def match_or_create_action(self, *, raw_input: str, scene_context, actions: list[dict]) -> ActionMatchDecision:
        self.ensure_configured()
        tool_call = self.client.create_tool_call(
            system_prompt=(
                "You classify a player's intended out-of-combat RPG action. "
                "Use exactly one tool call. "
                "Pick select_action when an existing action is a semantic match. "
                "Pick create_action only when none of the existing actions fit."
            ),
            user_payload={
                "raw_input": raw_input,
                "scene_context": scene_context.model_dump(mode="json"),
                "actions": actions,
            },
            tools=[
                {
                    "type": "function",
                    "function": {
                        "name": "select_action",
                        "description": "Select the best matching existing action.",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "action_id": {"type": "string"},
                                "confidence": {"type": "number"},
                            },
                            "required": ["action_id", "confidence"],
                            "additionalProperties": False,
                        },
                    },
                },
                {
                    "type": "function",
                    "function": {
                        "name": "create_action",
                        "description": "Create a new reusable action when no existing action fits the input.",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "name": {"type": "string"},
                                "description": {"type": "string"},
                                "aliases": {"type": "array", "items": {"type": "string"}},
                                "relevant_attribute": {
                                    "type": "string",
                                    "enum": [
                                        "strength",
                                        "dexterity",
                                        "constitution",
                                        "intelligence",
                                        "wisdom",
                                        "charisma",
                                        "diplomacy",
                                        "survival",
                                        "stealth",
                                        "melee",
                                    ],
                                },
                                "difficulty": {"type": "integer", "minimum": 0},
                                "action_point_cost": {"type": "integer", "minimum": 0},
                            },
                            "required": [
                                "name",
                                "description",
                                "aliases",
                                "relevant_attribute",
                                "difficulty",
                                "action_point_cost",
                            ],
                            "additionalProperties": False,
                        },
                    },
                },
            ],
        )
        if tool_call["name"] == "select_action":
            return ActionMatchDecision.model_validate(
                {
                    "action_id": tool_call["arguments"]["action_id"],
                    "confidence": tool_call["arguments"]["confidence"],
                }
            )
        if tool_call["name"] == "create_action":
            return ActionMatchDecision.model_validate(
                {
                    "created_action": ActionDraft.model_validate(tool_call["arguments"]).model_dump(mode="json"),
                }
            )
        raise RuntimeError(f"Unsupported tool call: {tool_call['name']}")

    def generate_out_of_combat_effects(
        self,
        *,
        proposal: ActionProposal,
        scene_context,
        success_tier: SuccessTier,
    ) -> NarrationResponse:
        self.ensure_configured()
        allowed_operations = [
            PatchOperationKind.ADVANCE_TIME,
            PatchOperationKind.CREATE_EVENT,
            PatchOperationKind.UPDATE_QUEST,
            PatchOperationKind.UPDATE_RELATIONSHIP,
            PatchOperationKind.ADD_BELIEF,
            PatchOperationKind.ADD_ITEM,
            PatchOperationKind.MOVE_ENTITY,
            PatchOperationKind.HEAL_ENTITY,
        ]
        data = self.client.create_completion(
            system_prompt=(
                "Resolve a player's confirmed out-of-combat RPG action. "
                "Return terse JSON with narration plus only the allowed structured operations. "
                "Never start combat and never modify action points."
            ),
            user_payload={
                "proposal": proposal.model_dump(mode="json"),
                "scene_context": scene_context.model_dump(mode="json"),
                "success_tier": success_tier.value,
                "allowed_operations": [kind.value for kind in allowed_operations],
            },
        )
        response = NarrationResponse.model_validate(data)
        return validate_allowed_operations(allowed_operations, response)
