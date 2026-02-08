"""
PropFirmTracker Bot V4 — Professional Edition
All commands, admin panel, AI toggle, polished UX.
"""
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
            InlineKeyboardButton("📢 Free Channel", url="https://t.me/PropFirmTrackerFree")
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


@premium_required
async def cmd_history(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    firm_filter = ctx.args[0].lower() if ctx.args else None
    changes = get_recent_changes(10, firm_filter)

    if not changes:
        await update.message.reply_text(
            "📜  <b>Change History</b>\n\nNo changes recorded yet.",
            parse_mode='HTML'
        )
        return

    msg = "📜  <b>Recent Changes</b>\n"
    msg += "━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"

    for c in changes:
        fn = PROP_FIRMS.get(c['firm_slug'], {}).get('name', c['firm_slug'])
        ct = c.get('change_type', '')
        icon = {"pricing_change": "💰", "rules_change": "📋", "new_promo": "🎟", "scam_alert": "🚨"}.get(ct, "🔄")
        ts = c.get('detected_at', '')[:10]
        summary = c.get('summary', '')

        # Take first meaningful line
        first_line = ""
        for line in summary.split('\n'):
            line = line.strip()
            if line and not line.startswith(('💰', '📋', '🎟', '🔄')):
                first_line = line[:80]
                break
        if not first_line:
            first_line = summary.split('\n')[0][:80] if summary else "Update detected"

        msg += f"   {icon}  <b>{fn}</b>  ·  {ts}\n"
        msg += f"       {first_line}\n\n"

    msg += "━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
    msg += "Filter:  /history <code>ftmo</code>"

    await update.message.reply_text(msg, parse_mode='HTML')


@premium_required
async def cmd_scams(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    from database import get_connection
    conn = get_connection()
    alerts = conn.execute(
        "SELECT * FROM scam_alerts ORDER BY detected_at DESC LIMIT 10"
    ).fetchall()
    conn.close()

    if not alerts:
        await update.message.reply_text(
            "🚨  <b>Scam Alerts</b>\n\nNo warnings detected. All clear for now.",
            parse_mode='HTML'
        )
        return

    msg = "🚨  <b>Scam & Warning Alerts</b>\n"
    msg += "━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"

    for a in alerts:
        sev_icon = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(a['severity'], "⚪")
        fn = PROP_FIRMS.get(a['firm_slug'], {}).get('name', a['firm_slug'])
        ts = a['detected_at'][:10]

        msg += f"   {sev_icon}  <b>{fn}</b>  ·  {a['severity'].upper()}\n"
        msg += f"       {a['description'][:100]}\n"
        msg += f"       {ts}\n\n"

    msg += "━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
    msg += "⚡ Always do your own due diligence."

    await update.message.reply_text(msg, parse_mode='HTML')


async def cmd_referral(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    get_or_create_user(uid, update.effective_user.username, update.effective_user.first_name)

    rc = get_referral_code(uid)
    total = get_total_referrals(uid)
    current = get_referral_count(uid)

    link = f"https://t.me/{bot_name(ctx)}?start=REF_{rc}"
    progress = min(current, REFERRALS_NEEDED)
    bar = "▓" * progress + "░" * (REFERRALS_NEEDED - progress)

    msg = "👥  <b>Referral Program</b>\n"
    msg += "━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
    msg += f"   Invite {REFERRALS_NEEDED} friends → earn <b>{REFERRAL_REWARD_DAYS} days FREE</b>\n\n"
    msg += f"   Progress:  {bar}  {progress}/{REFERRALS_NEEDED}\n"
    msg += f"   Total referrals:  {total}\n\n"
    msg += f"   Your link:\n"
    msg += f"   <code>{link}</code>\n\n"
    msg += "━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
    msg += "Share your link — every friend counts!"

    kb = [[InlineKeyboardButton(
        "📤 Share Link",
        url=f"https://t.me/share/url?url={link}&text=Track+prop+firm+changes+in+real-time!"
    )]]

    await update.message.reply_text(msg, parse_mode='HTML', reply_markup=InlineKeyboardMarkup(kb))


async def cmd_premium(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id

    if is_premium(uid):
        from database import get_connection
        conn = get_connection()
        r = conn.execute("SELECT premium_expires_at FROM users WHERE user_id=?", (uid,)).fetchone()
        conn.close()
        exp = r['premium_expires_at'][:10] if r and r['premium_expires_at'] else 'N/A'

        await update.message.reply_text(
            "💎  <b>Premium Active</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"   Expires:  {exp}\n\n"
            "   You're getting real-time alerts,\n"
            "   AI analysis, and scam warnings.\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "/referral to extend for free",
            parse_mode='HTML'
        )
        return

    msg = "💎  <b>Premium Plan</b>\n"
    msg += "━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
    msg += "   ⚡  Real-time alerts (no 24h delay)\n"
    msg += "   🧠  AI-powered change analysis\n"
    msg += "   🚨  Instant scam warnings\n"
    msg += "   📜  Full change history\n"
    msg += "   🎟  Promo alerts before anyone\n\n"
    msg += f"   Monthly    <b>${PREMIUM_PRICE_MONTHLY}</b>\n"
    msg += f"   Yearly     <b>${PREMIUM_PRICE_YEARLY}</b>  (save 33%)\n\n"
    msg += "━━━━━━━━━━━━━━━━━━━━━━━━━━"

    kb = []
    if STRIPE_API_KEY:
        kb.append([
            InlineKeyboardButton(f"💳 ${PREMIUM_PRICE_MONTHLY}/mo", callback_data="pay_stripe_monthly"),
            InlineKeyboardButton(f"💳 ${PREMIUM_PRICE_YEARLY}/yr", callback_data="pay_stripe_yearly")
        ])
    kb.append([InlineKeyboardButton("₿ Pay with USDT", callback_data="pay_crypto")])
    kb.append([InlineKeyboardButton("🆓 Earn Free Days", callback_data="referral_info")])

    await update.message.reply_text(msg, parse_mode='HTML', reply_markup=InlineKeyboardMarkup(kb))


async def cmd_status(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    db = get_or_create_user(uid, update.effective_user.username, update.effective_user.first_name)

    prem = is_premium(uid)
    adm = is_admin(uid)

    if adm and prem:
        badge = "👑  Admin + Premium"
    elif adm:
        badge = "👑  Admin"
    elif prem:
        badge = "💎  Premium"
    else:
        badge = "🆓  Free"

    exp = db.get('premium_expires_at', 'N/A')
    exp = exp[:10] if exp and exp != 'N/A' else '—'
    refs = get_total_referrals(uid)

    msg = "👤  <b>Your Account</b>\n"
    msg += "━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
    msg += f"   ID:  <code>{uid}</code>\n"
    msg += f"   Plan:  <b>{badge}</b>\n"
    msg += f"   Expires:  {exp}\n"
    msg += f"   Referrals:  {refs}\n\n"
    msg += "━━━━━━━━━━━━━━━━━━━━━━━━━━"

    if not prem and not adm:
        msg += "\n💎 /premium  ·  /referral for free days"

    await update.message.reply_text(msg, parse_mode='HTML')


async def cmd_support(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🆘  <b>Support</b>\n\n"
        "Contact  @PropFirmTrackerSupport\n"
        "for any questions or issues.",
        parse_mode='HTML'
    )


# ══════════════════════════════════════
# CALLBACK QUERIES
# ══════════════════════════════════════

async def handle_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    d = q.data

    if d == "firms_list":
        scores = get_latest_trustpilot_scores()
        msg = "📊  <b>Monitored Firms</b>\n\n"
        for slug, cfg in PROP_FIRMS.items():
            sd = scores.get(slug, {})
            sc = sd.get('score', 0)
            dot = "🟢" if sc >= 4.5 else "🟡" if sc >= 3.5 else "🔴" if sc > 0 else "⚪"
            msg += f"   {dot}  {cfg['name']}  ·  {sc:.1f}/5\n" if sc > 0 else f"   {dot}  {cfg['name']}  ·  —\n"
        msg += f"\n/scores  ·  /compare"
        await q.edit_message_text(msg, parse_mode='HTML')

    elif d == "promos":
        ps = get_active_promos()
        msg = "🎟  <b>Active Promos</b>\n\n"
        if ps:
            for p in ps[:5]:
                fn = PROP_FIRMS.get(p['firm_slug'], {}).get('name', '?')
                msg += f"   {fn}:  <code>{p.get('promo_code', '?')}</code>  {p.get('discount', '')}\n"
        else:
            msg += "   No active promos right now.\n"
        msg += "\n/promos for full details"
        await q.edit_message_text(msg, parse_mode='HTML')

    elif d == "scores":
        scores = get_latest_trustpilot_scores()
        if scores:
            ss = sorted(scores.items(), key=lambda x: x[1].get('score', 0), reverse=True)
            msg = "⭐  <b>Scores</b>\n\n"
            for i, (slug, sd) in enumerate(ss[:5]):
                fn = PROP_FIRMS.get(slug, {}).get('name', slug)
                sc = sd.get('score', 0)
                msg += f"   {i+1}. {fn}  —  {sc:.1f}/5\n"
            msg += "\n/scores for full leaderboard"
        else:
            msg = "⭐  Collecting scores..."
        await q.edit_message_text(msg, parse_mode='HTML')

    elif d == "premium_info":
        await q.edit_message_text(
            f"💎  <b>Premium</b>\n\n"
            f"   ⚡ Real-time alerts\n   🧠 AI analysis\n   🚨 Scam warnings\n\n"
            f"   ${PREMIUM_PRICE_MONTHLY}/mo  ·  ${PREMIUM_PRICE_YEARLY}/yr\n\n"
            f"/premium to subscribe  ·  /referral for free",
            parse_mode='HTML'
        )

    elif d == "referral_info":
        rc = get_referral_code(q.from_user.id)
        link = f"https://t.me/{bot_name(ctx)}?start=REF_{rc}"
        await q.edit_message_text(
            f"👥  <b>Referral</b>\n\n"
            f"Invite {REFERRALS_NEEDED} friends → {REFERRAL_REWARD_DAYS} days FREE\n\n"
            f"<code>{link}</code>\n\n/referral for details",
            parse_mode='HTML'
        )

    elif d == "pay_crypto":
        await q.edit_message_text(
            f"₿  <b>Pay with USDT</b>\n\n"
            f"Send <b>${PREMIUM_PRICE_MONTHLY}</b> USDT (TRC20) to:\n\n"
            f"<code>{CRYPTO_WALLET_USDT_TRC20}</code>\n\n"
            f"After sending, contact @PropFirmTrackerSupport\nwith your TX hash.",
            parse_mode='HTML'
        )

    elif d in ("pay_stripe_monthly", "pay_stripe_yearly", "pay_stars"):
        await q.edit_message_text(
            "💳  Contact @PropFirmTrackerSupport to set up payment.",
            parse_mode='HTML'
        )


# ══════════════════════════════════════
# ADMIN COMMANDS
# ══════════════════════════════════════

@admin_required
async def cmd_admin(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    st = get_user_stats()
    from database import get_connection
    conn = get_connection()
    tc = conn.execute("SELECT COUNT(*) as c FROM changes").fetchone()['c']
    tp = conn.execute("SELECT COUNT(*) as c FROM promos WHERE is_active=1").fetchone()['c']
    ts = conn.execute("SELECT COUNT(*) as c FROM scam_alerts").fetchone()['c']
    conn.close()

    ai_status = get_setting("ai_enabled", "off")
    ai_icon = "🟢" if ai_status == "on" else "🔴"

    msg = "👑  <b>Admin Dashboard</b>\n"
    msg += "━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
    msg += f"   <b>Users</b>\n"
    msg += f"   👥  {st['total']} total  ·  💎 {st['premium']} premium  ·  🆕 {st['today_new']} today\n"
    msg += f"   💰  ~${st['premium'] * PREMIUM_PRICE_MONTHLY:.0f} MRR\n\n"
    msg += f"   <b>Data</b>\n"
    msg += f"   📈  {tc} changes  ·  🎟 {tp} promos  ·  🚨 {ts} scam alerts\n\n"
    msg += f"   <b>Settings</b>\n"
    msg += f"   {ai_icon}  AI Analysis: {ai_status.upper()}\n\n"
    msg += "━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
    msg += "<b>Commands</b>\n"
    msg += "   /stats — Quick stats\n"
    msg += "   /scrape — Force scrape\n"
    msg += "   /activate <code>ID [days]</code>\n"
    msg += "   /addvip <code>ID [days]</code>\n"
    msg += "   /broadcast <code>message</code>\n"
    msg += "   /ai <code>on|off</code>"

    await update.message.reply_text(msg, parse_mode='HTML')


@admin_required
async def cmd_stats(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    st = get_user_stats()
    from database import get_connection
    conn = get_connection()
    tc = conn.execute("SELECT COUNT(*) as c FROM changes").fetchone()['c']
    tp = conn.execute("SELECT COUNT(*) as c FROM promos WHERE is_active=1").fetchone()['c']
    ts = conn.execute("SELECT COUNT(*) as c FROM scam_alerts").fetchone()['c']
    conn.close()

    msg = "📊  <b>Quick Stats</b>\n\n"
    msg += f"   👥 {st['total']}  ·  💎 {st['premium']}  ·  🆕 {st['today_new']}\n"
    msg += f"   📈 {tc} changes  ·  🎟 {tp} promos  ·  🚨 {ts} scams\n"
    msg += f"   💰 ~${st['premium'] * PREMIUM_PRICE_MONTHLY:.0f} MRR"

    await update.message.reply_text(msg, parse_mode='HTML')


@admin_required
async def cmd_activate(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not ctx.args:
        await update.message.reply_text(
            "Usage:  /activate <code>USER_ID [days]</code>\nDefault: 30 days",
            parse_mode='HTML'
        )
        return

    try:
        tid = int(ctx.args[0])
    except:
        await update.message.reply_text("❌  Invalid user ID.")
        return

    days = int(ctx.args[1]) if len(ctx.args) > 1 else 30
    get_or_create_user(tid)
    activate_premium(tid, days, "admin")

    await update.message.reply_text(
        f"✅  <code>{tid}</code> → <b>{days} days</b> Premium activated",
        parse_mode='HTML'
    )


@admin_required
async def cmd_addvip(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not ctx.args:
        await update.message.reply_text(
            "Usage:  /addvip <code>USER_ID [days]</code>\nActivates Premium + sends invite link",
            parse_mode='HTML'
        )
        return

    try:
        tid = int(ctx.args[0])
    except:
        await update.message.reply_text("❌  Invalid user ID.")
        return

    days = int(ctx.args[1]) if len(ctx.args) > 1 else 30
    get_or_create_user(tid)
    activate_premium(tid, days, "admin_vip")

    # Create invite link
    invite = None
    if PREMIUM_CHANNEL_ID:
        try:
            link_obj = await ctx.bot.create_chat_invite_link(
                chat_id=PREMIUM_CHANNEL_ID, member_limit=1, name=f"VIP-{tid}"
            )
            invite = link_obj.invite_link
        except Exception as e:
            log_error(f"Invite link: {e}", tag="ADMIN")

    # Notify user
    notified = False
    try:
        notif = f"🎉  <b>Welcome to Premium!</b>\n\n"
        notif += f"You have <b>{days} days</b> of Premium access.\n\n"
        notif += "   ⚡  Real-time alerts\n   🧠  AI analysis\n   🚨  Scam warnings\n\n"
        if invite:
            notif += f"Join the VIP channel:\n{invite}\n\n"
        notif += "Enjoy! 🚀"
        await ctx.bot.send_message(chat_id=tid, text=notif, parse_mode='HTML')
        notified = True
    except:
        pass

    await update.message.reply_text(
        f"✅  VIP <code>{tid}</code>  ·  {days} days\n"
        f"   🔗 Invite: {'✅' if invite else '❌'}\n"
        f"   📨 Notified: {'✅' if notified else '❌'}",
        parse_mode='HTML'
    )


@admin_required
async def cmd_broadcast(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not ctx.args:
        await update.message.reply_text(
            "Usage:  /broadcast <code>your message here</code>",
            parse_mode='HTML'
        )
        return

    msg = " ".join(ctx.args)
    from database import get_connection
    conn = get_connection()
    users = conn.execute("SELECT user_id FROM users WHERE is_banned=0").fetchall()
    conn.close()

    status = await update.message.reply_text(f"📢  Broadcasting to {len(users)} users...")

    sent, failed = 0, 0
    for u in users:
        try:
            await ctx.bot.send_message(chat_id=u['user_id'], text=msg, parse_mode='HTML')
            sent += 1
            await asyncio.sleep(0.05)
        except:
            failed += 1

    await status.edit_text(f"📢  Done  ·  ✅ {sent}  ·  ❌ {failed}")


@admin_required
async def cmd_scrape(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🔍  Scraping all sources...")

    from scrapers import PropFirmScraper, RedditScraper, TrustpilotScraper
    results = []

    for name, Cls in [("Firms", PropFirmScraper), ("Reddit", RedditScraper), ("Trustpilot", TrustpilotScraper)]:
        try:
            r = Cls().scrape_all()
            errs = r.get('errors', 0)
            icon = "✅" if errs == 0 else "⚠️" if errs < 5 else "❌"
            results.append(f"   {icon}  {name}:  {r}")
        except Exception as e:
            results.append(f"   ❌  {name}:  {e}")

    msg = "📊  <b>Scrape Results</b>\n"
    msg += "━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
    msg += "\n".join(results)

    await update.message.reply_text(msg, parse_mode='HTML')


@admin_required
async def cmd_ai_toggle(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not ctx.args:
        current = get_setting("ai_enabled", "off")
        icon = "🟢 ON" if current == "on" else "🔴 OFF"
        await update.message.reply_text(
            f"🧠  <b>AI Analysis</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"   Status:  <b>{icon}</b>\n\n"
            f"   When ON, Claude analyzes each detected\n"
            f"   change and explains the impact for traders.\n\n"
            f"   Cost:  ~$0.01 per change\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"   /ai <code>on</code>  ·  /ai <code>off</code>",
            parse_mode='HTML'
        )
        return

    action = ctx.args[0].lower()
    if action == "on":
        set_setting("ai_enabled", "on")
        await update.message.reply_text(
            "🧠  AI Analysis:  <b>🟢 ON</b>\n\n"
            "Next scrape will include AI summaries.\n"
            "Cost: ~$0.01 per change detected.\n\n"
            "/ai off to disable anytime",
            parse_mode='HTML'
        )
        log_info("AI ENABLED by admin", tag="AI")
    elif action == "off":
        set_setting("ai_enabled", "off")
        await update.message.reply_text(
            "🧠  AI Analysis:  <b>🔴 OFF</b>\n\n"
            "Using text diff only (free).\n\n"
            "/ai on to enable",
            parse_mode='HTML'
        )
        log_info("AI DISABLED by admin", tag="AI")
    else:
        await update.message.reply_text("Usage:  /ai <code>on</code> or <code>off</code>", parse_mode='HTML')


# ══════════════════════════════════════
# BOT SETUP
# ══════════════════════════════════════

async def error_handler(update, ctx):
    log_error(f"Bot error: {ctx.error}", tag="ERROR")


async def post_init(app):
    commands = [
        BotCommand("start", "Start the bot"),
        BotCommand("help", "All commands"),
        BotCommand("firms", "Monitored firms"),
        BotCommand("promos", "Active promo codes"),
        BotCommand("scores", "Trustpilot leaderboard"),
        BotCommand("compare", "Compare two firms"),
        BotCommand("referral", "Earn free Premium"),
        BotCommand("premium", "Upgrade to Premium"),
        BotCommand("status", "Your account"),
        BotCommand("support", "Get help"),
    ]
    await app.bot.set_my_commands(commands)
    log_info(f"Bot ready  ·  Admin IDs: {ADMIN_USER_IDS}", tag="STARTUP")


def create_bot():
    log_info("Creating bot...", tag="STARTUP")
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).post_init(post_init).build()

    handlers = [
        ("start", cmd_start), ("help", cmd_help), ("firms", cmd_firms),
        ("promos", cmd_promos), ("scores", cmd_scores), ("compare", cmd_compare),
        ("referral", cmd_referral), ("premium", cmd_premium), ("status", cmd_status),
        ("support", cmd_support), ("history", cmd_history), ("scams", cmd_scams),
        ("admin", cmd_admin), ("stats", cmd_stats), ("activate", cmd_activate),
        ("addvip", cmd_addvip), ("broadcast", cmd_broadcast), ("scrape", cmd_scrape),
        ("ai", cmd_ai_toggle),
    ]
    for cmd, func in handlers:
        app.add_handler(CommandHandler(cmd, func))

    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_error_handler(error_handler)

    log_info("All handlers registered", tag="STARTUP")
    return app
