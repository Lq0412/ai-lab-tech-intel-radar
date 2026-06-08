from radar.notify import send_feishu


class FakeResponse:
    def raise_for_status(self):
        return None

    def json(self):
        return {"code": 0}


class FakeClient:
    def __init__(self):
        self.payload = None

    def post(self, url, json=None):
        self.payload = json
        return FakeResponse()


def test_send_feishu_posts_text_payload():
    client = FakeClient()
    send_feishu("https://feishu/webhook", "# report", client=client)
    assert client.payload["msg_type"] == "text"
    assert client.payload["content"]["text"] == "# report"
