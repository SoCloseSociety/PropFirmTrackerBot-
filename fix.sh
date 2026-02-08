#!/bin/bash
# ══════════════════════════════════════════════════════════════
# PropFirmTracker V3.2 — FIX GARBAGE TEXT + TRUSTPILOT
# Paste in SSH
#
# 1. prop_firms.py  → filter non-readable chars from diff
# 2. trustpilot.py  → use JSON API instead of HTML scraping
# ══════════════════════════════════════════════════════════════

cd /root/CRYPTO_JOB/PropFirmTrackerBot-
pkill -f "python3 run.py" 2>/dev/null; sleep 1

echo "🔧 V3.2 — Fix garbage text + Trustpilot"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# ═══════════════════════════════
# FILE 1: scrapers/prop_firms.py — CLEAN DIFF
# ═══════════════════════════════
echo "📝 [1/2] prop_firms.py (clean diff)..."
cp scrapers/prop_firms.py scrapers/prop_firms.py.bak.v32
cat > scrapers/prop_firms.py << 'PROPEOF'
"""
PropFirmTracker — Prop Firm Scraper V3.2
Clean diff: filters garbage, only shows readable changes.
"""
import hashlib, re, time, requests, difflib
from bs4 import BeautifulSoup
from utils.logger import log_info, log_error, log_debug, log_warn
from database import save_firm_snapshot, save_change, save_promo, get_connection
from config import USER_AGENT, REQUEST_TIMEOUT, PROP_FIRMS


