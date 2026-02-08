"""
PropFirmTracker Bot - Scheduler
=================================
Runs scrapers at configured intervals and sends alerts.
Also posts promotional messages to free channel periodically.
"""

import asyncio
from datetime import datetime
from utils.logger import log_info, log_error, log_warn
from scrapers import PropFirmScraper, RedditScraper, TrustpilotScraper
from services.alert_service import AlertService
from services.ai_summarizer import AISummarizer
from config import SCRAPE_INTERVAL_HOURS, FREE_CHANNEL_ID, PREMIUM_CHANNEL_ID, PROP_FIRMS
from database import get_active_promos, get_latest_trustpilot_scores, get_user_stats


class Scheduler:
    """Manages periodic scraping and alert tasks."""

    # Post promo to free channel every N scrape cycles
    # With 3h interval: 16 cycles = ~48h (every 2 days)
    PROMO_POST_EVERY_N_CYCLES = 16

    def __init__(self, bot_app=None):
        self.bot_app = bot_app
        self.alert_service = AlertService(bot_app)
        self.ai = AISummarizer()
        self.running = False
        self._task = None
        self._cycle_count = 0

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

        # 4. Send alerts to premium channel
        try:
            await self.alert_service.send_premium_alerts()
            await self.alert_service.send_free_alerts()
            log_info("Alerts sent ✓", tag="ALERT")
        except Exception as e:
            log_error(f"Alert sending failed: {e}", tag="ERROR")

        # 5. Periodic promo post to free channel (every ~2 days)
        self._cycle_count += 1
        if self._cycle_count >= self.PROMO_POST_EVERY_N_CYCLES:
            self._cycle_count = 0
            try:
                await self.post_free_channel_promo()
            except Exception as e:
                log_error(f"Free channel promo post failed: {e}", tag="ERROR")

        log_info(f"═══ Scrape cycle complete ═══", tag="SCRAPE")

    async def post_free_channel_promo(self):
        """Post a promotional/summary message to the free channel."""
        bot = self.alert_service.bot
        if not bot or not FREE_CHANNEL_ID:
            return

        # Build a useful summary message
        promos = get_active_promos()
        scores = get_latest_trustpilot_scores()
        stats = get_user_stats()

        msg = "📊 <b>PropFirmTracker — Weekly Summary</b>\n\n"

        # Show active promos (teaser)
        if promos:
            msg += f"🎟️ <b>{len(promos)} Active Promo(s)</b>\n"
            for p in promos[:3]:
                fn = PROP_FIRMS.get(p['firm_slug'], {}).get('name', p['firm_slug'])
                msg += f"  • {fn}: <code>{p.get('promo_code', '?')}</code> — {p.get('discount', '?')}\n"
            if len(promos) > 3:
                msg += f"  ... and {len(promos) - 3} more\n"
            msg += "\n"

        # Show top scores
        if scores:
            sorted_scores = sorted(scores.items(), key=lambda x: x[1].get('score', 0), reverse=True)
            msg += "⭐ <b>Top Rated Firms</b>\n"
            for slug, data in sorted_scores[:3]:
                fn = PROP_FIRMS.get(slug, {}).get('name', slug)
                msg += f"  • {fn}: {data.get('score', 0):.1f}/5\n"
            msg += "\n"

        # Monitored firms count
        msg += f"🔍 Monitoring <b>{len(PROP_FIRMS)} prop firms</b> 24/7\n"
        msg += f"👥 <b>{stats['total']}</b> traders using PropFirmTracker\n\n"

        # CTA for premium
        msg += (
            "━━━━━━━━━━━━━━━━━━━━━\n\n"
            "💎 <b>Want REAL-TIME alerts?</b>\n\n"
            "Free users get alerts with 24h delay.\n"
            "Premium members get:\n"
            "⚡ Instant alerts (no delay)\n"
            "🧠 AI-powered analysis\n"
            "🚨 Scam warnings first\n"
            "🎟️ Promo codes before anyone else\n\n"
            "👉 Start the bot: @PropFirmTrackerBot\n"
            "👉 Type /premium to upgrade\n\n"
            "🆓 Or invite 3 friends for FREE Premium! → /referral"
        )

        try:
            await bot.send_message(
                chat_id=FREE_CHANNEL_ID,
                text=msg,
                parse_mode='HTML',
                disable_web_page_preview=True
            )
            log_info("📢 Promo message posted to free channel", tag="ALERT")
        except Exception as e:
            log_warn(f"Failed to post promo to free channel: {e}", tag="ALERT")

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