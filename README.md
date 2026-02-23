<p align="center">
  <img src="assets/banner.svg" alt="PropFirm Tracker Bot" width="900">
</p>

<p align="center">
  <strong>Real-time Telegram bot monitoring 10+ prop firms — rule changes, pricing, promos, scam alerts, Trustpilot scores.</strong>
</p>

<p align="center">
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-575ECF?style=flat-square" alt="License: MIT"></a>
  <a href="https://www.python.org/downloads/"><img src="https://img.shields.io/badge/Python-3.10%2B-575ECF?style=flat-square&logo=python&logoColor=white" alt="Python 3.10+"></a>
  <img src="https://img.shields.io/badge/Firms-10%2B%20Monitored-575ECF?style=flat-square" alt="10+ Firms">
  <a href="https://github.com/SoCloseSociety/PropFirmTrackerBot-/stargazers"><img src="https://img.shields.io/github/stars/SoCloseSociety/PropFirmTrackerBot-?style=flat-square&color=575ECF" alt="Stars"></a>
  <a href="https://github.com/SoCloseSociety/PropFirmTrackerBot-/issues"><img src="https://img.shields.io/github/issues/SoCloseSociety/PropFirmTrackerBot-?style=flat-square&color=575ECF" alt="Issues"></a>
</p>

<p align="center">
  <a href="#quick-start">Quick Start</a> &bull;
  <a href="#key-features">Features</a> &bull;
  <a href="#monitored-firms">Firms</a> &bull;
  <a href="#faq">FAQ</a> &bull;
  <a href="#contributing">Contributing</a>
</p>

---

## What is PropFirm Tracker Bot?

**PropFirm Tracker Bot** is a free, open-source Telegram bot that monitors proprietary trading firms in real-time. It scrapes firm websites for rule changes, pricing updates, and promotional codes, tracks Trustpilot ratings, scans Reddit for scam alerts, and delivers AI-powered summaries — all automatically.

Built for traders who need to stay ahead of prop firm changes without manually checking 10+ websites daily.

### Who is this for?

- **Prop Firm Traders** who want real-time alerts on rule changes
- **Trading Communities** looking for a monitoring tool for their Telegram group
- **Content Creators** covering prop firm news
- **Developers** interested in web scraping + Telegram bots + AI integration

### Key Features

- **10+ Firms Monitored** — FTMO, Funded Next, The 5%ers, MyFundedFX, TopStep, Apex, E8, Funding Pips, Goat Funded, Blueberry Funded
- **Rule Change Detection** — Alerts when firms update their rules or pricing
- **Promo Code Scraping** — Automatically discovers discount codes
- **Trustpilot Tracking** — Monitors ratings and alerts on score drops
- **Reddit Scam Scanner** — Scans trading subreddits for scam reports
- **AI Summaries** — Claude Haiku analyzes changes and their impact on traders
- **Premium/Free Tiers** — Free alerts (24h delay) + premium (real-time)
- **Referral System** — Users earn premium days by inviting others
- **Admin Dashboard** — User stats, revenue tracking, manual controls
- **VPS Deployment** — systemd service with auto-restart

---

## Quick Start

### Prerequisites

