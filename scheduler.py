"""
PropFirmTracker — Scheduler V4
Content engine: VIP alerts + Free channel engagement posts.
Free channel gets 4 types of content in rotation every ~6h.
"""
import asyncio
import random
from datetime import datetime
from utils.logger import log_info, log_error, log_warn
from scrapers import PropFirmScraper, RedditScraper, TrustpilotScraper
from services.alert_service import AlertService
from services.ai_summarizer import AISummarizer
from config import SCRAPE_INTERVAL_HOURS, FREE_CHANNEL_ID, PROP_FIRMS
from database import (
    get_active_promos, get_latest_trustpilot_scores, get_user_stats,
    get_connection
)


TRADING_TIPS = [
    ("Risk Management 101", "Never risk more than 1-2% of your account on a single trade. This is the #1 rule that separates funded traders from blown accounts."),
    ("Challenge Strategy", "Most prop firm challenges have a time limit but no minimum trades. Don't overtrade to hit a target — wait for A+ setups only."),
    ("Drawdown Control", "Track your daily drawdown BEFORE you trade. Set hard limits. If you hit 50% of your daily max, close the platform."),
    ("News Trading", "Check the economic calendar every morning. Many prop firms restrict trading during high-impact events like NFP, CPI, or FOMC."),
    ("Consistency Rule", "More firms now require consistency — no single day can be >30% of total profits. Spread your wins across sessions."),
    ("Start Small", "Start with a $25K challenge to learn the rules. It's cheaper to retry than a $200K challenge — and the rules are the same."),
    ("Weekend Gaps", "Most firms charge swap fees. Some don't allow weekend holding at all. Close positions before Friday if you're unsure."),
    ("Journal Everything", "Keep a detailed trade journal with entries, exits, and reasoning. It helps you spot patterns and some firms ask for it."),
    ("Diversify Firms", "Run challenges at 2-3 firms simultaneously. Different firms have different rules — find what fits your style."),
    ("Take Payouts", "Once funded, take regular payouts. Don't let profits accumulate. Firms can change rules or face issues at any time."),
    ("Avoid Revenge Trading", "Lost 2 trades in a row? Stop. The market will be there tomorrow. Revenge trading is the #1 account killer."),
    ("Use a Trading Plan", "Define your entry, stop loss, and take profit BEFORE entering. If a trade doesn't meet all criteria, skip it."),
]


