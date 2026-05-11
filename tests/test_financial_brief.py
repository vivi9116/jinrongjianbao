import pytest

from scripts import financial_brief


def test_build_brief_includes_mode_title_sources_and_timestamp():
    brief = financial_brief.build_brief("morning", now_utc="2026-05-12T00:00:00Z")

    assert "\u91d1\u878d\u7ecf\u6d4e\u65e9\u62a5" in brief
    assert "BJT" in brief
    assert "\u6838\u5fc3\u7ed3\u8bba" in brief
    assert "\u6765\u6e90" in brief
    assert "Federal Reserve" in brief
    assert "BLS CPI" in brief


def test_build_brief_rejects_unknown_mode():
    with pytest.raises(ValueError, match="Unsupported brief mode"):
        financial_brief.build_brief("weekly")


def test_send_telegram_message_posts_expected_payload():
    calls = []

    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {"ok": True, "result": {"message_id": 42}}

    class FakeSession:
        def post(self, url, data, timeout):
            calls.append({"url": url, "data": data, "timeout": timeout})
            return FakeResponse()

    result = financial_brief.send_telegram_message(
        token="123:abc",
        chat_id="-100123",
        text="hello",
        session=FakeSession(),
    )

    assert result["ok"] is True
    assert calls == [
        {
            "url": "https://api.telegram.org/bot123:abc/sendMessage",
            "data": {
                "chat_id": "-100123",
                "text": "hello",
                "disable_web_page_preview": "true",
            },
            "timeout": 30,
        }
    ]


def test_run_requires_telegram_environment(monkeypatch):
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    monkeypatch.delenv("TELEGRAM_CHAT_ID", raising=False)

    with pytest.raises(RuntimeError, match="TELEGRAM_BOT_TOKEN"):
        financial_brief.run(mode="morning")


def test_run_sends_generated_brief(monkeypatch):
    sent = []

    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "token")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "chat")

    def fake_send(token, chat_id, text, session=None):
        sent.append({"token": token, "chat_id": chat_id, "text": text})
        return {"ok": True}

    monkeypatch.setattr(financial_brief, "send_telegram_message", fake_send)

    result = financial_brief.run(mode="night", now_utc="2026-05-12T13:30:00Z")

    assert result == {"ok": True}
    assert sent[0]["token"] == "token"
    assert sent[0]["chat_id"] == "chat"
    assert "\u91d1\u878d\u7ecf\u6d4e\u591c\u62a5" in sent[0]["text"]


def test_alert_mode_skips_when_no_major_move(monkeypatch):
    sent = []

    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "token")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "chat")
    monkeypatch.setattr(
        financial_brief,
        "fetch_market_quotes",
        lambda session=None: [
            {
                "label": "S&P 500",
                "price": "6,000.00",
                "change": "+0.25%",
                "seen": "2026-05-12 13:30 UTC",
            }
        ],
    )
    monkeypatch.setattr(
        financial_brief,
        "send_telegram_message",
        lambda token, chat_id, text, session=None: sent.append(text),
    )

    result = financial_brief.run(mode="alert", now_utc="2026-05-12T13:30:00Z")

    assert result == {"ok": True, "skipped": True, "reason": "no major market move"}
    assert sent == []


def test_alert_mode_skips_when_quote_feed_is_rate_limited(monkeypatch):
    sent = []

    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "token")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "chat")

    def fake_fetch(session=None):
        raise RuntimeError("429 Too Many Requests")

    monkeypatch.setattr(financial_brief, "fetch_market_quotes", fake_fetch)
    monkeypatch.setattr(
        financial_brief,
        "send_telegram_message",
        lambda token, chat_id, text, session=None: sent.append(text),
    )

    result = financial_brief.run(mode="alert", now_utc="2026-05-12T13:30:00Z")

    assert result == {
        "ok": True,
        "skipped": True,
        "reason": "quote feed unavailable: RuntimeError",
    }
    assert sent == []


def test_main_prints_skip_reason_for_alert_quote_failure(monkeypatch, capsys):
    monkeypatch.setattr("sys.argv", ["financial_brief.py", "--mode", "alert"])
    monkeypatch.setattr(
        financial_brief,
        "run",
        lambda mode: {
            "ok": True,
            "skipped": True,
            "reason": "quote feed unavailable: HTTPError",
        },
    )

    financial_brief.main()

    output = capsys.readouterr().out
    assert "telegram_ok=True" in output
    assert "skipped=True reason=quote feed unavailable: HTTPError" in output
