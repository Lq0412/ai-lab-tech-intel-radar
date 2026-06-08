import json
from radar.llm.client import LLMClient


class FakeMessage:
    def __init__(self, content):
        self.content = content


class FakeChoice:
    def __init__(self, content):
        self.message = FakeMessage(content)


class FakeCompletions:
    def __init__(self, content):
        self._content = content
        self.last_kwargs = None

    def create(self, **kwargs):
        self.last_kwargs = kwargs
        return type("Resp", (), {"choices": [FakeChoice(self._content)]})()


class FakeChat:
    def __init__(self, content):
        self.completions = FakeCompletions(content)


class FakeSDK:
    def __init__(self, content):
        self.chat = FakeChat(content)


def test_complete_json_parses_model_output():
    sdk = FakeSDK(json.dumps({"category": "tool_framework", "score": 5}))
    client = LLMClient(sdk=sdk, model="test-model")
    result = client.complete_json("sys", "user")
    assert result["category"] == "tool_framework"
    assert sdk.chat.completions.last_kwargs["model"] == "test-model"


def test_complete_json_strips_code_fences():
    sdk = FakeSDK("```json\n{\"ok\": true}\n```")
    client = LLMClient(sdk=sdk, model="m")
    assert client.complete_json("s", "u") == {"ok": True}
