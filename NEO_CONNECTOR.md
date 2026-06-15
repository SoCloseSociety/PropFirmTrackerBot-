# NEO_CONNECTOR -- propfirmtracker
- service: propfirmtracker
- base_url_prod: none (no HTTP server)
- auth: none (no inbound network surface; users interact only via Telegram)
- env_required: [TELEGRAM_BOT_TOKEN]  # run.py exits if it is the placeholder
- generated_at:

> Machine-readable connection manifest for NeoBot. Everything below is proven from
> code. Do NOT edit by hand -- regenerate via the Neo Connector audit.
>
> NOTE: this repo's directory name has a TRAILING SPACE ("PropFirmTrackerBot ").
> Always quote the path.
>
> VERDICT: NOT WIREABLE as an HTTP connector. This is a long-polling Telegram bot
> (python-telegram-bot v21). It exposes NO inbound HTTP/REST/WS/webhook endpoint --
> it pulls updates via `app.run_polling(...)`. There is no port for Neo to call.

## What this is (proven from source)
- Entry point: `run.py` -> `main()` -> `app.run_polling(allowed_updates=["message",
  "callback_query"], drop_pending_updates=True)` (line 114).
- Bot built in `bot.py` `create_bot()` -> `Application.builder().token(...).post_init(post_init).build()`
  (line 830); handlers registered via `CommandHandler`/`CallbackQueryHandler`.
- Background work: `scheduler.py` (`Scheduler`) runs scrapers on a timer
  (SCRAPE_INTERVAL_HOURS=3) and pushes alerts to Telegram channels.
- Scrapers (`scrapers/`) + AI summarizer (`services/ai_summarizer.py`, Anthropic
  Haiku) + alert service. SQLite persistence (`database.py`).
- No web framework anywhere (verified: no flask/fastapi/uvicorn/aiohttp.web/
  web.Application/run_app/set_webhook/@app.route in source).

## User-facing commands (NOT an API; Telegram only -- from bot.py BotCommand list)
`/start`, `/help`, `/firms` (monitored firms), `/promos` (active promo codes),
`/scores` (Trustpilot leaderboard), `/compare` (compare two firms),
`/referral` (earn free Premium), `/premium` (upgrade), `/status` (your account),
`/support`. Reachable only by a Telegram user, not by Neo over HTTP.

## Run (the only "interface")
```bash
pip install -r requirements.txt   # python-telegram-bot==21.6, requests, beautifulsoup4, python-dotenv
cp .env.example .env              # fill credentials
python run.py                     # starts long-polling
```

## Config / env (proven from `config.py`)
- `TELEGRAM_BOT_TOKEN` (required; run.py refuses the placeholder `YOUR_BOT_TOKEN_HERE`)
- `FREE_CHANNEL_ID`, `PREMIUM_CHANNEL_ID` (target broadcast channels)
- `ADMIN_USER_IDS` (comma-separated; default `123456789`)
- `ANTHROPIC_API_KEY` (AI summaries; model `claude-haiku-4-5-20251001`, max 300 tokens)
- `DATABASE_PATH` (default `data/propfirm_tracker.db`)
- `STRIPE_API_KEY`, `STRIPE_WEBHOOK_SECRET` (present as env vars only -- see Gaps)
- `CRYPTO_WALLET` (USDT TRC20 address)
- `LOG_LEVEL` (default INFO); also static: PREMIUM_PRICE_MONTHLY 14.99, TRIAL_DAYS 3,
  REFERRAL_REWARD_DAYS 7, REFERRALS_NEEDED 3, SCRAPE_INTERVAL_HOURS 3,
  FREE_ALERT_DELAY_HOURS 24, plus the `PROP_FIRMS` and `REDDIT_SUBREDDITS` catalogs.

## Endpoints
None. No HTTP server exists in this repo.

## Gaps
- `STRIPE_WEBHOOK_SECRET` exists in `config.py`, but NO HTTP route consumes it: there
  is no served `/webhook` (or any HTTP server) in the audited source. So even Stripe
  webhooks are NOT a callable surface here. Where/whether the secret is used is
  UNKNOWN -- not found in bot.py/run.py/scheduler.py/services/scrapers. (`.bak`/`.bak.v3`
  copies were not audited; they are not the live entry points.)
- No inbound HTTP/REST/GraphQL/WebSocket server anywhere; mode is pure long-polling.
- To make this Neo-callable you would need a separate HTTP service (e.g. over
  `database.py`/scrapers) or a python-telegram-bot webhook server. Neither exists
  today; building one would modify the project -- out of scope.
- `.env` not audited for secret values.
