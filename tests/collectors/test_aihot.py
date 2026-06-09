from radar.config import Source
from radar.collectors.aihot import AihotCollector


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

    def get(self, url):
        return FakeResponse(self._payload)


def test_aihot_collector_maps_daily_api():
    payload = {
        "date": "2026-06-09",
        "sections": [{
            "label": "模型发布/更新",
            "items": [{
                "title": "新模型发布",
                "url": "https://example.com/a",
                "summary": "简要说明",
            }],
        }],
        "flashes": [{
            "title": "快讯条目",
            "url": "https://example.com/b",
            "summary": "快讯摘要",
        }],
    }
    source = Source(name="AI HOT 日报", url="daily", tier="T1.5",
                    type="article", kind="aihot")
    items = AihotCollector(client=FakeClient(payload)).collect(
        source, now="2026-06-09T00:00:00")

    assert len(items) == 2
    assert items[0].title == "新模型发布"
    assert items[0].raw_id == "aihot:https://example.com/a"
    assert items[0].published_at == "2026-06-09"
    assert items[1].title == "快讯条目"
