"""
PropFirmTracker Bot - Reddit Scraper
=======================================
Scrapes Reddit for prop firm mentions using OAuth API.
Requires REDDIT_CLIENT_ID and REDDIT_CLIENT_SECRET in .env
(free, create at https://www.reddit.com/prefs/apps/)
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
        self.access_token = None
        self.firm_names = {slug: cfg['name'].lower() for slug, cfg in PROP_FIRMS.items()}
        self.results = {"posts_found": 0, "mentions": 0, "scam_alerts": 0, "errors": 0}

        # Try OAuth first, fallback to unauthenticated
        self._authenticate()

    def _authenticate(self):
        """Get Reddit OAuth access token (application-only)."""
        try:
            from config import REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET
        except ImportError:
            log_warn("REDDIT_CLIENT_ID/SECRET not in config — using unauthenticated mode", tag="SCRAPE")
            self._setup_unauthenticated()
            return

        if not REDDIT_CLIENT_ID or not REDDIT_CLIENT_SECRET or REDDIT_CLIENT_ID == "YOUR_REDDIT_CLIENT_ID":
            log_warn("Reddit OAuth not configured — using unauthenticated mode (may get 403)", tag="SCRAPE")
            self._setup_unauthenticated()
            return

        try:
            auth = requests.auth.HTTPBasicAuth(REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET)
            data = {"grant_type": "client_credentials"}
            headers = {"User-Agent": "PropFirmTracker/1.0 (by /u/PropFirmBot)"}

            resp = requests.post(
                "https://www.reddit.com/api/v1/access_token",
                auth=auth, data=data, headers=headers, timeout=10
            )
            resp.raise_for_status()
            token_data = resp.json()
            self.access_token = token_data.get("access_token")

            if self.access_token:
                self.session.headers.update({
                    "Authorization": f"bearer {self.access_token}",
                    "User-Agent": "PropFirmTracker/1.0 (by /u/PropFirmBot)",
                })
                log_info("Reddit OAuth authenticated ✓", tag="SCRAPE")
            else:
                log_warn("Reddit OAuth: no token received", tag="SCRAPE")
                self._setup_unauthenticated()

        except Exception as e:
            log_warn(f"Reddit OAuth failed: {e} — falling back to unauthenticated", tag="SCRAPE")
            self._setup_unauthenticated()

    def _setup_unauthenticated(self):
        """Setup for unauthenticated requests (may get 403)."""
        self.access_token = None
        self.session.headers.update({
            "User-Agent": "PropFirmTracker/1.0 (telegram bot; monitoring prop firm discussions)",
            "Accept": "application/json",
        })

    def _get_subreddit_posts(self, subreddit, sort="new", limit=25):
        """Fetch recent posts from a subreddit."""
        if self.access_token:
            # OAuth endpoint (higher rate limits, no 403)
            url = f"https://oauth.reddit.com/r/{subreddit}/{sort}?limit={limit}&raw_json=1"
        else:
            # Public endpoint (may get 403)
            url = f"https://www.reddit.com/r/{subreddit}/{sort}.json?limit={limit}&raw_json=1"

        try:
            response = self.session.get(url, timeout=REQUEST_TIMEOUT)

            if response.status_code == 429:
                retry_after = int(response.headers.get('Retry-After', 10))
                log_warn(f"Reddit rate limit, waiting {retry_after}s...", tag="SCRAPE")
                time.sleep(retry_after)
                response = self.session.get(url, timeout=REQUEST_TIMEOUT)

            if response.status_code == 403:
                if self.access_token:
                    log_warn(f"r/{subreddit}: 403 even with OAuth — subreddit may be private", tag="SCRAPE")
                else:
                    log_warn(f"r/{subreddit}: 403 — add REDDIT_CLIENT_ID to .env for OAuth", tag="SCRAPE")
                self.results["errors"] += 1
                return []

            response.raise_for_status()
            data = response.json()
            posts = data.get('data', {}).get('children', [])
            return [p['data'] for p in posts if p.get('data')]

        except requests.exceptions.HTTPError as e:
            log_error(f"Reddit HTTP error r/{subreddit}: {e}", tag="SCRAPE")
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