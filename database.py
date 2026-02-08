"""
PropFirmTracker Bot - Database
================================
SQLite database for users, subscriptions, referrals, scraped data, and alerts.
"""

import sqlite3
import os
from datetime import datetime, timedelta
from utils.logger import log_info, log_error, log_debug

DATABASE_PATH = None


def get_db_path():
    global DATABASE_PATH
    if DATABASE_PATH is None:
        from config import DATABASE_PATH as cfg_path
        DATABASE_PATH = cfg_path
    return DATABASE_PATH


def get_connection():
    """Get a database connection."""
    db_path = get_db_path()
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_database():
    """Initialize all database tables."""
    log_info("Initializing database...", tag="DB")
    conn = get_connection()
    cursor = conn.cursor()

    # ── Users table ──────────────────────────────────────
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_premium INTEGER DEFAULT 0,
            premium_expires_at TIMESTAMP,
            referral_code TEXT UNIQUE,
            referred_by INTEGER,
            total_referrals INTEGER DEFAULT 0,
            is_banned INTEGER DEFAULT 0
        )
    """)

    # ── Referrals tracking ───────────────────────────────
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS referrals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            referrer_id INTEGER NOT NULL,
            referred_id INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            rewarded INTEGER DEFAULT 0,
            FOREIGN KEY (referrer_id) REFERENCES users(user_id),
            FOREIGN KEY (referred_id) REFERENCES users(user_id),
            UNIQUE(referred_id)
        )
    """)

    # ── Referral rewards log ─────────────────────────────
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS referral_rewards (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            days_awarded INTEGER NOT NULL,
            reason TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        )
    """)

    # ── Subscriptions / Payments ─────────────────────────
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            amount REAL,
            currency TEXT DEFAULT 'USD',
            method TEXT,
            stripe_session_id TEXT,
            status TEXT DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        )
    """)

    # ── Scraped firm data (latest snapshot) ──────────────
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS firm_snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            firm_slug TEXT NOT NULL,
            page_type TEXT NOT NULL,
            content_hash TEXT NOT NULL,
            content TEXT,
            scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(firm_slug, page_type)
        )
    """)

    # ── Change history (diffs detected) ──────────────────
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS changes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            firm_slug TEXT NOT NULL,
            page_type TEXT NOT NULL,
            change_type TEXT NOT NULL,
            old_hash TEXT,
            new_hash TEXT,
            summary TEXT,
            ai_analysis TEXT,
            detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            alerted_premium INTEGER DEFAULT 0,
            alerted_free INTEGER DEFAULT 0
        )
    """)

    # ── Promos detected ──────────────────────────────────
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS promos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            firm_slug TEXT NOT NULL,
            promo_code TEXT,
            discount TEXT,
            description TEXT,
            source_url TEXT,
            detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            expires_at TIMESTAMP,
            is_active INTEGER DEFAULT 1,
            alerted INTEGER DEFAULT 0
        )
    """)

    # ── Scam / negative review alerts ────────────────────
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS scam_alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            firm_slug TEXT NOT NULL,
            alert_type TEXT NOT NULL,
            severity TEXT DEFAULT 'medium',
            description TEXT,
            source TEXT,
            detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            alerted INTEGER DEFAULT 0
        )
    """)

    # ── Trustpilot scores history ────────────────────────
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS trustpilot_scores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            firm_slug TEXT NOT NULL,
            score REAL,
            review_count INTEGER,
            scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # ── Reddit mentions ──────────────────────────────────
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS reddit_mentions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            firm_slug TEXT,
            subreddit TEXT,
            post_title TEXT,
            post_url TEXT,
            score INTEGER DEFAULT 0,
            sentiment TEXT,
            detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(post_url)
        )
    """)

    conn.commit()
    conn.close()
    log_info("Database initialized successfully ✓", tag="DB")


# ══════════════════════════════════════════════════════════════
# USER MANAGEMENT
# ══════════════════════════════════════════════════════════════

def get_or_create_user(user_id, username=None, first_name=None, referred_by_code=None):
    """Get existing user or create a new one. Returns user dict."""
    conn = get_connection()
    cursor = conn.cursor()

    user = cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)).fetchone()

    if user is None:
        import hashlib
        referral_code = hashlib.md5(str(user_id).encode()).hexdigest()[:8].upper()

        # Check if referred by someone
        referrer_id = None
        if referred_by_code:
            referrer = cursor.execute(
                "SELECT user_id FROM users WHERE referral_code = ?", (referred_by_code,)
            ).fetchone()
            if referrer and referrer['user_id'] != user_id:
                referrer_id = referrer['user_id']

        cursor.execute("""
            INSERT INTO users (user_id, username, first_name, referral_code, referred_by)
            VALUES (?, ?, ?, ?, ?)
        """, (user_id, username, first_name, referral_code, referrer_id))

        # Record the referral
        if referrer_id:
            cursor.execute("""
                INSERT OR IGNORE INTO referrals (referrer_id, referred_id)
                VALUES (?, ?)
            """, (referrer_id, user_id))
            cursor.execute("""
                UPDATE users SET total_referrals = total_referrals + 1 WHERE user_id = ?
            """, (referrer_id,))
            log_info(f"New referral: {user_id} referred by {referrer_id}", tag="REF")

        conn.commit()
        user = cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)).fetchone()
        log_info(f"New user registered: {user_id} (@{username})", tag="BOT")
    
    conn.close()
    return dict(user)


def is_premium(user_id):
    """Check if a user has an active premium subscription."""
    conn = get_connection()
    user = conn.execute("SELECT is_premium, premium_expires_at FROM users WHERE user_id = ?", (user_id,)).fetchone()
    conn.close()

    if not user or not user['is_premium']:
        return False

    if user['premium_expires_at']:
        expires = datetime.fromisoformat(user['premium_expires_at'])
        if expires < datetime.now():
            # Expired — deactivate
            deactivate_premium(user_id)
            return False

    return True


def activate_premium(user_id, days=30, reason="payment"):
    """Activate premium for N days."""
    conn = get_connection()
    
    current = conn.execute("SELECT premium_expires_at FROM users WHERE user_id = ?", (user_id,)).fetchone()
    
    if current and current['premium_expires_at']:
        current_expiry = datetime.fromisoformat(current['premium_expires_at'])
        if current_expiry > datetime.now():
            new_expiry = current_expiry + timedelta(days=days)
        else:
            new_expiry = datetime.now() + timedelta(days=days)
    else:
        new_expiry = datetime.now() + timedelta(days=days)

    conn.execute("""
        UPDATE users SET is_premium = 1, premium_expires_at = ? WHERE user_id = ?
    """, (new_expiry.isoformat(), user_id))
    conn.commit()
    conn.close()
    log_info(f"Premium activated for user {user_id} — {days} days ({reason})", tag="PAY")


def deactivate_premium(user_id):
    """Deactivate premium."""
    conn = get_connection()
    conn.execute("UPDATE users SET is_premium = 0 WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()
    log_info(f"Premium deactivated for user {user_id}", tag="PAY")


def get_user_stats():
    """Get overall user statistics."""
    conn = get_connection()
    total = conn.execute("SELECT COUNT(*) as c FROM users").fetchone()['c']
    premium = conn.execute("SELECT COUNT(*) as c FROM users WHERE is_premium = 1").fetchone()['c']
    today = conn.execute(
        "SELECT COUNT(*) as c FROM users WHERE DATE(joined_at) = DATE('now')"
    ).fetchone()['c']
    conn.close()
    return {"total": total, "premium": premium, "today_new": today}


# ══════════════════════════════════════════════════════════════
# REFERRAL SYSTEM
# ══════════════════════════════════════════════════════════════

def get_referral_count(user_id):
    """Get number of unrewarded referrals for a user."""
    conn = get_connection()
    count = conn.execute(
        "SELECT COUNT(*) as c FROM referrals WHERE referrer_id = ? AND rewarded = 0",
        (user_id,)
    ).fetchone()['c']
    conn.close()
    return count


def get_total_referrals(user_id):
    """Get total number of referrals for a user."""
    conn = get_connection()
    count = conn.execute(
        "SELECT COUNT(*) as c FROM referrals WHERE referrer_id = ?",
        (user_id,)
    ).fetchone()['c']
    conn.close()
    return count


def check_and_reward_referrals(user_id, referrals_needed=3, reward_days=7):
    """Check if user has enough referrals for a reward. Returns True if rewarded."""
    unrewarded = get_referral_count(user_id)

    if unrewarded >= referrals_needed:
        conn = get_connection()
        # Mark referrals as rewarded
        refs = conn.execute(
            "SELECT id FROM referrals WHERE referrer_id = ? AND rewarded = 0 LIMIT ?",
            (user_id, referrals_needed)
        ).fetchall()

        for ref in refs:
            conn.execute("UPDATE referrals SET rewarded = 1 WHERE id = ?", (ref['id'],))

        conn.execute("""
            INSERT INTO referral_rewards (user_id, days_awarded, reason)
            VALUES (?, ?, ?)
        """, (user_id, reward_days, f"Referred {referrals_needed} users"))

        conn.commit()
        conn.close()

        activate_premium(user_id, days=reward_days, reason=f"referral_reward_{referrals_needed}")
        log_info(f"Referral reward: user {user_id} earned {reward_days} days premium!", tag="REF")
        return True

    return False


def get_referral_code(user_id):
    """Get the referral code for a user."""
    conn = get_connection()
    row = conn.execute("SELECT referral_code FROM users WHERE user_id = ?", (user_id,)).fetchone()
    conn.close()
    return row['referral_code'] if row else None


# ══════════════════════════════════════════════════════════════
# SCRAPER DATA
# ══════════════════════════════════════════════════════════════

def save_firm_snapshot(firm_slug, page_type, content_hash, content):
    """Save or update a firm page snapshot. Returns True if new/changed."""
    conn = get_connection()
    existing = conn.execute(
        "SELECT content_hash FROM firm_snapshots WHERE firm_slug = ? AND page_type = ?",
        (firm_slug, page_type)
    ).fetchone()

    if existing is None:
        conn.execute("""
            INSERT INTO firm_snapshots (firm_slug, page_type, content_hash, content)
            VALUES (?, ?, ?, ?)
        """, (firm_slug, page_type, content_hash, content))
        conn.commit()
        conn.close()
        log_debug(f"New snapshot saved: {firm_slug}/{page_type}", tag="DB")
        return True  # New entry
    elif existing['content_hash'] != content_hash:
        old_hash = existing['content_hash']
        conn.execute("""
            UPDATE firm_snapshots SET content_hash = ?, content = ?, scraped_at = CURRENT_TIMESTAMP
            WHERE firm_slug = ? AND page_type = ?
        """, (content_hash, content, firm_slug, page_type))
        conn.commit()
        conn.close()
        log_info(f"Change detected: {firm_slug}/{page_type} (hash changed)", tag="DIFF")
        return True  # Changed
    else:
        conn.close()
        return False  # No change


def save_change(firm_slug, page_type, change_type, old_hash, new_hash, summary, ai_analysis=None):
    """Record a detected change."""
    conn = get_connection()
    conn.execute("""
        INSERT INTO changes (firm_slug, page_type, change_type, old_hash, new_hash, summary, ai_analysis)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (firm_slug, page_type, change_type, old_hash, new_hash, summary, ai_analysis))
    conn.commit()
    conn.close()
    log_info(f"Change recorded: {firm_slug} - {change_type}", tag="DIFF")


