import argparse
import datetime as dt
import os
from typing import Any

import requests


MODE_TITLES = {
    "morning": "\u91d1\u878d\u7ecf\u6d4e\u65e9\u62a5",
    "afternoon": "\u91d1\u878d\u7ecf\u6d4e\u5348\u540e\u7b80\u62a5",
    "night": "\u91d1\u878d\u7ecf\u6d4e\u591c\u62a5",
    "alert": "\u91d1\u878d\u91cd\u5927\u4e8b\u4ef6\u5feb\u8baf\u76d1\u63a7",
}

MODE_FOCUS = {
    "morning": "\u9694\u591c\u7f8e\u80a1\u3001\u5168\u7403\u503a\u5238\u3001\u7f8e\u5143\u3001\u5546\u54c1\u3001\u4e9a\u6d32\u76d8\u524d\u98ce\u9669\u548c\u4eca\u65e5\u7ecf\u6d4e\u65e5\u5386\u3002",
    "afternoon": "\u4e9a\u6d32\u6536\u76d8\u3001\u6b27\u6d32\u65e9\u76d8\u3001\u4eba\u6c11\u5e01\u8d44\u4ea7\u3001\u6b27\u7f8e\u65f6\u6bb5\u6570\u636e\u548c\u4e8b\u4ef6\u98ce\u9669\u3002",
    "night": "\u7f8e\u80a1\u76d8\u524d/\u5f00\u76d8\u3001\u7f8e\u5143\u5229\u7387\u3001\u91cd\u70b9\u516c\u53f8\u65b0\u95fb\u548c\u6b21\u65e5\u4e9a\u6d32\u5e02\u573a\u5f71\u54cd\u3002",
    "alert": "\u53ea\u5728\u8de8\u8d44\u4ea7\u4ef7\u683c\u6216\u6743\u5a01\u65b0\u95fb\u6e90\u663e\u793a\u91cd\u5927\u98ce\u9669\u65f6\u53d1\u9001\u9ad8\u4f18\u5148\u7ea7\u5feb\u8baf\u3002",
}

YAHOO_SYMBOLS = {
    "S&P 500": "^GSPC",
    "Nasdaq": "^IXIC",
    "Dow": "^DJI",
    "VIX": "^VIX",
    "US 10Y Yield": "^TNX",
    "Dollar Index": "DX-Y.NYB",
    "WTI Crude": "CL=F",
    "Gold": "GC=F",
    "Bitcoin": "BTC-USD",
    "Shanghai Composite": "000001.SS",
    "Hang Seng": "^HSI",
    "Nikkei 225": "^N225",
}

SOURCE_LINKS = [
    ("Federal Reserve", "https://www.federalreserve.gov/newsevents/pressreleases.htm"),
    ("BLS CPI", "https://www.bls.gov/schedule/news_release/cpi.htm"),
    ("U.S. Treasury auctions", "https://home.treasury.gov/policy-issues/financing-the-government/quarterly-refunding/treasury-quarterly-refunding"),
    ("EIA petroleum status", "https://www.eia.gov/petroleum/supply/weekly/"),
    ("CME FedWatch", "https://www.cmegroup.com/markets/interest-rates/cme-fedwatch-tool.html"),
    ("Yahoo Finance quote feed", "https://query1.finance.yahoo.com/v7/finance/quote"),
    ("CNBC Markets", "https://www.cnbc.com/markets/"),
    ("MarketWatch Markets", "https://www.marketwatch.com/markets"),
    ("Reuters Markets", "https://www.reuters.com/markets/"),
    ("Bloomberg Markets", "https://www.bloomberg.com/markets"),
]


def beijing_timestamp(now_utc: str | None = None) -> str:
    if now_utc:
        parsed = dt.datetime.fromisoformat(now_utc.replace("Z", "+00:00"))
    else:
        parsed = dt.datetime.now(dt.timezone.utc)
    beijing = parsed.astimezone(dt.timezone(dt.timedelta(hours=8)))
    return beijing.strftime("%Y-%m-%d %H:%M BJT")


