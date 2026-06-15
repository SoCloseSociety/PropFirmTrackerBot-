# CLAUDE.md -- PropFirmTrackerBot

## 1. Project Identity

**Name:** PropFirmTrackerBot -- Real-time prop firm monitoring for traders
**Role:** Telegram bot that monitors 10+ prop firms for rule/pricing changes, promo
codes, scam/Trustpilot-score warnings, and Reddit sentiment; broadcasts alerts to a
free channel (24h delay) and a Premium channel ($14.99/mo). Referral + affiliate model.
**Author:** SoClose Society (https://soclose.co)
**License:** MIT

> NOTE: this repo's directory name has a TRAILING SPACE ("PropFirmTrackerBot ").
> Always quote the path in shell commands.

### Stack
- Language: Python 3.x
- Bot framework: python-telegram-bot 21.6 (long-polling)
- Scraping: requests + beautifulsoup4
- AI summaries: Anthropic Claude Haiku (`services/ai_summarizer.py`)
- Database: SQLite (`database.py`)
- Scheduling: custom `Scheduler` (`scheduler.py`)
- Config: python-dotenv (`config.py`)

### Critical Files
- `run.py` -- entry point (`app.run_polling`)
- `bot.py` -- handlers + `create_bot()`
- `scheduler.py` -- periodic scrape + alert loop
- `config.py` -- env, prop-firm catalog, pricing
- `database.py` -- SQLite layer
- `scrapers/`, `services/` -- data collection + AI/alerts

## 2. Standard Workflow
- Enter plan mode for non-trivial tasks
- Test scrapers with `test_scrapers_verify.py` before deploying
- Track tasks in `tasks/todo.md`, lessons in `tasks/lessons.md`

## 3. Dev Commands
```bash
pip install -r requirements.txt
cp .env.example .env   # fill TELEGRAM_BOT_TOKEN, channel IDs, ANTHROPIC_API_KEY, etc.
python run.py          # starts long-polling
```

## 4. Core Principles
- Simplicity First, No Laziness, Minimal Impact
- Never use em dashes (use -- instead)
- Never invent data; scrapers/AI must back any number reported

## Neo Connector (auto)

- Slug: `propfirmtracker`
- Verdict: NOT WIREABLE -- long-polling Telegram bot (python-telegram-bot v21), no inbound HTTP server. Entry is `app.run_polling(...)` in `run.py`; users interact via Telegram chat only.
- Manifest: `NEO_CONNECTOR.md` (proven from `run.py` + `bot.py` + `config.py`; regenerate via the Neo Connector audit).
- For Neo: there is no port/endpoint to call. Do not invent endpoints. Commands (`/firms`, `/promos`, `/scores`, `/compare`, `/premium`, etc.) are Telegram commands, not HTTP. `STRIPE_WEBHOOK_SECRET` is present in config but NO HTTP route consumes it (see NEO_CONNECTOR.md Gaps). If wiring is ever needed, a separate HTTP service or a telegram webhook server would have to be built (out of scope; would modify the project).
- When `run.py`, `bot.py`, or `config.py` change, re-run the audit and regenerate `NEO_CONNECTOR.md`. The pre-commit hook warns if they changed without touching `NEO_CONNECTOR.md`.