def save_promo(firm_slug, promo_code, discount, description, source_url=None, expires_at=None):
    """Save a detected promo."""
    conn = get_connection()
    # Check if promo already exists
    existing = conn.execute(
        "SELECT id FROM promos WHERE firm_slug = ? AND promo_code = ? AND is_active = 1",
        (firm_slug, promo_code)
    ).fetchone()
    
    if existing is None:
        conn.execute("""
            INSERT INTO promos (firm_slug, promo_code, discount, description, source_url, expires_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (firm_slug, promo_code, discount, description, source_url, expires_at))
        conn.commit()
        conn.close()
        log_info(f"New promo detected: {firm_slug} - {promo_code} ({discount})", tag="ALERT")
        return True
    conn.close()
    return False


def get_active_promos():
    """Get all active promos."""
    conn = get_connection()
    promos = conn.execute(
        "SELECT * FROM promos WHERE is_active = 1 ORDER BY detected_at DESC"
    ).fetchall()
    conn.close()
    return [dict(p) for p in promos]


def save_scam_alert(firm_slug, alert_type, severity, description, source):
    """Save a scam/warning alert."""
    conn = get_connection()
    conn.execute("""
        INSERT INTO scam_alerts (firm_slug, alert_type, severity, description, source)
        VALUES (?, ?, ?, ?, ?)
    """, (firm_slug, alert_type, severity, description, source))
    conn.commit()
    conn.close()
    log_info(f"⚠️  Scam alert: {firm_slug} - {alert_type} ({severity})", tag="ALERT")


def save_trustpilot_score(firm_slug, score, review_count):
    """Save a Trustpilot score snapshot."""
    conn = get_connection()
    conn.execute("""
        INSERT INTO trustpilot_scores (firm_slug, score, review_count)
        VALUES (?, ?, ?)
    """, (firm_slug, score, review_count))
    conn.commit()
    conn.close()


def get_latest_trustpilot_scores():
    """Get latest Trustpilot score for each firm."""
    conn = get_connection()
    scores = conn.execute("""
        SELECT t1.* FROM trustpilot_scores t1
        INNER JOIN (
            SELECT firm_slug, MAX(scraped_at) as max_date
            FROM trustpilot_scores GROUP BY firm_slug
        ) t2 ON t1.firm_slug = t2.firm_slug AND t1.scraped_at = t2.max_date
    """).fetchall()
    conn.close()
    return {s['firm_slug']: dict(s) for s in scores}


def save_reddit_mention(firm_slug, subreddit, post_title, post_url, score=0, sentiment=None):
    """Save a Reddit mention."""
    conn = get_connection()
    try:
        conn.execute("""
            INSERT OR IGNORE INTO reddit_mentions (firm_slug, subreddit, post_title, post_url, score, sentiment)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (firm_slug, subreddit, post_title, post_url, score, sentiment))
        conn.commit()
    except Exception:
        pass
    conn.close()


