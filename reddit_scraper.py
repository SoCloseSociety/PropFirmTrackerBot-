"""
PropFirmTracker Bot - Reddit Scraper
=======================================
Scrapes Reddit for prop firm mentions using the free JSON API.
No API key needed — uses old.reddit.com/.json endpoints.
"""

import re
import time
import requests
from utils.logger import log_info, log_error, log_debug
from database import save_reddit_mention, save_scam_alert
from config import PROP_FIRMS, REDDIT_SUBREDDITS, USER_AGENT, REQUEST_TIMEOUT


class RedditScraper:
    """Scrapes Reddit for prop firm discussions and scam reports."""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": f"PropFirmTracker/1.0 ({USER_AGENT})",
        })
        self.firm_names = {slug: cfg['name'].lower() for slug, cfg in PROP_FIRMS.items()}
        self.results = {"posts_found": 0, "mentions": 0, "scam_alerts": 0, "errors": 0}

    def _get_subreddit_posts(self, subreddit, sort="new", limit=25):
        """Fetch recent posts from a subreddit."""
        url = f"https://old.reddit.com/r/{subreddit}/{sort}.json?limit={limit}"
        try:
            response = self.session.get(url, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()
            data = response.json()
            posts = data.get('data', {}).get('children', [])
            return [p['data'] for p in posts if p.get('data')]
        except Exception as e:
            log_error(f"Failed to fetch r/{subreddit}: {e}", tag="SCRAPE")
            self.results["errors"] += 1
            return []

    def _detect_firm_mention(self, text):
        """Detect which prop firm(s) are mentioned in text."""
        text_lower = text.lower()
        mentioned = []

        # Direct name matching
        name_to_slug = {}
        for slug, cfg in PROP_FIRMS.items():
            names = [cfg['name'].lower(), slug.replace('_', ' ')]
            # Add common variations
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
                names.extend(["e8 funding", "e8"])
            elif slug == "fundingpips":
                names.extend(["funding pips", "fundingpips"])
            elif slug == "goatfunded":
                names.extend(["goat funded", "goatfunded"])

            for name in names:
                name_to_slug[name] = slug

        for name, slug in name_to_slug.items():
            if name in text_lower and slug not in mentioned:
                mentioned.append(slug)

        return mentioned

    def _detect_scam_keywords(self, text):
        """Detect if a post is reporting a scam or major issue."""
        text_lower = text.lower()
        scam_keywords = [
            'scam', 'fraud', 'ponzi', 'rug pull', 'won\'t pay', 'not paying',
            'refused payout', 'denied payout', 'stole my', 'stolen', 'avoid',
            'stay away', 'do not use', 'warning', 'shut down', 'shutdown',
            'bankrupt', 'disappeared', 'no payout', 'payout denied',
            'fake reviews', 'manipulated', 'rigged',
        ]

        severity_high = ['scam', 'fraud', 'ponzi', 'rug pull', 'stole', 'stolen', 'bankrupt']

        found_keywords = [kw for kw in scam_keywords if kw in text_lower]

        if found_keywords:
            is_high = any(kw in text_lower for kw in severity_high)
            return {
                "is_scam_report": True,
                "keywords": found_keywords,
                "severity": "high" if is_high else "medium"
            }
        return {"is_scam_report": False}

    def _analyze_sentiment(self, text, score):
        """Basic sentiment analysis based on keywords and upvotes."""
        text_lower = text.lower()

        positive = ['great', 'excellent', 'recommend', 'best', 'love', 'amazing', 'paid out', 'got payout',
                     'legit', 'reliable', 'fast payout', 'good experience']
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
        """Scrape a single subreddit for prop firm mentions."""
        log_info(f"Scraping r/{subreddit}...", tag="SCRAPE")

        posts = self._get_subreddit_posts(subreddit)
        self.results["posts_found"] += len(posts)

        for post in posts:
            title = post.get('title', '')
            selftext = post.get('selftext', '')
            full_text = f"{title} {selftext}"
            post_url = f"https://reddit.com{post.get('permalink', '')}"
            score = post.get('score', 0)

            # Detect which firms are mentioned
            mentioned_firms = self._detect_firm_mention(full_text)

            if not mentioned_firms:
                # Generic prop firm post — check for scam reports anyway
                if any(kw in full_text.lower() for kw in ['prop firm', 'funded account', 'prop trading']):
                    mentioned_firms = ['general']

            for firm_slug in mentioned_firms:
                sentiment = self._analyze_sentiment(full_text, score)

                save_reddit_mention(
                    firm_slug=firm_slug,
                    subreddit=subreddit,
                    post_title=title[:200],
                    post_url=post_url,
                    score=score,
                    sentiment=sentiment
                )
                self.results["mentions"] += 1

                # Check for scam reports
                scam_check = self._detect_scam_keywords(full_text)
                if scam_check["is_scam_report"] and firm_slug != 'general':
                    save_scam_alert(
                        firm_slug=firm_slug,
                        alert_type="reddit_scam_report",
                        severity=scam_check["severity"],
                        description=f"Reddit post: {title[:150]}",
                        source=post_url
                    )
                    self.results["scam_alerts"] += 1
                    log_info(f"⚠️  Scam report detected for {firm_slug}: {title[:80]}", tag="ALERT")

    def scrape_all(self):
        """Scrape all configured subreddits."""
        log_info(f"Starting Reddit scrape of {len(REDDIT_SUBREDDITS)} subreddits...", tag="SCRAPE")
        self.results = {"posts_found": 0, "mentions": 0, "scam_alerts": 0, "errors": 0}

        for subreddit in REDDIT_SUBREDDITS:
            try:
                self.scrape_subreddit(subreddit)
            except Exception as e:
                log_error(f"Error scraping r/{subreddit}: {e}", tag="SCRAPE")
                self.results["errors"] += 1
            time.sleep(2)  # Be polite to Reddit

        log_info(
            f"Reddit scrape complete — Posts: {self.results['posts_found']} | "
            f"Mentions: {self.results['mentions']} | "
            f"Scam alerts: {self.results['scam_alerts']} | "
            f"Errors: {self.results['errors']}",
            tag="SCRAPE"
        )
        return self.results