class Scheduler:
    FREE_POST_EVERY = 2  # every 2 cycles = ~6h

    CONTENT_TYPES = [
        "market_update",
        "firm_spotlight",
        "reddit_pulse",
        "trading_tip",
    ]

    def __init__(self, bot_app=None):
        self.bot_app = bot_app
        self.alert_service = AlertService(bot_app)
        self.ai = AISummarizer()
        self.running = False
        self._task = None
        self._cycle = 0
        self._content_idx = 0
        self._tip_idx = 0

    def set_bot(self, bot):
        self.alert_service.set_bot(bot)

    async def run_scrape_cycle(self):
        ts = datetime.now().strftime('%H:%M')
        log_info(f"{'='*20} Scrape {ts} {'='*20}", tag="SCRAPE")

        for name, Cls in [("Prop firms", PropFirmScraper), ("Reddit", RedditScraper), ("Trustpilot", TrustpilotScraper)]:
            try:
                r = Cls().scrape_all()
                log_info(f"{name}: {r}", tag="SCRAPE")
            except Exception as e:
                log_error(f"{name}: {e}", tag="ERROR")

        try:
            await self.alert_service.send_premium_alerts()
            await self.alert_service.send_free_alerts()
            log_info("Alerts done", tag="ALERT")
        except Exception as e:
            log_error(f"Alerts: {e}", tag="ERROR")

        self._cycle += 1
        if self._cycle >= self.FREE_POST_EVERY:
            self._cycle = 0
            try:
                await self._post_free()
            except Exception as e:
                log_error(f"Free post: {e}", tag="ERROR")

        log_info(f"{'='*20} Complete {'='*20}", tag="SCRAPE")

    async def _post_free(self):
        bot = self.alert_service.bot
        if not bot or not FREE_CHANNEL_ID:
            return

        ct = self.CONTENT_TYPES[self._content_idx % len(self.CONTENT_TYPES)]
        self._content_idx += 1

        builders = {
            "market_update": self._msg_market,
            "firm_spotlight": self._msg_spotlight,
            "reddit_pulse": self._msg_reddit,
            "trading_tip": self._msg_tip,
        }
        msg = builders.get(ct, self._msg_market)()
        if not msg:
            msg = self._msg_market()

        try:
            await bot.send_message(chat_id=FREE_CHANNEL_ID, text=msg,
                parse_mode='HTML', disable_web_page_preview=True)
            log_info(f"Free channel: {ct}", tag="ALERT")
        except Exception as e:
            log_warn(f"Free post failed: {e}", tag="ALERT")

    def _msg_market(self):
        promos = get_active_promos()
        scores = get_latest_trustpilot_scores()
        stats = get_user_stats()

        m = "📊  <b>PROP FIRM MARKET UPDATE</b>\n"
        m += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"

        if promos:
            m += f"🎟  <b>{len(promos)} Active Promo{'s' if len(promos) > 1 else ''}</b>\n\n"
            for p in promos[:3]:
                fn = PROP_FIRMS.get(p['firm_slug'], {}).get('name', p['firm_slug'])
                code = p.get('promo_code', '')
                disc = p.get('discount', '')
                m += f"   <b>{fn}</b>\n"
                if code:
                    m += f"   Code  <code>{code}</code>"
                if disc:
                    m += f"  —  {disc}"
                m += "\n\n"
        else:
            m += "   No promos right now — we'll alert you!\n\n"

        if scores:
            ss = sorted(scores.items(), key=lambda x: x[1].get('score', 0), reverse=True)
            m += "⭐  <b>Top Rated</b>\n\n"
            for slug, d in ss[:5]:
                fn = PROP_FIRMS.get(slug, {}).get('name', slug)
                sc = d.get('score', 0)
                bar = "█" * int(sc) + "░" * (5 - int(sc))
                m += f"   {fn}  {bar}  {sc:.1f}\n"
            m += "\n"

        m += f"   {len(PROP_FIRMS)} firms monitored  ·  {stats['total']} traders\n\n"
        m += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        m += "💎 Real-time alerts & AI analysis\n"
        m += "👉 @PropFirmTrackerBot  ·  /premium"
        return m

    def _msg_spotlight(self):
        slug = random.choice(list(PROP_FIRMS.keys()))
        cfg = PROP_FIRMS[slug]
        fn = cfg['name']
        scores = get_latest_trustpilot_scores()
        sd = scores.get(slug, {})
        sc = sd.get('score', 0)
        rc = sd.get('review_count', 0)

        mentions = 0
        try:
            conn = get_connection()
            row = conn.execute(
                "SELECT COUNT(*) as c FROM reddit_mentions WHERE firm_slug=? AND created_at > datetime('now','-7 days')",
                (slug,)).fetchone()
            mentions = row['c'] if row else 0
            conn.close()
        except:
            pass

        promos = [p for p in get_active_promos() if p['firm_slug'] == slug]

        m = "🎯  <b>FIRM SPOTLIGHT</b>\n"
        m += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        m += f"   <b>{fn}</b>\n\n"

        if sc > 0:
            stars = "⭐" * int(round(sc))
            m += f"   {stars}  {sc:.1f}/5  ({rc:,} reviews)\n\n"

        if mentions > 0:
            m += f"   💬  {mentions} Reddit mentions this week\n"

        m += f"   🔗  <a href='{cfg.get('url', '#')}'>{fn} Website</a>\n\n"

        if promos:
            p = promos[0]
            m += f"   🎟  Code: <code>{p.get('promo_code', '?')}</code>"
            if p.get('discount'):
                m += f"  —  {p['discount']}"
            m += "\n\n"

        m += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        m += "🔔 Get instant alerts for this firm\n"
        m += "👉 @PropFirmTrackerBot  ·  /premium"
        return m

    def _msg_reddit(self):
        try:
            conn = get_connection()
            rows = conn.execute("""
                SELECT firm_slug, COUNT(*) as c,
                    SUM(CASE WHEN sentiment='positive' THEN 1 ELSE 0 END) as pos,
                    SUM(CASE WHEN sentiment='negative' THEN 1 ELSE 0 END) as neg
                FROM reddit_mentions
                WHERE firm_slug != 'general' AND created_at > datetime('now','-24 hours')
                GROUP BY firm_slug ORDER BY c DESC LIMIT 5
            """).fetchall()
            scams = conn.execute("""
                SELECT firm_slug, description FROM scam_alerts
                WHERE detected_at > datetime('now','-48 hours')
                ORDER BY detected_at DESC LIMIT 3
            """).fetchall()
            conn.close()
        except:
            rows, scams = [], []

        m = "💬  <b>COMMUNITY PULSE</b>\n"
        m += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"

        if rows:
            m += "   <b>Most Discussed (24h)</b>\n\n"
            for r in rows:
                fn = PROP_FIRMS.get(r['firm_slug'], {}).get('name', r['firm_slug'])
                pos, neg = r['pos'] or 0, r['neg'] or 0
                mood = "🟢" if pos > neg else "🔴" if neg > pos else "⚪"
                m += f"   {mood}  {fn}  —  {r['c']} mentions\n"
            m += "\n"
        else:
            m += "   Quiet day — no major discussions\n\n"

        if scams:
            m += "   ⚠️  <b>Recent Warnings</b>\n\n"
            for s in scams[:2]:
                fn = PROP_FIRMS.get(s['firm_slug'], {}).get('name', s['firm_slug'])
                m += f"   🔴  {fn}\n"
                m += f"       {s['description'][:70]}\n\n"

        m += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        m += "🚨 Instant scam alerts for VIP\n"
        m += "👉 @PropFirmTrackerBot  ·  /premium"
        return m

    def _msg_tip(self):
        title, tip = TRADING_TIPS[self._tip_idx % len(TRADING_TIPS)]
        self._tip_idx += 1

        m = "💡  <b>TRADER'S TIP</b>\n"
        m += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        m += f"   <b>{title}</b>\n\n"
        m += f"   {tip}\n\n"
        m += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        m += "📊 Track prop firms 24/7 for free\n"
        m += "👉 @PropFirmTrackerBot  ·  /premium"
        return m

    async def run_loop(self):
        self.running = True
        log_info(f"Scheduler: every {SCRAPE_INTERVAL_HOURS}h", tag="STARTUP")
        await asyncio.sleep(30)
        while self.running:
            try:
                await self.run_scrape_cycle()
            except Exception as e:
                log_error(f"Cycle: {e}", tag="ERROR")
            log_info(f"Next in {SCRAPE_INTERVAL_HOURS}h...", tag="SCRAPE")
            await asyncio.sleep(SCRAPE_INTERVAL_HOURS * 3600)

    def start(self):
        self._task = asyncio.get_running_loop().create_task(self.run_loop())
        log_info("Scheduler running", tag="STARTUP")

    def stop(self):
        self.running = False
        if self._task:
            self._task.cancel()
