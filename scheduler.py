"""Scheduler V3 — promo to free channel every ~2 days"""
import asyncio
from datetime import datetime
from utils.logger import log_info, log_error, log_warn
from scrapers import PropFirmScraper, RedditScraper, TrustpilotScraper
from services.alert_service import AlertService
from services.ai_summarizer import AISummarizer
from config import SCRAPE_INTERVAL_HOURS, FREE_CHANNEL_ID, PROP_FIRMS
from database import get_active_promos, get_latest_trustpilot_scores, get_user_stats

class Scheduler:
    PROMO_EVERY = 16  # cycles (~48h at 3h interval)
    def __init__(self, bot_app=None):
        self.bot_app=bot_app; self.alert_service=AlertService(bot_app); self.ai=AISummarizer()
        self.running=False; self._task=None; self._cy=0
    def set_bot(self, bot): self.alert_service.set_bot(bot)

    async def run_scrape_cycle(self):
        log_info(f"═══ Scrape {datetime.now().strftime('%H:%M:%S')} ═══", tag="SCRAPE")
        for nm,Cl in [("Prop firms",PropFirmScraper),("Reddit",RedditScraper),("Trustpilot",TrustpilotScraper)]:
            try: r=Cl().scrape_all(); log_info(f"{nm}: {r}", tag="SCRAPE")
            except Exception as e: log_error(f"{nm}: {e}", tag="ERROR")
        try:
            await self.alert_service.send_premium_alerts()
            await self.alert_service.send_free_alerts()
            log_info("Alerts ✓", tag="ALERT")
        except Exception as e: log_error(f"Alerts: {e}", tag="ERROR")
        self._cy += 1
        if self._cy >= self.PROMO_EVERY:
            self._cy=0
            try: await self._promo()
            except Exception as e: log_error(f"Promo: {e}", tag="ERROR")
        log_info("═══ Complete ═══", tag="SCRAPE")

    async def _promo(self):
        bot=self.alert_service.bot
        if not bot or not FREE_CHANNEL_ID: return
        ps=get_active_promos(); sc=get_latest_trustpilot_scores(); st=get_user_stats()
        m="📊 <b>PropFirmTracker Update</b>\n\n"
        if ps:
            m+=f"🎟️ <b>{len(ps)} Promo(s)</b>\n"
            for p in ps[:3]: m+=f"  • {PROP_FIRMS.get(p['firm_slug'],{}).get('name','?')}: <code>{p.get('promo_code','?')}</code> {p.get('discount','')}\n"
            m+="\n"
        if sc:
            m+="⭐ <b>Top</b>\n"
            for s,d in sorted(sc.items(),key=lambda x:x[1].get('score',0),reverse=True)[:3]:
                m+=f"  • {PROP_FIRMS.get(s,{}).get('name',s)}: {d.get('score',0):.1f}/5\n"
            m+="\n"
        m+=f"🔍 {len(PROP_FIRMS)} firms | {st['total']} traders\n\n━━━━━━━━━━━━━━━━━━━━━\n\n💎 <b>Real-time alerts?</b>\n👉 @PropFirmTrackerBot → /premium\n🆓 /referral"
        try: await bot.send_message(chat_id=FREE_CHANNEL_ID,text=m,parse_mode='HTML',disable_web_page_preview=True); log_info("📢 Promo → free ch", tag="ALERT")
        except Exception as e: log_warn(f"Promo failed: {e}", tag="ALERT")

    async def run_loop(self):
        self.running=True; log_info(f"Scheduler: every {SCRAPE_INTERVAL_HOURS}h", tag="STARTUP")
        await asyncio.sleep(30)
        while self.running:
            try: await self.run_scrape_cycle()
            except Exception as e: log_error(f"Cycle: {e}", tag="ERROR")
            log_info(f"Next in {SCRAPE_INTERVAL_HOURS}h...", tag="SCRAPE")
            await asyncio.sleep(SCRAPE_INTERVAL_HOURS*3600)
    def start(self): self._task=asyncio.get_running_loop().create_task(self.run_loop()); log_info("Scheduler ✓", tag="STARTUP")
    def stop(self): self.running=False; self._task and self._task.cancel()