def fetch_market_quotes(session: Any | None = None) -> list[dict[str, str]]:
    client = session or requests
    response = client.get(
        "https://query1.finance.yahoo.com/v7/finance/quote",
        params={"symbols": ",".join(YAHOO_SYMBOLS.values())},
        timeout=20,
    )
    response.raise_for_status()
    results = response.json().get("quoteResponse", {}).get("result", [])
    by_symbol = {item.get("symbol"): item for item in results}

    rows = []
    for label, symbol in YAHOO_SYMBOLS.items():
        item = by_symbol.get(symbol, {})
        price = item.get("regularMarketPrice")
        change = item.get("regularMarketChangePercent")
        timestamp = item.get("regularMarketTime")
        if price is None:
            continue
        seen = (
            dt.datetime.fromtimestamp(timestamp, dt.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
            if timestamp
            else "timestamp unavailable"
        )
        rows.append(
            {
                "label": label,
                "price": f"{price:,.2f}",
                "change": "n/a" if change is None else f"{change:+.2f}%",
                "change_percent": "" if change is None else f"{change:.4f}",
                "seen": seen,
            }
        )
    return rows


def format_market_quotes(rows: list[dict[str, str]]) -> str:
    if not rows:
        return "- \u5b9e\u65f6\u62a5\u4ef7\u6682\u4e0d\u53ef\u7528\uff1b\u8bf7\u4f18\u5148\u6838\u5bf9\u4ea4\u6613\u6240\u3001\u5238\u5546\u7ec8\u7aef\u6216 Yahoo Finance quote feed\u3002"
    return "\n".join(
        f"- {row['label']}: {row['price']} ({row['change']}), quote time {row['seen']}"
        for row in rows
    )


def parse_change_percent(row: dict[str, str]) -> float | None:
    raw = row.get("change_percent") or row.get("change", "").replace("%", "")
    try:
        return float(raw)
    except ValueError:
        return None


def major_move_reasons(rows: list[dict[str, str]]) -> list[str]:
    thresholds = {
        "S&P 500": 1.5,
        "Nasdaq": 2.0,
        "Dow": 1.5,
        "VIX": 8.0,
        "US 10Y Yield": 3.0,
        "Dollar Index": 0.8,
        "WTI Crude": 2.5,
        "Gold": 1.5,
        "Bitcoin": 4.0,
        "Shanghai Composite": 2.0,
        "Hang Seng": 2.0,
        "Nikkei 225": 2.0,
    }
    reasons = []
    for row in rows:
        label = row.get("label", "")
        change = parse_change_percent(row)
        threshold = thresholds.get(label)
        if change is not None and threshold is not None and abs(change) >= threshold:
            reasons.append(f"{label} {row.get('change')} exceeds {threshold:.1f}% threshold")
    return reasons


def build_brief(
    mode: str,
    now_utc: str | None = None,
    session: Any | None = None,
    quote_rows: list[dict[str, str]] | None = None,
) -> str:
    if mode not in MODE_TITLES:
        raise ValueError(f"Unsupported brief mode: {mode}")

    if quote_rows is None:
        try:
            quote_rows = fetch_market_quotes(session=session)
        except Exception as exc:
            quote_rows = []
            quote_warning = f"\n\u62a5\u4ef7\u6293\u53d6\u72b6\u6001: Yahoo Finance quote feed \u6682\u4e0d\u53ef\u7528\uff0c\u9519\u8bef\u7c7b\u578b {type(exc).__name__}\u3002"
        else:
            quote_warning = ""
    else:
        quote_warning = ""

    sources = "\n".join(f"- {name}: {url}" for name, url in SOURCE_LINKS)
    return f"""\u3010{MODE_TITLES[mode]}\u3011{beijing_timestamp(now_utc)}

\u6838\u5fc3\u7ed3\u8bba
- \u672c\u7b80\u62a5\u6309\u534e\u5c14\u8857 desk update \u683c\u5f0f\u7ec4\u7ec7\uff1a\u5148\u770b\u8de8\u8d44\u4ea7\u4ef7\u683c\uff0c\u518d\u770b\u5b8f\u89c2/\u592e\u884c\u3001\u653f\u7b56\u3001\u5546\u54c1\u548c\u98ce\u9669\u4e8b\u4ef6\u3002
- \u5f53\u524d\u6863\u4f4d\u91cd\u70b9\uff1a{MODE_FOCUS[mode]}
- \u4e8b\u5b9e\u4e0e\u4ef7\u683c\u6765\u81ea\u516c\u5f00\u6570\u636e\u6e90\uff1b\u65b9\u5411\u5224\u65ad\u9700\u8981\u7ed3\u5408\u4f60\u7684\u4ed3\u4f4d\u3001\u671f\u9650\u548c\u98ce\u9669\u9884\u7b97\uff0c\u4e0d\u6784\u6210\u6295\u8d44\u5efa\u8bae\u3002

\u5e02\u573a\u4ef7\u683c
{format_market_quotes(quote_rows)}{quote_warning}

\u9a71\u52a8\u56e0\u7d20
- \u5229\u7387: \u6838\u5bf9 Federal Reserve \u6700\u65b0\u58f0\u660e\u3001CME FedWatch \u5229\u7387\u8def\u5f84\u548c\u7f8e\u503a\u62cd\u5356\u7ed3\u679c\uff0c\u91cd\u70b9\u770b\u5b9e\u9645\u5229\u7387\u5bf9\u6210\u957f\u80a1\u548c\u9ec4\u91d1\u7684\u5f71\u54cd\u3002
- \u901a\u80c0: \u6838\u5bf9 BLS CPI/PPI \u53d1\u5e03\u65f6\u95f4\u548c\u5206\u9879\uff0c\u80fd\u6e90\u3001\u4f4f\u623f\u3001\u6838\u5fc3\u670d\u52a1\u662f\u5f71\u54cd\u964d\u606f\u9884\u671f\u7684\u5173\u952e\u3002
- \u80fd\u6e90: \u6838\u5bf9 EIA \u5468\u5ea6\u5e93\u5b58\u3001WTI/Brent \u671f\u9650\u7ed3\u6784\u548c\u5730\u7f18\u653f\u6cbb\u6d88\u606f\uff0c\u6cb9\u4ef7\u4f1a\u901a\u8fc7\u901a\u80c0\u9884\u671f\u4f20\u5bfc\u81f3\u5229\u7387\u3002
- \u98ce\u9669\u504f\u597d: \u540c\u65f6\u89c2\u5bdf VIX\u3001\u7f8e\u5143\u6307\u6570\u3001\u6bd4\u7279\u5e01\u3001\u534a\u5bfc\u4f53/\u5927\u578b\u79d1\u6280\u80a1\u548c\u4e9a\u6d32\u4e3b\u8981\u6307\u6570\u3002

\u98ce\u9669\u6e05\u5355
- CPI\u3001\u5c31\u4e1a\u3001\u96f6\u552e\u9500\u552e\u3001PMI\u3001\u592e\u884c\u8bb2\u8bdd\u663e\u8457\u504f\u79bb\u5e02\u573a\u9884\u671f\u3002
- \u7f8e\u503a\u957f\u7aef\u62cd\u5356\u9700\u6c42\u5f31\u3001\u6536\u76ca\u7387\u5feb\u901f\u4e0a\u884c\u6216\u7f8e\u5143\u6025\u5347\u3002
- \u539f\u6cb9\u3001\u9ec4\u91d1\u3001\u6bd4\u7279\u5e01\u51fa\u73b0\u8de8\u5e02\u573a\u8054\u52a8\u5f0f\u6ce2\u52a8\u3002
- \u5730\u7f18\u653f\u6cbb\u3001\u5173\u7a0e\u3001\u5236\u88c1\u3001\u76d1\u7ba1\u6216\u5927\u578b\u91d1\u878d\u673a\u6784\u4fe1\u7528\u4e8b\u4ef6\u3002

\u4eca\u65e5\u5173\u6ce8
- \u5b98\u65b9\u65e5\u5386: BLS\u3001Federal Reserve\u3001U.S. Treasury\u3001EIA\u3002
- \u5e02\u573a\u5165\u53e3: Reuters\u3001Bloomberg\u3001CNBC\u3001MarketWatch\u3001Yahoo Finance\u3002

\u6765\u6e90
{sources}
"""


def send_telegram_message(
    token: str,
    chat_id: str,
    text: str,
    session: Any | None = None,
) -> dict[str, Any]:
    client = session or requests
    response = client.post(
        f"https://api.telegram.org/bot{token}/sendMessage",
        data={
            "chat_id": chat_id,
            "text": text,
            "disable_web_page_preview": "true",
        },
        timeout=30,
    )
    response.raise_for_status()
    return response.json()


def run(
    mode: str,
    now_utc: str | None = None,
    session: Any | None = None,
) -> dict[str, Any]:
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        raise RuntimeError("TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID must be set")

    if mode == "alert":
        quote_rows = fetch_market_quotes(session=session)
        reasons = major_move_reasons(quote_rows)
        if not reasons:
            return {"ok": True, "skipped": True, "reason": "no major market move"}
        brief = build_brief(mode=mode, now_utc=now_utc, session=session, quote_rows=quote_rows)
        brief = brief.replace(
            "\u6838\u5fc3\u7ed3\u8bba\n",
            "\u6838\u5fc3\u7ed3\u8bba\n"
            + "\n".join(f"- \u89e6\u53d1\u6761\u4ef6: {reason}" for reason in reasons)
            + "\n",
            1,
        )
    else:
        brief = build_brief(mode=mode, now_utc=now_utc, session=session)
    return send_telegram_message(token=token, chat_id=chat_id, text=brief, session=session)


def main() -> None:
    parser = argparse.ArgumentParser(description="Send a scheduled financial brief to Telegram.")
    parser.add_argument(
        "--mode",
        choices=sorted(MODE_TITLES),
        default="morning",
        help="Brief mode to generate.",
    )
    args = parser.parse_args()
    result = run(mode=args.mode)
    print(f"telegram_ok={result.get('ok')}")


if __name__ == "__main__":
    main()
