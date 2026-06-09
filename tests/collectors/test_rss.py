from types import SimpleNamespace

from radar.config import Source
from radar.collectors.rss import RssCollector


def fake_parse(url):
    entry = SimpleNamespace(
        title="GPT-5 released",
        link="https://openai.com/news/gpt-5",
        summary="A new frontier model.",
        published="Mon, 01 Jun 2026 10:00:00 GMT",
    )
    return SimpleNamespace(entries=[entry])


class FakeHttpResponse:
    def raise_for_status(self):
        return None

    text = "<rss/>"


class FakeHttpClient:
    def get(self, url):
        return FakeHttpResponse()


def test_rss_collector_maps_to_techitem():
    source = Source(name="OpenAI Blog", url="https://openai.com/news/rss.xml",
                    tier="T1", type="official_blog", kind="rss")
    items = RssCollector(parse_fn=fake_parse, client=FakeHttpClient()).collect(
        source, now="2026-06-08T00:00:00")

    assert len(items) == 1
    it = items[0]
    assert it.source == "rss"
    assert it.source_tier == "T1"
    assert it.title == "GPT-5 released"
    assert it.url == "https://openai.com/news/gpt-5"
    assert it.raw_id == "rss:https://openai.com/news/gpt-5"
    assert it.published_at == "2026-06-01"