| Requirement | Details |
|-------------|---------|
| **Python** | 3.10+ ([Download](https://www.python.org/downloads/)) |
| **Telegram Bot Token** | Create via [@BotFather](https://t.me/BotFather) |
| **Anthropic API Key** | Optional — for AI summaries ([Get key](https://console.anthropic.com)) |

### Installation

```bash
# 1. Clone the repository
git clone https://github.com/SoCloseSociety/PropFirmTrackerBot-.git
cd PropFirmTrackerBot-

# 2. Create a virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure
cp .env.example .env
# Edit .env with your credentials

# 5. Run
python run.py
```

---

## How It Works

```
Every 3 hours (configurable)
         │
         ▼
┌─────────────────────────────┐
│       3 Scrapers (async)    │
│                             │
│  1. Firm websites → diffs   │
│  2. Reddit RSS → mentions   │
│  3. Trustpilot → scores     │
└─────────────────────────────┘
         │
         ▼
┌─────────────────────────────┐
│     AI Summarizer (Claude)  │
│     Analyzes impact for     │
│     traders                 │
└─────────────────────────────┘
         │
         ▼
┌─────────────────────────────┐
│    Alert Engine             │
│                             │
│  Premium → real-time alerts │
│  Free → 24h delayed alerts  │
└─────────────────────────────┘
```

---

## Monitored Firms

| Firm | Pages Tracked |
|------|---------------|
| FTMO | Homepage, Pricing, Rules, Blog |
| Funded Next | Homepage, Pricing, Rules, Blog |
| The 5%ers | Homepage, Pricing, Rules, Blog |
| MyFundedFX | Homepage, Pricing, Rules, Blog |
| TopStep | Homepage, Pricing, Rules, Blog |
| Apex Trader | Homepage, Pricing, Rules, Blog |
| E8 Funding | Homepage, Pricing, Rules, Blog |
| Funding Pips | Homepage, Pricing, Rules, Blog |
| Goat Funded | Homepage, Pricing, Rules, Blog |
| Blueberry Funded | Homepage, Pricing, Rules, Blog |

---

## Bot Commands

| Command | Description | Access |
|---------|-------------|--------|
| `/start` | Register and get started | All |
| `/firms` | List monitored firms with scores | All |
| `/promos` | Active promo codes | All |
| `/scores` | Trustpilot leaderboard | All |
| `/compare [firm1] [firm2]` | Side-by-side comparison | All |
| `/referral` | Your referral link & stats | All |
| `/premium` | Subscription options | All |
| `/history [firm]` | Change history | Premium |
| `/scams` | Scam warnings | Premium |
| `/analysis [firm]` | AI analysis | Premium |
| `/rules [firm]` | Detailed rules | Premium |
| `/stats` | User & revenue dashboard | Admin |
| `/broadcast [msg]` | Mass message | Admin |
| `/scrape` | Trigger manual scrape | Admin |

---

## Configuration

| Variable | Description | Required |
|----------|-------------|----------|
| `TELEGRAM_BOT_TOKEN` | Bot token from @BotFather | Yes |
| `FREE_CHANNEL_ID` | Free alerts channel ID | Yes |
| `PREMIUM_CHANNEL_ID` | Premium alerts channel ID | Yes |
| `ADMIN_USER_IDS` | Admin Telegram user IDs | Yes |
| `ANTHROPIC_API_KEY` | Claude API key for AI summaries | Optional |
| `STRIPE_API_KEY` | Stripe for payments | Optional |
| `CRYPTO_WALLET` | USDT TRC20 address | Optional |

---

## Troubleshooting

### Bot doesn't start

1. Check your `.env` — token must be valid
2. Verify Python 3.10+ with `python --version`
3. Run `pip install -r requirements.txt`

### Scraper returns no data

1. Some firms use Cloudflare — the scraper retries automatically
2. Check `data/bot.log` for error details
3. Run `/scrape` manually from Telegram to test

### AI summaries not working

1. Verify your `ANTHROPIC_API_KEY` is set
2. Check API credits at console.anthropic.com
3. Bot falls back to templates if AI is unavailable

---

## FAQ

**Q: Is this free?**
A: Yes. The bot itself is free and open source. Optional: Claude Haiku costs ~$2-5/month for AI summaries.

**Q: How often does it check firms?**
A: Every 3 hours by default (configurable in `config.py`).

**Q: Can I add more firms?**
A: Yes — add entries to `FIRMS` dict in `config.py` with their URLs.

**Q: What's the VPS cost?**
A: ~$4-6/month (Hetzner/Contabo). Total operating cost: $8-12/month.

---

## Alternatives Comparison

| Feature | PropFirm Tracker | Manual Checking | Paid Services |
|---------|-----------------|-----------------|---------------|
| Price | **Free** | Free | $30-100/mo |
| Real-time alerts | Yes | No | Some |
| AI summaries | Yes (Claude) | No | Rare |
| Scam detection | Yes (Reddit) | Manual | Some |
| Trustpilot tracking | Yes | Manual | Some |
| Open source | Yes | N/A | No |

---

## Contributing

Contributions are welcome! Please read the [Contributing Guide](CONTRIBUTING.md) before submitting a pull request.

---

## License

This project is licensed under the [MIT License](LICENSE).

---

## Disclaimer

This tool is provided for **educational and informational purposes only**. It does not constitute financial advice. The authors are not responsible for trading decisions made based on the bot's alerts.

---

<p align="center">
  <strong>If this project helps you, please give it a star!</strong><br>
  <a href="https://github.com/SoCloseSociety/PropFirmTrackerBot-">
    <img src="https://img.shields.io/github/stars/SoCloseSociety/PropFirmTrackerBot-?style=for-the-badge&logo=github&color=575ECF" alt="Star this repo">
  </a>
</p>

<br>

<p align="center">
  <sub>Built with purpose by <a href="https://soclose.co"><strong>SoClose</strong></a> &mdash; Digital Innovation Through Automation & AI</sub><br>
  <sub>
    <a href="https://soclose.co">Website</a> &bull;
    <a href="https://linkedin.com/company/soclose-agency">LinkedIn</a> &bull;
    <a href="https://twitter.com/SoCloseAgency">Twitter</a> &bull;
    <a href="mailto:contact@soclose.co">Contact</a>
  </sub>
</p>
