"""
PropFirmTracker Bot - Alert Service
======================================
Manages sending alerts to free and premium channels.
Handles delay for free channel, formatting, and affiliate links.
"""

import asyncio
from datetime import datetime, timedelta
from utils.logger import log_info, log_error
from database import (
    get_unalerted_changes, mark_change_alerted,
    get_active_promos, get_all_premium_users
)
from config import (
    FREE_CHANNEL_ID, PREMIUM_CHANNEL_ID,
    FREE_ALERT_DELAY_HOURS, PROP_FIRMS
)


class AlertService:
    """Sends formatted alerts to Telegram channels."""

    def __init__(self, bot_app):
        self.bot = bot_app.bot if bot_app else None

    def set_bot(self, bot):
        """Set the bot instance (called after bot initialization)."""
        self.bot = bot

    def _get_affiliate_link(self, firm_slug):
        """Get the affiliate link for a firm."""
        firm = PROP_FIRMS.get(firm_slug, {})
        return firm.get("affiliate_url", firm.get("url", "#"))

    def _get_firm_name(self, firm_slug):
        """Get the display name for a firm."""
        firm = PROP_FIRMS.get(firm_slug, {})
        return firm.get("name", firm_slug.replace("_", " ").title())

    def format_change_alert(self, change, is_premium=True):
        """Format a change alert message."""
        firm_name = self._get_firm_name(change['firm_slug'])
        affiliate_link = self._get_affiliate_link(change['firm_slug'])

        # Emoji based on change type
        type_emojis = {
            "content_update": "🔄",
            "pricing_change": "💰",
            "rules_change": "📋",
            "new_promo": "🎟️",
            "scam_alert": "🚨",
            "trustpilot_drop": "📉",
        }
        emoji = type_emojis.get(change.get('change_type', ''), '🔔')

        # Build message
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
            msg += f"\n\n💎 Upgrade to Premium: /premium"

        msg += "\n\n━━━━━━━━━━━━━━━━━━━━━"
        msg += "\n🤖 @PropFirmTrackerBot"

        return msg

    def format_promo_alert(self, promo, is_premium=True):
        """Format a promo alert message."""
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

        msg += "\n\n━━━━━━━━━━━━━━━━━━━━━"
        msg += "\n🤖 @PropFirmTrackerBot"

        return msg

    def format_scam_alert(self, alert, is_premium=True):
        """Format a scam/warning alert."""
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

        msg += "\n\n━━━━━━━━━━━━━━━━━━━━━"
        msg += "\n🤖 @PropFirmTrackerBot"

        return msg

    async def send_premium_alerts(self):
        """Send all pending alerts to premium channel immediately."""
        if not self.bot:
            log_error("Bot not initialized — cannot send alerts", tag="ALERT")
            return

        changes = get_unalerted_changes("premium")
        if not changes:
            log_info("No new premium alerts to send", tag="ALERT")
            return

        log_info(f"Sending {len(changes)} alerts to premium channel...", tag="ALERT")

        for change in changes:
            try:
                msg = self.format_change_alert(change, is_premium=True)
                await self.bot.send_message(
                    chat_id=PREMIUM_CHANNEL_ID,
                    text=msg,
                    parse_mode='HTML',
                    disable_web_page_preview=True
                )
                mark_change_alerted(change['id'], "premium")
                log_info(f"✅ Premium alert sent: {change['firm_slug']} - {change['change_type']}", tag="ALERT")
                await asyncio.sleep(1)  # Rate limiting
            except Exception as e:
                log_error(f"Failed to send premium alert: {e}", tag="ALERT")

    async def send_free_alerts(self):
        """Send delayed alerts to free channel."""
        if not self.bot:
            return

        changes = get_unalerted_changes("free")
        if not changes:
            return

        delay_cutoff = datetime.now() - timedelta(hours=FREE_ALERT_DELAY_HOURS)

        for change in changes:
            detected = datetime.fromisoformat(change['detected_at'])
            if detected <= delay_cutoff:
                try:
                    msg = self.format_change_alert(change, is_premium=False)
                    await self.bot.send_message(
                        chat_id=FREE_CHANNEL_ID,
                        text=msg,
                        parse_mode='HTML',
                        disable_web_page_preview=True
                    )
                    mark_change_alerted(change['id'], "free")
                    log_info(f"✅ Free alert sent (delayed): {change['firm_slug']}", tag="ALERT")
                    await asyncio.sleep(1)
                except Exception as e:
                    log_error(f"Failed to send free alert: {e}", tag="ALERT")

    async def send_promo_to_channel(self, promo, channel_type="premium"):
        """Send a promo alert to a channel."""
        if not self.bot:
            return

        channel_id = PREMIUM_CHANNEL_ID if channel_type == "premium" else FREE_CHANNEL_ID
        is_premium = channel_type == "premium"

        try:
            msg = self.format_promo_alert(promo, is_premium=is_premium)
            await self.bot.send_message(
                chat_id=channel_id,
                text=msg,
                parse_mode='HTML',
                disable_web_page_preview=True
            )
            log_info(f"Promo alert sent to {channel_type} channel: {promo['firm_slug']}", tag="ALERT")
        except Exception as e:
            log_error(f"Failed to send promo alert: {e}", tag="ALERT")
