from utils.logger import log_info, log_error, log_warn
from database import save_trustpilot_score, get_latest_trustpilot_scores, save_scam_alert
from config import PROP_FIRMS, REQUEST_TIMEOUT

class TrustpilotScraper:
    SCORE_DROP = 0.3
    LOW_SCORE = 2.5

    API_URL = "https://www.trustpilot.com/api/categoriespages/{domain}"
    WIDGET_URL = "https://widget.trustpilot.com/trustboxes/findBusinessUnit"

    UAS = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/131.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/131.0.0.0 Safari/537.36",
    ]

    def __init__(self):
        self.session = requests.Session()
        self.results = {"scraped": 0, "score_drops": 0, "low_scores": 0, "errors": 0}

    def _domain(self, url):
        m = re.search(r'trustpilot\.com/review/([^/?#]+)', url)
        return m.group(1) if m else None

    def _try_api(self, domain):
        try:
            r = self.session.get(self.API_URL.format(domain=domain), headers={
                "User-Agent": random.choice(self.UAS),
                "Accept": "application/json",
                "Referer": "https://www.trustpilot.com/",
            }, timeout=REQUEST_TIMEOUT)
            if r.status_code != 200:
                return None, None
            data = r.json()
            sm = data.get('data', {}).get('averageScore')
            cm = data.get('data', {}).get('numberOfReviews')
            if sm is not None and cm is not None:
                return float(sm), int(cm)
        except Exception as e:
            log_error(f"API error: {e}", tag="SCRAPE")
        return None, None

    def _try_widget(self, domain):
        try:
            r = self.session.get(self.WIDGET_URL, params={"locale": "en-US", "query": domain},
                headers={"User-Agent": random.choice(self.UAS), "Accept": "application/json"},
                timeout=REQUEST_TIMEOUT)
            if r.status_code != 200:
                return None, None
            data = r.json()
            bu = data[0] if isinstance(data, list) and data else data if isinstance(data, dict) else None
            if bu:
                sc = bu.get('score') or bu.get('trustScore')
                ct = bu.get('numberOfReviews') or bu.get('reviewCount')
                if sc is not None and ct is not None:
                    return float(sc), int(ct)
        except Exception as e:
            log_error(f"Widget error: {e}", tag="SCRAPE")
        return None, None

    def _try_html(self, domain):
        try:
            r = self.session.get(f"https://www.trustpilot.com/review/{domain}", headers={
                "User-Agent": random.choice(self.UAS),
                "Accept": "text/html,*/*",
                "Sec-Fetch-Dest": "document",
                "Sec-Fetch-Mode": "navigate",
                "Referer": "https://www.google.com/",
            }, timeout=REQUEST_TIMEOUT)
            if r.status_code != 200:
                return None, None

            # JSON-LD
            for m in re.finditer(r'<script type="application/ld\+json">(.*?)</script>', r.text, re.DOTALL):
                try:
                    items = json.loads(m.group(1))
                    if not isinstance(items, list):
                        items = [items]
                    for item in items:
                        if isinstance(item, dict) and 'aggregateRating' in item:
                            ar = item['aggregateRating']
                            return float(ar.get('ratingValue', 0)), int(ar.get('reviewCount', 0))
                except Exception as e:
                    log_error(f"JSON-LD error: {e}", tag="SCRAPE")

            # __NEXT_DATA__
            m = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', r.text, re.DOTALL)
            if m:
                try:
                    data = json.loads(m.group(1))
                    sm = data.get('props', {}).get('pageProps', {}).get('businessUnitPageData', {}).get('averageScore')
                    cm = data.get('props', {}).get('pageProps', {}).get('businessUnitPageData', {}).get('numberOfReviews')
                    if sm is not None and cm is not None:
                        return float(sm), int(cm)
                except Exception as e:
                    log_error(f"__NEXT_DATA__ error: {e}", tag="SCRAPE")
        except Exception as e:
            log_error(f"HTML error: {e}", tag="SCRAPE")
        return None, None

    def scrape_firm(self, slug, cfg):
        tp = cfg.get("trustpilot")
        if not tp:
            return
        domain = self._domain(tp)
        if not domain:
            self.results["errors"] += 1
            return

        score, count = None, None
        for method_name, method in [("API", self._try_api), ("Widget", self._try_widget), ("HTML", self._try_html)]:
            score, count = method(domain)
            if score and score > 0:
                log_info(f"TP {cfg['name']}: {score}/5 ({count}) via {method_name}", tag="SCRAPE")
                break
            time.sleep(1)

        if score and score > 0:
            self.results["scraped"] += 1
            save_trustpilot_score(slug, score, count or 0)
            prev = get_latest_trustpilot_scores().get(slug)
            if prev and prev.get('score') and score < prev['score'] - self.SCORE_DROP:
                self.results["score_drops"] += 1
                save_scam_alert(slug, "trustpilot_drop", "medium",
                    f"{cfg['name']}: {prev['score']:.1f} -> {score:.1f}", "Trustpilot")
            if score < self.LOW_SCORE:
                self.results["low_scores"] += 1
        else:
            self.results["errors"] += 1
            log_warn(f"TP {cfg['name']}: all methods failed", tag="SCRAPE")

    def scrape_all(self):
        log_info(f"Trustpilot ({len(PROP_FIRMS)} firms)...", tag="SCRAPE")
        self.results = {"scraped": 0, "score_drops": 0, "low_scores": 0, "errors": 0}
        for slug, cfg in PROP_FIRMS.items():
            try:
                self.scrape_firm(slug, cfg)
            except Exception as e:
                log_error(f"TP {slug}: {e}", tag="SCRAPE")
                self.results["errors"] += 1
            time.sleep(random.uniform(2, 5))
        log_info(f"Trustpilot: {self.results['scraped']}ok {self.results['errors']}err", tag="SCRAPE")
        return self.results