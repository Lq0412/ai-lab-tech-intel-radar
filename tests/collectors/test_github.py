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


def test_github_collector_default_per_page_is_50():
    collector = GithubCollector(client=FakeClient({"items": []}), token="")
    assert collector.per_page == 50


def test_github_collector_passes_per_page_param():
    fake = FakeClient({"items": []})
    source = Source(name="gh", url="topic:llm stars:>500",
                    tier="T1.5", type="repo_index", kind="github")
    GithubCollector(client=fake, token="", per_page=50).collect(
        source, now="2026-06-08T00:00:00")
    assert fake.last_params["per_page"] == 50


def test_github_collector_respects_sort_and_records_created():
    payload = {"items": [{
        "full_name": "acme/new-agent",
        "html_url": "https://github.com/acme/new-agent",
        "description": "Fresh agent toolkit",
        "stargazers_count": 1200,
        "language": "Python",
        "created_at": "2026-05-15T08:00:00Z",
        "pushed_at": "2026-06-08T12:00:00Z",
    }]}
    fake = FakeClient(payload)
    source = Source(
        name="GitHub Active Agents", url="topic:agent stars:>300",
        tier="T1.5", type="repo_index", kind="github", sort="updated",
    )
    items = GithubCollector(client=fake, token="").collect(
        source, now="2026-06-09T00:00:00")

    assert fake.last_params["sort"] == "updated"
    # published_at reflects last activity (pushed_at), not repo creation
    assert items[0].published_at == "2026-06-08"
    assert items[0].metrics["pushed_at"] == "2026-06-08"
    assert items[0].metrics["created_at"] == "2026-05-15"