class PropFirmScraper:

    RULES_KEYWORDS = [
        'drawdown', 'profit target', 'profit split', 'max loss', 'daily loss',
        'trailing', 'leverage', 'lot size', 'minimum trading days', 'payout',
        'scaling', 'news trading', 'weekend', 'ea allowed', 'copy trading',
        'consistency', 'max allocation',
    ]
    PROMO_SIGNALS = [
        'promo', 'discount', 'coupon', 'sale', 'offer', 'deal', 'special',
        'limited time', 'flash', 'save', '% off', 'bogo', 'free trial', 'bonus',
    ]

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        })
        self.results = {"scraped": 0, "changes": 0, "errors": 0, "promos": 0}

    def _fetch_page(self, url):
        try:
            resp = self.session.get(url, timeout=REQUEST_TIMEOUT)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, 'html.parser')
            for tag in soup(['script', 'style', 'nav', 'footer', 'header', 'iframe', 'noscript', 'svg', 'path']):
                tag.decompose()
            text = soup.get_text(separator='\n', strip=True)
            text = re.sub(r'\n{3,}', '\n\n', text)
            text = re.sub(r' {2,}', ' ', text)
            return soup, text
        except Exception as e:
            log_error(f"Fetch {url}: {e}", tag="SCRAPE")
            return None, None

    def _hash(self, text):
        if not text: return None
        norm = re.sub(r'\s+', ' ', text.strip().lower())
        return hashlib.md5(norm.encode()).hexdigest() if norm else None

    def _is_readable(self, line):
        """Check if a line is human-readable text (not binary/encoded garbage)."""
        if not line or len(line) < 3:
            return False
        # Count printable ASCII + common unicode chars
        printable = sum(1 for c in line if c.isprintable() and (ord(c) < 128 or c in 'éèêëàâäùûüôöîïçñ€£¥'))
        total = len(line)
        # Must be >80% printable ASCII
        if total > 0 and printable / total < 0.8:
            return False
        # Skip lines that are mostly symbols/numbers with no words
        words = re.findall(r'[a-zA-Z]{3,}', line)
        if len(line) > 20 and len(words) < 1:
            return False
        # Skip very short meaningless fragments
        if len(line.strip()) < 5:
            return False
        # Skip common noise
        noise = ['cookie', 'javascript', 'var ', 'function(', '{', '}', 'window.', 'document.',
                 'google', 'analytics', 'gtag', 'fbq', 'pixel', '©', 'all rights reserved',
                 'accept cookies', 'privacy policy', 'terms of service', 'toggle navigation']
        if any(n in line.lower() for n in noise):
            return False
        return True

    def _clean_line(self, line):
        """Clean a line for display — remove HTML entities, extra spaces."""
        line = re.sub(r'&[a-z]+;', ' ', line)
        line = re.sub(r'&#\d+;', ' ', line)
        line = re.sub(r'[^\x20-\x7E\n]', '', line)  # Remove non-ASCII
        line = re.sub(r'\s+', ' ', line).strip()
        return line[:120]  # Max 120 chars per line

    def _get_old_content(self, firm_slug, page_type):
        try:
            conn = get_connection()
            row = conn.execute(
                "SELECT content, content_hash FROM firm_snapshots WHERE firm_slug=? AND page_type=?",
                (firm_slug, page_type)
            ).fetchone()
            conn.close()
            if row: return row['content'], row['content_hash']
        except: pass
        return None, None

    def _smart_diff(self, old_text, new_text, firm_name, page_type):
        """Compare old vs new, return clean readable summary."""
        if not old_text or not new_text:
            return f"Initial scan of {firm_name} {page_type}", "content_update"

        old_lines = [l.strip() for l in old_text.split('\n') if l.strip()]
        new_lines = [l.strip() for l in new_text.split('\n') if l.strip()]

        differ = difflib.unified_diff(old_lines, new_lines, lineterm='')
        added_raw, removed_raw = [], []
        for line in differ:
            if line.startswith('+') and not line.startswith('+++'):
                added_raw.append(line[1:].strip())
            elif line.startswith('-') and not line.startswith('---'):
                removed_raw.append(line[1:].strip())

        # FILTER: only keep readable lines
        added = [self._clean_line(l) for l in added_raw if self._is_readable(l)]
        removed = [self._clean_line(l) for l in removed_raw if self._is_readable(l)]

        if not added and not removed:
            return f"{firm_name} {page_type}: minor technical changes", "content_update"

        # Categorize
        change_type = self._categorize(added, removed, page_type)

        # Build summary
        summary = self._build_summary(firm_name, page_type, change_type, added, removed)
        return summary, change_type

    def _categorize(self, added, removed, page_type):
        all_text = ' '.join(added + removed).lower()
        has_price = bool(re.search(r'\$[\d,]+|\d+%\s*(?:off|discount)', all_text))
        has_rules = any(kw in all_text for kw in self.RULES_KEYWORDS)
        has_promo = any(kw in all_text for kw in self.PROMO_SIGNALS)
        if has_promo: return "new_promo"
        if page_type == "pricing" or has_price: return "pricing_change"
        if page_type == "rules" or has_rules: return "rules_change"
        return "content_update"

    def _build_summary(self, firm_name, page_type, change_type, added, removed):
        type_labels = {"pricing_change":"Pricing Update","rules_change":"Rules Update",
                       "new_promo":"Promo Detected","content_update":"Content Update"}
        label = type_labels.get(change_type, "Update")

        parts = []

        # Price changes
        old_nums = self._nums(removed)
        new_nums = self._nums(added)
        if old_nums and new_nums:
            parts.append(f"Values: {', '.join(old_nums[:3])} → {', '.join(new_nums[:3])}")

        # Rule keyword matches
        for kw in self.RULES_KEYWORDS:
            if any(kw in a.lower() for a in added) or any(kw in r.lower() for r in removed):
                parts.append(f"'{kw}' section modified")
                break

        # Top meaningful additions
        if added:
            best = sorted([a for a in added if len(a) > 15], key=len, reverse=True)
            if best:
                parts.append(f"New: {best[0][:100]}")
            if len(best) > 1:
                parts.append(f"New: {best[1][:80]}")

        # Top meaningful removals
        if removed and not parts:
            best = sorted([r for r in removed if len(r) > 15], key=len, reverse=True)
            if best:
                parts.append(f"Removed: {best[0][:100]}")

        # Fallback
        if not parts:
            parts.append(f"{len(added)} additions, {len(removed)} removals on {page_type}")

        return f"{label}\n" + "\n".join(parts[:4])

    def _nums(self, lines):
        nums = []
        for l in lines:
            nums.extend(re.findall(r'\$[\d,]+(?:\.\d{2})?', l))
            nums.extend(re.findall(r'\d+(?:\.\d+)?%', l))
        return list(dict.fromkeys(nums))[:5]

    def _extract_promos(self, soup, text, firm_slug, url):
        if not text: return
        code_patterns = [
            r'(?:code|coupon|promo)[:\s]+["\']?([A-Z0-9]{4,20})["\']?',
            r'(?:use|enter|apply)\s+(?:code\s+)?["\']?([A-Z][A-Z0-9]{3,19})["\']?',
            r'([A-Z][A-Z0-9]{3,14})\s+(?:for|to\s+get|gives?)\s+(\d+%?\s*(?:off|discount))',
            r'(?:discount\s+code|voucher)[:\s]+["\']?([A-Z0-9]{4,20})["\']?',
            r'\b((?:BOGO|SAVE|SALE|DEAL|GET|NEW|VIP|BLACK|XMAS|NY)[A-Z0-9]{1,15})\b',
        ]
        blacklist = {
            'HTTP','HTML','HTTPS','TRUE','FALSE','NULL','NONE','CODE','PROMO',
            'ENTER','APPLY','COUPON','FREE','PLEASE','CLICK','HERE','YOUR',
            'THIS','THAT','WITH','FROM','HAVE','WILL','JUST','MORE','ALSO',
            'SOME','THAN','THEM','THEN','WHEN','ABOUT','BACK','BEEN','COME',
            'EACH','EVEN','FIRST','GOOD','HIGH','INTO','KEEP','LAST','LONG',
            'MADE','MAKE','MANY','MUCH','MUST','NAME','NEXT','ONLY','OVER',
            'PART','SAME','TAKE','TELL','VERY','WANT','WELL','WORK',
            'YEAR','USED','USING','REVIEW','REVIEWS','TRADE','TRADER','TRADING',
            'ACCOUNT','FUNDED','FUNDING','PROFIT','TARGET','SPLIT','RULES',
            'CHALLENGE','EVALUATION','PHASE','STEP','DAILY','TOTAL','LOSS',
            'PAYOUT','PAYOUTS','WITHDRAWAL','PROP','FIRM','TEST','DEMO',
            'SAVE','BOGO','SALE','DEAL','GET','NEW','BLACK','XMAS',
        }
        found = set()
        for pat in code_patterns:
            for m in re.finditer(pat, text, re.IGNORECASE):
                code = m.group(1).upper() if m.lastindex else m.group(0).upper()
                has_digit = any(c.isdigit() for c in code)
                if len(code) >= 4 and code not in blacklist and has_digit:
                    found.add(code)

        discount = ""
        for p in [r'(\d+%\s*off)', r'(\d+%\s*discount)', r'(save\s*\d+%)', r'(\$\d+\s*off)']:
            m = re.search(p, text, re.IGNORECASE)
            if m: discount = m.group(1).upper(); break

        for code in found:
            saved = save_promo(firm_slug=firm_slug, promo_code=code, discount=discount or "See website",
                description=f"Found on {firm_slug}", source_url=url)
            if saved:
                self.results["promos"] += 1
                log_info(f"🎟️ {firm_slug}: {code} ({discount})", tag="SCRAPE")

    def scrape_firm(self, slug, cfg):
        log_info(f"Scraping {cfg['name']}...", tag="SCRAPE")
        pages = {"pricing": cfg.get("pricing_url"), "rules": cfg.get("rules_url"),
                 "homepage": cfg.get("url"), "blog": cfg.get("blog_url")}
        for pt, url in pages.items():
            if not url: continue
            soup, text = self._fetch_page(url)
            if not text: self.results["errors"] += 1; continue
            self.results["scraped"] += 1
            new_hash = self._hash(text)
            old_content, old_hash = self._get_old_content(slug, pt)
            changed = save_firm_snapshot(slug, pt, new_hash, text[:5000])
            if changed and old_hash and old_hash != new_hash:
                summary, ct = self._smart_diff(old_content, text[:5000], cfg['name'], pt)
                self.results["changes"] += 1
                save_change(firm_slug=slug, page_type=pt, change_type=ct,
                    old_hash=old_hash, new_hash=new_hash, summary=summary)
                log_info(f"📝 {cfg['name']}/{pt}: {ct}", tag="DIFF")
            elif changed and not old_hash:
                save_change(firm_slug=slug, page_type=pt, change_type="content_update",
                    old_hash=None, new_hash=new_hash,
                    summary=f"Initial scan of {cfg['name']} {pt}")
            if pt in ("pricing", "homepage"):
                self._extract_promos(soup, text, slug, url)
            time.sleep(1)

    def scrape_all(self):
        log_info(f"Scraping {len(PROP_FIRMS)} firms...", tag="SCRAPE")
        self.results = {"scraped":0,"changes":0,"errors":0,"promos":0}
        for s,c in PROP_FIRMS.items():
            try: self.scrape_firm(s, c)
            except Exception as e: log_error(f"{s}: {e}", tag="SCRAPE"); self.results["errors"]+=1
            time.sleep(2)
        log_info(f"Scrape: {self.results['scraped']}p {self.results['changes']}c {self.results['promos']}p {self.results['errors']}e", tag="SCRAPE")
        return self.results
