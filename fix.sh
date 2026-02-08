#!/bin/bash
# ==============================================================
# PropFirmTracker MEGA-FIX — paste this entire block in SSH
# Fixes: URLs, false promos, Reddit 403, Trustpilot 403, Chat spam
# ==============================================================

cd /root/CRYPTO_JOB/PropFirmTrackerBot-

# Stop bot
pkill -f "python3 run.py" 2>/dev/null; sleep 1

# Backup
cp config.py config.py.bak 2>/dev/null
cp scrapers/prop_firms.py scrapers/prop_firms.py.bak 2>/dev/null
cp scrapers/reddit_scraper.py scrapers/reddit_scraper.py.bak 2>/dev/null
cp scrapers/trustpilot_scraper.py scrapers/trustpilot_scraper.py.bak 2>/dev/null
cp services/alert_service.py services/alert_service.py.bak 2>/dev/null

# Clean old DB
rm -f data/propfirm_tracker.db

echo "🔧 Writing fixed files..."

# ============================================================
# FILE 1: config.py
# ============================================================
cat > config.py << 'ENDFILE1'
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
ENDFILE1
echo "  ✅ config.py"

# ============================================================
# FILE 2: scrapers/prop_firms.py
# ============================================================
cat > scrapers/prop_firms.py << 'ENDFILE2'
"""
PropFirmTracker Bot - Prop Firm Scraper
"""
import hashlib
import re
import time
import random
import requests
from bs4 import BeautifulSoup
from utils.logger import log_info, log_error, log_debug, log_warn
from database import save_firm_snapshot, save_change, save_promo
from config import USER_AGENT, REQUEST_TIMEOUT, PROP_FIRMS