def get_recent_changes(limit=10, firm_slug=None):
    """Get recent changes, optionally filtered by firm."""
    conn = get_connection()
    if firm_slug:
        changes = conn.execute(
            "SELECT * FROM changes WHERE firm_slug = ? ORDER BY detected_at DESC LIMIT ?",
            (firm_slug, limit)
        ).fetchall()
    else:
        changes = conn.execute(
            "SELECT * FROM changes ORDER BY detected_at DESC LIMIT ?", (limit,)
        ).fetchall()
    conn.close()
    return [dict(c) for c in changes]


def get_unalerted_changes(channel_type="premium"):
    """Get changes that haven't been alerted yet."""
    col = "alerted_premium" if channel_type == "premium" else "alerted_free"
    conn = get_connection()
    changes = conn.execute(
        f"SELECT * FROM changes WHERE {col} = 0 ORDER BY detected_at ASC"
    ).fetchall()
    conn.close()
    return [dict(c) for c in changes]


def mark_change_alerted(change_id, channel_type="premium"):
    """Mark a change as alerted."""
    col = "alerted_premium" if channel_type == "premium" else "alerted_free"
    conn = get_connection()
    conn.execute(f"UPDATE changes SET {col} = 1 WHERE id = ?", (change_id,))
    conn.commit()
    conn.close()


def get_all_premium_users():
    """Get all users with active premium."""
    conn = get_connection()
    users = conn.execute(
        "SELECT user_id FROM users WHERE is_premium = 1"
    ).fetchall()
    conn.close()
    return [u['user_id'] for u in users]
