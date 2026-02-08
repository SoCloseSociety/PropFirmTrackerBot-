"""
PropFirmTracker Bot - Scheduler
=================================
Runs scrapers at configured intervals and sends alerts.
"""

import asyncio
from datetime import datetime
from utils.logger import log_info, log_error
from scrapers import PropFirmScraper, RedditScraper, TrustpilotScraper
from services.alert_service import AlertService
from services.ai_summarizer import AISummarizer
from config import SCRAPE_INTERVAL_HOURS


class Scheduler:
    """Manages periodic scraping and alert tasks."""

    def __init__(self, bot_app=None):
        self.bot_app = bot_app
        self.alert_service = AlertService(bot_app)
        self.ai = AISummarizer()
        self.running = False
        self._task = None

    def set_bot(self, bot):
        """Set bot instance after initialization."""
        self.alert_service.set_bot(bot)

    async def run_scrape_cycle(self):
        """Run one complete scrape cycle."""
        log_info(f"═══ Starting scrape cycle at {datetime.now().strftime('%H:%M:%S')} ═══", tag="SCRAPE")

        # 1. Scrape prop firm websites
        try:
            pf_scraper = PropFirmScraper()
            pf_results = pf_scraper.scrape_all()
            log_info(f"Prop firms done: {pf_results}", tag="SCRAPE")
        except Exception as e:
            log_error(f"Prop firm scraper failed: {e}", tag="ERROR")

        # 2. Scrape Reddit
        try:
            reddit_scraper = RedditScraper()
            reddit_results = reddit_scraper.scrape_all()
            log_info(f"Reddit done: {reddit_results}", tag="SCRAPE")
        except Exception as e:
            log_error(f"Reddit scraper failed: {e}", tag="ERROR")

        # 3. Scrape Trustpilot
        try:
            tp_scraper = TrustpilotScraper()
            tp_results = tp_scraper.scrape_all()
            log_info(f"Trustpilot done: {tp_results}", tag="SCRAPE")
        except Exception as e:
            log_error(f"Trustpilot scraper failed: {e}", tag="ERROR")

        # 4. Send alerts
        try:
            await self.alert_service.send_premium_alerts()
            await self.alert_service.send_free_alerts()
            log_info("Alerts sent ✓", tag="ALERT")
        except Exception as e:
            log_error(f"Alert sending failed: {e}", tag="ERROR")

        log_info(f"═══ Scrape cycle complete ═══", tag="SCRAPE")

    async def run_loop(self):
        """Main scheduler loop."""
        self.running = True
        interval_seconds = SCRAPE_INTERVAL_HOURS * 3600

        log_info(f"Scheduler started — scraping every {SCRAPE_INTERVAL_HOURS}h", tag="STARTUP")

        # Run initial scrape after 30 second delay (let bot initialize)
        await asyncio.sleep(30)

        while self.running:
            try:
                await self.run_scrape_cycle()
            except Exception as e:
                log_error(f"Scheduler cycle error: {e}", tag="ERROR")

            log_info(f"Next scrape in {SCRAPE_INTERVAL_HOURS}h...", tag="SCRAPE")
            await asyncio.sleep(interval_seconds)

    def start(self):
        """Start the scheduler as a background task."""
        loop = asyncio.get_running_loop()
        self._task = loop.create_task(self.run_loop())
        log_info("Scheduler background task started ✓", tag="STARTUP")

    def stop(self):
        """Stop the scheduler."""
        self.running = False
        if self._task:
            self._task.cancel()
        log_info("Scheduler stopped", tag="STARTUP")