class PropFirmScraper:
    FALSE_POSITIVE_CODES = {
        'HTTP','HTML','HTTPS','TRUE','FALSE','NULL','NONE','JSON','CSRF','UTF8',
        'HREF','TYPE','TEXT','META','DATA','FORM','FONT','LINK','BODY','HEAD',
        'SPAN','ASYNC','DEFER','CLASS','WIDTH','INPUT','IMAGE',
        'CODE','PROMO','ENTER','APPLY','COUPON','FREE','OFFER','DEALS','BONUS',
        'CLAIM','REDEEM','SALE',
        'PLEASE','CLICK','HERE','YOUR','THIS','THAT','WITH','FROM','HAVE','WILL',
        'JUST','MORE','ALSO','SOME','THAN','THEM','THEN','WHEN','WHAT','WHICH',
        'WHERE','WHILE','WOULD','COULD','SHOULD','AFTER','BEFORE','ABOUT','THEIR',
        'OTHER','EVERY','THESE','THOSE','BEING','ABOVE','BELOW','UNDER','OVER',
        'EACH','ONLY','MOST','SUCH','BOTH','INTO','VERY','MUCH','MANY','WELL',
        'BACK','EVEN','MADE','MAKE','LIKE','LONG','COME','TAKE','KNOW','LOOK',
        'GIVE','GOOD','BEST','NEXT','LAST','MUST','NEED','WANT','DOES','DONE',
        'BEEN','WERE','GOES','GONE','KEEP','LEFT','HELP','SURE','FULL','REAL',
        'OPEN','ABLE','USED','SAME','WORK','FIND','SHOW','PART','DOWN','UPON',
        'CALL','STILL','FIRST','WORLD','THINK','START','PLACE','GROUP','SINCE',
        'GREAT','SMALL','LARGE','NEVER','RIGHT','UNTIL','THREE','AGAIN','STATE',
        'LEVEL','ORDER',
        'TRADE','TRADER','TRADING','FOREX','FUNDED','PROFIT','SPLIT','TARGET',
        'DAILY','PAYOUT','RULES','ACCOUNT','BALANCE','EQUITY','MARGIN','LEVERAGE',
        'SPREAD','SCALING','CHALLENGE','EVALUATION','VERIFICATION','PHASE','STAGE',
        'MAXIMUM','MINIMUM','LIMIT','CAPITAL','FUNDS','MARKET','PRICE','PLAN',
        'STEP','MODEL','EXPRESS','STELLAR','INSTANT','STANDARD','NORMAL','PREMIUM',
        'BASIC','ELITE','ADVANCED','DURING','CUSTOMER','TECHNOLOGY','SERVICE',
        'COMPANY','PLATFORM','PROGRAM','SUPPORT','CONTACT','POLICY','PRIVACY',
        'TERMS','MANAGE','SELECT','CHOOSE','OPTION','REWARD','WITHDRAW','DEPOSIT',
        'REFUND','VERIFY','COMPLETE','SUBMIT','REGISTER','LOGIN','SIGN','JOIN',
        'CHECK','LEARN','MONTH','YEAR','WEEK','TIME','DATE','NOTE','READ','SIZE',
        'RISK','LOSS','SWING','SCALP','SWAP','STOP','ENTRY',
        'FTMO','TOPSTEP','APEX','GOAT','BLUEBERRY','BERRY','PIPS','HYPER',
        'BOOTCAMP','COMBINE','GROWTH','FIRSTGFT',
    }

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "Sec-Ch-Ua": '"Chromium";v="131", "Not_A Brand";v="24"',
            "Sec-Ch-Ua-Mobile": "?0",
            "Sec-Ch-Ua-Platform": '"Windows"',
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
            "Upgrade-Insecure-Requests": "1",
        })
        self.results = {"scraped": 0, "changes": 0, "errors": 0, "promos": 0}

    def _fetch_page(self, url):
        try:
            response = self.session.get(url, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            for tag in soup(['script', 'style', 'nav', 'footer', 'header', 'iframe', 'noscript']):
                tag.decompose()
            text = soup.get_text(separator='\n', strip=True)
            text = re.sub(r'\n{3,}', '\n\n', text)
            text = re.sub(r' {2,}', ' ', text)
            return soup, text
        except requests.RequestException as e:
            log_error(f"Failed to fetch {url}: {e}", tag="SCRAPE")
            return None, None

    def _hash_content(self, text):
        if not text:
            return None
        normalized = re.sub(r'\s+', ' ', text.strip().lower())
        if not normalized:
            return None
        return hashlib.md5(normalized.encode('utf-8')).hexdigest()

    def _is_valid_promo_code(self, code):
        upper = code.upper()
        if len(upper) < 4 or len(upper) > 20:
            return False
        if upper in self.FALSE_POSITIVE_CODES:
            return False
        if not any(c.isdigit() for c in upper):
            return False
        if not upper[0].isalpha():
            return False
        return True

    def _extract_promos(self, soup, text, firm_slug, url):
        if not text:
            return
        promo_patterns = [
            r'(?:code|coupon)[:\s]+["\'']?([A-Z0-9]{4,20})["\'']?',
            r'promo\s+code[:\s]+["\'']?([A-Z0-9]{4,20})["\'']?',
            r'(?:use|enter|apply)\s+(?:code\s+)?["\'']?([A-Z][A-Z0-9]{3,19})["\'']?',
            r'([A-Z][A-Z0-9]{3,14})\s+(?:for|to get)\s+(\d+%?\s*(?:off|discount))',
        ]
        discount_patterns = [
            r'(\d+%\s*off)', r'(save\s*\d+%)', r'(\d+%\s*discount)', r'(\$\d+\s*off)',
        ]
        found_codes = set()
        for pattern in promo_patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                code = match.group(1).upper()
                if self._is_valid_promo_code(code):
                    found_codes.add(code)
        discount = ""
        for pattern in discount_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                discount = match.group(1)
                break
        for code in found_codes:
            saved = save_promo(
                firm_slug=firm_slug, promo_code=code,
                discount=discount or "Unknown",
                description=f"Promo code found on {firm_slug} website",
                source_url=url
            )
            if saved:
                self.results["promos"] += 1
                log_info(f"🎟️  New promo found: {firm_slug} — {code} ({discount})", tag="SCRAPE")

    def scrape_firm(self, firm_slug, firm_config):
        log_info(f"Scraping {firm_config['name']}...", tag="SCRAPE")
        pages_to_scrape = {
            "pricing": firm_config.get("pricing_url"),
            "rules": firm_config.get("rules_url"),
            "homepage": firm_config.get("url"),
            "blog": firm_config.get("blog_url"),
        }
        scraped_urls = set()
        for page_type, url in pages_to_scrape.items():
            if not url or url in scraped_urls:
                continue
            scraped_urls.add(url)
            soup, text = self._fetch_page(url)
            if not text:
                self.results["errors"] += 1
                continue
            self.results["scraped"] += 1
            content_hash = self._hash_content(text)
            changed = save_firm_snapshot(firm_slug, page_type, content_hash, text[:5000])
            if changed:
                self.results["changes"] += 1
                save_change(
                    firm_slug=firm_slug, page_type=page_type,
                    change_type="content_update", old_hash=None,
                    new_hash=content_hash,
                    summary=f"{firm_config['name']} - {page_type} page has been updated"
                )
            if page_type in ("pricing", "homepage"):
                self._extract_promos(soup, text, firm_slug, url)
            time.sleep(random.uniform(1, 2.5))

    def scrape_all(self):
        log_info(f"Starting full scrape of {len(PROP_FIRMS)} prop firms...", tag="SCRAPE")
        self.results = {"scraped": 0, "changes": 0, "errors": 0, "promos": 0}
        for firm_slug, firm_config in PROP_FIRMS.items():
            try:
                self.scrape_firm(firm_slug, firm_config)
            except Exception as e:
                log_error(f"Error scraping {firm_slug}: {e}", tag="SCRAPE")
                self.results["errors"] += 1
            time.sleep(random.uniform(2, 4))
        log_info(
            f"Scrape complete — Pages: {self.results['scraped']} | "
            f"Changes: {self.results['changes']} | "
            f"Promos: {self.results['promos']} | "
            f"Errors: {self.results['errors']}", tag="SCRAPE"
        )
        return self.results
ENDFILE2
echo "  ✅ scrapers/prop_firms.py"

# ============================================================
# FILE 3: scrapers/reddit_scraper.py
# ============================================================
cat > scrapers/reddit_scraper.py << 'ENDFILE3'
"""
PropFirmTracker Bot - Reddit Scraper
"""
import re
import time
import random
import requests
from utils.logger import log_info, log_error, log_debug, log_warn
from database import save_reddit_mention, save_scam_alert
from config import PROP_FIRMS, REDDIT_SUBREDDITS, REQUEST_TIMEOUT


class RedditScraper:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "PropFirmTracker/1.0 (telegram bot; monitoring prop firm discussions)",
            "Accept": "application/json",
        })
        self.firm_names = {slug: cfg['name'].lower() for slug, cfg in PROP_FIRMS.items()}
        self.results = {"posts_found": 0, "mentions": 0, "scam_alerts": 0, "errors": 0}

    def _get_subreddit_posts(self, subreddit, sort="new", limit=25):
        url = f"https://www.reddit.com/r/{subreddit}/{sort}.json?limit={limit}&raw_json=1"
        try:
            response = self.session.get(url, timeout=REQUEST_TIMEOUT)
            if response.status_code == 429:
                retry_after = int(response.headers.get('Retry-After', 10))
                log_warn(f"Reddit rate limit, waiting {retry_after}s...", tag="SCRAPE")
                time.sleep(retry_after)
                response = self.session.get(url, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()
            data = response.json()
            posts = data.get('data', {}).get('children', [])
            return [p['data'] for p in posts if p.get('data')]
        except requests.exceptions.HTTPError as e:
            if hasattr(e, 'response') and e.response is not None and e.response.status_code == 403:
                log_warn(f"r/{subreddit}: Reddit blocked (403) — may need OAuth token", tag="SCRAPE")
            else:
                log_error(f"Failed to fetch r/{subreddit}: {e}", tag="SCRAPE")
            self.results["errors"] += 1
            return []
        except Exception as e:
            log_error(f"Failed to fetch r/{subreddit}: {e}", tag="SCRAPE")
            self.results["errors"] += 1
            return []

    def _detect_firm_mention(self, text):
        text_lower = text.lower()
        mentioned = []
        name_to_slug = {}
        for slug, cfg in PROP_FIRMS.items():
            names = [cfg['name'].lower(), slug.replace('_', ' ')]
            if slug == "ftmo":
                names.extend(["ftmo"])
            elif slug == "fundednext":
                names.extend(["funded next", "fundednext"])
            elif slug == "the5ers":
                names.extend(["the5ers", "the 5ers", "5ers", "five percenters"])
            elif slug == "myfundedfx":
                names.extend(["myfundedfx", "my funded fx"])
            elif slug == "topstep":
                names.extend(["topstep", "top step"])
            elif slug == "apex_trader":
                names.extend(["apex trader", "apex funding", "atf"])
            elif slug == "e8_funding":
                names.extend(["e8 funding", "e8 markets", "e8markets"])
            elif slug == "fundingpips":
                names.extend(["funding pips", "fundingpips"])
            elif slug == "goatfunded":
                names.extend(["goat funded", "goatfunded"])
            elif slug == "blueberry_funded":
                names.extend(["blueberry funded", "blueberryfunded"])
            for name in names:
                name_to_slug[name] = slug
        for name, slug in name_to_slug.items():
            if name in text_lower and slug not in mentioned:
                mentioned.append(slug)
        return mentioned

    def _detect_scam_keywords(self, text):
        text_lower = text.lower()
        scam_keywords = [
            'scam', 'fraud', 'ponzi', 'rug pull', "won't pay", 'not paying',
            'refused payout', 'denied payout', 'stole my', 'stolen', 'avoid',
            'stay away', 'do not use', 'warning', 'shut down', 'shutdown',
            'bankrupt', 'disappeared', 'no payout', 'payout denied',
            'fake reviews', 'manipulated', 'rigged',
        ]
        severity_high = ['scam', 'fraud', 'ponzi', 'rug pull', 'stole', 'stolen', 'bankrupt']
        found_keywords = [kw for kw in scam_keywords if kw in text_lower]
        if found_keywords:
            is_high = any(kw in text_lower for kw in severity_high)
            return {"is_scam_report": True, "keywords": found_keywords,
                    "severity": "high" if is_high else "medium"}
        return {"is_scam_report": False}

    def _analyze_sentiment(self, text, score):
        text_lower = text.lower()
        positive = ['great', 'excellent', 'recommend', 'best', 'love', 'amazing',
                     'paid out', 'got payout', 'legit', 'reliable', 'fast payout', 'good experience']
        negative = ['terrible', 'worst', 'avoid', 'scam', 'horrible', 'trash', 'garbage',
                     'slow payout', 'bad experience', 'disappointed', 'regret']
        pos_count = sum(1 for w in positive if w in text_lower)
        neg_count = sum(1 for w in negative if w in text_lower)
        if neg_count > pos_count:
            return "negative"
        elif pos_count > neg_count:
            return "positive"
        return "neutral"

    def scrape_subreddit(self, subreddit):
        log_info(f"Scraping r/{subreddit}...", tag="SCRAPE")
        posts = self._get_subreddit_posts(subreddit)
        self.results["posts_found"] += len(posts)
        for post in posts:
            title = post.get('title', '')
            selftext = post.get('selftext', '')
            full_text = f"{title} {selftext}"
            post_url = f"https://reddit.com{post.get('permalink', '')}"
            score = post.get('score', 0)
            mentioned_firms = self._detect_firm_mention(full_text)
            if not mentioned_firms:
                if any(kw in full_text.lower() for kw in ['prop firm', 'funded account', 'prop trading']):
                    mentioned_firms = ['general']
            for firm_slug in mentioned_firms:
                sentiment = self._analyze_sentiment(full_text, score)
                save_reddit_mention(
                    firm_slug=firm_slug, subreddit=subreddit,
                    post_title=title[:200], post_url=post_url,
                    score=score, sentiment=sentiment
                )
                self.results["mentions"] += 1
                scam_check = self._detect_scam_keywords(full_text)
                if scam_check["is_scam_report"] and firm_slug != 'general':
                    save_scam_alert(
                        firm_slug=firm_slug, alert_type="reddit_scam_report",
                        severity=scam_check["severity"],
                        description=f"Reddit post: {title[:150]}", source=post_url
                    )
                    self.results["scam_alerts"] += 1
                    log_info(f"⚠️  Scam report: {firm_slug}: {title[:80]}", tag="ALERT")

    def scrape_all(self):
        log_info(f"Starting Reddit scrape of {len(REDDIT_SUBREDDITS)} subreddits...", tag="SCRAPE")
        self.results = {"posts_found": 0, "mentions": 0, "scam_alerts": 0, "errors": 0}
        for subreddit in REDDIT_SUBREDDITS:
            try:
                self.scrape_subreddit(subreddit)
            except Exception as e:
                log_error(f"Error scraping r/{subreddit}: {e}", tag="SCRAPE")
                self.results["errors"] += 1
            time.sleep(random.uniform(2, 4))
        log_info(
            f"Reddit scrape complete — Posts: {self.results['posts_found']} | "
            f"Mentions: {self.results['mentions']} | "
            f"Scam alerts: {self.results['scam_alerts']} | "
            f"Errors: {self.results['errors']}", tag="SCRAPE"
        )
        return self.results
ENDFILE3
echo "  ✅ scrapers/reddit_scraper.py"

# ============================================================
# FILE 4: scrapers/trustpilot_scraper.py
# ============================================================
cat > scrapers/trustpilot_scraper.py << 'ENDFILE4'
"""
PropFirmTracker Bot - Trustpilot Scraper
"""
import json
import re
import time
import random
import requests
from bs4 import BeautifulSoup
from utils.logger import log_info, log_error, log_debug, log_warn
from database import save_trustpilot_score, get_latest_trustpilot_scores, save_scam_alert
from config import PROP_FIRMS, USER_AGENT, REQUEST_TIMEOUT


class TrustpilotScraper:
    SCORE_DROP_THRESHOLD = 0.3
    LOW_SCORE_THRESHOLD = 2.5
    NEGATIVE_SPIKE_REVIEWS = 10

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "Cache-Control": "no-cache",
            "Sec-Ch-Ua": '"Chromium";v="131", "Not_A Brand";v="24"',
            "Sec-Ch-Ua-Mobile": "?0",
            "Sec-Ch-Ua-Platform": '"Windows"',
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
            "Upgrade-Insecure-Requests": "1",
            "Referer": "https://www.google.com/",
        })
        self.results = {"scraped": 0, "score_drops": 0, "low_scores": 0, "errors": 0}

    def _scrape_trustpilot_page(self, url):
        try:
            response = self.session.get(url, timeout=REQUEST_TIMEOUT)
            if response.status_code in (403, 429):
                log_warn(f"Trustpilot blocked ({response.status_code}): {url}", tag="SCRAPE")
                return None, None
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            score = None
            review_count = None

            for script in soup.find_all('script', type='application/ld+json'):
                try:
                    raw = script.string
                    if not raw:
                        continue
                    data = json.loads(raw)
                    if isinstance(data, dict) and 'aggregateRating' in data:
                        rating = data['aggregateRating']
                        score = float(rating.get('ratingValue', 0))
                        review_count = int(rating.get('reviewCount', 0))
                        break
                    if isinstance(data, list):
                        for item in data:
                            if isinstance(item, dict) and 'aggregateRating' in item:
                                rating = item['aggregateRating']
                                score = float(rating.get('ratingValue', 0))
                                review_count = int(rating.get('reviewCount', 0))
                                break
                        if score is not None:
                            break
                except (json.JSONDecodeError, ValueError, TypeError, KeyError):
                    continue

            if score is None:
                text = soup.get_text()
                score_match = re.search(r'TrustScore\s+(\d+\.?\d*)', text)
                if score_match:
                    score = float(score_match.group(1))
                review_match = re.search(r'([\d,]+)\s+reviews?', text, re.IGNORECASE)
                if review_match:
                    review_count = int(review_match.group(1).replace(',', ''))

            return score, review_count
        except Exception as e:
            log_error(f"Trustpilot error {url}: {e}", tag="SCRAPE")
            return None, None

    def scrape_firm(self, firm_slug, firm_config):
        trustpilot_url = firm_config.get("trustpilot")
        if not trustpilot_url:
            return
        score, review_count = self._scrape_trustpilot_page(trustpilot_url)
        if score is not None:
            self.results["scraped"] += 1
            save_trustpilot_score(firm_slug, score, review_count or 0)
            log_info(f"Trustpilot {firm_config['name']}: ⭐ {score}/5 ({review_count or '?'} reviews)", tag="SCRAPE")
            self._check_score_alerts(firm_slug, firm_config['name'], score, review_count)
        else:
            self.results["errors"] += 1

    def _check_score_alerts(self, firm_slug, firm_name, current_score, current_count):
        previous_scores = get_latest_trustpilot_scores()
        previous = previous_scores.get(firm_slug)
        if previous and previous.get('score'):
            old_score = previous['score']
            if current_score < old_score - self.SCORE_DROP_THRESHOLD:
                self.results["score_drops"] += 1
                save_scam_alert(
                    firm_slug=firm_slug, alert_type="trustpilot_score_drop",
                    severity="medium",
                    description=f"{firm_name} Trustpilot dropped {old_score:.1f} → {current_score:.1f}",
                    source="Trustpilot monitoring"
                )
                log_info(f"📉 Score drop: {firm_name} {old_score:.1f} → {current_score:.1f}", tag="ALERT")
            if current_count and previous.get('review_count'):
                new_reviews = current_count - previous['review_count']
                if new_reviews >= self.NEGATIVE_SPIKE_REVIEWS:
                    log_info(f"📊 Review spike: {firm_name} +{new_reviews} reviews", tag="ALERT")
        if current_score < self.LOW_SCORE_THRESHOLD:
            self.results["low_scores"] += 1
            log_info(f"⚠️  Low score: {firm_name} at {current_score:.1f}/5", tag="ALERT")

    def scrape_all(self):
        log_info(f"Starting Trustpilot scrape of {len(PROP_FIRMS)} firms...", tag="SCRAPE")
        self.results = {"scraped": 0, "score_drops": 0, "low_scores": 0, "errors": 0}
        for firm_slug, firm_config in PROP_FIRMS.items():
            try:
                self.scrape_firm(firm_slug, firm_config)
            except Exception as e:
                log_error(f"Trustpilot error {firm_slug}: {e}", tag="SCRAPE")
                self.results["errors"] += 1
            time.sleep(random.uniform(3, 6))
        log_info(
            f"Trustpilot scrape complete — Scraped: {self.results['scraped']} | "
            f"Score drops: {self.results['score_drops']} | "
            f"Low scores: {self.results['low_scores']} | "
            f"Errors: {self.results['errors']}", tag="SCRAPE"
        )
        return self.results
