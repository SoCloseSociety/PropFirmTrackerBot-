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
