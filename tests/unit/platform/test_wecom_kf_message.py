from astrbot.core.platform.sources.wecom.wecom_kf_message import WeChatKFMessage


def _message_api() -> tuple[WeChatKFMessage, list[tuple[str, str, str, dict]]]:
    api = WeChatKFMessage.__new__(WeChatKFMessage)
    calls: list[tuple[str, str, str, dict]] = []

    def send(user_id, open_kfid, msgid="", msg=None):
        calls.append((user_id, open_kfid, msgid, msg or {}))
        return {}

    api.send = send
    return api, calls


def test_wecom_kf_location_uses_location_payload():
    api, calls = _message_api()

    api.send_location("user", "kf", "Office", "Road 1", 12.5, 34.5)

    assert calls[0][3] == {
        "msgtype": "location",
        "location": {
            "name": "Office",
            "address": "Road 1",
            "latitude": 12.5,
            "longitude": 34.5,
        },
    }


def test_wecom_kf_miniprogram_uses_miniprogram_payload():
    api, calls = _message_api()

    api.send_miniprogram("user", "kf", "appid", "Title", "thumb", "pages/index")

    assert calls[0][3] == {
        "msgtype": "miniprogram",
        "miniprogram": {
            "appid": "appid",
            "title": "Title",
            "thumb_media_id": "thumb",
            "pagepath": "pages/index",
        },
    }


def test_wecom_kf_article_link_uses_link_payload():
    api, calls = _message_api()
    article = {
        "title": "Title",
        "desc": "Desc",
        "url": "https://example.com",
        "thumb_media_id": "thumb",
    }

    api.send_articles_link("user", "kf", article)

    assert calls[0][3] == {"msgtype": "link", "link": article}