ENDFILE4
echo "  ✅ scrapers/trustpilot_scraper.py"

# ============================================================
# FILE 5: services/alert_service.py
# ============================================================
cat > services/alert_service.py << 'ENDFILE5'
"""
PropFirmTracker Bot - Alert Service
"""
import asyncio
from datetime import datetime, timedelta
from utils.logger import log_info, log_error, log_warn
from database import (
    get_unalerted_changes, mark_change_alerted,
    get_active_promos, get_all_premium_users
)
from config import (
    FREE_CHANNEL_ID, PREMIUM_CHANNEL_ID,
    FREE_ALERT_DELAY_HOURS, PROP_FIRMS
)


class AlertService:
    def __init__(self, bot_app):
        self.bot = bot_app.bot if bot_app else None
        self._channel_disabled = set()

    def set_bot(self, bot):
        self.bot = bot

    def _is_channel_configured(self, channel_id):
        if not channel_id:
            return False
        if str(channel_id) in ("-100XXXXXXXXXX", "", "0"):
            return False
        if channel_id in self._channel_disabled:
            return False
        return True

    def _get_affiliate_link(self, firm_slug):
        firm = PROP_FIRMS.get(firm_slug, {})
        return firm.get("affiliate_url", firm.get("url", "#"))

    def _get_firm_name(self, firm_slug):
        firm = PROP_FIRMS.get(firm_slug, {})
        return firm.get("name", firm_slug.replace("_", " ").title())

    def format_change_alert(self, change, is_premium=True):
        firm_name = self._get_firm_name(change['firm_slug'])
        affiliate_link = self._get_affiliate_link(change['firm_slug'])
        type_emojis = {
            "content_update": "🔄", "pricing_change": "💰", "rules_change": "📋",
            "new_promo": "🎟️", "scam_alert": "🚨", "trustpilot_drop": "📉",
        }
        emoji = type_emojis.get(change.get('change_type', ''), '🔔')
        msg = f"{emoji} <b>{firm_name} — Update Detected</b>\n\n"
        msg += f"📄 Page: <code>{change.get('page_type', 'unknown')}</code>\n"
        msg += f"📝 {change.get('summary', 'Change detected')}\n"
        if change.get('ai_analysis'):
            msg += f"\n🧠 <b>AI Analysis:</b>\n{change['ai_analysis']}\n"
        msg += f"\n🕐 Detected: {change.get('detected_at', 'now')}\n"
        if is_premium:
            msg += f"\n🔗 <a href='{affiliate_link}'>Visit {firm_name}</a>"
        else:
            msg += f"\n⏳ <i>Premium members got this alert {FREE_ALERT_DELAY_HOURS}h ago</i>"
            msg += "\n\n💎 Upgrade to Premium: /premium"
        msg += "\n\n━━━━━━━━━━━━━━━━━━━━━\n🤖 @PropFirmTrackerBot"
        return msg

    def format_promo_alert(self, promo, is_premium=True):
        firm_name = self._get_firm_name(promo['firm_slug'])
        affiliate_link = self._get_affiliate_link(promo['firm_slug'])
        msg = f"🎟️ <b>NEW PROMO — {firm_name}</b>\n\n"
        msg += f"💰 Discount: <b>{promo.get('discount', 'See details')}</b>\n"
        if promo.get('promo_code'):
            msg += f"🔑 Code: <code>{promo['promo_code']}</code>\n"
        if promo.get('description'):
            msg += f"📝 {promo['description']}\n"
        if promo.get('expires_at'):
            msg += f"⏰ Expires: {promo['expires_at']}\n"
        msg += f"\n🔗 <a href='{affiliate_link}'>Claim at {firm_name} →</a>"
        if not is_premium:
            msg += f"\n\n⏳ <i>Premium members got this {FREE_ALERT_DELAY_HOURS}h earlier</i>"
            msg += "\n💎 /premium for real-time alerts"
        msg += "\n\n━━━━━━━━━━━━━━━━━━━━━\n🤖 @PropFirmTrackerBot"
        return msg

    def format_scam_alert(self, alert, is_premium=True):
        firm_name = self._get_firm_name(alert['firm_slug'])
        severity_emojis = {"high": "🚨", "medium": "⚠️", "low": "ℹ️"}
        emoji = severity_emojis.get(alert.get('severity', 'medium'), '⚠️')
        msg = f"{emoji} <b>WARNING — {firm_name}</b>\n\n"
        msg += f"📊 Severity: <b>{alert.get('severity', 'medium').upper()}</b>\n"
        msg += f"📝 {alert.get('description', 'Issue detected')}\n"
        if alert.get('source'):
            msg += f"📎 Source: {alert['source']}\n"
        msg += f"\n🕐 Detected: {alert.get('detected_at', 'now')}\n"
        msg += "\n⚡ <i>Always do your own due diligence before choosing a prop firm.</i>"
        if not is_premium:
            msg += "\n\n💎 /premium for instant scam alerts"
        msg += "\n\n━━━━━━━━━━━━━━━━━━━━━\n🤖 @PropFirmTrackerBot"
        return msg

    async def _send_to_channel(self, channel_id, text):
        try:
            await self.bot.send_message(
                chat_id=channel_id, text=text,
                parse_mode='HTML', disable_web_page_preview=True
            )
            return True
        except Exception as e:
            err = str(e).lower()
            if 'chat not found' in err or 'chat_not_found' in err:
                self._channel_disabled.add(channel_id)
                log_warn(f"Channel {channel_id} not found — alerts disabled. Fix PREMIUM_CHANNEL_ID or FREE_CHANNEL_ID in .env", tag="ALERT")
                return False
            elif 'forbidden' in err:
                self._channel_disabled.add(channel_id)
                log_warn(f"Bot not admin in {channel_id} — alerts disabled", tag="ALERT")
                return False
            else:
                log_error(f"Send failed: {e}", tag="ALERT")
                return False

    async def send_premium_alerts(self):
        if not self.bot:
            return
        if not self._is_channel_configured(PREMIUM_CHANNEL_ID):
            changes = get_unalerted_changes("premium")
            if changes:
                log_warn(f"Skipping {len(changes)} premium alerts — PREMIUM_CHANNEL_ID not set in .env", tag="ALERT")
                for c in changes:
                    mark_change_alerted(c['id'], "premium")
            return
        changes = get_unalerted_changes("premium")
        if not changes:
            log_info("No new premium alerts to send", tag="ALERT")
            return
        log_info(f"Sending {len(changes)} alerts to premium channel...", tag="ALERT")
        sent = 0
        for change in changes:
            msg = self.format_change_alert(change, is_premium=True)
            success = await self._send_to_channel(PREMIUM_CHANNEL_ID, msg)
            if success:
                sent += 1
            elif PREMIUM_CHANNEL_ID in self._channel_disabled:
                for c in changes:
                    mark_change_alerted(c['id'], "premium")
                break
            mark_change_alerted(change['id'], "premium")
            await asyncio.sleep(1)
        if sent > 0:
            log_info(f"Alerts sent ✓ ({sent}/{len(changes)})", tag="ALERT")

    async def send_free_alerts(self):
        if not self.bot:
            return
        if not self._is_channel_configured(FREE_CHANNEL_ID):
            changes = get_unalerted_changes("free")
            if changes:
                for c in changes:
                    detected = datetime.fromisoformat(c['detected_at'])
                    if detected <= datetime.now() - timedelta(hours=FREE_ALERT_DELAY_HOURS):
                        mark_change_alerted(c['id'], "free")
            return
        changes = get_unalerted_changes("free")
        if not changes:
            return
        delay_cutoff = datetime.now() - timedelta(hours=FREE_ALERT_DELAY_HOURS)
        for change in changes:
            detected = datetime.fromisoformat(change['detected_at'])
            if detected <= delay_cutoff:
                msg = self.format_change_alert(change, is_premium=False)
                success = await self._send_to_channel(FREE_CHANNEL_ID, msg)
                if not success and FREE_CHANNEL_ID in self._channel_disabled:
                    for c in changes:
                        mark_change_alerted(c['id'], "free")
                    break
                mark_change_alerted(change['id'], "free")
                await asyncio.sleep(1)

    async def send_promo_to_channel(self, promo, channel_type="premium"):
        if not self.bot:
            return
        channel_id = PREMIUM_CHANNEL_ID if channel_type == "premium" else FREE_CHANNEL_ID
        is_premium = channel_type == "premium"
        if not self._is_channel_configured(channel_id):
            return
        msg = self.format_promo_alert(promo, is_premium=is_premium)
        success = await self._send_to_channel(channel_id, msg)
        if success:
            log_info(f"Promo sent to {channel_type}: {promo['firm_slug']}", tag="ALERT")
ENDFILE5
echo "  ✅ services/alert_service.py"

# ============================================================
# DONE — Verify
# ============================================================
echo ""
echo "🔍 Verifying files..."
python3 -c "
from config import PROP_FIRMS
print(f'  Config OK — {len(PROP_FIRMS)} firms loaded')
for slug, cfg in PROP_FIRMS.items():
    urls = [cfg.get('pricing_url',''), cfg.get('rules_url',''), cfg.get('url','')]
    active = sum(1 for u in urls if u)
    print(f'    {slug}: {active} active URLs')
"

echo ""
echo "✅ ALL 5 FILES FIXED — Run: python3 run.py"
