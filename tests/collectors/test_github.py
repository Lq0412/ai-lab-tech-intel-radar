from radar.config import Source
from radar.collectors.github import GithubCollector


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


def test_github_collector_maps_to_techitem():
    payload = {"items": [{
        "full_name": "vllm-project/vllm",
        "html_url": "https://github.com/vllm-project/vllm",
        "description": "High-throughput LLM inference engine",
        "stargazers_count": 85000,
        "language": "Python",
        "pushed_at": "2026-06-01T10:00:00Z",
    }]}
    source = Source(name="GitHub Trending AI", url="topic:ai stars:>500",
                    tier="T1.5", type="repo_index", kind="github")
    collector = GithubCollector(client=FakeClient(payload), token="")
    items = collector.collect(source, now="2026-06-08T00:00:00")

    assert len(items) == 1
    it = items[0]
    assert it.source == "github"
    assert it.source_tier == "T1.5"
    assert it.raw_id == "github:vllm-project/vllm"
    assert it.metrics["stars"] == 85000
    assert it.metrics["language"] == "Python"
    assert it.title == "vllm-project/vllm"
