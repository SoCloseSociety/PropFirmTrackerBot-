"""PropFirmTracker Bot V3"""
import asyncio, functools
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, BotCommand
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from utils.logger import log_info, log_error, log_warn
from database import (
    get_or_create_user, is_premium, activate_premium, get_referral_code,
    get_referral_count, get_total_referrals, check_and_reward_referrals,
    get_active_promos, get_recent_changes, get_latest_trustpilot_scores, get_user_stats
)
from config import (
    TELEGRAM_BOT_TOKEN, ADMIN_USER_IDS, PROP_FIRMS,
    PREMIUM_PRICE_MONTHLY, PREMIUM_PRICE_YEARLY,
    REFERRALS_NEEDED, REFERRAL_REWARD_DAYS,
    CRYPTO_WALLET_USDT_TRC20, STRIPE_API_KEY, PREMIUM_CHANNEL_ID
)

def is_admin(uid): return int(uid) in ADMIN_USER_IDS

def premium_required(func):
    @functools.wraps(func)
    async def w(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
        uid = update.effective_user.id
        if not is_premium(uid) and not is_admin(uid):
            kb = [[InlineKeyboardButton("💎 Upgrade", callback_data="premium_info")]]
            await update.message.reply_text(f"🔒 <b>Premium only</b>\n${PREMIUM_PRICE_MONTHLY}/mo or /referral for free!", parse_mode='HTML', reply_markup=InlineKeyboardMarkup(kb))
            return
        return await func(update, ctx)
    return w

def admin_required(func):
    @functools.wraps(func)
    async def w(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
        if not is_admin(update.effective_user.id):
            await update.message.reply_text("⛔ Admin only."); return
        return await func(update, ctx)
    return w

def bn(ctx): return ctx.bot.username

async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    u = update.effective_user; rc = None
    if ctx.args and ctx.args[0].startswith("REF_"):
        rc = ctx.args[0].replace("REF_",""); log_info(f"Referral join: {u.id} via {rc}", tag="REF")
    db = get_or_create_user(u.id, u.username, u.first_name, rc)
    if rc and db.get('referred_by'):
        if check_and_reward_referrals(db['referred_by'], REFERRALS_NEEDED, REFERRAL_REWARD_DAYS):
            try: await ctx.bot.send_message(chat_id=db['referred_by'], text=f"🎉 Referral reward! {REFERRAL_REWARD_DAYS} days FREE! → /referral", parse_mode='HTML')
            except: pass
    kb = [[InlineKeyboardButton("📊 Firms",callback_data="firms_list"),InlineKeyboardButton("🎟️ Promos",callback_data="promos")],
          [InlineKeyboardButton("💎 Premium",callback_data="premium_info"),InlineKeyboardButton("👥 Free Days",callback_data="referral_info")],
          [InlineKeyboardButton("📢 Free Channel",url="https://t.me/PropFirmTrackerFree")]]
    await update.message.reply_text(
        f"👋 <b>Welcome {u.first_name}!</b>\n\n🤖 Monitoring <b>{len(PROP_FIRMS)} prop firms</b> 24/7\n"
        f"🔄 Rules | 💰 Pricing | 🎟️ Promos | 🚨 Scams\n\n"
        f"🆓 Free = 24h delay | 💎 Premium = real-time\n💡 /referral for {REFERRAL_REWARD_DAYS} FREE days\n/help for commands",
        parse_mode='HTML', reply_markup=InlineKeyboardMarkup(kb))
    log_info(f"User started: {u.id} (@{u.username})", tag="BOT")

async def cmd_help(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    m = "📋 <b>Commands</b>\n\n🆓 /firms /promos /scores /compare /referral /premium /status\n💎 /history /scams\nℹ️ /help /support\n"
    if is_admin(update.effective_user.id): m += "\n🔐 /admin /stats /scrape /activate /addvip /broadcast\n"
    await update.message.reply_text(m, parse_mode='HTML')

async def cmd_firms(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    sc = get_latest_trustpilot_scores()
    m = "📊 <b>Monitored Firms</b>\n\n"
    for s,c in PROP_FIRMS.items():
        d = sc.get(s); v = f"⭐{d['score']:.1f}" if d and d.get('score') else "⭐N/A"
        m += f"• <b>{c['name']}</b> {v}\n"
    m += f"\n{len(PROP_FIRMS)} firms | /compare /promos"
    await update.message.reply_text(m, parse_mode='HTML')

async def cmd_promos(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ps = get_active_promos()
    if not ps: await update.message.reply_text("🎟️ No promos right now.\n💎 /premium for instant alerts", parse_mode='HTML'); return
    m = "🎟️ <b>Active Promos</b>\n\n"
    for p in ps[:10]:
        fn = PROP_FIRMS.get(p['firm_slug'],{}).get('name',p['firm_slug'])
        af = PROP_FIRMS.get(p['firm_slug'],{}).get('affiliate_url','#')
        m += f"🏷️ <b>{fn}</b>\n"
        if p.get('promo_code'): m += f"   <code>{p['promo_code']}</code>"
        if p.get('discount'): m += f" — {p['discount']}"
        m += f"\n   <a href='{af}'>Claim →</a>\n\n"
    await update.message.reply_text(m, parse_mode='HTML', disable_web_page_preview=True)

async def cmd_scores(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    sc = get_latest_trustpilot_scores()
    if not sc: await update.message.reply_text("⭐ Collecting...", parse_mode='HTML'); return
    ss = sorted(sc.items(), key=lambda x:x[1].get('score',0), reverse=True)
    m = "⭐ <b>Trustpilot</b>\n\n"
    for i,(s,d) in enumerate(ss,1):
        v=d.get('score',0); e="🟢" if v>=4.5 else "🟡" if v>=3.5 else "🟠" if v>=2.5 else "🔴"
        m += f"{e} {i}. <b>{PROP_FIRMS.get(s,{}).get('name',s)}</b> {v:.1f}/5 ({d.get('review_count',0)})\n"
    m += "\n💎 Score alerts → /premium"
    await update.message.reply_text(m, parse_mode='HTML')

async def cmd_compare(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if len(ctx.args)<2:
        fl=", ".join([f"<code>{s}</code>" for s in PROP_FIRMS])
        await update.message.reply_text(f"🔍 /compare [a] [b]\n{fl}", parse_mode='HTML'); return
    f1,f2=ctx.args[0].lower(),ctx.args[1].lower(); c1,c2=PROP_FIRMS.get(f1),PROP_FIRMS.get(f2)
    if not c1 or not c2: await update.message.reply_text("❌ Not found. /firms"); return
    sc=get_latest_trustpilot_scores(); s1,s2=sc.get(f1,{}),sc.get(f2,{})
    await update.message.reply_text(f"🔍 <b>{c1['name']} vs {c2['name']}</b>\n⭐ {s1.get('score','?')}/5 vs {s2.get('score','?')}/5", parse_mode='HTML')

@premium_required
async def cmd_history(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    fs=ctx.args[0].lower() if ctx.args else None; ch=get_recent_changes(10, fs)
    if not ch: await update.message.reply_text("📜 No changes yet.", parse_mode='HTML'); return
    m="📜 <b>Changes</b>\n\n"
    for c in ch: m += f"🔄 <b>{PROP_FIRMS.get(c['firm_slug'],{}).get('name',c['firm_slug'])}</b> {c.get('page_type','')}\n   {c.get('summary','')}\n   📅 {c.get('detected_at','')[:16]}\n\n"
    await update.message.reply_text(m, parse_mode='HTML')

@premium_required
async def cmd_scams(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    from database import get_connection
    cn=get_connection(); al=cn.execute("SELECT * FROM scam_alerts ORDER BY detected_at DESC LIMIT 10").fetchall(); cn.close()
    if not al: await update.message.reply_text("🚨 No alerts.", parse_mode='HTML'); return
    m="🚨 <b>Scam Alerts</b>\n\n"
    for a in al:
        sv={"high":"🔴","medium":"🟡","low":"🟢"}.get(a['severity'],"⚪")
        m += f"{sv} <b>{PROP_FIRMS.get(a['firm_slug'],{}).get('name',a['firm_slug'])}</b>\n   {a['description'][:100]}\n\n"
    await update.message.reply_text(m, parse_mode='HTML')

async def cmd_referral(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid=update.effective_user.id; get_or_create_user(uid, update.effective_user.username, update.effective_user.first_name)
    rc=get_referral_code(uid); t=get_total_referrals(uid); u=get_referral_count(uid)
    link=f"https://t.me/{bn(ctx)}?start=REF_{rc}"; p="🟢"*min(u,REFERRALS_NEEDED)+"⚪"*max(0,REFERRALS_NEEDED-u)
    m=f"👥 <b>Referral</b>\n\n🎁 {REFERRALS_NEEDED} friends → {REFERRAL_REWARD_DAYS}d FREE\n{p} ({u}/{REFERRALS_NEEDED})\n\n🔗 <code>{link}</code>"
    kb=[[InlineKeyboardButton("📤 Share",url=f"https://t.me/share/url?url={link}&text=Track+prop+firms!")]]
    await update.message.reply_text(m, parse_mode='HTML', reply_markup=InlineKeyboardMarkup(kb))

async def cmd_premium(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid=update.effective_user.id
    if is_premium(uid):
        from database import get_connection
        cn=get_connection(); r=cn.execute("SELECT premium_expires_at FROM users WHERE user_id=?",(uid,)).fetchone(); cn.close()
        await update.message.reply_text(f"💎 <b>Active!</b> Expires: {r['premium_expires_at'][:10] if r and r['premium_expires_at'] else 'N/A'}\n/referral to extend", parse_mode='HTML'); return
    kb=[]
    if STRIPE_API_KEY: kb.append([InlineKeyboardButton("💳 Monthly",callback_data="pay_stripe_monthly"),InlineKeyboardButton("💳 Yearly",callback_data="pay_stripe_yearly")])
    kb += [[InlineKeyboardButton("₿ USDT",callback_data="pay_crypto")],[InlineKeyboardButton("🆓 Referral",callback_data="referral_info")]]
    await update.message.reply_text(f"💎 <b>Premium</b>\n⚡ Real-time | 🧠 AI | 🚨 Scams\n\n${PREMIUM_PRICE_MONTHLY}/mo | ${PREMIUM_PRICE_YEARLY}/yr\n/referral for free!", parse_mode='HTML', reply_markup=InlineKeyboardMarkup(kb))

async def cmd_status(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid=update.effective_user.id; db=get_or_create_user(uid, update.effective_user.username, update.effective_user.first_name)
    pr,ad=is_premium(uid),is_admin(uid)
    st="👑 Admin+Premium" if ad and pr else "👑 Admin" if ad else "💎 Premium" if pr else "🆓 Free"
    exp=db.get('premium_expires_at','N/A'); exp=exp[:10] if exp and exp!='N/A' else exp
    m=f"👤 <b>Account</b>\n\n🆔 <code>{uid}</code>\n📊 <b>{st}</b>\n📅 Expires: {exp}\n👥 Refs: {get_total_referrals(uid)}\n🔑 <code>{db.get('referral_code','')}</code>"
    if ad: m+=f"\n\n🔐 IDs: {ADMIN_USER_IDS}\n📺 Ch: {PREMIUM_CHANNEL_ID or 'Not set'}\n→ /admin"
    await update.message.reply_text(m, parse_mode='HTML')

async def handle_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q=update.callback_query; await q.answer(); d=q.data
    if d=="firms_list":
        sc=get_latest_trustpilot_scores(); m="📊 <b>Firms</b>\n\n"
        for s,c in PROP_FIRMS.items(): v=sc.get(s,{}); m+=f"• <b>{c['name']}</b> {'⭐'+str(round(v.get('score',0),1)) if v.get('score') else '⭐N/A'}\n"
        await q.edit_message_text(m, parse_mode='HTML')
    elif d=="promos":
        ps=get_active_promos(); m="🎟️ <b>Promos</b>\n\n"
        for p in (ps or [])[:5]: m+=f"• {PROP_FIRMS.get(p['firm_slug'],{}).get('name','?')}: <code>{p.get('promo_code','?')}</code> {p.get('discount','')}\n"
        if not ps: m+="None right now."
        await q.edit_message_text(m, parse_mode='HTML')
    elif d=="premium_info": await q.edit_message_text(f"💎 ${PREMIUM_PRICE_MONTHLY}/mo\n⚡ Real-time | 🧠 AI | 🚨 Scams\n/premium or /referral", parse_mode='HTML')
    elif d=="referral_info":
        rc=get_referral_code(q.from_user.id); lk=f"https://t.me/{bn(ctx)}?start=REF_{rc}"
        await q.edit_message_text(f"👥 {REFERRALS_NEEDED} friends → {REFERRAL_REWARD_DAYS}d FREE\n<code>{lk}</code>\n/referral", parse_mode='HTML')
    elif d=="pay_crypto": await q.edit_message_text(f"₿ ${PREMIUM_PRICE_MONTHLY} USDT TRC20:\n<code>{CRYPTO_WALLET_USDT_TRC20}</code>\nTX → @PropFirmTrackerSupport", parse_mode='HTML')
    elif d in ("pay_stripe_monthly","pay_stripe_yearly","pay_stars"): await q.edit_message_text("Contact @PropFirmTrackerSupport", parse_mode='HTML')

# ══ ADMIN ═════════════════════════════════════════════
@admin_required
async def cmd_admin(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    st=get_user_stats(); from database import get_connection
    cn=get_connection(); tc=cn.execute("SELECT COUNT(*) as c FROM changes").fetchone()['c']; tp=cn.execute("SELECT COUNT(*) as c FROM promos WHERE is_active=1").fetchone()['c']; cn.close()
    await update.message.reply_text(f"👑 <b>Admin</b>\n\n👥 {st['total']} (💎{st['premium']})\n📈 {tc} changes | {tp} promos\n\n/stats /scrape\n/activate <code>[id] [days]</code>\n/addvip <code>[id] [days]</code>\n/broadcast <code>[msg]</code>", parse_mode='HTML')

@admin_required
async def cmd_stats(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    st=get_user_stats(); from database import get_connection
    cn=get_connection(); tc=cn.execute("SELECT COUNT(*)as c FROM changes").fetchone()['c']; tp=cn.execute("SELECT COUNT(*)as c FROM promos WHERE is_active=1").fetchone()['c']; ts=cn.execute("SELECT COUNT(*)as c FROM scam_alerts").fetchone()['c']; cn.close()
    await update.message.reply_text(f"📊 👥{st['total']} 💎{st['premium']} 🆕{st['today_new']}\n📈 Changes:{tc} Promos:{tp} Scams:{ts}\n💰 ~${st['premium']*PREMIUM_PRICE_MONTHLY:.0f} MRR", parse_mode='HTML')

@admin_required
async def cmd_activate(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not ctx.args: await update.message.reply_text("/activate <code>[id] [days=30]</code>", parse_mode='HTML'); return
    try: tid=int(ctx.args[0])
    except: await update.message.reply_text("❌ Invalid ID"); return
    d=int(ctx.args[1]) if len(ctx.args)>1 else 30
    get_or_create_user(tid); activate_premium(tid, d, "admin")
    await update.message.reply_text(f"✅ <code>{tid}</code> → {d}d premium", parse_mode='HTML')

@admin_required
async def cmd_addvip(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not ctx.args: await update.message.reply_text("🎟️ /addvip <code>[id] [days=30]</code>", parse_mode='HTML'); return
    try: tid=int(ctx.args[0])
    except: await update.message.reply_text("❌ Invalid ID"); return
    d=int(ctx.args[1]) if len(ctx.args)>1 else 30
    get_or_create_user(tid); activate_premium(tid, d, "admin_vip")
    inv=None
    if PREMIUM_CHANNEL_ID:
        try: lo=await ctx.bot.create_chat_invite_link(chat_id=PREMIUM_CHANNEL_ID,member_limit=1,name=f"VIP-{tid}"); inv=lo.invite_link
        except Exception as e: log_error(f"Invite: {e}", tag="ADMIN")
    ok=False
    try:
        m=f"🎉 <b>{d}d Premium!</b> 💎\n⚡ Real-time | 🧠 AI | 🚨 Scams\n"
        if inv: m+=f"\n🔗 VIP:\n{inv}\n"
        await ctx.bot.send_message(chat_id=tid, text=m+"\nEnjoy! 🚀", parse_mode='HTML'); ok=True
    except: pass
    await update.message.reply_text(f"✅ VIP <code>{tid}</code> {d}d\n🔗 {'✅' if inv else '❌'} 📨 {'✅' if ok else '❌'}", parse_mode='HTML')

@admin_required
async def cmd_broadcast(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not ctx.args: await update.message.reply_text("/broadcast <code>[msg]</code>", parse_mode='HTML'); return
    msg=" ".join(ctx.args); from database import get_connection
    cn=get_connection(); us=cn.execute("SELECT user_id FROM users WHERE is_banned=0").fetchall(); cn.close()
    await update.message.reply_text(f"📢 → {len(us)} users...")
    s,f=0,0
    for u in us:
        try: await ctx.bot.send_message(chat_id=u['user_id'],text=msg,parse_mode='HTML'); s+=1; await asyncio.sleep(0.05)
        except: f+=1
    await update.message.reply_text(f"📢 ✅{s} ❌{f}")

@admin_required
async def cmd_scrape(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🔍 Scraping...")
    from scrapers import PropFirmScraper, RedditScraper, TrustpilotScraper
    res=[]
    for nm,Cl in [("Firms",PropFirmScraper),("Reddit",RedditScraper),("Trustpilot",TrustpilotScraper)]:
        try: r=Cl().scrape_all(); res.append(f"{'✅' if r.get('errors',0)<3 else '⚠️'} {nm}: {r}")
        except Exception as e: res.append(f"❌ {nm}: {e}")
    await update.message.reply_text("📊 <b>Done</b>\n\n"+"\n".join(res), parse_mode='HTML')

async def cmd_support(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🆘 @PropFirmTrackerSupport", parse_mode='HTML')

async def error_handler(u, ctx): log_error(f"Bot: {ctx.error}", tag="ERROR")

async def post_init(app):
    cmds=[BotCommand("start","Start"),BotCommand("help","Commands"),BotCommand("firms","Firms"),BotCommand("promos","Promos"),
        BotCommand("scores","Trustpilot"),BotCommand("compare","Compare"),BotCommand("referral","Referral"),
        BotCommand("premium","Upgrade"),BotCommand("status","Account"),BotCommand("support","Help")]
    await app.bot.set_my_commands(cmds)
    log_info(f"Bot ready ✓ Admin: {ADMIN_USER_IDS}", tag="STARTUP")

def create_bot():
    log_info("Creating bot...", tag="STARTUP")
    app=Application.builder().token(TELEGRAM_BOT_TOKEN).post_init(post_init).build()
    for c,f in [("start",cmd_start),("help",cmd_help),("firms",cmd_firms),("promos",cmd_promos),
        ("scores",cmd_scores),("compare",cmd_compare),("referral",cmd_referral),("premium",cmd_premium),
        ("status",cmd_status),("support",cmd_support),("history",cmd_history),("scams",cmd_scams),
        ("admin",cmd_admin),("stats",cmd_stats),("activate",cmd_activate),("addvip",cmd_addvip),
        ("broadcast",cmd_broadcast),("scrape",cmd_scrape)]:
        app.add_handler(CommandHandler(c, f))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_error_handler(error_handler)
    log_info("Handlers ✓", tag="STARTUP"); return app