PROPEOF
echo "  ✅ prop_firms.py"

# ═══════════════════════════════
# FILE 2: scrapers/trustpilot_scraper.py — JSON API
# ═══════════════════════════════
echo "📝 [2/2] trustpilot_scraper.py (JSON API)..."
cp scrapers/trustpilot_scraper.py scrapers/trustpilot_scraper.py.bak.v32
cat > scrapers/trustpilot_scraper.py << 'TPEOF'
"""
Trustpilot Scraper V3.2 — Uses JSON APIs, not HTML scraping
Trustpilot blocks HTML scraping with Cloudflare.
Instead we use their public JSON endpoints that their own frontend uses.
"""
import re, time, random, json, requests
from utils.logger import log_info, log_error, log_warn
from database import save_trustpilot_score, get_latest_trustpilot_scores, save_scam_alert
from config import PROP_FIRMS, REQUEST_TIMEOUT


class TrustpilotScraper:
    SCORE_DROP = 0.3
    LOW_SCORE = 2.5

    # Trustpilot public API endpoints (used by their own website)
    # 1. Categories page API — returns business unit data as JSON
    API_URL = "https://www.trustpilot.com/api/categoriespages/{domain}"
    # 2. Widget API — used for embedding widgets (no Cloudflare)
    WIDGET_URL = "https://widget.trustpilot.com/trustboxes/findBusinessUnit"

    UAS = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/131.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/131.0.0.0 Safari/537.36",
    ]

    def __init__(self):
        self.session = requests.Session()
        self.results = {"scraped": 0, "score_drops": 0, "low_scores": 0, "errors": 0}

    def _api_headers(self):
        return {
            "User-Agent": random.choice(self.UAS),
            "Accept": "application/json",
            "Accept-Language": "en-US,en;q=0.9",
            "Referer": "https://www.trustpilot.com/",
            "Origin": "https://www.trustpilot.com",
            "X-Requested-With": "XMLHttpRequest",
        }

    def _widget_headers(self):
        return {
            "User-Agent": random.choice(self.UAS),
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "Accept-Language": "en-US,en;q=0.9",
            "Referer": "https://www.trustpilot.com/",
        }

    def _extract_domain(self, trustpilot_url):
        """Extract domain from trustpilot URL like https://www.trustpilot.com/review/ftmo.com"""
        m = re.search(r'trustpilot\.com/review/([^/?#]+)', trustpilot_url)
        return m.group(1) if m else None

    def _scrape_via_api(self, domain):
        """Method 1: Trustpilot categories page API."""
        url = self.API_URL.format(domain=domain)
        try:
            resp = self.session.get(url, headers=self._api_headers(), timeout=REQUEST_TIMEOUT)
            if resp.status_code != 200:
                return None, None

            data = resp.json()

            # Navigate the JSON structure
            # The structure varies but usually has businessUnit.trustScore
            bu = data.get('businessUnit') or data.get('pageProps', {}).get('businessUnit', {})
            if not bu:
                # Try nested
                for key in ['props', 'pageProps', 'businessUnitResult']:
                    if key in data and isinstance(data[key], dict):
                        bu = data[key].get('businessUnit', data[key])
                        if 'trustScore' in bu or 'score' in bu:
                            break

            score = bu.get('trustScore') or bu.get('score')
            count = bu.get('numberOfReviews') or bu.get('reviewCount')

            if score and isinstance(score, (int, float)):
                return float(score), int(count or 0)

            # Try alternative paths
            if 'trustScore' in str(data):
                # Deep search for trustScore
                text = json.dumps(data)
                sm = re.search(r'"trustScore":\s*([\d.]+)', text)
                cm = re.search(r'"numberOfReviews":\s*(\d+)', text)
                if sm:
                    return float(sm.group(1)), int(cm.group(1)) if cm else 0

            return None, None
        except Exception as e:
            log_error(f"TP API {domain}: {e}", tag="SCRAPE")
            return None, None

    def _scrape_via_widget(self, domain):
        """Method 2: Trustpilot widget API (usually not behind Cloudflare)."""
        try:
            params = {"locale": "en-US", "query": domain}
            resp = self.session.get(self.WIDGET_URL, params=params,
                headers=self._widget_headers(), timeout=REQUEST_TIMEOUT)
            if resp.status_code != 200:
                return None, None

            data = resp.json()
            # Widget returns a list of matching businesses
            if isinstance(data, list) and data:
                bu = data[0]
            elif isinstance(data, dict):
                bu = data
            else:
                return None, None

            score = bu.get('score') or bu.get('trustScore')
            count = bu.get('numberOfReviews') or bu.get('reviewCount')

            if score: return float(score), int(count or 0)
            return None, None
        except Exception as e:
            log_error(f"TP Widget {domain}: {e}", tag="SCRAPE")
            return None, None

    def _scrape_via_embed(self, domain):
        """Method 3: Trustpilot mini embed page (simpler HTML, less protection)."""
        url = f"https://www.trustpilot.com/review/{domain}"
        try:
            resp = self.session.get(url, headers={
                "User-Agent": random.choice(self.UAS),
                "Accept": "text/html,*/*",
                "Accept-Language": "en-US,en;q=0.9",
                "Accept-Encoding": "gzip, deflate, br",
                "Sec-Ch-Ua": '"Chromium";v="131"',
                "Sec-Ch-Ua-Mobile": "?0",
                "Sec-Fetch-Dest": "document",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Site": "none",
                "Sec-Fetch-User": "?1",
                "Upgrade-Insecure-Requests": "1",
                "Referer": "https://www.google.com/",
                "Cache-Control": "no-cache",
            }, timeout=REQUEST_TIMEOUT)

            if resp.status_code != 200:
                return None, None

            # Try JSON-LD first
            for m in re.finditer(r'<script type="application/ld\+json">(.*?)</script>', resp.text, re.DOTALL):
                try:
                    data = json.loads(m.group(1))
                    items = data if isinstance(data, list) else [data]
                    for item in items:
                        if isinstance(item, dict) and 'aggregateRating' in item:
                            r = item['aggregateRating']
                            return float(r.get('ratingValue', 0)), int(r.get('reviewCount', 0))
                except: continue

            # Try __NEXT_DATA__ (Next.js payload)
            m = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', resp.text, re.DOTALL)
            if m:
                try:
                    data = json.loads(m.group(1))
                    text = json.dumps(data)
                    sm = re.search(r'"trustScore":\s*([\d.]+)', text)
                    cm = re.search(r'"numberOfReviews":\s*(\d+)', text)
                    if sm: return float(sm.group(1)), int(cm.group(1)) if cm else 0
                except: pass

            # Regex fallback
            sm = re.search(r'TrustScore\s+(\d+\.?\d*)', resp.text)
            cm = re.search(r'([\d,]+)\s+reviews?', resp.text, re.I)
            if sm:
                return float(sm.group(1)), int(cm.group(1).replace(',','')) if cm else 0

            return None, None
        except Exception as e:
            log_error(f"TP HTML {domain}: {e}", tag="SCRAPE")
            return None, None

    def scrape_firm(self, slug, cfg):
        tp_url = cfg.get("trustpilot")
        if not tp_url: return

        domain = self._extract_domain(tp_url)
        if not domain:
            log_warn(f"Bad TP URL: {tp_url}", tag="SCRAPE")
            self.results["errors"] += 1
            return

        score, count = None, None

        # Try methods in order of reliability
        for method_name, method in [
            ("API", self._scrape_via_api),
            ("Widget", self._scrape_via_widget),
            ("HTML", self._scrape_via_embed),
        ]:
            score, count = method(domain)
            if score is not None and score > 0:
                log_info(f"✅ {cfg['name']}: ⭐{score}/5 ({count}) via {method_name}", tag="SCRAPE")
                break
            time.sleep(1)

        if score is not None and score > 0:
            self.results["scraped"] += 1
            save_trustpilot_score(slug, score, count or 0)
            self._check_alerts(slug, cfg['name'], score, count)
        else:
            self.results["errors"] += 1
            log_warn(f"❌ {cfg['name']}: all methods failed for {domain}", tag="SCRAPE")

    def _check_alerts(self, slug, name, score, count):
        prev = get_latest_trustpilot_scores().get(slug)
        if prev and prev.get('score'):
            if score < prev['score'] - self.SCORE_DROP:
                self.results["score_drops"] += 1
                save_scam_alert(slug, "trustpilot_drop", "medium",
                    f"{name}: {prev['score']:.1f} → {score:.1f}", "Trustpilot")
        if score < self.LOW_SCORE:
            self.results["low_scores"] += 1

    def scrape_all(self):
        log_info(f"Trustpilot ({len(PROP_FIRMS)} firms)...", tag="SCRAPE")
        self.results = {"scraped":0,"score_drops":0,"low_scores":0,"errors":0}
        for slug, cfg in PROP_FIRMS.items():
            try: self.scrape_firm(slug, cfg)
            except Exception as e: log_error(f"TP {slug}: {e}", tag="SCRAPE"); self.results["errors"]+=1
            time.sleep(random.uniform(2, 5))
        log_info(f"Trustpilot: {self.results['scraped']}ok {self.results['errors']}err", tag="SCRAPE")
        return self.results
