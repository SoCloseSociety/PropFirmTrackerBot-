"""
PropFirmTracker Bot - Configuration
====================================
All settings and environment variables.
"""

import os
from dotenv import load_dotenv

load_dotenv()

# ============================================================
# TELEGRAM BOT
# ============================================================
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
FREE_CHANNEL_ID = os.getenv("FREE_CHANNEL_ID", "-100XXXXXXXXXX")       # Public channel
PREMIUM_CHANNEL_ID = os.getenv("PREMIUM_CHANNEL_ID", "-100XXXXXXXXXX") # Private premium channel
ADMIN_USER_IDS = [int(x) for x in os.getenv("ADMIN_USER_IDS", "123456789").split(",")]

# ============================================================
# SUBSCRIPTION PRICING
# ============================================================
PREMIUM_PRICE_MONTHLY = 14.99   # USD
PREMIUM_PRICE_YEARLY = 119.99   # USD
TRIAL_DAYS = 3                  # Free trial for new users
REFERRAL_REWARD_DAYS = 7        # Days of free premium per 3 referrals
REFERRALS_NEEDED = 3            # Number of referrals needed for reward

# ============================================================
# SCRAPING SETTINGS
# ============================================================
SCRAPE_INTERVAL_HOURS = 3       # How often to scrape (in hours)
FREE_ALERT_DELAY_HOURS = 24     # Delay for free channel alerts
REQUEST_TIMEOUT = 15            # HTTP request timeout in seconds
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

# ============================================================
# AI SUMMARIZER (Claude Haiku - cheapest option)
# ============================================================
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "YOUR_ANTHROPIC_KEY_HERE")
AI_MODEL = "claude-haiku-4-5-20251001"
AI_MAX_TOKENS = 300  # Keep summaries short = keep costs low

# ============================================================
# DATABASE
# ============================================================
DATABASE_PATH = os.getenv("DATABASE_PATH", "data/propfirm_tracker.db")

# ============================================================
# PAYMENT (Stripe or Crypto)
# ============================================================
STRIPE_API_KEY = os.getenv("STRIPE_API_KEY", "")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "")
CRYPTO_WALLET_USDT_TRC20 = os.getenv("CRYPTO_WALLET", "YOUR_USDT_TRC20_ADDRESS")

# ============================================================
# PROP FIRMS TO MONITOR
# ============================================================
PROP_FIRMS = {
    "ftmo": {
        "name": "FTMO",
        "url": "https://ftmo.com",
        "pricing_url": "https://ftmo.com/en/pricing/",
        "rules_url": "https://ftmo.com/en/trading-rules/",
        "blog_url": "https://ftmo.com/en/blog/",
        "trustpilot": "https://www.trustpilot.com/review/ftmo.com",
        "affiliate_url": "https://ftmo.com?ref=YOUR_REF_ID",
        "affiliate_commission": "15%",
    },
    "fundednext": {
        "name": "Funded Next",
        "url": "https://fundednext.com",
        "pricing_url": "https://fundednext.com/pricing/",
        "rules_url": "https://fundednext.com/rules/",
        "blog_url": "https://fundednext.com/blog/",
        "trustpilot": "https://www.trustpilot.com/review/fundednext.com",
        "affiliate_url": "https://fundednext.com?ref=YOUR_REF_ID",
        "affiliate_commission": "15%",
    },
    "the5ers": {
        "name": "The 5%ers",
        "url": "https://the5ers.com",
        "pricing_url": "https://the5ers.com/pricing/",
        "rules_url": "https://the5ers.com/trading-rules/",
        "blog_url": "https://the5ers.com/blog/",
        "trustpilot": "https://www.trustpilot.com/review/the5ers.com",
        "affiliate_url": "https://the5ers.com?ref=YOUR_REF_ID",
        "affiliate_commission": "10%",
    },
    "myfundedfx": {
        "name": "MyFundedFX",
        "url": "https://myfundedfx.com",
        "pricing_url": "https://myfundedfx.com/pricing/",
        "rules_url": "https://myfundedfx.com/rules/",
        "blog_url": "https://myfundedfx.com/blog/",
        "trustpilot": "https://www.trustpilot.com/review/myfundedfx.com",
        "affiliate_url": "https://myfundedfx.com?ref=YOUR_REF_ID",
        "affiliate_commission": "20%",
    },
    "topstep": {
        "name": "TopStep",
        "url": "https://www.topstep.com",
        "pricing_url": "https://www.topstep.com/pricing/",
        "rules_url": "https://www.topstep.com/rules/",
        "blog_url": "https://www.topstep.com/blog/",
        "trustpilot": "https://www.trustpilot.com/review/topstep.com",
        "affiliate_url": "https://www.topstep.com?ref=YOUR_REF_ID",
        "affiliate_commission": "15%",
    },
    "apex_trader": {
        "name": "Apex Trader Funding",
        "url": "https://apextraderfunding.com",
        "pricing_url": "https://apextraderfunding.com/pricing/",
        "rules_url": "https://apextraderfunding.com/rules/",
        "blog_url": "https://apextraderfunding.com/blog/",
        "trustpilot": "https://www.trustpilot.com/review/apextraderfunding.com",
        "affiliate_url": "https://apextraderfunding.com?ref=YOUR_REF_ID",
        "affiliate_commission": "15%",
    },
    "e8_funding": {
        "name": "E8 Funding",
        "url": "https://e8funding.com",
        "pricing_url": "https://e8funding.com/pricing/",
        "rules_url": "https://e8funding.com/rules/",
        "blog_url": "https://e8funding.com/blog/",
        "trustpilot": "https://www.trustpilot.com/review/e8funding.com",
        "affiliate_url": "https://e8funding.com?ref=YOUR_REF_ID",
        "affiliate_commission": "12%",
    },
    "fundingpips": {
        "name": "Funding Pips",
        "url": "https://fundingpips.com",
        "pricing_url": "https://fundingpips.com/pricing/",
        "rules_url": "https://fundingpips.com/rules/",
        "blog_url": "https://fundingpips.com/blog/",
        "trustpilot": "https://www.trustpilot.com/review/fundingpips.com",
        "affiliate_url": "https://fundingpips.com?ref=YOUR_REF_ID",
        "affiliate_commission": "15%",
    },
    "goatfunded": {
        "name": "Goat Funded Trader",
        "url": "https://goatfundedtrader.com",
        "pricing_url": "https://goatfundedtrader.com/pricing/",
        "rules_url": "https://goatfundedtrader.com/rules/",
        "blog_url": "https://goatfundedtrader.com/blog/",
        "trustpilot": "https://www.trustpilot.com/review/goatfundedtrader.com",
        "affiliate_url": "https://goatfundedtrader.com?ref=YOUR_REF_ID",
        "affiliate_commission": "15%",
    },
    "blueberry_funded": {
        "name": "Blueberry Funded",
        "url": "https://blueberryfunded.com",
        "pricing_url": "https://blueberryfunded.com/pricing/",
        "rules_url": "https://blueberryfunded.com/rules/",
        "blog_url": "https://blueberryfunded.com/blog/",
        "trustpilot": "https://www.trustpilot.com/review/blueberryfunded.com",
        "affiliate_url": "https://blueberryfunded.com?ref=YOUR_REF_ID",
        "affiliate_commission": "10%",
    },
}

# ============================================================
# REDDIT SOURCES (free JSON API)
# ============================================================
REDDIT_SUBREDDITS = [
    "FundedTrading",
    "proptrading",
    "Forex",
    "FuturesTrading",
]

# ============================================================
# LOGGING
# ============================================================
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FILE = "data/bot.log"
