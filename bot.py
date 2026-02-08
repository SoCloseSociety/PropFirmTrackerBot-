"""
PropFirmTracker Bot - Main Bot
=================================
Telegram bot with free/premium tiers, referral system, and admin commands.
"""

import asyncio
import functools
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, BotCommand
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes
)
from utils.logger import log_info, log_error, log_warn
from database import (
    get_or_create_user, is_premium, activate_premium, get_referral_code,
    get_referral_count, get_total_referrals, check_and_reward_referrals,
    get_active_promos, get_recent_changes, get_latest_trustpilot_scores,
    get_user_stats
)
from config import (
    TELEGRAM_BOT_TOKEN, ADMIN_USER_IDS, PROP_FIRMS,
    PREMIUM_PRICE_MONTHLY, PREMIUM_PRICE_YEARLY,
    REFERRALS_NEEDED, REFERRAL_REWARD_DAYS,
    CRYPTO_WALLET_USDT_TRC20, STRIPE_API_KEY,
    PREMIUM_CHANNEL_ID
)


# ══════════════════════════════════════════════════════════════
# HELPER FUNCTIONS
# ══════════════════════════════════════════════════════════════

def is_admin(user_id):
    """Check if user is admin."""
    return int(user_id) in ADMIN_USER_IDS


def premium_required(func):
    """Decorator to restrict commands to premium users."""
    @functools.wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        if not is_premium(user_id) and not is_admin(user_id):
            keyboard = [[InlineKeyboardButton("💎 Upgrade to Premium", callback_data="premium_info")]]
            await update.message.reply_text(
                "🔒 <b>Premium Feature</b>\n\n"
                "This command is available for premium members only.\n\n"
                f"💰 Only ${PREMIUM_PRICE_MONTHLY}/month for:\n"
                "• ⚡ Real-time alerts (no 24h delay)\n"
                "• 🔍 Detailed rule comparisons\n"
                "• 🧠 AI-powered analysis\n"
                "• 🚨 Instant scam warnings\n"
                "• 📊 Full change history\n\n"
                "Or invite 3 friends and get 1 week FREE! → /referral",
                parse_mode='HTML',
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            return
        return await func(update, context)
    return wrapper


def admin_required(func):
    """Decorator for admin-only commands with feedback."""
    @functools.wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        if not is_admin(user_id):
            await update.message.reply_text("⛔ Admin only.")
            return
        return await func(update, context)
    return wrapper


def get_bot_name(context):
    """Get bot username for referral links."""
    return context.bot.username


# ══════════════════════════════════════════════════════════════
# /start — Welcome + Referral handling
# ══════════════════════════════════════════════════════════════

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command with optional referral code."""
    user = update.effective_user
    referral_code = None

    # Check for referral code: /start REF_XXXXXX
    if context.args and context.args[0].startswith("REF_"):
        referral_code = context.args[0].replace("REF_", "")
        log_info(f"User {user.id} joined via referral: {referral_code}", tag="REF")

    # Register user
    db_user = get_or_create_user(
        user_id=user.id,
        username=user.username,
        first_name=user.first_name,
        referred_by_code=referral_code
    )

    # If referred, check and reward the referrer
    if referral_code and db_user.get('referred_by'):
        rewarded = check_and_reward_referrals(
            db_user['referred_by'], REFERRALS_NEEDED, REFERRAL_REWARD_DAYS
        )
        if rewarded:
            try:
                await context.bot.send_message(
                    chat_id=db_user['referred_by'],
                    text=(
                        f"🎉 <b>Referral Reward Unlocked!</b>\n\n"
                        f"Your friend just joined! You've referred {REFERRALS_NEEDED} people "
                        f"and earned <b>{REFERRAL_REWARD_DAYS} days of FREE Premium!</b> 🚀\n\n"
                        f"Keep sharing to earn more → /referral"
                    ),
                    parse_mode='HTML'
                )
            except Exception:
                pass

    bot_name = get_bot_name(context)

    keyboard = [
        [
            InlineKeyboardButton("📊 Firms List", callback_data="firms_list"),
            InlineKeyboardButton("🎟️ Active Promos", callback_data="promos"),
        ],
        [
            InlineKeyboardButton("💎 Premium", callback_data="premium_info"),
            InlineKeyboardButton("👥 Earn Free Days", callback_data="referral_info"),
        ],
        [
            InlineKeyboardButton("📢 Join Free Channel", url=f"https://t.me/PropFirmTrackerFree"),
        ],
    ]

    welcome = (
        f"👋 <b>Welcome to PropFirmTracker, {user.first_name}!</b>\n\n"
        f"🤖 I monitor <b>{len(PROP_FIRMS)}+ prop firms</b> 24/7 and alert you about:\n\n"
        f"🔄 Rule changes (drawdown, profit targets, etc.)\n"
        f"💰 Pricing updates\n"
        f"🎟️ Promo codes & discounts\n"
        f"🚨 Scam warnings & Trustpilot drops\n"
        f"📊 Reddit community sentiment\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"<b>🆓 Free:</b> Alerts with 24h delay + basic commands\n"
        f"<b>💎 Premium:</b> Real-time alerts + AI analysis + full history\n\n"
        f"💡 <b>Get {REFERRAL_REWARD_DAYS} days FREE Premium</b> — invite {REFERRALS_NEEDED} friends!\n"
        f"→ /referral\n\n"
        f"Type /help to see all commands."
    )

    await update.message.reply_text(
        welcome,
        parse_mode='HTML',
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    log_info(f"User started bot: {user.id} (@{user.username})", tag="BOT")


# ══════════════════════════════════════════════════════════════
# /help — Command list
# ══════════════════════════════════════════════════════════════

async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show available commands."""
    msg = (
        "📋 <b>Available Commands</b>\n\n"
        "<b>🆓 Free Commands:</b>\n"
        "/firms — List all monitored prop firms\n"
        "/promos — Show active promo codes\n"
        "/scores — Trustpilot scores overview\n"
        "/compare [firm1] [firm2] — Basic comparison\n"
        "/referral — Your referral link & stats\n"
        "/premium — Upgrade to premium\n"
        "/status — Your account status\n\n"
        "<b>💎 Premium Commands:</b>\n"
        "/alerts — Your alert preferences\n"
        "/rules [firm] — Detailed rules for a firm\n"
        "/history [firm] — Change history\n"
        "/scams — Recent scam warnings\n"
        "/analysis [firm] — AI-powered analysis\n"
        "/payout [firm] — Payout reliability info\n\n"
        "<b>ℹ️ Other:</b>\n"
        "/help — This message\n"
        "/support — Contact support\n"
    )

    # Show admin commands to admins
    if is_admin(update.effective_user.id):
        msg += (
            "\n<b>🔐 Admin Commands:</b>\n"
            "/admin — Admin dashboard\n"
            "/stats — Bot statistics\n"
            "/scrape — Force manual scrape\n"
            "/activate [user_id] [days] — Give premium\n"
            "/addvip [user_id] [days] — Premium + channel invite\n"
            "/broadcast [message] — Send to all users\n"
        )

    await update.message.reply_text(msg, parse_mode='HTML')


# ══════════════════════════════════════════════════════════════
# /firms — List all monitored firms
# ══════════════════════════════════════════════════════════════

async def cmd_firms(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show all monitored prop firms with Trustpilot scores."""
    scores = get_latest_trustpilot_scores()

    msg = "📊 <b>Monitored Prop Firms</b>\n\n"

    for slug, cfg in PROP_FIRMS.items():
        score_data = scores.get(slug)
        score_str = f"⭐ {score_data['score']:.1f}/5" if score_data and score_data.get('score') else "⭐ N/A"
        reviews_str = f"({score_data['review_count']} reviews)" if score_data and score_data.get('review_count') else ""

        msg += f"• <b>{cfg['name']}</b> — {score_str} {reviews_str}\n"

    msg += f"\n📈 <b>{len(PROP_FIRMS)} firms</b> monitored 24/7\n"
    msg += "\n🔍 Use /compare [firm1] [firm2] to compare\n"
    msg += "🎟️ Use /promos to see active discounts"

    await update.message.reply_text(msg, parse_mode='HTML')


# ══════════════════════════════════════════════════════════════
# /promos — Active promo codes
# ══════════════════════════════════════════════════════════════

async def cmd_promos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show active promo codes."""
    promos = get_active_promos()

    if not promos:
        await update.message.reply_text(
            "🎟️ <b>Active Promos</b>\n\n"
            "No active promos detected right now.\n"
            "I'll alert you as soon as one appears!\n\n"
            "💎 Premium members get promo alerts in real-time → /premium",
            parse_mode='HTML'
        )
        return

    msg = "🎟️ <b>Active Promo Codes</b>\n\n"

    for promo in promos[:10]:
        firm_name = PROP_FIRMS.get(promo['firm_slug'], {}).get('name', promo['firm_slug'])
        affiliate = PROP_FIRMS.get(promo['firm_slug'], {}).get('affiliate_url', '#')

        msg += f"🏷️ <b>{firm_name}</b>\n"
        if promo.get('promo_code'):
            msg += f"   Code: <code>{promo['promo_code']}</code>\n"
        if promo.get('discount'):
            msg += f"   Discount: {promo['discount']}\n"
        msg += f"   <a href='{affiliate}'>Claim →</a>\n\n"

    msg += "━━━━━━━━━━━━━━━━━━━━━\n"
    msg += "💎 Premium = instant promo alerts → /premium"

    await update.message.reply_text(msg, parse_mode='HTML', disable_web_page_preview=True)


# ══════════════════════════════════════════════════════════════
# /scores — Trustpilot overview
# ══════════════════════════════════════════════════════════════

async def cmd_scores(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show Trustpilot scores for all firms."""
    scores = get_latest_trustpilot_scores()

    if not scores:
        await update.message.reply_text(
            "⭐ <b>Trustpilot Scores</b>\n\nScores are being collected. Check back soon!",
            parse_mode='HTML'
        )
        return

    # Sort by score descending
    sorted_scores = sorted(scores.items(), key=lambda x: x[1].get('score', 0), reverse=True)

    msg = "⭐ <b>Trustpilot Scores — Prop Firms</b>\n\n"

    for i, (slug, data) in enumerate(sorted_scores, 1):
        firm_name = PROP_FIRMS.get(slug, {}).get('name', slug)
        score = data.get('score', 0)
        reviews = data.get('review_count', 0)

        if score >= 4.5:
            emoji = "🟢"
        elif score >= 3.5:
            emoji = "🟡"
        elif score >= 2.5:
            emoji = "🟠"
        else:
            emoji = "🔴"

        msg += f"{emoji} {i}. <b>{firm_name}</b> — {score:.1f}/5 ({reviews} reviews)\n"

    msg += "\n💎 Premium: Get alerts when scores drop → /premium"

    await update.message.reply_text(msg, parse_mode='HTML')


# ══════════════════════════════════════════════════════════════
# /compare — Compare two firms
# ══════════════════════════════════════════════════════════════

async def cmd_compare(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Compare two prop firms."""
    if len(context.args) < 2:
        firms_list = ", ".join([f"<code>{slug}</code>" for slug in PROP_FIRMS.keys()])
        await update.message.reply_text(
            f"🔍 <b>Compare Prop Firms</b>\n\n"
            f"Usage: /compare [firm1] [firm2]\n\n"
            f"Available firms:\n{firms_list}\n\n"
            f"Example: <code>/compare ftmo fundednext</code>",
            parse_mode='HTML'
        )
        return

    firm1_slug = context.args[0].lower()
    firm2_slug = context.args[1].lower()

    firm1 = PROP_FIRMS.get(firm1_slug)
    firm2 = PROP_FIRMS.get(firm2_slug)

    if not firm1 or not firm2:
        await update.message.reply_text("❌ One or both firm names not found. Use /firms to see available firms.")
        return

    scores = get_latest_trustpilot_scores()
    s1 = scores.get(firm1_slug, {})
    s2 = scores.get(firm2_slug, {})

    msg = f"🔍 <b>{firm1['name']} vs {firm2['name']}</b>\n\n"

    score1 = f"{s1.get('score', 'N/A')}/5" if s1.get('score') else "N/A"
    score2 = f"{s2.get('score', 'N/A')}/5" if s2.get('score') else "N/A"
    msg += f"⭐ Trustpilot: <b>{score1}</b> vs <b>{score2}</b>\n"
    msg += f"🏢 Commission: {firm1.get('affiliate_commission', '?')} vs {firm2.get('affiliate_commission', '?')}\n"

    msg += f"\n🔗 <a href='{firm1.get('affiliate_url', firm1.get('url', '#'))}'>{firm1['name']}</a>"
    msg += f" | <a href='{firm2.get('affiliate_url', firm2.get('url', '#'))}'>{firm2['name']}</a>\n"

    if is_premium(update.effective_user.id):
        msg += "\n🧠 Use /analysis [firm] for AI-powered deep analysis"
    else:
        msg += "\n💎 Premium: AI-powered detailed comparison → /premium"

    await update.message.reply_text(msg, parse_mode='HTML', disable_web_page_preview=True)


# ══════════════════════════════════════════════════════════════
# /history — Change history (Premium)
# ══════════════════════════════════════════════════════════════

@premium_required
async def cmd_history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show change history for a firm."""
    firm_slug = context.args[0].lower() if context.args else None
    changes = get_recent_changes(limit=10, firm_slug=firm_slug)

    if not changes:
        await update.message.reply_text(
            "📜 <b>Change History</b>\n\nNo changes recorded yet. I'm monitoring!",
            parse_mode='HTML'
        )
        return

    msg = "📜 <b>Recent Changes</b>\n\n"

    for change in changes:
        firm_name = PROP_FIRMS.get(change['firm_slug'], {}).get('name', change['firm_slug'])
        emoji = "🔄"
        if "scam" in change.get('change_type', ''):
            emoji = "🚨"
        elif "promo" in change.get('change_type', ''):
            emoji = "🎟️"
        elif "pricing" in change.get('change_type', ''):
            emoji = "💰"

        msg += f"{emoji} <b>{firm_name}</b> — {change.get('page_type', '?')}\n"
        msg += f"   {change.get('summary', 'Change detected')}\n"
        msg += f"   📅 {change.get('detected_at', '')[:16]}\n\n"

    await update.message.reply_text(msg, parse_mode='HTML')


# ══════════════════════════════════════════════════════════════
# /scams — Scam alerts (Premium)
# ══════════════════════════════════════════════════════════════

@premium_required
async def cmd_scams(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show recent scam warnings."""
    from database import get_connection
    conn = get_connection()
    alerts = conn.execute(
        "SELECT * FROM scam_alerts ORDER BY detected_at DESC LIMIT 10"
    ).fetchall()
    conn.close()

    if not alerts:
        await update.message.reply_text(
            "🚨 <b>Scam Alerts</b>\n\nNo scam alerts right now. I'm watching!",
            parse_mode='HTML'
        )
        return

    msg = "🚨 <b>Recent Scam Alerts & Warnings</b>\n\n"

    for alert in alerts:
        firm_name = PROP_FIRMS.get(alert['firm_slug'], {}).get('name', alert['firm_slug'])
        sev = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(alert['severity'], "⚪")

        msg += f"{sev} <b>{firm_name}</b> — {alert['alert_type'].replace('_', ' ').title()}\n"
        msg += f"   {alert['description'][:100]}\n"
        msg += f"   📅 {alert['detected_at'][:16]}\n\n"

    msg += "\n⚡ Always DYOR before choosing a prop firm."

    await update.message.reply_text(msg, parse_mode='HTML')


# ══════════════════════════════════════════════════════════════
# /referral — Referral program
# ══════════════════════════════════════════════════════════════

async def cmd_referral(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show referral info and link."""
    user_id = update.effective_user.id
    get_or_create_user(user_id, update.effective_user.username, update.effective_user.first_name)

    ref_code = get_referral_code(user_id)
    total = get_total_referrals(user_id)
    unrewarded = get_referral_count(user_id)
    remaining = max(0, REFERRALS_NEEDED - unrewarded)

    bot_name = get_bot_name(context)
    ref_link = f"https://t.me/{bot_name}?start=REF_{ref_code}"

    filled = min(unrewarded, REFERRALS_NEEDED)
    progress = "🟢" * filled + "⚪" * (REFERRALS_NEEDED - filled)

    msg = (
        f"👥 <b>Referral Program</b>\n\n"
        f"🎁 Invite <b>{REFERRALS_NEEDED} friends</b> → Get <b>{REFERRAL_REWARD_DAYS} days FREE Premium!</b>\n\n"
        f"📊 <b>Your Stats:</b>\n"
        f"   Total referrals: <b>{total}</b>\n"
        f"   Current progress: {progress} ({unrewarded}/{REFERRALS_NEEDED})\n"
    )

    if remaining > 0:
        msg += f"   📍 <b>{remaining} more</b> to unlock reward!\n"
    else:
        msg += f"   🎉 <b>Reward available!</b>\n"

    msg += (
        f"\n🔗 <b>Your Referral Link:</b>\n"
        f"<code>{ref_link}</code>\n\n"
        f"📤 Share this link — when {REFERRALS_NEEDED} friends join, "
        f"you get {REFERRAL_REWARD_DAYS} days premium!\n"
        f"You can earn unlimited rewards! 🔄"
    )

    keyboard = [[
        InlineKeyboardButton("📤 Share Link", url=f"https://t.me/share/url?url={ref_link}&text=Track%20prop%20firm%20changes%2C%20promos%20and%20scam%20alerts%20in%20real-time!")
    ]]

    await update.message.reply_text(
        msg,
        parse_mode='HTML',
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


# ══════════════════════════════════════════════════════════════
# /premium — Subscription info & payment
# ══════════════════════════════════════════════════════════════

async def cmd_premium(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show premium subscription options."""
    user_id = update.effective_user.id
    user_is_premium = is_premium(user_id)

    if user_is_premium:
        from database import get_connection
        conn = get_connection()
        user = conn.execute("SELECT premium_expires_at FROM users WHERE user_id = ?", (user_id,)).fetchone()
        conn.close()
        expires = user['premium_expires_at'][:10] if user and user['premium_expires_at'] else "N/A"

        await update.message.reply_text(
            f"💎 <b>You're a Premium Member!</b>\n\n"
            f"✅ Subscription active until: <b>{expires}</b>\n\n"
            f"Enjoy all premium features:\n"
            f"• ⚡ Real-time alerts\n"
            f"• 🧠 AI analysis\n"
            f"• 📜 Full change history\n"
            f"• 🚨 Instant scam warnings\n\n"
            f"👥 Extend for free with referrals → /referral",
            parse_mode='HTML'
        )
        return

    msg = (
        f"💎 <b>PropFirmTracker Premium</b>\n\n"
        f"<b>What you get:</b>\n"
        f"⚡ Real-time alerts (no 24h delay)\n"
        f"🧠 AI-powered change analysis\n"
        f"📜 Full change history per firm\n"
        f"🚨 Instant scam & risk warnings\n"
        f"🔍 Detailed rule comparisons\n"
        f"📊 Payout reliability data\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"💰 <b>Pricing:</b>\n"
        f"   Monthly: <b>${PREMIUM_PRICE_MONTHLY}</b>/month\n"
        f"   Yearly:  <b>${PREMIUM_PRICE_YEARLY}</b>/year (save 33%!)\n\n"
        f"🆓 <b>Or get it FREE:</b>\n"
        f"   Invite {REFERRALS_NEEDED} friends → {REFERRAL_REWARD_DAYS} days premium!\n"
        f"   → /referral\n\n"
        f"<b>Payment methods:</b>"
    )

    keyboard = []

    if STRIPE_API_KEY:
        keyboard.append([
            InlineKeyboardButton("💳 Pay with Card — Monthly", callback_data="pay_stripe_monthly"),
            InlineKeyboardButton("💳 Pay with Card — Yearly", callback_data="pay_stripe_yearly"),
        ])

    keyboard.append([
        InlineKeyboardButton("₿ Pay with Crypto (USDT)", callback_data="pay_crypto"),
    ])
    keyboard.append([
        InlineKeyboardButton("⭐ Pay with Telegram Stars", callback_data="pay_stars"),
    ])
    keyboard.append([
        InlineKeyboardButton("🆓 Earn Free Premium (Referral)", callback_data="referral_info"),
    ])

    await update.message.reply_text(msg, parse_mode='HTML', reply_markup=InlineKeyboardMarkup(keyboard))


# ══════════════════════════════════════════════════════════════
# /status — User account status
# ══════════════════════════════════════════════════════════════

async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show user account status."""
    user_id = update.effective_user.id
    db_user = get_or_create_user(user_id, update.effective_user.username, update.effective_user.first_name)

    premium = is_premium(user_id)
    admin = is_admin(user_id)

    if admin and premium:
        status = "👑 Admin + Premium"
    elif admin:
        status = "👑 Admin"
    elif premium:
        status = "💎 Premium"
    else:
        status = "🆓 Free"

    expires = db_user.get('premium_expires_at', 'N/A')
    if expires and expires != 'N/A':
        expires = expires[:10]
    total_refs = get_total_referrals(user_id)
    ref_code = db_user.get('referral_code', 'N/A')

    msg = (
        f"👤 <b>Your Account</b>\n\n"
        f"🆔 ID: <code>{user_id}</code>\n"
        f"📊 Status: <b>{status}</b>\n"
        f"📅 Premium expires: {expires}\n"
        f"👥 Total referrals: {total_refs}\n"
        f"🔑 Referral code: <code>{ref_code}</code>\n"
        f"📅 Joined: {db_user.get('joined_at', 'N/A')[:10]}\n"
    )

    if admin:
        msg += (
            f"\n🔐 <b>Admin Panel</b>\n"
            f"  ADMIN_USER_IDS: {ADMIN_USER_IDS}\n"
            f"  PREMIUM_CHANNEL: {PREMIUM_CHANNEL_ID or 'Not set'}\n"
            f"  Type /admin for admin commands\n"
        )

    await update.message.reply_text(msg, parse_mode='HTML')


# ══════════════════════════════════════════════════════════════
# CALLBACK QUERY HANDLER (button clicks)
# ══════════════════════════════════════════════════════════════

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle inline button callbacks."""
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "firms_list":
        scores = get_latest_trustpilot_scores()
        msg = "📊 <b>Monitored Firms</b>\n\n"
        for slug, cfg in PROP_FIRMS.items():
            s = scores.get(slug, {})
            score_str = f"⭐{s.get('score', 0):.1f}" if s.get('score') else "⭐N/A"
            msg += f"• <b>{cfg['name']}</b> {score_str}\n"
        msg += "\nUse /compare [firm1] [firm2] to compare"
        await query.edit_message_text(msg, parse_mode='HTML')

    elif data == "promos":
        promos = get_active_promos()
        if promos:
            msg = "🎟️ <b>Active Promos</b>\n\n"
            for p in promos[:5]:
                fn = PROP_FIRMS.get(p['firm_slug'], {}).get('name', p['firm_slug'])
                msg += f"• <b>{fn}</b>: <code>{p.get('promo_code', '?')}</code> — {p.get('discount', '?')}\n"
        else:
            msg = "🎟️ No active promos right now. Stay tuned!"
        await query.edit_message_text(msg, parse_mode='HTML')

    elif data == "premium_info":
        msg = (
            f"💎 <b>Premium — ${PREMIUM_PRICE_MONTHLY}/mo</b>\n\n"
            f"⚡ Real-time alerts\n"
            f"🧠 AI analysis\n"
            f"📜 Full history\n"
            f"🚨 Instant scam alerts\n\n"
            f"Use /premium to subscribe\n"
            f"Or /referral for FREE access!"
        )
        await query.edit_message_text(msg, parse_mode='HTML')

    elif data == "referral_info":
        ref_code = get_referral_code(query.from_user.id)
        bot_name = get_bot_name(context)
        link = f"https://t.me/{bot_name}?start=REF_{ref_code}"
        msg = (
            f"👥 <b>Earn Free Premium!</b>\n\n"
            f"Invite {REFERRALS_NEEDED} friends → {REFERRAL_REWARD_DAYS} days FREE\n\n"
            f"Your link:\n<code>{link}</code>\n\n"
            f"Use /referral for full stats."
        )
        await query.edit_message_text(msg, parse_mode='HTML')

    elif data == "pay_crypto":
        msg = (
            f"₿ <b>Pay with Crypto</b>\n\n"
            f"Send <b>${PREMIUM_PRICE_MONTHLY} USDT (TRC20)</b> to:\n\n"
            f"<code>{CRYPTO_WALLET_USDT_TRC20}</code>\n\n"
            f"After payment, send the TX hash to @PropFirmTrackerSupport\n"
            f"Your premium will be activated within 1 hour.\n\n"
            f"For yearly (${PREMIUM_PRICE_YEARLY}), same address."
        )
        await query.edit_message_text(msg, parse_mode='HTML')

    elif data == "pay_stars":
        msg = (
            f"⭐ <b>Pay with Telegram Stars</b>\n\n"
            f"Coming soon! In the meantime, you can:\n\n"
            f"💳 Pay with card → /premium\n"
            f"₿ Pay with crypto\n"
            f"🆓 Invite friends → /referral"
        )
        await query.edit_message_text(msg, parse_mode='HTML')

    elif data in ("pay_stripe_monthly", "pay_stripe_yearly"):
        msg = (
            f"💳 <b>Card Payment</b>\n\n"
            f"Contact @PropFirmTrackerSupport to receive your payment link.\n"
            f"Or pay with crypto for instant activation!"
        )
        await query.edit_message_text(msg, parse_mode='HTML')


# ══════════════════════════════════════════════════════════════
# ADMIN COMMANDS
# ══════════════════════════════════════════════════════════════

@admin_required
async def cmd_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin: Show admin dashboard with all commands."""
    stats = get_user_stats()
    from database import get_connection
    conn = get_connection()
    total_changes = conn.execute("SELECT COUNT(*) as c FROM changes").fetchone()['c']
    total_promos = conn.execute("SELECT COUNT(*) as c FROM promos WHERE is_active = 1").fetchone()['c']
    conn.close()

    msg = (
        f"👑 <b>Admin Dashboard</b>\n\n"
        f"👥 Users: {stats['total']} (💎 {stats['premium']} premium)\n"
        f"📈 Changes: {total_changes} | Promos: {total_promos}\n\n"
        f"<b>🔐 Admin Commands:</b>\n\n"
        f"/stats — Full statistics\n"
        f"/scrape — Force manual scrape now\n"
        f"/activate <code>[user_id] [days]</code> — Give premium\n"
        f"/addvip <code>[user_id] [days]</code> — Premium + invite link\n"
        f"/broadcast <code>[message]</code> — Send to all users\n\n"
        f"<b>💡 Examples:</b>\n"
        f"<code>/activate 123456789 30</code>\n"
        f"<code>/addvip 123456789 90</code>\n"
        f"<code>/broadcast 🎉 New feature! Check /promos</code>\n"
    )

    await update.message.reply_text(msg, parse_mode='HTML')


@admin_required
async def cmd_admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin: Show bot statistics."""
    stats = get_user_stats()
    from database import get_connection
    conn = get_connection()
    total_changes = conn.execute("SELECT COUNT(*) as c FROM changes").fetchone()['c']
    total_promos = conn.execute("SELECT COUNT(*) as c FROM promos WHERE is_active = 1").fetchone()['c']
    total_scam = conn.execute("SELECT COUNT(*) as c FROM scam_alerts").fetchone()['c']
    conn.close()

    msg = (
        f"📊 <b>Admin Dashboard</b>\n\n"
        f"👥 <b>Users:</b>\n"
        f"   Total: {stats['total']}\n"
        f"   Premium: {stats['premium']}\n"
        f"   New today: {stats['today_new']}\n\n"
        f"📈 <b>Data:</b>\n"
        f"   Changes detected: {total_changes}\n"
        f"   Active promos: {total_promos}\n"
        f"   Scam alerts: {total_scam}\n\n"
        f"💰 <b>Revenue (est):</b>\n"
        f"   MRR: ~${stats['premium'] * PREMIUM_PRICE_MONTHLY:.0f}"
    )

    await update.message.reply_text(msg, parse_mode='HTML')


@admin_required
async def cmd_admin_activate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin: Manually activate premium for a user."""
    if len(context.args) < 1:
        await update.message.reply_text(
            "Usage: /activate <code>[user_id]</code> <code>[days=30]</code>\n\n"
            "Example: <code>/activate 123456789 30</code>",
            parse_mode='HTML'
        )
        return

    try:
        target_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("❌ Invalid user ID. Must be a number.")
        return

    days = int(context.args[1]) if len(context.args) > 1 else 30

    # Make sure user exists in DB
    get_or_create_user(target_id)

    activate_premium(target_id, days=days, reason="admin_manual")
    await update.message.reply_text(
        f"✅ <b>Premium activated!</b>\n\n"
        f"👤 User: <code>{target_id}</code>\n"
        f"📅 Duration: {days} days\n"
        f"💎 Status: Premium active",
        parse_mode='HTML'
    )
    log_info(f"Admin activated premium: user {target_id} for {days} days", tag="PAY")


@admin_required
async def cmd_admin_addvip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin: Activate premium AND send invite link to premium channel."""
    if len(context.args) < 1:
        await update.message.reply_text(
            "🎟️ <b>Add VIP Member</b>\n\n"
            "Usage: /addvip <code>[user_id]</code> <code>[days=30]</code>\n\n"
            "This will:\n"
            "1. Activate premium for the user\n"
            "2. Send them an invite link to the VIP channel\n\n"
            "Example: <code>/addvip 123456789 90</code>",
            parse_mode='HTML'
        )
        return

    try:
        target_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("❌ Invalid user ID. Must be a number.")
        return

    days = int(context.args[1]) if len(context.args) > 1 else 30

    # Ensure user exists
    get_or_create_user(target_id)

    # 1. Activate premium
    activate_premium(target_id, days=days, reason="admin_vip_gift")

    # 2. Try to create invite link and send to user
    invite_link = None
    if PREMIUM_CHANNEL_ID:
        try:
            link_obj = await context.bot.create_chat_invite_link(
                chat_id=PREMIUM_CHANNEL_ID,
                member_limit=1,
                name=f"VIP-{target_id}"
            )
            invite_link = link_obj.invite_link
        except Exception as e:
            log_error(f"Failed to create invite link: {e}", tag="ADMIN")

    # 3. Notify the user
    try:
        msg = (
            f"🎉 <b>Congratulations!</b>\n\n"
            f"You've been granted <b>{days} days of Premium</b> access! 💎\n\n"
            f"You now get:\n"
            f"⚡ Real-time alerts (no delay)\n"
            f"🧠 AI-powered analysis\n"
            f"🚨 Instant scam warnings\n"
            f"📜 Full change history\n"
        )
        if invite_link:
            msg += f"\n🔗 <b>Join the VIP Channel:</b>\n{invite_link}\n"
        msg += f"\nEnjoy! 🚀"

        await context.bot.send_message(
            chat_id=target_id,
            text=msg,
            parse_mode='HTML'
        )
        user_notified = True
    except Exception as e:
        user_notified = False
        log_error(f"Failed to notify user {target_id}: {e}", tag="ADMIN")

    # 4. Confirm to admin
    result_msg = (
        f"✅ <b>VIP Added!</b>\n\n"
        f"👤 User: <code>{target_id}</code>\n"
        f"📅 Duration: {days} days\n"
        f"💎 Premium: ✅\n"
        f"🔗 Invite link: {'✅ Sent' if invite_link else '❌ Could not create (check channel ID)'}\n"
        f"📨 User notified: {'✅' if user_notified else '❌ (user may not have started bot)'}"
    )

    await update.message.reply_text(result_msg, parse_mode='HTML')
    log_info(f"Admin added VIP: user {target_id} for {days} days", tag="PAY")


@admin_required
async def cmd_admin_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin: Broadcast a message to all users."""
    if not context.args:
        await update.message.reply_text(
            "Usage: /broadcast <code>[message]</code>\n\n"
            "Supports HTML formatting.",
            parse_mode='HTML'
        )
        return

    message = " ".join(context.args)
    from database import get_connection
    conn = get_connection()
    users = conn.execute("SELECT user_id FROM users WHERE is_banned = 0").fetchall()
    conn.close()

    await update.message.reply_text(f"📢 Broadcasting to {len(users)} users...")

    sent = 0
    failed = 0
    for user in users:
        try:
            await context.bot.send_message(
                chat_id=user['user_id'],
                text=message,
                parse_mode='HTML'
            )
            sent += 1
            await asyncio.sleep(0.05)
        except Exception:
            failed += 1

    await update.message.reply_text(f"📢 Broadcast done: ✅ {sent} delivered, ❌ {failed} failed")


@admin_required
async def cmd_admin_scrape(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin: Trigger manual scrape."""
    await update.message.reply_text("🔍 Starting manual scrape... I'll report when done.")
    log_info("Admin triggered manual scrape", tag="SCRAPE")

    from scrapers import PropFirmScraper, RedditScraper, TrustpilotScraper

    results = []
    try:
        pf = PropFirmScraper()
        r = pf.scrape_all()
        results.append(f"✅ Firms: {r['scraped']} pages, {r['changes']} changes, {r['promos']} promos, {r['errors']} errors")
    except Exception as e:
        results.append(f"❌ Firms: {e}")

    try:
        rs = RedditScraper()
        r = rs.scrape_all()
        results.append(f"{'✅' if r['errors'] == 0 else '⚠️'} Reddit: {r['posts_found']} posts, {r['mentions']} mentions, {r['errors']} errors")
    except Exception as e:
        results.append(f"❌ Reddit: {e}")

    try:
        ts = TrustpilotScraper()
        r = ts.scrape_all()
        results.append(f"{'✅' if r['errors'] < 5 else '⚠️'} Trustpilot: {r['scraped']} scores, {r['errors']} errors")
    except Exception as e:
        results.append(f"❌ Trustpilot: {e}")

    await update.message.reply_text(
        "📊 <b>Scrape Complete</b>\n\n" + "\n".join(results),
        parse_mode='HTML'
    )


# ══════════════════════════════════════════════════════════════
# /support — Contact support
# ══════════════════════════════════════════════════════════════

async def cmd_support(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show support contact info."""
    await update.message.reply_text(
        "🆘 <b>Support</b>\n\n"
        "For questions, payment issues, or bug reports:\n\n"
        "📧 Contact: @PropFirmTrackerSupport\n"
        "📢 Channel: @PropFirmTrackerFree\n\n"
        "We typically respond within a few hours.",
        parse_mode='HTML'
    )


# ══════════════════════════════════════════════════════════════
# ERROR HANDLER
# ══════════════════════════════════════════════════════════════

async def error_handler(update, context):
    """Handle errors."""
    log_error(f"Bot error: {context.error}", tag="ERROR")


# ══════════════════════════════════════════════════════════════
# BOT SETUP
# ══════════════════════════════════════════════════════════════

async def post_init(application):
    """Set bot commands after initialization."""
    commands = [
        BotCommand("start", "Start the bot"),
        BotCommand("help", "Show all commands"),
        BotCommand("firms", "List monitored prop firms"),
        BotCommand("promos", "Active promo codes"),
        BotCommand("scores", "Trustpilot scores"),
        BotCommand("compare", "Compare two firms"),
        BotCommand("referral", "Your referral link"),
        BotCommand("premium", "Upgrade to premium"),
        BotCommand("status", "Your account status"),
        BotCommand("history", "Change history (Premium)"),
        BotCommand("scams", "Scam alerts (Premium)"),
        BotCommand("support", "Contact support"),
    ]
    await application.bot.set_my_commands(commands)
    log_info("Bot commands registered ✓", tag="BOT")

    # Log admin IDs for debugging
    log_info(f"Admin user IDs: {ADMIN_USER_IDS}", tag="STARTUP")


def create_bot():
    """Create and configure the bot application."""
    log_info("Creating bot application...", tag="STARTUP")

    app = Application.builder().token(TELEGRAM_BOT_TOKEN).post_init(post_init).build()

    # Free commands
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("firms", cmd_firms))
    app.add_handler(CommandHandler("promos", cmd_promos))
    app.add_handler(CommandHandler("scores", cmd_scores))
    app.add_handler(CommandHandler("compare", cmd_compare))
    app.add_handler(CommandHandler("referral", cmd_referral))
    app.add_handler(CommandHandler("premium", cmd_premium))
    app.add_handler(CommandHandler("status", cmd_status))
    app.add_handler(CommandHandler("support", cmd_support))

    # Premium commands
    app.add_handler(CommandHandler("history", cmd_history))
    app.add_handler(CommandHandler("scams", cmd_scams))

    # Admin commands
    app.add_handler(CommandHandler("admin", cmd_admin))
    app.add_handler(CommandHandler("stats", cmd_admin_stats))
    app.add_handler(CommandHandler("activate", cmd_admin_activate))
    app.add_handler(CommandHandler("addvip", cmd_admin_addvip))
    app.add_handler(CommandHandler("broadcast", cmd_admin_broadcast))
    app.add_handler(CommandHandler("scrape", cmd_admin_scrape))

    # Callback handler for buttons
    app.add_handler(CallbackQueryHandler(handle_callback))

    # Error handler
    app.add_error_handler(error_handler)

    log_info("Bot handlers registered ✓", tag="STARTUP")
    return app