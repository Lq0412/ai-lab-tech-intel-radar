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
        self.last_params = None

    def get(self, url, params=None, headers=None):
        self.last_params = params
        return FakeResponse(self._payload)


def test_huggingface_collector_maps_to_techitem():
    payload = [{
        "id": "meta-llama/Llama-3-8B",
        "pipeline_tag": "text-generation",
        "downloads": 1200000,
        "likes": 3400,
        "trendingScore": 120,
        "createdAt": "2026-05-30T00:00:00.000Z",
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
    assert it.metrics["trending"] == 120
    # published_at comes from createdAt (HF list API does not return lastModified)
    assert it.published_at == "2026-05-30"


def test_huggingface_published_at_falls_back_to_last_modified():
    payload = [{
        "id": "org/model",
        "pipeline_tag": "text-generation",
        "lastModified": "2026-04-01T00:00:00.000Z",
    }]
    source = Source(name="HF", url="pipeline_tag:text-generation",
                    tier="T1.5", type="model_index", kind="huggingface")
    items = HuggingFaceCollector(client=FakeClient(payload)).collect(
        source, now="2026-06-08T00:00:00")
    assert items[0].published_at == "2026-04-01"


def test_huggingface_default_sort_is_trending():
    fake = FakeClient([])
    source = Source(name="HF", url="pipeline_tag:text-generation",
                    tier="T1.5", type="model_index", kind="huggingface")
    HuggingFaceCollector(client=fake).collect(source, now="2026-06-09T00:00:00")
    assert fake.last_params["sort"] == "trendingScore"


def test_huggingface_collector_respects_source_sort():
    source = Source(
        name="HF Trending", url="pipeline_tag:text-generation",
        tier="T1.5", type="model_index", kind="huggingface", sort="downloads",
    )
    fake = FakeClient([])
    HuggingFaceCollector(client=fake).collect(source, now="2026-06-09T00:00:00")
    assert fake.last_params["sort"] == "downloads"
