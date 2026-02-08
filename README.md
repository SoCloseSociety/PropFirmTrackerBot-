# 🏆 PropFirmTracker Bot v1.0

> **Real-time prop firm monitoring for traders** — Track rule changes, pricing, promos, scams & Trustpilot scores across 10+ prop firms. 24/7 automated. Revenue-generating.

---

## 📋 Table of Contents

- [Features](#-features)
- [Revenue Model](#-revenue-model)
- [Architecture](#-architecture)
- [Quick Start](#-quick-start)
- [VPS Deployment](#-vps-deployment)
- [Configuration](#-configuration)
- [Bot Commands](#-bot-commands)
- [Adding New Firms](#-adding-new-firms)
- [Affiliate Setup](#-affiliate-setup)
- [Launch Strategy](#-launch-strategy)
- [Cost Breakdown](#-cost-breakdown)

---

## ✨ Features

### Scraping Engine
- **Prop Firm Websites** — Monitors pricing, rules, homepage, and blog pages for 10+ firms
- **Reddit** — Scans r/FundedTrading, r/PropFirm, r/Forex for mentions, scam reports, sentiment
- **Trustpilot** — Tracks rating scores and review counts; alerts on significant drops
- **Promo Detection** — Automatically finds promo codes and discount offers on firm pages

### Alert System
- **Dual Channel** — Free (24h delay) + Premium (real-time) alerts
- **AI-Powered Summaries** — Uses Claude Haiku to explain what changed and how it impacts traders
- **Scam Detection** — Flags suspicious activity, negative review spikes, payout issues

### Monetization
- **Premium Subscriptions** — $14.99/month or $119.99/year
- **Referral Program** — Invite 3 friends = 7 days free premium (viral growth)
- **Affiliate Links** — Earn 10-20% commission from prop firm referrals (passive income!)
- **Payment Methods** — Crypto (USDT), Stripe (cards), Telegram Stars

### Admin Tools
- `/stats` — Live dashboard (users, revenue, data)
- `/activate [user_id] [days]` — Manual premium activation
- `/broadcast [message]` — Message all users
- `/scrape` — Trigger manual scrape cycle

---

## 💰 Revenue Model

```
┌─────────────────────────────────────────────────────┐
│                   REVENUE STREAMS                    │
├─────────────────────────────────────────────────────┤
│                                                      │
│  1. PREMIUM SUBS      $14.99/mo × subscribers       │
│     └── Target: 100 subs = $1,499/mo                │
│                                                      │
│  2. AFFILIATE LINKS    10-20% per challenge sold    │
│     └── FTMO $100K challenge = ~$80 commission      │
│     └── Even free users click these → passive $$$   │
│                                                      │
│  3. REFERRAL VIRALITY  Users promote for you (free) │
│     └── 3 invites = 7 days premium                  │
│     └── Exponential growth at zero cost              │
│                                                      │
│  Monthly target (Month 6):                           │
│  • 300 premium × $14.99 = $4,497                    │
│  • Affiliate: ~$1,000-2,000                          │
│  • Total: $5,500-6,500/mo                            │
│                                                      │
│  Costs: ~$10-15/mo  →  ROI: 400-600x               │
│                                                      │
└─────────────────────────────────────────────────────┘
```

---

## 🏗 Architecture

```
prop-firm-tracker/
├── run.py                  # Main entry point
├── config.py               # All configuration & firm list
├── database.py             # SQLite DB (users, subs, data)
├── bot.py                  # Telegram bot (commands, callbacks)
├── scheduler.py            # Cron-like scheduler for scrapers
├── scrapers/
│   ├── prop_firms.py       # Website scraper + promo detection
│   ├── reddit_scraper.py   # Reddit mentions + scam detection
│   └── trustpilot_scraper.py # Rating tracker
├── services/
│   ├── alert_service.py    # Alert formatting & delivery
│   └── ai_summarizer.py    # Claude Haiku for summaries
├── utils/
│   └── logger.py           # Colored console + file logging
├── data/                   # SQLite DB + logs (auto-created)
├── requirements.txt
├── .env.example
└── README.md
```

---

## 🚀 Quick Start

### Prerequisites
- Python 3.10+
- A Telegram bot token (from [@BotFather](https://t.me/BotFather))

### 1. Clone & Install

```bash
git clone <your-repo>
cd prop-firm-tracker

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure

```bash
cp .env.example .env
nano .env   # Fill in your values
```

**Minimum required:**
- `TELEGRAM_BOT_TOKEN` — Get from @BotFather
- `ADMIN_USER_IDS` — Your Telegram user ID

**Recommended:**
- `ANTHROPIC_API_KEY` — For AI summaries (~$2-5/mo)
- `FREE_CHANNEL_ID` / `PREMIUM_CHANNEL_ID` — Your alert channels

### 3. Create Telegram Channels

1. Create **@PropFirmTrackerFree** (public channel)
2. Create a private premium channel
3. Add your bot as **admin** to both channels
4. Get channel IDs (forward a message to [@userinfobot](https://t.me/userinfobot))
5. Put IDs in `.env`

### 4. Run

```bash
python run.py
```

You should see the ASCII banner and startup logs. The bot will:
1. Initialize the SQLite database
2. Register Telegram commands
3. Start the scraper scheduler (first scrape after 30s)
4. Begin polling for user messages

---

## 🖥 VPS Deployment

### Recommended: Hetzner Cloud ($4.51/mo) or Contabo ($5.99/mo)

```bash
# SSH into your VPS
ssh root@your-server-ip

# Install Python
apt update && apt install -y python3 python3-pip python3-venv git

# Clone project
git clone <your-repo> /opt/prop-firm-tracker
cd /opt/prop-firm-tracker

# Setup
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
nano .env  # Configure

# Test run
python run.py
```

### Run as systemd service (auto-restart, auto-start on boot)

```bash
sudo cat > /etc/systemd/system/propfirmbot.service << 'EOF'
[Unit]
Description=PropFirmTracker Bot
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/prop-firm-tracker
ExecStart=/opt/prop-firm-tracker/venv/bin/python run.py
Restart=always
RestartSec=10
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
EOF

# Enable and start
sudo systemctl enable propfirmbot
sudo systemctl start propfirmbot

# Check status
sudo systemctl status propfirmbot

# View logs
sudo journalctl -u propfirmbot -f
```

---

## ⚙️ Configuration

### Adding Affiliate Links

In `config.py`, update each firm's `affiliate_url`:

```python
"ftmo": {
    ...
    "affiliate_url": "https://ftmo.com?ref=YOUR_ACTUAL_REF_ID",
    ...
}
```

**How to get affiliate links:**
1. Go to each firm's website
2. Look for "Affiliate" or "Partners" in the footer
3. Sign up for their affiliate program
4. Replace `YOUR_REF_ID` with your actual referral ID

### Scrape Interval

In `config.py`:
```python
SCRAPE_INTERVAL_HOURS = 3   # Scrape every 3 hours (8x/day)
```

### Alert Delay for Free Channel

```python
FREE_ALERT_DELAY_HOURS = 24  # Free users get alerts 24h late
```

### Subscription Pricing

```python
PREMIUM_PRICE_MONTHLY = 14.99
PREMIUM_PRICE_YEARLY = 119.99
```

---

## 🤖 Bot Commands

### Free Commands
| Command | Description |
|---------|-------------|
| `/start` | Welcome + registration |
| `/help` | All commands |
| `/firms` | List all monitored firms with Trustpilot scores |
| `/promos` | Active promo codes |
| `/scores` | Trustpilot leaderboard |
| `/compare ftmo fundednext` | Side-by-side comparison |
| `/referral` | Your referral link + stats |
| `/premium` | Subscription options |
| `/status` | Account info |

### Premium Commands
| Command | Description |
|---------|-------------|
| `/history [firm]` | Full change history |
| `/scams` | Recent scam warnings |
| `/analysis [firm]` | AI-powered analysis |
| `/rules [firm]` | Detailed current rules |

### Admin Commands
| Command | Description |
|---------|-------------|
| `/stats` | User + revenue dashboard |
| `/activate 12345 30` | Give user 30 days premium |
| `/broadcast Hello!` | Message all users |
| `/scrape` | Trigger manual scrape |

---

## ➕ Adding New Firms

Edit `config.py` and add to `PROP_FIRMS`:

```python
"new_firm": {
    "name": "New Firm Name",
    "url": "https://newfirm.com",
    "pricing_url": "https://newfirm.com/pricing/",
    "rules_url": "https://newfirm.com/rules/",
    "blog_url": "https://newfirm.com/blog/",
    "trustpilot": "https://www.trustpilot.com/review/newfirm.com",
    "affiliate_url": "https://newfirm.com?ref=YOUR_REF",
    "affiliate_commission": "15%",
},
```

That's it — the bot will automatically start monitoring the new firm on the next scrape cycle.

---

## 🚀 Launch Strategy

### Week 1: Build & Seed
- [ ] Deploy bot on VPS
- [ ] Create free Telegram channel
- [ ] Let it scrape for 2-3 days to build initial data
- [ ] Post bot link in 10+ trading Telegram groups

### Week 2: Grow
- [ ] Buy 3-5 sponsored posts in trading channels ($50-100 each)
- [ ] Post on Reddit r/FundedTrading, r/PropFirm
- [ ] Create a Twitter thread showing the bot's alerts
- [ ] Target: 500 free users

### Week 3: Convert
- [ ] Enable premium features
- [ ] Send a killer free alert (big promo detected) then upsell
- [ ] Activate referral program
- [ ] Target: 20-50 premium users

### Week 4+: Scale
- [ ] YouTube Short / TikTok showing the bot
- [ ] Partner with trading influencers (revenue share)
- [ ] Add more firms based on user requests
- [ ] Target: 100+ premium users

---

## 💵 Cost Breakdown

| Item | Monthly Cost |
|------|-------------|
| VPS (Hetzner CX22) | $4.51 |
| Domain (optional) | ~$1 |
| Claude Haiku API | $2-5 |
| **Total** | **~$8-12/mo** |

**Break-even: 1 premium subscriber covers all costs.**

---

## 📝 License

MIT — Use it, fork it, make money with it.

---

## 🆘 Troubleshooting

**Bot not responding?**
- Check `TELEGRAM_BOT_TOKEN` in `.env`
- Ensure no other instance is running: `ps aux | grep run.py`

**Scraper errors?**
- Some firms may block scrapers — add delays in `config.py`
- Check `data/bot.log` for detailed errors

**No alerts being sent?**
- Ensure bot is admin in both channels
- Check channel IDs are correct (should start with `-100`)
- Run `/scrape` to trigger manual scrape

**Database reset?**
```bash
rm data/propfirm_tracker.db
python run.py  # Will recreate
```
