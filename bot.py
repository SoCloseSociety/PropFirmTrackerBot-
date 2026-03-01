# PropFirmTracker Bot V4 — Professional Edition
All commands, admin panel, AI toggle, polished UX.

import asyncio
import functools
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, BotCommand
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from utils.logger import log_info, log_error, log_warn
from database import (
    get_or_create_user, is_premium, activate_premium, get_referral_code,
    get_referral_count, get_total_referrals, check_and_reward_referrals,
    get_active_promos, get_recent_changes, get_latest_trustpilot_scores,
    get_user_stats, get_setting, set_setting
)
from config import (
    TELEGRAM_BOT_TOKEN, ADMIN_USER_IDS, PROP_FIRMS,
    PREMIUM_PRICE_MONTHLY, PREMIUM_PRICE_YEARLY,
    REFERRALS_NEEDED, REFERRAL_REWARD_DAYS,
    CRYPTO_WALLET_USDT_TRC20, STRIPE_API_KEY, PREMIUM_CHANNEL_ID
)
from os import environ

# ══════════════════════════════════════
# HELPERS
# ══════════════════════════════════════

def is_admin(uid):
    return int(uid) in ADMIN_USER_IDS


def premium_required(func):
    @functools.wraps(func)
    async def wrapper(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
        uid = update.effective_user.id
        if not is_premium(uid) and not is_admin(uid):
            kb = [[InlineKeyboardButton("💎 Go Premium", callback_data="premium_info")]]
            await update.message.reply_text(
                "🔒  <b>Premium Feature</b>\n\n"
                "This command is available for Premium members.\n\n"
                f"Starting at <b>${PREMIUM_PRICE_MONTHLY}/mo</b>  ·  or earn free days via /referral",
                parse_mode='HTML', reply_markup=InlineKeyboardMarkup(kb)
            )
            return
        return await func(update, ctx)
    return wrapper


def admin_required(func):
    @functools.wraps(func)
    async def wrapper(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
        if not is_admin(update.effective_user.id):
            await update.message.reply_text("⛔  Admin only.")
            return
        return await func(update, ctx)
    return wrapper


def bot_name(ctx):
    return ctx.bot.username

# ══════════════════════════════════════
# PUBLIC COMMANDS
# ══════════════════════════════════════

async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    u = update.effective_user
    ref_code = None

    if ctx.args and ctx.args[0].startswith("REF_"):
        ref_code = ctx.args[0].replace("REF_", "")
        log_info(f"Referral join: {u.id} via {ref_code}", tag="REF")

    db = get_or_create_user(u.id, u.username, u.first_name, ref_code)

    if ref_code and db.get('referred_by'):
        if check_and_reward_referrals(db['referred_by'], REFERRALS_NEEDED, REFERRAL_REWARD_DAYS):
            try:
                await ctx.bot.send_message(
                    chat_id=db['referred_by'],
                    text=f"🎉  <b>Referral Reward!</b>\n\n{REFERRAL_REWARD_DAYS} days of Premium unlocked.\nCheck /referral for details.",
                    parse_mode='HTML'
                )
            except:
                pass

    kb = [
        [
            InlineKeyboardButton("📊 Firms", callback_data="firms_list"),
            InlineKeyboardButton("🎟 Promos", callback_data="promos")
        ],
        [
            InlineKeyboardButton("⭐ Scores", callback_data="scores"),
            InlineKeyboardButton("💎 Premium", callback_data="premium_info")
        ],
        [
            InlineKeyboardButton("👥 Earn Free Days", callback_data="referral_info")
        ],
        [
            InlineKeyboardButton("📢 Free Channel", url=environ.get('FREE_CHANNEL_URL'))
        ]
    ]

    await update.message.reply_text(
        f"👋  <b>Welcome, {u.first_name}!</b>\n\n"
        f"I monitor <b>{len(PROP_FIRMS)} prop firms</b> around the clock\n"
        f"and alert you the moment something changes.\n\n"
        f"   🔄  Rule changes\n"
        f"   💰  Pricing updates\n"
        f"   🎟  Promo codes & deals\n"
        f"   🚨  Scam warnings\n"
        f"   ⭐  Trustpilot score drops\n\n"
        f"<b>Free</b> — alerts with 24 h delay\n"
        f"<b>Premium</b> — real-time + AI analysis\n\n"
        f"Type /help for all commands.",
        parse_mode='HTML',
        reply_markup=InlineKeyboardMarkup(kb)
    )
    log_info(f"User started: {u.id} (@{u.username})", tag="BOT")

async def cmd_help(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    adm = is_admin(uid)
    prem = is_premium(uid)

    msg = "📖  <b>Commands</b>\n\n"

    msg += "<b>Everyone</b>\n"
    msg += "   /firms — Monitored firms + ratings\n"
    msg += "   /promos — Active promo codes\n"
    msg += "   /scores — Trustpilot leaderboard\n"
    msg += "   /compare — Compare two firms\n"
    msg += "   /referral — Earn free Premium days\n"
    msg += "   /premium — Subscription info\n"
    msg += "   /status — Your account\n"
    msg += "   /support — Get help\n\n"

    msg += "<b>Premium 💎</b>\n"
    msg += "   /history — Recent changes log\n"
    msg += "   /scams — Scam & warning alerts\n"

    if adm:
        msg += "\n<b>Admin 👑</b>\n"
        msg += "   /admin — Dashboard\n"
        msg += "   /stats — Quick stats\n"
        msg += "   /scrape — Force scrape now\n"
        msg += "   /activate <code>ID [days]</code> — Add premium\n"
        msg += "   /addvip <code>ID [days]</code> — VIP + invite link\n"
        msg += "   /broadcast <code>message</code> — Send to all\n"
        msg += "   /ai <code>on|off</code> — Toggle AI analysis\n"

    await update.message.reply_text(msg, parse_mode='HTML')

async def cmd_firms(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    scores = get_latest_trustpilot_scores()

    msg = "📊  <b>Monitored Firms</b>\n"
    msg += "━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"

    for slug, cfg in PROP_FIRMS.items():
        d = scores.get(slug, {})
        sc = d.get('score', 0)
        if sc >= 4.5:
            dot = "🟢"
        elif sc >= 3.5:
            dot = "🟡"
        elif sc > 0:
            dot = "🔴"
        else:
            dot = "⚪"

        name = cfg['name']
        rating = f"{sc:.1f}/5" if sc > 0 else "—"
        msg += f"   {dot}  <b>{name}</b>  ·  {rating}\n"

    msg += f"\n   {len(PROP_FIRMS)} firms tracked 24/7\n\n"
    msg += "━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
    msg += "/scores for full leaderboard  ·  /compare to compare"

    await update.message.reply_text(msg, parse_mode='HTML')

async def cmd_promos(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    promos = get_active_promos()

    if not promos:
        await update.message.reply_text(
            "🎟  <b>Active Promos</b>\n\n"
            "No promos detected right now.\n\n"
            "💎 Premium members get notified the moment\n"
            "a new promo appears.  ·  /premium",
            parse_mode='HTML'
        )
        return

    msg = "🎟  <b>Active Promos</b>\n"
    msg += "━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"

    for p in promos[:8]:
        fn = PROP_FIRMS.get(p['firm_slug'], {}).get('name', p['firm_slug'])
        af = PROP_FIRMS.get(p['firm_slug'], {}).get('affiliate_url', '#')
        code = p.get('promo_code', '')
        disc = p.get('discount', '')

        msg += f"   <b>{fn}</b>\n"
        if code:
            msg += f"   Code  <code>{code}</code>"
        if disc:
            msg += f"  —  {disc}"
        msg += f"\n   <a href='{af}'>Claim this offer →</a>\n\n"

    msg += "━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
    msg += "🔔 Get new promos instantly  ·  /premium"

    await update.message.reply_text(msg, parse_mode='HTML', disable_web_page_preview=True)

async def cmd_scores(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    scores = get_latest_trustpilot_scores()

    if not scores:
        await update.message.reply_text(
            "⭐  <b>Trustpilot Scores</b>\n\nCollecting data — check back soon.",
            parse_mode='HTML'
        )
        return

    ss = sorted(scores.items(), key=lambda x: x[1].get('score', 0), reverse=True)

    msg = "⭐  <b>Trustpilot Leaderboard</b>\n"
    msg += "━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"

    medals = ["🥇", "🥈", "🥉"]
    for i, (slug, d) in enumerate(ss):
        sc = d.get('score', 0)
        rc = d.get('review_count', 0)
        fn = PROP_FIRMS.get(slug, {}).get('name', slug)

        rank = medals[i] if i < 3 else f"  {i+1}."
        bar = "█" * int(sc) + "░" * (5 - int(sc))

        msg += f"   {rank}  <b>{fn}</b>\n"
        msg += f"        {bar}  {sc:.1f}  ({rc:,})\n\n"

    msg += "━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
    msg += "📉 Score drop alerts  ·  /premium"

    await update.message.reply_text(msg, parse_mode='HTML')

async def cmd_compare(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if len(ctx.args) < 2:
        firms_list = ", ".join([f"<code>{s}</code>" for s in list(PROP_FIRMS.keys())[:6]])
        await update.message.reply_text(
            "🔍  <b>Compare Firms</b>\n\n"
            f"Usage:  /compare <code>firm1</code> <code>firm2</code>\n\n"
            f"Available:  {firms_list}, ...\n\n"
            "Tip: use the slug name (no spaces)",
            parse_mode='HTML'
        )
        return

    f1, f2 = ctx.args[0].lower(), ctx.args[1].lower()
    c1, c2 = PROP_FIRMS.get(f1), PROP_FIRMS.get(f2)

    if not c1 or not c2:
        await update.message.reply_text("❌  Firm not found. /firms to see available slugs.")
        return

    scores = get_latest_trustpilot_scores()
    s1, s2 = scores.get(f1, {}), scores.get(f2, {})

    sc1 = s1.get('score', 0)
    sc2 = s2.get('score', 0)
    rc1 = s1.get('review_count', 0)
    rc2 = s2.get('review_count', 0)

    winner_sc = "←" if sc1 > sc2 else "→" if sc2 > sc1 else "="
    winner_rc = "←" if rc1 > rc2 else "→" if rc2 > rc1 else "="

    msg = "🔍  <b>Head to Head</b>\n"
    msg += "━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
    msg += f"   <b>{c1['name']}</b>  vs  <b>{c2['name']}</b>\n\n"

    msg += f"   ⭐ Score\n"
    msg += f"   {sc1:.1f}  {winner_sc}  {sc2:.1f}\n\n"

    msg += f"   💬 Reviews\n"
    msg += f"   {rc1:,}  {winner_rc}  {rc2:,}\n\n"

    msg += f"   🔗 <a href='{c1.get('url','#')}'>{c1['name']}</a>  ·  <a href='{c2.get('url','#')}'>{c2['name']}</a>\n\n"
    msg += "━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
    msg += "Full change history  ·  /history (Premium)"

    await update.message.reply_text(msg, parse_mode='HTML', disable_web_page_preview=True)

... (truncated, 549 more lines)