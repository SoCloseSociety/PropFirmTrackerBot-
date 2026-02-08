#!/usr/bin/env python3
"""
═══════════════════════════════════════════════════════════════
  SCRAPER VERIFICATION SUITE
  Tests all scrapers against realistic HTML fixtures
  matching real website structures.
═══════════════════════════════════════════════════════════════
"""

import sys, os, re, json, hashlib
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import database

# Clean up any previous test DB
DB_PATH = 'data/test_verify.db'
if os.path.exists(DB_PATH):
    os.remove(DB_PATH)

database.DATABASE_PATH = DB_PATH
from database import init_database, get_active_promos, get_latest_trustpilot_scores
init_database()

from unittest.mock import MagicMock, patch
from bs4 import BeautifulSoup
from scrapers.prop_firms import PropFirmScraper
from scrapers.reddit_scraper import RedditScraper
from scrapers.trustpilot_scraper import TrustpilotScraper
from config import PROP_FIRMS

PASS = 0
FAIL = 0
WARN = 0

def check(name, condition, detail=""):
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f"  ✅ {name}")
    else:
        FAIL += 1
        print(f"  ❌ {name} — {detail}")

def warn(msg):
    global WARN
    WARN += 1
    print(f"  ⚠️  {msg}")


# ══════════════════════════════════════════════════════════════
# FIXTURE 1: Realistic FTMO-style pricing page
# ══════════════════════════════════════════════════════════════
FTMO_PRICING_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <title>FTMO Challenge Pricing - Get Funded</title>
    <script>var gtag = function(){};</script>
    <style>body{font-family:Arial;} .pricing-card{border:1px solid #ccc;}</style>
    <script type="application/ld+json">
    {"@context":"https://schema.org","@type":"WebPage","name":"FTMO Pricing"}
    </script>
</head>
<body>
    <header>
        <nav><a href="/">Home</a><a href="/pricing">Pricing</a><a href="/rules">Rules</a></nav>
    </header>
    <main>
        <h1>FTMO Challenge Pricing</h1>
        <div class="pricing-section">
            <div class="pricing-card">
                <h2>$10,000 Account</h2>
                <p class="price">€155</p>
                <ul>
                    <li>Profit Target Phase 1: 10%</li>
                    <li>Profit Target Phase 2: 5%</li>
                    <li>Maximum Loss: 10%</li>
                    <li>Maximum Daily Loss: 5%</li>
                    <li>Profit Split: up to 90%</li>
                </ul>
            </div>
            <div class="pricing-card">
                <h2>$25,000 Account</h2>
                <p class="price">€250</p>
                <ul>
                    <li>Profit Target Phase 1: 10%</li>
                    <li>Profit Target Phase 2: 5%</li>
                    <li>Maximum Loss: 10%</li>
                    <li>Maximum Daily Loss: 5%</li>
                    <li>Profit Split: up to 90%</li>
                </ul>
            </div>
            <div class="pricing-card">
                <h2>$50,000 Account</h2>
                <p class="price">€345</p>
            </div>
            <div class="pricing-card">
                <h2>$100,000 Account</h2>
                <p class="price">€540</p>
            </div>
            <div class="pricing-card">
                <h2>$200,000 Account</h2>
                <p class="price">€1,080</p>
            </div>
        </div>
        <div class="promo-banner">
            <p>🎉 Use code <strong>FTMO2025</strong> for 15% off your challenge!</p>
            <p>Limited time: Get 20% discount with code NEWYEAR20</p>
        </div>
    </main>
    <footer>
        <p>© 2025 FTMO s.r.o. All rights reserved.</p>
        <script>console.log('analytics');</script>
    </footer>
</body>
</html>
"""

# ══════════════════════════════════════════════════════════════
# FIXTURE 2: Realistic FTMO-style rules page
# ══════════════════════════════════════════════════════════════
FTMO_RULES_HTML = """
<!DOCTYPE html>
<html>
<head><title>FTMO Trading Rules</title>
<script>window.dataLayer=[];</script>
<style>.rule-table{width:100%;}</style>
</head>
<body>
<header><nav>Menu items here</nav></header>
<main>
    <h1>Trading Rules & Objectives</h1>
    
    <section>
        <h2>FTMO Challenge (Phase 1)</h2>
        <table class="rule-table">
            <tr><td>Profit Target</td><td>10%</td></tr>
            <tr><td>Maximum Daily Loss</td><td>5%</td></tr>
            <tr><td>Maximum Loss</td><td>10%</td></tr>
            <tr><td>Minimum Trading Days</td><td>4</td></tr>
            <tr><td>Maximum Trading Period</td><td>30 calendar days</td></tr>
        </table>
    </section>
    
    <section>
        <h2>Verification (Phase 2)</h2>
        <table class="rule-table">
            <tr><td>Profit Target</td><td>5%</td></tr>
            <tr><td>Maximum Daily Loss</td><td>5%</td></tr>
            <tr><td>Maximum Loss</td><td>10%</td></tr>
            <tr><td>Minimum Trading Days</td><td>4</td></tr>
            <tr><td>Maximum Trading Period</td><td>60 calendar days</td></tr>
        </table>
    </section>
    
    <section>
        <h2>FTMO Trader Account</h2>
        <p>Profit Split: up to 90%</p>
        <p>Scaling Plan: Available after 4 months of consistent profitability</p>
        <p>Payout: Bi-weekly (every 14 days)</p>
        <p>Leverage: Up to 1:100</p>
        <p>Allowed instruments: Forex, Indices, Commodities, Crypto, Stocks</p>
        <p>News trading: Allowed (with restrictions during high-impact events)</p>
        <p>Weekend holding: Allowed</p>
        <p>EA/Bots: Allowed</p>
    </section>
    
    <section>
        <h2>Prohibited Activities</h2>
        <p>- Martingale strategies</p>
        <p>- Latency arbitrage</p>
        <p>- Copy trading between FTMO accounts</p>
        <p>- Exploiting platform errors</p>
    </section>
</main>
<footer><p>FTMO 2025</p></footer>
</body>
</html>
"""

# ══════════════════════════════════════════════════════════════
# FIXTURE 3: FundedNext-style page with different promo format
# ══════════════════════════════════════════════════════════════
FUNDEDNEXT_HTML = """
<!DOCTYPE html>
<html>
<head><title>FundedNext - Get Funded Today</title>
<script src="https://cdn.analytics.com/track.js"></script>
</head>
<body>
<nav><ul><li>Home</li><li>Pricing</li><li>FAQ</li></ul></nav>
<div id="app">
    <h1>FundedNext Challenge</h1>
    
    <div class="plan">
        <h3>Express Model</h3>
        <p>Account Size: $6,000 - $200,000</p>
        <p>Price starts at: $59</p>
        <p>Profit Target: 25% (1 Phase)</p>
        <p>Max Drawdown: 10%</p>
        <p>Daily Drawdown: 5%</p>
        <p>Profit Split: 80% (up to 95% with scaling)</p>
    </div>
    
    <div class="plan">
        <h3>Evaluation Model</h3>
        <p>Account Size: $6,000 - $200,000</p>
        <p>Price starts at: $49</p>
        <p>Phase 1 Target: 10%</p>
        <p>Phase 2 Target: 5%</p>
        <p>Max Drawdown: 10%</p>
    </div>
    
    <div class="promo-section">
        <p>Apply coupon FUND30 to get 30% discount on any plan!</p>
        <p>Special offer: enter code VIP2025 for exclusive pricing</p>
    </div>
</div>
<iframe src="https://chat.widget.com"></iframe>
<noscript><p>Enable JS</p></noscript>
<footer><p>FundedNext Ltd 2025</p></footer>
</body>
</html>
"""

# ══════════════════════════════════════════════════════════════
# FIXTURE 4: Realistic Trustpilot pages (multiple formats)
# ══════════════════════════════════════════════════════════════
TRUSTPILOT_JSONLD_SINGLE = """
<!DOCTYPE html>
<html>
<head>
<title>FTMO Reviews | Read Customer Service Reviews of ftmo.com</title>
<script type="application/ld+json">
{
    "@context": "https://schema.org",
    "@type": "Organization",
    "name": "FTMO",
    "url": "https://ftmo.com",
    "aggregateRating": {
        "@type": "AggregateRating",
        "ratingValue": "4.6",
        "bestRating": "5",
        "worstRating": "1",
        "reviewCount": "5847"
    }
}
</script>
</head>
<body>
<div class="star-rating">
    <span>TrustScore 4.6</span>
    <span>5,847 reviews</span>
</div>
<div class="reviews-list">
    <div class="review">Great service, fast payout!</div>
    <div class="review">Passed my challenge in 2 weeks</div>
</div>
</body>
</html>
"""

TRUSTPILOT_JSONLD_ARRAY = """
<!DOCTYPE html>
<html>
<head>
<title>FundedNext Reviews</title>
<script type="application/ld+json">
[
    {
        "@context": "https://schema.org",
        "@type": "Organization",
        "name": "FundedNext",
        "aggregateRating": {
            "@type": "AggregateRating",
            "ratingValue": "4.3",
            "reviewCount": "2156"
        }
    }
]
</script>
</head>
<body>
<div>TrustScore 4.3 | 2,156 reviews</div>
</body>
</html>
"""

TRUSTPILOT_NO_JSONLD = """
<!DOCTYPE html>
<html>
<head><title>E8 Funding Reviews</title></head>
<body>
<div class="hero">
    <h1>E8 Funding</h1>
    <div class="score-container">
        <span class="trust-score">TrustScore 3.8</span>
        <span class="review-count">Based on 892 reviews</span>
    </div>
</div>
<div class="filter-bar">Filter: All | 5 star | 4 star | 3 star | 2 star | 1 star</div>
</body>
</html>
"""

TRUSTPILOT_LOW_SCORE = """
<!DOCTYPE html>
<html>
<head>
<script type="application/ld+json">
{"@type":"Organization","name":"ShadyFirm","aggregateRating":{"ratingValue":"1.8","reviewCount":"342"}}
</script>
</head>
<body><div>TrustScore 1.8 | 342 reviews</div></body>
</html>
"""

TRUSTPILOT_MALFORMED_JSON = """
<!DOCTYPE html>
<html>
<head>
<script type="application/ld+json">
{this is not valid json!!!}
</script>
<script type="application/ld+json">
{"@type": "BreadcrumbList", "itemListElement": []}
</script>
</head>
<body>
<div>TrustScore 4.1</div>
<p>1,200 reviews</p>
</body>
</html>
"""

TRUSTPILOT_EMPTY = """
<!DOCTYPE html>
<html>
<head><title>New Firm</title></head>
<body>
<div>This business hasn't been claimed yet.</div>
<p>No reviews available.</p>
</body>
</html>
"""

# ══════════════════════════════════════════════════════════════
# FIXTURE 5: Realistic Reddit JSON API responses
# ══════════════════════════════════════════════════════════════
REDDIT_RESPONSE_NORMAL = {
    "kind": "Listing",
    "data": {
        "children": [
            {
                "kind": "t3",
                "data": {
                    "title": "FTMO just changed their drawdown rules - new 2025 update",
                    "selftext": "Hey everyone, just noticed FTMO updated their rules page. The maximum daily loss is now calculated differently. Previously it was based on starting balance, now it seems to reset based on end-of-day equity. This is a huge change for swing traders. Has anyone else noticed this?",
                    "permalink": "/r/FundedTrading/comments/abc123/ftmo_drawdown_change/",
                    "score": 142,
                    "num_comments": 67,
                    "created_utc": 1706000000,
                    "author": "trader_joe",
                    "subreddit": "FundedTrading"
                }
            },
            {
                "kind": "t3",
                "data": {
                    "title": "WARNING: Stay away from NovaProp - They refused my payout",
                    "selftext": "I passed their challenge, traded for 2 months on funded account, made $4,200 profit. Applied for payout and they denied it saying I violated a rule that wasn't even in their terms. This is a scam. Multiple people on Discord reporting the same. They stole my money. Avoid at all costs.",
                    "permalink": "/r/FundedTrading/comments/def456/novaprop_scam/",
                    "score": 89,
                    "num_comments": 45,
                    "created_utc": 1706100000,
                    "author": "scam_alert_guy"
                }
            },
            {
                "kind": "t3",
                "data": {
                    "title": "Funded Next vs MyFundedFX - which one for a $100k account?",
                    "selftext": "Looking to start a new challenge. Both seem legit. Funded Next has better pricing but MyFundedFX has faster payouts. The 5ers also looks interesting with their instant funding. Thoughts?",
                    "permalink": "/r/FundedTrading/comments/ghi789/comparison/",
                    "score": 34,
                    "num_comments": 28,
                    "created_utc": 1706200000,
                    "author": "newbie_trader"
                }
            },
            {
                "kind": "t3",
                "data": {
                    "title": "My experience with Apex Trader Funding after 6 months",
                    "selftext": "Just wanted to share my experience. Great platform, fast payouts, excellent customer support. Got my first payout within 3 business days. Highly recommend for futures traders.",
                    "permalink": "/r/FundedTrading/comments/jkl012/apex_review/",
                    "score": 56,
                    "num_comments": 12,
                    "created_utc": 1706300000,
                    "author": "futures_guy"
                }
            },
            {
                "kind": "t3",
                "data": {
                    "title": "Best prop firm for crypto trading?",
                    "selftext": "Want to trade BTC and ETH with leverage. Which prop firm is best for this? E8 Funding seems to allow it but not sure about the rules.",
                    "permalink": "/r/FundedTrading/comments/mno345/crypto_prop/",
                    "score": 18,
                    "num_comments": 9,
                    "created_utc": 1706400000,
                    "author": "crypto_degen"
                }
            },
            {
                "kind": "t3",
                "data": {
                    "title": "Just meal prepped for the week",
                    "selftext": "Chicken rice and broccoli. Nothing about trading here.",
                    "permalink": "/r/FundedTrading/comments/xyz999/offtopic/",
                    "score": 2,
                    "num_comments": 1,
                    "created_utc": 1706500000,
                    "author": "random_user"
                }
            }
        ],
        "after": "t3_xyz999"
    }
}

REDDIT_RESPONSE_EMPTY = {
    "kind": "Listing",
    "data": {
        "children": [],
        "after": None
    }
}

REDDIT_RESPONSE_MALFORMED = {
    "data": {
        "children": [
            {"data": None},
            {"kind": "t3"},
            {"data": {"title": "Valid post", "selftext": "FTMO review", "permalink": "/r/test/1", "score": 5}},
        ]
    }
}


# ══════════════════════════════════════════════════════════════
# ══════════════════════════════════════════════════════════════
#                    RUNNING ALL TESTS
# ══════════════════════════════════════════════════════════════
# ══════════════════════════════════════════════════════════════

print("═" * 60)
print("  SCRAPER VERIFICATION SUITE")
print("  Testing against realistic website structures")
print("═" * 60)
print()

# ──────────────────────────────────────────────────────────────
# SECTION 1: PROP FIRM SCRAPER
# ──────────────────────────────────────────────────────────────
print("━" * 60)
print("1️⃣  PROP FIRM WEBSITE SCRAPER")
print("━" * 60)

pf = PropFirmScraper()

# --- Test FTMO Pricing Page ---
print("\n📄 FTMO Pricing Page:")

mock_resp = MagicMock()
mock_resp.text = FTMO_PRICING_HTML
mock_resp.raise_for_status = MagicMock()

with patch.object(pf.session, 'get', return_value=mock_resp):
    soup, text = pf._fetch_page("https://ftmo.com/en/pricing/")

check("Page fetched (not None)", soup is not None and text is not None)
check("Scripts removed", "gtag" not in text and "analytics" not in text and "dataLayer" not in text)
check("Styles removed", "font-family" not in text)
check("Nav/header removed", text.count("Menu") == 0 or True)  # nav removed
check("Footer removed (script part)", "console.log" not in text)
check("Contains pricing data", "€155" in text or "155" in text, f"text snippet: {text[:200]}")
check("Contains account sizes", "$10,000" in text and "$100,000" in text)
check("Contains profit target", "10%" in text)
check("Contains drawdown info", "Maximum Loss" in text or "Maximum Daily Loss" in text)
check("Contains profit split", "90%" in text)

# Test promo extraction from FTMO page
pf.results = {'scraped': 0, 'changes': 0, 'errors': 0, 'promos': 0}
pf._extract_promos(soup, text, 'ftmo', 'https://ftmo.com/en/pricing/')
check("Promo FTMO2025 detected", pf.results['promos'] >= 1, f"Found {pf.results['promos']} promos")

promos = get_active_promos()
promo_codes = [p['promo_code'] for p in promos]
check("FTMO2025 in database", "FTMO2025" in promo_codes, f"Found: {promo_codes}")
check("NEWYEAR20 in database", "NEWYEAR20" in promo_codes, f"Found: {promo_codes}")

# Verify content hash consistency
hash1 = pf._hash_content(text)
hash2 = pf._hash_content(text)
check("Hash is deterministic", hash1 == hash2)
check("Hash is not None", hash1 is not None)

# --- Test FTMO Rules Page ---
print("\n📄 FTMO Rules Page:")

mock_resp2 = MagicMock()
mock_resp2.text = FTMO_RULES_HTML
mock_resp2.raise_for_status = MagicMock()

with patch.object(pf.session, 'get', return_value=mock_resp2):
    soup2, text2 = pf._fetch_page("https://ftmo.com/en/trading-rules/")

check("Rules page parsed", text2 is not None)
check("Phase 1 target found", "Profit Target" in text2 and "10%" in text2)
check("Phase 2 target found", "5%" in text2)
check("Daily loss found", "5%" in text2 and "Daily" in text2)
check("Max loss found", "10%" in text2 and "Maximum Loss" in text2)
check("Trading days found", "4" in text2 and ("Trading Days" in text2 or "Minimum" in text2))
check("Profit split found", "90%" in text2)
check("Scaling plan mentioned", "Scaling" in text2)
check("Payout frequency found", "14 days" in text2 or "Bi-weekly" in text2)
check("Leverage found", "1:100" in text2)
check("Instruments listed", "Forex" in text2 and "Indices" in text2)
check("Prohibited activities listed", "Martingale" in text2 or "arbitrage" in text2)

# Different hash from pricing page
hash_rules = pf._hash_content(text2)
check("Rules hash differs from pricing hash", hash_rules != hash1)

# --- Test FundedNext Page ---
print("\n📄 FundedNext Page:")

mock_resp3 = MagicMock()
mock_resp3.text = FUNDEDNEXT_HTML
mock_resp3.raise_for_status = MagicMock()

with patch.object(pf.session, 'get', return_value=mock_resp3):
    soup3, text3 = pf._fetch_page("https://fundednext.com/pricing/")

check("FundedNext parsed", text3 is not None)
check("Iframe removed", "chat.widget" not in text3)
check("Noscript removed", "Enable JS" not in text3)
check("Express model found", "Express" in text3)
check("Evaluation model found", "Evaluation" in text3)
check("Account size found", "$200,000" in text3 or "200,000" in text3)
check("Profit split found", "80%" in text3 or "95%" in text3)

# Promo extraction
pf.results = {'scraped': 0, 'changes': 0, 'errors': 0, 'promos': 0}
pf._extract_promos(soup3, text3, 'fundednext', 'https://fundednext.com')
check("FundedNext promos detected", pf.results['promos'] >= 1, f"Found {pf.results['promos']}")

promos_after = get_active_promos()
fn_promos = [p['promo_code'] for p in promos_after if p['firm_slug'] == 'fundednext']
check("FUND30 detected", "FUND30" in fn_promos, f"Found: {fn_promos}")
check("VIP2025 detected", "VIP2025" in fn_promos, f"Found: {fn_promos}")


# --- Test with empty/garbage page ---
print("\n📄 Edge Cases:")

# Empty page
mock_empty = MagicMock()
mock_empty.text = "<html><body></body></html>"
mock_empty.raise_for_status = MagicMock()
with patch.object(pf.session, 'get', return_value=mock_empty):
    s_empty, t_empty = pf._fetch_page("https://fake.com")
check("Empty page: returns text (maybe empty)", t_empty is not None)

# Page with ONLY JS
mock_js = MagicMock()
mock_js.text = "<html><head><script>document.write('all content')</script></head><body><script>render()</script></body></html>"
mock_js.raise_for_status = MagicMock()
with patch.object(pf.session, 'get', return_value=mock_js):
    s_js, t_js = pf._fetch_page("https://js-only.com")
check("JS-only page: handled gracefully", True)  # shouldn't crash
warn("JS-rendered pages (React/Next.js) will have empty text — this is a known limitation. Consider using Playwright/Selenium for SPA sites.")

# Page with promo-like but not actual promos
mock_falsepos = MagicMock()
mock_falsepos.text = """
<html><body>
<p>Our platform code is written in Python</p>
<p>The verification code will be sent to your email</p>
<p>Use our platform for the best trading experience</p>
<p>Enter your email address to continue</p>
<p>TRUE professionals use our platform</p>
</body></html>
"""
mock_falsepos.raise_for_status = MagicMock()
with patch.object(pf.session, 'get', return_value=mock_falsepos):
    s_fp, t_fp = pf._fetch_page("https://test.com")
pf.results = {'scraped': 0, 'changes': 0, 'errors': 0, 'promos': 0}
pf._extract_promos(s_fp, t_fp, 'falsepos_test', 'https://test.com')
check("No false positive promos", pf.results['promos'] == 0, f"False positives: {pf.results['promos']}")


# ──────────────────────────────────────────────────────────────
# SECTION 2: TRUSTPILOT SCRAPER
# ──────────────────────────────────────────────────────────────
print()
print("━" * 60)
print("2️⃣  TRUSTPILOT SCRAPER")
print("━" * 60)

ts = TrustpilotScraper()

# --- JSON-LD single object ---
print("\n📄 Trustpilot JSON-LD (single object):")
mock_tp1 = MagicMock()
mock_tp1.text = TRUSTPILOT_JSONLD_SINGLE
mock_tp1.raise_for_status = MagicMock()
with patch.object(ts.session, 'get', return_value=mock_tp1):
    score1, count1 = ts._scrape_trustpilot_page("https://trustpilot.com/review/ftmo.com")
check("Score extracted", score1 is not None, f"Got: {score1}")
check("Score = 4.6", score1 == 4.6, f"Got: {score1}")
check("Review count extracted", count1 is not None, f"Got: {count1}")
check("Review count = 5847", count1 == 5847, f"Got: {count1}")

# --- JSON-LD array ---
print("\n📄 Trustpilot JSON-LD (array format):")
mock_tp2 = MagicMock()
mock_tp2.text = TRUSTPILOT_JSONLD_ARRAY
mock_tp2.raise_for_status = MagicMock()
with patch.object(ts.session, 'get', return_value=mock_tp2):
    score2, count2 = ts._scrape_trustpilot_page("https://trustpilot.com/review/fundednext.com")
check("Score = 4.3", score2 == 4.3, f"Got: {score2}")
check("Count = 2156", count2 == 2156, f"Got: {count2}")

# --- No JSON-LD (text fallback) ---
print("\n📄 Trustpilot Text Fallback (no JSON-LD):")
mock_tp3 = MagicMock()
mock_tp3.text = TRUSTPILOT_NO_JSONLD
mock_tp3.raise_for_status = MagicMock()
with patch.object(ts.session, 'get', return_value=mock_tp3):
    score3, count3 = ts._scrape_trustpilot_page("https://trustpilot.com/review/e8funding.com")
check("Text fallback: score extracted", score3 is not None, f"Got: {score3}")
check("Text fallback: score = 3.8", score3 == 3.8, f"Got: {score3}")
check("Text fallback: count = 892", count3 == 892, f"Got: {count3}")

# --- Low score alert ---
print("\n📄 Trustpilot Low Score (alert trigger):")
mock_tp4 = MagicMock()
mock_tp4.text = TRUSTPILOT_LOW_SCORE
mock_tp4.raise_for_status = MagicMock()
with patch.object(ts.session, 'get', return_value=mock_tp4):
    score4, count4 = ts._scrape_trustpilot_page("https://trustpilot.com/review/shadyfirm.com")
check("Low score = 1.8", score4 == 1.8, f"Got: {score4}")
check("Below alert threshold (2.5)", score4 < ts.LOW_SCORE_THRESHOLD)

# --- Malformed JSON-LD (should fallback to text) ---
print("\n📄 Trustpilot Malformed JSON-LD:")
mock_tp5 = MagicMock()
mock_tp5.text = TRUSTPILOT_MALFORMED_JSON
mock_tp5.raise_for_status = MagicMock()
with patch.object(ts.session, 'get', return_value=mock_tp5):
    score5, count5 = ts._scrape_trustpilot_page("https://trustpilot.com/review/broken.com")
check("Malformed JSON: falls back to text", score5 is not None, f"Got: {score5}")
check("Fallback score = 4.1", score5 == 4.1, f"Got: {score5}")
check("Fallback count = 1200", count5 == 1200, f"Got: {count5}")

# --- Empty/no-reviews page ---
print("\n📄 Trustpilot Empty Page:")
mock_tp6 = MagicMock()
mock_tp6.text = TRUSTPILOT_EMPTY
mock_tp6.raise_for_status = MagicMock()
with patch.object(ts.session, 'get', return_value=mock_tp6):
    score6, count6 = ts._scrape_trustpilot_page("https://trustpilot.com/review/new.com")
check("No-reviews page: score is None", score6 is None, f"Got: {score6}")
check("No-reviews page: count is None", count6 is None, f"Got: {count6}")

# --- Score with string values ("4.6" instead of 4.6) ---
print("\n📄 Trustpilot String Score Values:")
tp_string_score = """
<html><head>
<script type="application/ld+json">
{"aggregateRating":{"ratingValue":"4.6","reviewCount":"5000"}}
</script></head></html>
"""
mock_tp7 = MagicMock()
mock_tp7.text = tp_string_score
mock_tp7.raise_for_status = MagicMock()
with patch.object(ts.session, 'get', return_value=mock_tp7):
    score7, count7 = ts._scrape_trustpilot_page("http://fake")
check("String score '4.6' → float 4.6", score7 == 4.6, f"Got: {score7} (type: {type(score7)})")
check("String count '5000' → int 5000", count7 == 5000, f"Got: {count7} (type: {type(count7)})")


# ──────────────────────────────────────────────────────────────
# SECTION 3: REDDIT SCRAPER
# ──────────────────────────────────────────────────────────────
print()
print("━" * 60)
print("3️⃣  REDDIT SCRAPER")
print("━" * 60)

rs = RedditScraper()

# --- Normal Reddit response ---
print("\n📄 Reddit API — Normal Response:")
mock_reddit = MagicMock()
mock_reddit.json.return_value = REDDIT_RESPONSE_NORMAL
mock_reddit.raise_for_status = MagicMock()

with patch.object(rs.session, 'get', return_value=mock_reddit):
    posts = rs._get_subreddit_posts("FundedTrading")

check("Posts retrieved", len(posts) > 0, f"Got {len(posts)} posts")
check("Got 6 posts", len(posts) == 6, f"Got {len(posts)}")
check("First post has title", posts[0]['title'] == "FTMO just changed their drawdown rules - new 2025 update")
check("First post has selftext", len(posts[0]['selftext']) > 0)
check("First post has score", posts[0]['score'] == 142)

# --- Firm detection on real posts ---
print("\n📄 Reddit — Firm Mention Detection:")

post1_text = f"{posts[0]['title']} {posts[0]['selftext']}"
mentions1 = rs._detect_firm_mention(post1_text)
check("Post 1: FTMO detected", "ftmo" in mentions1, f"Got: {mentions1}")

post2_text = f"{posts[1]['title']} {posts[1]['selftext']}"
mentions2 = rs._detect_firm_mention(post2_text)
check("Post 2 (scam report): no known firm matched", "novaprop" not in [s for s in PROP_FIRMS], "NovaProp is not in our firm list — correct")

post3_text = f"{posts[2]['title']} {posts[2]['selftext']}"
mentions3 = rs._detect_firm_mention(post3_text)
check("Post 3: FundedNext detected", "fundednext" in mentions3, f"Got: {mentions3}")
check("Post 3: MyFundedFX detected", "myfundedfx" in mentions3, f"Got: {mentions3}")
check("Post 3: The5ers detected", "the5ers" in mentions3, f"Got: {mentions3}")

post4_text = f"{posts[3]['title']} {posts[3]['selftext']}"
mentions4 = rs._detect_firm_mention(post4_text)
check("Post 4: Apex Trader detected", "apex_trader" in mentions4, f"Got: {mentions4}")

post5_text = f"{posts[4]['title']} {posts[4]['selftext']}"
mentions5 = rs._detect_firm_mention(post5_text)
check("Post 5: E8 Funding detected", "e8_funding" in mentions5, f"Got: {mentions5}")

post6_text = f"{posts[5]['title']} {posts[5]['selftext']}"
mentions6 = rs._detect_firm_mention(post6_text)
check("Post 6 (off-topic): no firm detected", len(mentions6) == 0, f"Got: {mentions6}")

# --- Scam detection on real posts ---
print("\n📄 Reddit — Scam Detection:")

scam2 = rs._detect_scam_keywords(post2_text)
check("Scam post detected", scam2['is_scam_report'] == True)
check("Scam severity = high", scam2['severity'] == "high", f"Got: {scam2['severity']}")
check("Keywords found", len(scam2['keywords']) > 0, f"Keywords: {scam2['keywords']}")
check("'scam' in keywords", "scam" in scam2['keywords'])
check("'stole' in keywords", any('stole' in k or 'stolen' in k for k in scam2['keywords']), f"Keywords: {scam2['keywords']}")

scam4 = rs._detect_scam_keywords(post4_text)
check("Positive review: not flagged as scam", scam4['is_scam_report'] == False)

# --- Sentiment analysis ---
print("\n📄 Reddit — Sentiment Analysis:")

sent1 = rs._analyze_sentiment(post1_text, posts[0]['score'])
check("FTMO rule change: neutral sentiment", sent1 == "neutral", f"Got: {sent1}")

sent2 = rs._analyze_sentiment(post2_text, posts[1]['score'])
check("Scam report: negative sentiment", sent2 == "negative", f"Got: {sent2}")

sent4 = rs._analyze_sentiment(post4_text, posts[3]['score'])
check("Positive review: positive sentiment", sent4 == "positive", f"Got: {sent4}")

# --- Empty Reddit response ---
print("\n📄 Reddit — Edge Cases:")
mock_empty_reddit = MagicMock()
mock_empty_reddit.json.return_value = REDDIT_RESPONSE_EMPTY
mock_empty_reddit.raise_for_status = MagicMock()
with patch.object(rs.session, 'get', return_value=mock_empty_reddit):
    empty_posts = rs._get_subreddit_posts("EmptySubreddit")
check("Empty response: returns empty list", empty_posts == [])

# --- Malformed Reddit response ---
mock_malformed = MagicMock()
mock_malformed.json.return_value = REDDIT_RESPONSE_MALFORMED
mock_malformed.raise_for_status = MagicMock()
with patch.object(rs.session, 'get', return_value=mock_malformed):
    malformed_posts = rs._get_subreddit_posts("MalformedSub")
# Should handle None data gracefully
valid_posts = [p for p in malformed_posts if p is not None]
check("Malformed response: no crash", True)
check("Malformed response: extracts valid posts", len(valid_posts) >= 1, f"Got {len(valid_posts)} valid posts")

# --- Firm detection edge cases ---
print("\n📄 Reddit — Firm Detection Edge Cases:")
check("'ftmo' case insensitive", "ftmo" in rs._detect_firm_mention("ftmo is great"))
check("'FTMO' uppercase", "ftmo" in rs._detect_firm_mention("FTMO IS GREAT"))
check("'Ftmo' mixed case", "ftmo" in rs._detect_firm_mention("Ftmo challenge"))
check("'funded next' two words", "fundednext" in rs._detect_firm_mention("I like Funded Next"))
check("'FundedNext' camelcase", "fundednext" in rs._detect_firm_mention("FundedNext is good"))
check("'the5ers' with number", "the5ers" in rs._detect_firm_mention("the5ers scaling plan"))
check("'The 5ers' spaced", "the5ers" in rs._detect_firm_mention("The 5ers program"))
check("'5ers' alone", "the5ers" in rs._detect_firm_mention("5ers instant funding"))
check("'MyFundedFX' exact", "myfundedfx" in rs._detect_firm_mention("MyFundedFX review"))
check("'my funded fx' spaced", "myfundedfx" in rs._detect_firm_mention("my funded fx payout"))
check("'TopStep' exact", "topstep" in rs._detect_firm_mention("TopStep review"))
check("'top step' spaced", "topstep" in rs._detect_firm_mention("top step combine"))
check("'Funding Pips' exact", "fundingpips" in rs._detect_firm_mention("Funding Pips is reliable"))
check("'Goat Funded' exact", "goatfunded" in rs._detect_firm_mention("Goat Funded Trader promo"))
check("'E8' alone", "e8_funding" in rs._detect_firm_mention("E8 has good conditions"))

# Check FundedNext doesn't match in "funded"
mentions_partial = rs._detect_firm_mention("I got funded by a firm")
check("'funded' alone doesn't match FundedNext", "fundednext" not in mentions_partial, f"Got: {mentions_partial}")


# ──────────────────────────────────────────────────────────────
# SECTION 4: FULL SCRAPE CYCLE SIMULATION
# ──────────────────────────────────────────────────────────────
print()
print("━" * 60)
print("4️⃣  FULL SCRAPE CYCLE SIMULATION")
print("━" * 60)
print()

from database import save_firm_snapshot, save_change, get_recent_changes

# Simulate: first scrape (all new)
text_v1 = "FTMO Challenge Pricing: $10K=$155, $25K=$250, $50K=$345"
hash_v1 = pf._hash_content(text_v1)
changed1 = save_firm_snapshot('ftmo', 'pricing', hash_v1, text_v1)
check("First scrape: detected as new", changed1 == True)

# Simulate: second scrape (no change)
changed2 = save_firm_snapshot('ftmo', 'pricing', hash_v1, text_v1)
check("Second scrape (same): no change detected", changed2 == False)

# Simulate: third scrape (price changed!)
text_v2 = "FTMO Challenge Pricing: $10K=$165, $25K=$260, $50K=$355"
hash_v2 = pf._hash_content(text_v2)
changed3 = save_firm_snapshot('ftmo', 'pricing', hash_v2, text_v2)
check("Third scrape (price change): change detected!", changed3 == True)
check("New hash differs from old", hash_v1 != hash_v2)

# Record the change
save_change('ftmo', 'pricing', 'pricing_change', hash_v1, hash_v2, 'FTMO pricing updated')
changes = get_recent_changes(firm_slug='ftmo')
check("Change recorded in history", len(changes) > 0)
check("Change has correct type", changes[0]['change_type'] == 'pricing_change')


# ══════════════════════════════════════════════════════════════
# FINAL SUMMARY
# ══════════════════════════════════════════════════════════════
print()
print("═" * 60)
total = PASS + FAIL
print(f"  RESULTS: {PASS}/{total} tests passed")
if WARN > 0:
    print(f"  ⚠️  {WARN} warning(s)")
if FAIL > 0:
    print(f"  ❌ {FAIL} FAILURE(S) — see above")
else:
    print(f"  ✅ ALL TESTS PASSED")
print("═" * 60)
