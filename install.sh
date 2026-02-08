#!/bin/bash
# ══════════════════════════════════════════════════════════════
# PropFirmTracker V4 — INSTALLER
# Upload all V4 files to VPS then run: bash INSTALL.sh
#
# What V4 does:
#   - Clean text storage (no more garbage in alerts)
#   - Professional visual formatting everywhere
#   - Free channel content engine (4 post types in rotation)
#   - AI toggle (/ai on|off)
#   - Trustpilot multi-method (API + Widget + HTML)
#   - Flood control with smart retry
#   - Grouped VIP alerts (1 msg per firm)
# ══════════════════════════════════════════════════════════════

BOT_DIR="/root/CRYPTO_JOB/PropFirmTrackerBot-"
V4_DIR="$(cd "$(dirname "$0")" && pwd)"

cd "$BOT_DIR" || { echo "ERROR: $BOT_DIR not found"; exit 1; }
pkill -f "python3 run.py" 2>/dev/null; sleep 1

echo ""
echo "╔══════════════════════════════════════╗"
echo "║   PropFirmTracker V4 — Installer     ║"
echo "╚══════════════════════════════════════╝"
echo ""

# ═══════════════════ BACKUP ═══════════════════
echo "📦 Creating backup..."
BACKUP="backup_v4_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP"
for f in bot.py scheduler.py scrapers/prop_firms.py scrapers/reddit_scraper.py scrapers/trustpilot_scraper.py services/alert_service.py config.py; do
    if [ -f "$f" ]; then
        mkdir -p "$BACKUP/$(dirname $f)"
        cp "$f" "$BACKUP/$f"
    fi
done
echo "   Backup → $BACKUP/"
echo ""

# ═══════════════════ COPY FILES ═══════════════════
echo "📝 Installing V4 files..."

# Copy from V4 dir if available, otherwise use inline
if [ -f "$V4_DIR/bot.py" ]; then
    cp "$V4_DIR/bot.py" bot.py
    echo "   ✅ bot.py"
    cp "$V4_DIR/scheduler.py" scheduler.py
    echo "   ✅ scheduler.py"
    cp "$V4_DIR/scrapers/prop_firms.py" scrapers/prop_firms.py
    echo "   ✅ scrapers/prop_firms.py"
    cp "$V4_DIR/scrapers/trustpilot_scraper.py" scrapers/trustpilot_scraper.py
    echo "   ✅ scrapers/trustpilot_scraper.py"
    cp "$V4_DIR/services/alert_service.py" services/alert_service.py
    echo "   ✅ services/alert_service.py"
    # Reddit scraper stays V3 (RSS) — already working
    echo "   ℹ️  scrapers/reddit_scraper.py — kept (RSS v3 working)"
else
    echo "   ❌ V4 files not found in $V4_DIR"
    echo "   Upload all V4 files to VPS first!"
    exit 1
fi

# ═══════════════════ PATCH CONFIG ═══════════════════
echo ""
echo "🔧 Patching config.py..."

python3 << 'PYFIX'
with open("config.py", "r") as f:
    lines = f.readlines()

new = []
for line in lines:
    # Fix ADMIN_USER_IDS parsing
    if line.strip().startswith("ADMIN_USER_IDS") and "getenv" in line:
        new.append('ADMIN_USER_IDS = [int(x.strip()) for x in os.getenv("ADMIN_USER_IDS", "123456789").split(",") if x.strip()]\n')
    # Make sure channel IDs are clean strings
    elif "FREE_CHANNEL_ID" in line and "getenv" in line:
        new.append('FREE_CHANNEL_ID = os.getenv("FREE_CHANNEL_ID", "").strip()\n')
    elif "PREMIUM_CHANNEL_ID" in line and "getenv" in line:
        new.append('PREMIUM_CHANNEL_ID = os.getenv("PREMIUM_CHANNEL_ID", "").strip()\n')
    else:
        new.append(line)

with open("config.py", "w") as f:
    f.writelines(new)
print("   ✅ config.py patched")
PYFIX

# ═══════════════════ PATCH DATABASE ═══════════════════
echo ""
echo "🔧 Patching database.py..."

python3 << 'DBFIX'
with open("database.py", "r") as f:
    content = f.read()

# Add settings table if missing
if "bot_settings" not in content:
    # Add to init_database
    insert = '''
        conn.execute("""
            CREATE TABLE IF NOT EXISTS bot_settings (
                key TEXT PRIMARY KEY,
                value TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
'''
    # Find the last CREATE TABLE block and add after
    pos = content.rfind("CREATE TABLE IF NOT EXISTS reddit_mentions")
    if pos > 0:
        end = content.find("conn.commit()", pos)
        if end > 0:
            content = content[:end] + insert + "\n    " + content[end:]

