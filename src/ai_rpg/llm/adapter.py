from __future__ import annotations

from ai_rpg.core.config import Settings
from ai_rpg.core.contracts import NarrationRequest, NarrationResponse, PatchOperationKind
from ai_rpg.llm.openai_compatible import OpenAICompatibleClient


class FallbackNarrator:
    def generate_structured(self, request: NarrationRequest) -> NarrationResponse:
        location = request.scene_context.location.name if request.scene_context.location else "the wilds"
        if request.intent.action_type.value == "talk" and request.intent.target_name:
            narration = f"In {location}, the conversation with {request.intent.target_name} shifts the mood of the scene."
        elif request.intent.action_type.value == "move" and request.intent.destination_name:
            narration = f"You make your way toward {request.intent.destination_name}."
        elif request.intent.action_type.value == "attack" and request.intent.target_name:
            narration = f"Steel flashes as you move against {request.intent.target_name}."
        else:
            narration = request.resolution_hint
        return NarrationResponse(narration=narration)


class RoutedLLMAdapter:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.fallback = FallbackNarrator()
        self.client = OpenAICompatibleClient(settings)

    def generate_structured(self, request: NarrationRequest) -> NarrationResponse:
        if not self.settings.api_key:
            return self.fallback.generate_structured(request)
        try:
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
            allowed = {kind for kind in request.allowed_operations}
            if any(operation.kind not in allowed for operation in response.operations):
                filtered = [operation for operation in response.operations if operation.kind in allowed]
                response = response.model_copy(update={"operations": filtered})
            return response
        except Exception:
            return self.fallback.generate_structured(request)


def validate_allowed_operations(kinds: list[PatchOperationKind], response: NarrationResponse) -> NarrationResponse:
    allowed = set(kinds)
    filtered = [operation for operation in response.operations if operation.kind in allowed]
    return response.model_copy(update={"operations": filtered})

