# GitHub Actions Financial Brief

This repository sends Chinese financial market briefs to Telegram from GitHub Actions, so the local computer does not need to stay powered on.

## Schedule

GitHub cron is UTC. The workflows map to Beijing time as follows:

| Brief | Beijing time | UTC cron |
| --- | --- | --- |
| Morning brief | 08:00 daily | `0 0 * * *` |
| Afternoon brief | 15:00 daily | `0 7 * * *` |
| Night brief | 21:30 daily | `30 13 * * *` |
| Major event monitor | Hourly | `0 * * * *` |

## GitHub Secrets

Add these repository secrets in GitHub:

1. Open the repository on GitHub.
2. Go to **Settings** -> **Secrets and variables** -> **Actions**.
3. Add two repository secrets:
   - `TELEGRAM_BOT_TOKEN`
   - `TELEGRAM_CHAT_ID`

Do not commit the token or chat id into the repository.

## Manual Test

After pushing the files to GitHub:

1. Open **Actions**.
2. Choose **Financial Brief**.
3. Click **Run workflow**.
4. Choose `morning`, `afternoon`, or `night`.
5. Confirm Telegram receives the message.

You can also run the hourly alert workflow manually from **Financial Major Event Alerts**.

## Local Test

If Python is installed locally:

```powershell
python -m pip install -r requirements-dev.txt
python -m pytest tests/test_financial_brief.py -q
```

To send a local Telegram test:

```powershell
$env:TELEGRAM_BOT_TOKEN="your-token"
$env:TELEGRAM_CHAT_ID="your-chat-id"
python scripts/financial_brief.py --mode morning
```

## Data Sources

The script includes source links and public quote data from:

- Federal Reserve
- BLS CPI release calendar
- U.S. Treasury
- EIA
- CME FedWatch
- Yahoo Finance quote feed
- CNBC Markets
- MarketWatch Markets
- Reuters Markets
- Bloomberg Markets

For institutional-grade precision, connect paid market data or a professional news API later. This first version keeps deployment simple and avoids storing any paid credentials.
