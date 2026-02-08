"""
Alert Service V3.1 — Professional VIP alerts
Flood control + smart batching + beautiful formatting.
"""
import asyncio, re
from datetime import datetime, timedelta
from telegram.error import RetryAfter, BadRequest, Forbidden
from utils.logger import log_info, log_error, log_warn
from database import get_unalerted_changes, mark_change_alerted, get_active_promos
from config import FREE_CHANNEL_ID, PREMIUM_CHANNEL_ID, FREE_ALERT_DELAY_HOURS, PROP_FIRMS


class AlertService:
    MAX_PER_CYCLE = 15
    MSG_DELAY = 3.5
    # Group alerts for same firm into one message
    BATCH_SAME_FIRM = True

    def __init__(self, bot_app):
        self.bot = bot_app.bot if bot_app else None
        self._disabled = set()

    def set_bot(self, bot): self.bot = bot

    def _fn(self, slug): return PROP_FIRMS.get(slug, {}).get('name', slug.replace('_',' ').title())
    def _fl(self, slug): f=PROP_FIRMS.get(slug,{}); return f.get('affiliate_url', f.get('url','#'))

    def _ok(self, cid):
        if not cid: return False
        s=str(cid)
        return s not in self._disabled and "XXXX" not in s and s not in ("","0")

    async def _send(self, cid, text):
        try:
            await self.bot.send_message(chat_id=cid, text=text, parse_mode='HTML', disable_web_page_preview=True)
            return True
        except RetryAfter as e:
            w = e.retry_after + 3
            log_warn(f"⏳ Flood control — waiting {w}s", tag="ALERT")
            await asyncio.sleep(w)
            try:
                await self.bot.send_message(chat_id=cid, text=text, parse_mode='HTML', disable_web_page_preview=True)
                return True
            except Exception as e2: log_error(f"Retry failed: {e2}", tag="ALERT"); return False
        except (BadRequest, Forbidden) as e:
            if any(k in str(e).lower() for k in ['not found','kicked','blocked','deactivated']):
                log_warn(f"Channel {cid} inaccessible — disabling", tag="ALERT")
                self._disabled.add(str(cid))
            else: log_error(f"Send: {e}", tag="ALERT")
            return False
        except Exception as e: log_error(f"Send: {e}", tag="ALERT"); return False

    def _format_vip(self, changes):
        """Format changes for VIP channel — grouped by firm, professional look."""
        if not changes: return []
        messages = []

        if self.BATCH_SAME_FIRM:
            # Group by firm
            firms = {}
            for c in changes:
                slug = c['firm_slug']
                firms.setdefault(slug, []).append(c)

            for slug, firm_changes in firms.items():
                fn = self._fn(slug)
                lk = self._fl(slug)

                # Type icon
                types = set(c.get('change_type','') for c in firm_changes)
                if 'new_promo' in types: icon = "🎟️"
                elif 'pricing_change' in types: icon = "💰"
                elif 'rules_change' in types: icon = "📋"
                elif 'scam_alert' in types: icon = "🚨"
                else: icon = "🔄"

                msg = f"{icon} <b>{fn}</b>\n"
                msg += "─" * 22 + "\n\n"

                for c in firm_changes[:5]:  # Max 5 per firm
                    pt = c.get('page_type', '')
                    summary = c.get('summary', 'Update detected')

                    # Clean up summary — remove firm name prefix if present
                    summary = re.sub(rf'^{re.escape(fn)}\s*[-—|]\s*', '', summary)
                    summary = re.sub(r'^(?:💰|📋|🎟️|🔄)\s*(?:Pricing|Rules|Content|Promo)\s*(?:Update|Change)?\s*\|\s*', '', summary)

                    page_label = {"pricing":"💰 Pricing","rules":"📋 Rules","homepage":"🏠 Homepage","blog":"📰 Blog"}.get(pt, f"📄 {pt}")
                    msg += f"<b>{page_label}</b>\n"

                    # Parse multi-line summaries
                    for line in summary.split('\n'):
                        line = line.strip()
                        if line:
                            msg += f"  {line}\n"
                    msg += "\n"

                # AI analysis if available
                ai = firm_changes[0].get('ai_analysis')
                if ai: msg += f"🧠 <i>{ai[:200]}</i>\n\n"

                # Timestamp + link
                ts = firm_changes[0].get('detected_at','')[:16]
                msg += f"🕐 {ts}\n"
                msg += f"🔗 <a href='{lk}'>{fn}</a>\n"
                msg += "\n━━━━━━━━━━━━━━━━━━━━━\n"
                msg += "⚡ <b>PropFirmTracker VIP</b> — Real-time alerts"

                messages.append((msg, [c['id'] for c in firm_changes]))
        else:
            for c in changes:
                msg = self._format_single(c, premium=True)
                messages.append((msg, [c['id']]))

        return messages

    def _format_single(self, change, premium=True):
        """Format a single change alert."""
        fn = self._fn(change['firm_slug'])
        lk = self._fl(change['firm_slug'])
        ct = change.get('change_type','')

        icons = {"content_update":"🔄","pricing_change":"💰","rules_change":"📋","new_promo":"🎟️","scam_alert":"🚨"}
        icon = icons.get(ct, '🔔')

        msg = f"{icon} <b>{fn}</b>\n"
        msg += "─" * 22 + "\n\n"

        pt = change.get('page_type','')
        page_label = {"pricing":"💰 Pricing","rules":"📋 Rules","homepage":"🏠 Home","blog":"📰 Blog"}.get(pt, pt)
        msg += f"<b>{page_label}</b>\n"

        summary = change.get('summary', 'Change detected')
        summary = re.sub(rf'^{re.escape(fn)}\s*[-—|:]\s*', '', summary)
        for line in summary.split('\n'):
            if line.strip(): msg += f"  {line.strip()}\n"

        if change.get('ai_analysis'):
            msg += f"\n🧠 <i>{change['ai_analysis'][:200]}</i>\n"

        msg += f"\n🕐 {change.get('detected_at','')[:16]}\n"

        if premium:
            msg += f"🔗 <a href='{lk}'>{fn}</a>\n"
            msg += "\n━━━━━━━━━━━━━━━━━━━━━\n⚡ <b>PropFirmTracker VIP</b>"
        else:
            msg += f"\n⏳ <i>VIP members got this {FREE_ALERT_DELAY_HOURS}h ago</i>\n"
            msg += "💎 /premium for real-time alerts\n"
            msg += "\n━━━━━━━━━━━━━━━━━━━━━\n🤖 @PropFirmTrackerBot"

        return msg

    async def send_premium_alerts(self):
        if not self.bot or not self._ok(PREMIUM_CHANNEL_ID): return
        changes = get_unalerted_changes("premium")
        if not changes: return

        batch = changes[:self.MAX_PER_CYCLE]
        log_info(f"Sending {len(batch)} VIP alerts ({len(changes)} pending)...", tag="ALERT")

        messages = self._format_vip(batch)
        sent = 0
        for msg_text, change_ids in messages:
            ok = await self._send(PREMIUM_CHANNEL_ID, msg_text)
            if ok:
                for cid in change_ids: mark_change_alerted(cid, "premium")
                sent += 1
            else:
                if str(PREMIUM_CHANNEL_ID) in self._disabled:
                    for c in changes: mark_change_alerted(c['id'], "premium")
                    break
            await asyncio.sleep(self.MSG_DELAY)
        log_info(f"VIP alerts: {sent} messages sent ✓", tag="ALERT")

    async def send_free_alerts(self):
        if not self.bot or not self._ok(FREE_CHANNEL_ID): return
        changes = get_unalerted_changes("free")
        if not changes: return
        cutoff = datetime.now() - timedelta(hours=FREE_ALERT_DELAY_HOURS)
        sent = 0
        for c in changes[:self.MAX_PER_CYCLE]:
            if datetime.fromisoformat(c['detected_at']) <= cutoff:
                msg = self._format_single(c, premium=False)
                ok = await self._send(FREE_CHANNEL_ID, msg)
                if ok: mark_change_alerted(c['id'], "free"); sent += 1
                else:
                    if str(FREE_CHANNEL_ID) in self._disabled:
                        for ch in changes: mark_change_alerted(ch['id'], "free")
                        break
                await asyncio.sleep(self.MSG_DELAY)

    async def send_promo_to_channel(self, promo, ch="premium"):
        cid = PREMIUM_CHANNEL_ID if ch=="premium" else FREE_CHANNEL_ID
        if not self.bot or not self._ok(cid): return
        fn=self._fn(promo['firm_slug']); lk=self._fl(promo['firm_slug'])
        m = f"🎟️ <b>NEW PROMO — {fn}</b>\n"
        m += "─" * 22 + "\n\n"
        if promo.get('discount'): m += f"💰 <b>{promo['discount']}</b>\n"
        if promo.get('promo_code'): m += f"🔑 Code: <code>{promo['promo_code']}</code>\n"
        if promo.get('description'): m += f"📝 {promo['description']}\n"
        m += f"\n🔗 <a href='{lk}'>Claim at {fn} →</a>\n"
        m += "\n━━━━━━━━━━━━━━━━━━━━━\n⚡ <b>PropFirmTracker VIP</b>"
        await self._send(cid, m)
