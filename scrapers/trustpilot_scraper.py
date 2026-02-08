"""
PropFirmTracker Bot - Trustpilot Scraper
==========================================
Scrapes Trustpilot scores and detects significant rating changes.
"""

import re
import time
import requests
from bs4 import BeautifulSoup
from utils.logger import log_info, log_error, log_debug
from database import save_trustpilot_score, get_latest_trustpilot_scores, save_scam_alert
from config import PROP_FIRMS, USER_AGENT, REQUEST_TIMEOUT


class TrustpilotScraper:
    """Scrapes Trustpilot for prop firm ratings."""

    SCORE_DROP_THRESHOLD = 0.3     # Alert if score drops by this much
    LOW_SCORE_THRESHOLD = 2.5      # Alert if score is below this
    NEGATIVE_SPIKE_REVIEWS = 10    # Alert if N+ new reviews detected in one scrape

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/xhtml+xml",
            "Accept-Language": "en-US,en;q=0.9",
        })
        self.results = {"scraped": 0, "score_drops": 0, "low_scores": 0, "errors": 0}

    def _scrape_trustpilot_page(self, url):
        """Scrape a Trustpilot page for score and review count."""
        try:
            response = self.session.get(url, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')

            score = None
            review_count = None

            # Try multiple selectors (Trustpilot changes their HTML often)
            # Method 1: JSON-LD structured data
            import json
            for script in soup.find_all('script', type='application/ld+json'):
                try:
                    data = json.loads(script.string)
                    if isinstance(data, dict) and 'aggregateRating' in data:
                        rating = data['aggregateRating']
                        score = float(rating.get('ratingValue', 0))
                        review_count = int(rating.get('reviewCount', 0))
                        break
                    elif isinstance(data, list):
                        for item in data:
                            if isinstance(item, dict) and 'aggregateRating' in item:
                                rating = item['aggregateRating']
                                score = float(rating.get('ratingValue', 0))
                                review_count = int(rating.get('reviewCount', 0))
                                break
                except (json.JSONDecodeError, ValueError, TypeError):
                    continue

            # Method 2: Parse from page text
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
            log_error(f"Failed to scrape Trustpilot {url}: {e}", tag="SCRAPE")
            return None, None

    def scrape_firm(self, firm_slug, firm_config):
        """Scrape Trustpilot for a single firm."""
        trustpilot_url = firm_config.get("trustpilot")
        if not trustpilot_url:
            return

        score, review_count = self._scrape_trustpilot_page(trustpilot_url)

        if score is not None:
            self.results["scraped"] += 1
            save_trustpilot_score(firm_slug, score, review_count or 0)
            log_info(
                f"Trustpilot {firm_config['name']}: ⭐ {score}/5 ({review_count or '?'} reviews)",
                tag="SCRAPE"
            )

            # Check for alerts
            self._check_score_alerts(firm_slug, firm_config['name'], score, review_count)
        else:
            self.results["errors"] += 1

    def _check_score_alerts(self, firm_slug, firm_name, current_score, current_count):
        """Check if the score warrants an alert."""
        previous_scores = get_latest_trustpilot_scores()
        previous = previous_scores.get(firm_slug)

        # Alert: Score dropped significantly
        if previous and previous.get('score'):
            old_score = previous['score']
            if current_score < old_score - self.SCORE_DROP_THRESHOLD:
                self.results["score_drops"] += 1
                save_scam_alert(
                    firm_slug=firm_slug,
                    alert_type="trustpilot_score_drop",
                    severity="medium",
                    description=(
                        f"{firm_name} Trustpilot score dropped from "
                        f"{old_score:.1f} to {current_score:.1f}"
                    ),
                    source=f"Trustpilot monitoring"
                )
                log_info(
                    f"📉 Score drop alert: {firm_name} {old_score:.1f} → {current_score:.1f}",
                    tag="ALERT"
                )

            # Alert: Spike in review count (could indicate review bombing)
            if current_count and previous.get('review_count'):
                new_reviews = current_count - previous['review_count']
                if new_reviews >= self.NEGATIVE_SPIKE_REVIEWS:
                    log_info(
                        f"📊 Review spike: {firm_name} got {new_reviews} new reviews",
                        tag="ALERT"
                    )

        # Alert: Very low score
        if current_score < self.LOW_SCORE_THRESHOLD:
            self.results["low_scores"] += 1
            log_info(f"⚠️  Low score alert: {firm_name} at {current_score:.1f}/5", tag="ALERT")

    def scrape_all(self):
        """Scrape Trustpilot for all configured firms."""
        log_info(f"Starting Trustpilot scrape of {len(PROP_FIRMS)} firms...", tag="SCRAPE")
        self.results = {"scraped": 0, "score_drops": 0, "low_scores": 0, "errors": 0}

        for firm_slug, firm_config in PROP_FIRMS.items():
            try:
                self.scrape_firm(firm_slug, firm_config)
            except Exception as e:
                log_error(f"Error scraping Trustpilot for {firm_slug}: {e}", tag="SCRAPE")
                self.results["errors"] += 1
            time.sleep(3)  # Be extra polite to Trustpilot

        log_info(
            f"Trustpilot scrape complete — Scraped: {self.results['scraped']} | "
            f"Score drops: {self.results['score_drops']} | "
            f"Low scores: {self.results['low_scores']} | "
            f"Errors: {self.results['errors']}",
            tag="SCRAPE"
        )
        return self.results
