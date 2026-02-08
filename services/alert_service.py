"""
Alert Service V4 — Professional formatting, flood control, batching.
VIP: grouped by firm with clean layout.
Free: delayed alerts + conversion CTA.
"""
import asyncio
import re
from datetime import datetime, timedelta
from telegram.error import RetryAfter, BadRequest, Forbidden
from utils.logger import log_info, log_error, log_warn
from database import get_unalerted_changes, mark_change_alerted
from config import FREE_CHANNEL_ID, PREMIUM_CHANNEL_ID, FREE_ALERT_DELAY_HOURS, PROP_FIRMS


class AlertService:
    MAX_PER = 15
    DELAY = 3.5

    def __init__(self, bot_app):
        self.bot = bot_app.bot if bot_app else None
        self._off = set()

    def set_bot(self, bot):
        self.bot = bot

    def _fn(self, s):
        return PROP_FIRMS.get(s, {}).get('name', s.replace('_', ' ').title())

    def _fl(self, s):
        f = PROP_FIRMS.get(s, {})
        return f.get('affiliate_url', f.get('url', '#'))

    def _ok(self, cid):
        if not cid:
            return False
        s = str(cid).strip()
        if s in self._off or not s or s == "0":
            return False
        if "XXXX" in s or "xxxxxxxxxx" in s:
            return False
        try:
            int(s)
            return True
        except:
            return False

    async def _send(self, cid, text):
        try:
            await self.bot.send_message(
                chat_id=int(str(cid).strip()), text=text,
                parse_mode='HTML', disable_web_page_preview=True
            )
            return True
        except RetryAfter as e:
            w = e.retry_after + 3
            log_warn(f"Flood control: {w}s", tag="ALERT")
            await asyncio.sleep(w)
            try:
                await self.bot.send_message(
                    chat_id=int(str(cid).strip()), text=text,
                    parse_mode='HTML', disable_web_page_preview=True
                )
                return True
            except:
                return False
        except (BadRequest, Forbidden) as e:
            if any(k in str(e).lower() for k in ['not found', 'kicked', 'blocked']):
                self._off.add(str(cid))
                log_warn(f"Channel {cid} disabled", tag="ALERT")
            else:
                log_error(f"Send: {e}", tag="ALERT")
            return False
        except Exception as e:
            log_error(f"Send: {e}", tag="ALERT")
            return False

    def _format_vip_grouped(self, changes):
        """Group changes by firm -> one message per firm."""
        msgs = []
        firms = {}
        for c in changes:
            firms.setdefault(c['firm_slug'], []).append(c)

        for slug, chs in firms.items():
            fn = self._fn(slug)
            lk = self._fl(slug)
            types = set(c.get('change_type', '') for c in chs)

            if 'new_promo' in types:
                icon = "🎟"
            elif 'pricing_change' in types:
                icon = "💰"
            elif 'rules_change' in types:
                icon = "📋"
            elif 'scam_alert' in types:
                icon = "🚨"
            else:
                icon = "🔄"

            m = f"{icon}  <b>{fn}</b>\n"
            m += "━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"

            for c in chs[:4]:
                pt = c.get('page_type', '')
                plabel = {
                    "pricing": "💰 Pricing",
                    "rules": "📋 Rules",
                    "homepage": "🏠 Homepage",
                    "blog": "📰 Blog"
                }.get(pt, f"📄 {pt.title()}")

                summary = c.get('summary', 'Update detected')

                m += f"<b>{plabel}</b>\n"

                for line in summary.split('\n'):
                    line = line.strip()
                    if not line:
                        continue
                    # Skip type labels already in header
                    skip = ['Pricing Update', 'Rules Update', 'Content Update', 'Promo Detected', 'Update']
                    if line in skip:
                        continue
                    m += f"   {line}\n"
                m += "\n"

            # AI analysis
            ai = next((c.get('ai_analysis') for c in chs if c.get('ai_analysis')), None)
            if ai:
                m += f"🧠  <i>{ai[:250]}</i>\n\n"

            ts = chs[0].get('detected_at', '')[:16]
            m += f"🕐  {ts}\n"
            m += f"🔗  <a href='{lk}'>{fn}</a>\n\n"
            m += "━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            m += "⚡ <b>PropFirmTracker VIP</b>"

            msgs.append((m, [c['id'] for c in chs]))

        return msgs

    def _format_free(self, change):
        """Format a single change for free channel."""
        fn = self._fn(change['firm_slug'])
        ct = change.get('change_type', '')
        icon = {"pricing_change": "💰", "rules_change": "📋", "new_promo": "🎟", "scam_alert": "🚨"}.get(ct, "🔄")
        summary = change.get('summary', 'Update')

        m = f"{icon}  <b>{fn}</b>\n"
        m += "━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"

        for line in summary.split('\n'):
            line = line.strip()
            if line and line not in ['Pricing Update', 'Rules Update', 'Content Update', 'Promo Detected', 'Update']:
                m += f"   {line}\n"

        m += f"\n⏳  <i>VIP members got this {FREE_ALERT_DELAY_HOURS}h earlier</i>\n\n"
        m += "━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        m += "💎 Real-time alerts  ·  /premium\n"
        m += "🤖 @PropFirmTrackerBot"

        return m

    async def send_premium_alerts(self):
        if not self.bot or not self._ok(PREMIUM_CHANNEL_ID):
            return

        changes = get_unalerted_changes("premium")
        if not changes:
            return

        batch = changes[:self.MAX_PER]
        log_info(f"VIP: {len(batch)} alerts ({len(changes)} pending)", tag="ALERT")

        msgs = self._format_vip_grouped(batch)
        sent = 0
        for text, ids in msgs:
            ok = await self._send(PREMIUM_CHANNEL_ID, text)
            if ok:
                for i in ids:
                    mark_change_alerted(i, "premium")
                sent += 1
            else:
                if str(PREMIUM_CHANNEL_ID) in self._off:
                    for c in changes:
                        mark_change_alerted(c['id'], "premium")
                    break
            await asyncio.sleep(self.DELAY)

        log_info(f"VIP: {sent} msgs sent", tag="ALERT")

    async def send_free_alerts(self):
        if not self.bot or not self._ok(FREE_CHANNEL_ID):
            return

        changes = get_unalerted_changes("free")
        if not changes:
            return

        cutoff = datetime.now() - timedelta(hours=FREE_ALERT_DELAY_HOURS)
        sent = 0

        for c in changes[:self.MAX_PER]:
            try:
                det = datetime.fromisoformat(c['detected_at'])
            except:
                continue
            if det <= cutoff:
                msg = self._format_free(c)
                ok = await self._send(FREE_CHANNEL_ID, msg)
                if ok:
                    mark_change_alerted(c['id'], "free")
                    sent += 1
                else:
                    if str(FREE_CHANNEL_ID) in self._off:
                        for ch in changes:
                            mark_change_alerted(ch['id'], "free")
                        break
                await asyncio.sleep(self.DELAY)

        if sent:
            log_info(f"Free: {sent} alerts", tag="ALERT")

    async def send_promo_to_channel(self, promo, ch="premium"):
        cid = PREMIUM_CHANNEL_ID if ch == "premium" else FREE_CHANNEL_ID
        if not self.bot or not self._ok(cid):
            return

        fn = self._fn(promo['firm_slug'])
        lk = self._fl(promo['firm_slug'])

        m = f"🎟  <b>NEW PROMO — {fn}</b>\n"
        m += "━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        if promo.get('discount'):
            m += f"   💰  <b>{promo['discount']}</b>\n"
        if promo.get('promo_code'):
            m += f"   🔑  Code: <code>{promo['promo_code']}</code>\n"
        m += f"\n   🔗  <a href='{lk}'>Claim at {fn} →</a>\n\n"
        m += "━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        m += "⚡ <b>PropFirmTracker VIP</b>"

        await self._send(cid, m)
