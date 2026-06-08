from radar.config import Source
from radar.collectors.huggingface import HuggingFaceCollector


class FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


class FakeClient:
    def __init__(self, payload):
        self._payload = payload

    def get(self, url, params=None, headers=None):
        return FakeResponse(self._payload)


def test_huggingface_collector_maps_to_techitem():
    payload = [{
        "id": "meta-llama/Llama-3-8B",
        "pipeline_tag": "text-generation",
        "downloads": 1200000,
        "likes": 3400,
        "lastModified": "2026-05-30T00:00:00.000Z",
    }]
    source = Source(name="HF Models", url="pipeline_tag:text-generation",
                    tier="T1.5", type="model_index", kind="huggingface")
    items = HuggingFaceCollector(client=FakeClient(payload)).collect(
        source, now="2026-06-08T00:00:00")

    assert len(items) == 1
    it = items[0]
    assert it.source == "huggingface"
    assert it.raw_id == "huggingface:meta-llama/Llama-3-8B"
    assert it.url == "https://huggingface.co/meta-llama/Llama-3-8B"
    assert it.metrics["downloads"] == 1200000
    assert it.metrics["likes"] == 3400
    assert it.published_at == "2026-05-30"