if "def get_setting" not in content:
    content += '''

def get_setting(key, default=None):
    """Get a bot setting."""
    try:
        conn = get_connection()
        row = conn.execute("SELECT value FROM bot_settings WHERE key=?", (key,)).fetchone()
        conn.close()
        return row['value'] if row else default
    except:
        return default


def set_setting(key, value):
    """Set a bot setting."""
    conn = get_connection()
    conn.execute("""
        INSERT INTO bot_settings (key, value, updated_at) VALUES (?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=CURRENT_TIMESTAMP
    """, (key, str(value)))
    conn.commit()
    conn.close()
'''

with open("database.py", "w") as f:
    f.write(content)
print("   ✅ database.py patched (settings table + get/set)")
DBFIX

# ═══════════════════ CLEAN DB ═══════════════════
echo ""
echo "🗑️  Preparing database..."

python3 << 'CLEANDB'
import sqlite3, os
db = 'data/propfirm_tracker.db'
if not os.path.exists('data'):
    os.makedirs('data')
if os.path.exists(db):
    conn = sqlite3.connect(db)
    # Mark all old alerts as sent (avoid re-spam)
    conn.execute('UPDATE changes SET alerted_premium=1, alerted_free=1')
    # Clear old snapshots so next scrape stores CLEAN text
    conn.execute('DELETE FROM firm_snapshots')
    # Create settings table
    conn.execute("""CREATE TABLE IF NOT EXISTS bot_settings (
        key TEXT PRIMARY KEY, value TEXT, updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""")
    conn.execute("INSERT OR IGNORE INTO bot_settings (key, value) VALUES ('ai_enabled', 'off')")
    conn.commit()
    conn.close()
    print('   ✅ Old alerts marked sent')
    print('   ✅ Snapshots cleared (clean baseline)')
    print('   ✅ Settings table ready (AI: off)')
else:
    print('   ℹ️  Fresh start — DB will be created on first run')
CLEANDB

# ═══════════════════ VERIFY ═══════════════════
echo ""
echo "🔍 Verifying..."

python3 -c "from config import ADMIN_USER_IDS, FREE_CHANNEL_ID, PREMIUM_CHANNEL_ID; print(f'   Admin: {ADMIN_USER_IDS}'); print(f'   Free ch: {FREE_CHANNEL_ID}'); print(f'   VIP ch: {PREMIUM_CHANNEL_ID}')"

ERRORS=0
for f in bot.py scheduler.py scrapers/prop_firms.py scrapers/reddit_scraper.py scrapers/trustpilot_scraper.py services/alert_service.py database.py config.py; do
    if python3 -m py_compile "$f" 2>/dev/null; then
        echo "   ✅ $f"
    else
        echo "   ❌ $f — SYNTAX ERROR"
        ERRORS=$((ERRORS + 1))
    fi
done

echo ""
if [ $ERRORS -gt 0 ]; then
    echo "⚠️  $ERRORS file(s) have errors. Fix before starting!"
    echo "   Restore: cp -r $BACKUP/* ."
else
    echo "╔══════════════════════════════════════╗"
    echo "║         ✅ V4 INSTALLED!             ║"
    echo "╚══════════════════════════════════════╝"
    echo ""
    echo "   Start:  python3 run.py"
    echo ""
    echo "   ┌─────────────────────────────────┐"
    echo "   │ What's new in V4                │"
    echo "   ├─────────────────────────────────┤"
    echo "   │ ✅ Pro visual design            │"
    echo "   │ ✅ Free channel content engine  │"
    echo "   │    - Market updates             │"
    echo "   │    - Firm spotlights            │"
    echo "   │    - Reddit pulse               │"
    echo "   │    - Trading tips               │"
    echo "   │ ✅ Clean text diffs (no garbage)│"
    echo "   │ ✅ /ai on|off (Claude toggle)   │"
    echo "   │ ✅ Trustpilot API + Widget      │"
    echo "   │ ✅ Flood control + batching     │"
    echo "   │ ✅ Grouped VIP alerts           │"
    echo "   └─────────────────────────────────┘"
    echo ""
    echo "   First scrape = clean baseline (no alerts)"
    echo "   Second scrape (3h) = detect real changes"
    echo ""
    echo "   Free channel posts every ~6h:"
    echo "   📊 Market → 🎯 Spotlight → 💬 Reddit → 💡 Tip"
    echo ""
    echo "   AI:  /ai on  (in Telegram, ~\$0.01/change)"
fi