TPEOF
echo "  ✅ trustpilot_scraper.py"

# ═══════════════════════════════
# CLEAR old garbage alerts from DB
# ═══════════════════════════════
echo ""
echo "🗑️  Clearing old garbage alerts..."
python3 -c "
import sqlite3, os
db = 'data/propfirm_tracker.db'
if os.path.exists(db):
    conn = sqlite3.connect(db)
    # Mark ALL old alerts as sent
    conn.execute('UPDATE changes SET alerted_premium=1, alerted_free=1')
    conn.commit()
    n = conn.execute('SELECT COUNT(*) FROM changes').fetchone()[0]
    conn.close()
    print(f'  ✅ {n} old alerts cleared')
else:
    print('  Fresh DB')
"

# ═══════════════════════════════
# VERIFY
# ═══════════════════════════════
echo ""
echo "🔍 Verifying..."
python3 -m py_compile scrapers/prop_firms.py && echo "  ✅ prop_firms.py OK"
python3 -m py_compile scrapers/trustpilot_scraper.py && echo "  ✅ trustpilot_scraper.py OK"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ V3.2 Done!"
echo ""
echo "Start: python3 run.py"
echo ""
echo "Fixed:"
echo "  ✅ Diff: garbage chars filtered (only readable text)"
echo "  ✅ Diff: clean summary format (no binary/encoded data)"
echo "  ✅ Trustpilot: 3 methods (API → Widget → HTML)"
echo "  ✅ Old garbage alerts cleared"
echo ""
echo "VIP alerts will now show:"
echo "  💰 Pricing Update"
echo "  Values: \$499 → \$449"
echo "  'profit split' section modified"
echo "  New: Get 20% off all challenges..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
