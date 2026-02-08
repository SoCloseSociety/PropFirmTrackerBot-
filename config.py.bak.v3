"""
PropFirmTracker Bot - Configuration
"""
import os
from dotenv import load_dotenv
load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
FREE_CHANNEL_ID = os.getenv("FREE_CHANNEL_ID", "")
PREMIUM_CHANNEL_ID = os.getenv("PREMIUM_CHANNEL_ID", "")
ADMIN_USER_IDS = [int(x) for x in os.getenv("ADMIN_USER_IDS", "123456789").split(",")]

PREMIUM_PRICE_MONTHLY = 14.99
PREMIUM_PRICE_YEARLY = 119.99
TRIAL_DAYS = 3
REFERRAL_REWARD_DAYS = 7
REFERRALS_NEEDED = 3

SCRAPE_INTERVAL_HOURS = 3
FREE_ALERT_DELAY_HOURS = 24
REQUEST_TIMEOUT = 15
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "YOUR_ANTHROPIC_KEY_HERE")
AI_MODEL = "claude-haiku-4-5-20251001"
AI_MAX_TOKENS = 300

DATABASE_PATH = os.getenv("DATABASE_PATH", "data/propfirm_tracker.db")

STRIPE_API_KEY = os.getenv("STRIPE_API_KEY", "")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "")
CRYPTO_WALLET_USDT_TRC20 = os.getenv("CRYPTO_WALLET", "YOUR_USDT_TRC20_ADDRESS")

PROP_FIRMS = {
    "ftmo": {
        "name": "FTMO",
        "url": "https://ftmo.com/en/",
        "pricing_url": "https://ftmo.com/en/how-it-works/",
        "rules_url": "https://ftmo.com/en/trading-objectives/",
        "blog_url": "https://ftmo.com/en/blog/",
        "trustpilot": "https://www.trustpilot.com/review/ftmo.com",
        "affiliate_url": "https://ftmo.com?ref=YOUR_REF_ID",
        "affiliate_commission": "15%",
    },
    "fundednext": {
        "name": "Funded Next",
        "url": "https://fundednext.com",
        "pricing_url": "https://fundednext.com/plan",
        "rules_url": "https://fundednext.com/evaluation-model",
        "blog_url": "https://fundednext.com/blog/",
        "trustpilot": "https://www.trustpilot.com/review/fundednext.com",
        "affiliate_url": "https://fundednext.com?ref=YOUR_REF_ID",
        "affiliate_commission": "15%",
    },
    "the5ers": {
        "name": "The 5%ers",
        "url": "https://the5ers.com/",
        "pricing_url": "https://the5ers.com/high-stakes/",
        "rules_url": "https://the5ers.com/bootcamp/",
        "blog_url": "https://the5ers.com/blog/",
        "trustpilot": "https://www.trustpilot.com/review/the5ers.com",
        "affiliate_url": "https://the5ers.com?ref=YOUR_REF_ID",
        "affiliate_commission": "10%",
    },
    "myfundedfx": {
        "name": "MyFundedFX",
        "url": "https://myfundedfx.com",
        "pricing_url": "https://myfundedfx.com/",
        "rules_url": "https://myfundedfx.com/faq/",
        "blog_url": "https://myfundedfx.com/blog/",
        "trustpilot": "https://www.trustpilot.com/review/myfundedfx.com",
        "affiliate_url": "https://myfundedfx.com?ref=YOUR_REF_ID",
        "affiliate_commission": "20%",
    },
    "topstep": {
        "name": "TopStep",
        "url": "https://www.topstep.com",
        "pricing_url": "https://www.topstep.com/",
        "rules_url": "https://www.topstep.com/trading-combine/",
        "blog_url": "https://www.topstep.com/blog/",
        "trustpilot": "https://www.trustpilot.com/review/topstep.com",
        "affiliate_url": "https://www.topstep.com?ref=YOUR_REF_ID",
        "affiliate_commission": "15%",
    },
    "apex_trader": {
        "name": "Apex Trader Funding",
        "url": "",
        "pricing_url": "",
        "rules_url": "",
        "blog_url": "",
        "trustpilot": "https://www.trustpilot.com/review/apextraderfunding.com",
        "affiliate_url": "https://apextraderfunding.com?ref=YOUR_REF_ID",
        "affiliate_commission": "15%",
    },
    "e8_funding": {
        "name": "E8 Funding",
        "url": "",
        "pricing_url": "",
        "rules_url": "",
        "blog_url": "",
        "trustpilot": "https://www.trustpilot.com/review/e8funding.com",
        "affiliate_url": "https://e8markets.com?ref=YOUR_REF_ID",
        "affiliate_commission": "12%",
    },
    "fundingpips": {
        "name": "Funding Pips",
        "url": "https://fundingpips.com",
        "pricing_url": "https://fundingpips.com/",
        "rules_url": "",
        "blog_url": "https://fundingpips.com/blog/",
        "trustpilot": "https://www.trustpilot.com/review/fundingpips.com",
        "affiliate_url": "https://fundingpips.com?ref=YOUR_REF_ID",
        "affiliate_commission": "15%",
    },
    "goatfunded": {
        "name": "Goat Funded Trader",
        "url": "https://www.goatfundedtrader.com",
        "pricing_url": "https://www.goatfundedtrader.com/",
        "rules_url": "",
        "blog_url": "",
        "trustpilot": "https://www.trustpilot.com/review/goatfundedtrader.com",
        "affiliate_url": "https://www.goatfundedtrader.com?ref=YOUR_REF_ID",
        "affiliate_commission": "15%",
    },
    "blueberry_funded": {
        "name": "Blueberry Funded",
        "url": "https://blueberryfunded.com",
        "pricing_url": "https://blueberryfunded.com/",
        "rules_url": "",
        "blog_url": "",
        "trustpilot": "https://www.trustpilot.com/review/blueberryfunded.com",
        "affiliate_url": "https://blueberryfunded.com?ref=YOUR_REF_ID",
        "affiliate_commission": "10%",
    },
}

REDDIT_SUBREDDITS = ["FundedTrading", "proptrading", "Forex", "FuturesTrading"]
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FILE = "data/bot.log"
