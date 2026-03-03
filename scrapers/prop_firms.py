"""
PropFirmTracker — Prop Firm Scraper V4
Clean text: strips all garbage before DB storage.
Smart diff: compares readable text only.
AI summaries: optional, toggled via /ai.
"""
import hashlib, re, time, requests, difflib
from bs4 import BeautifulSoup
from utils.logger import log_info, log_error, log_warn
from database import save_firm_snapshot, save_change, save_promo, get_connection, get_setting
from config import USER_AGENT, REQUEST_TIMEOUT, PROP_FIRMS


class PropFirmScraper:

    RULES_KW = ['drawdown', 'profit target', 'profit split', 'max loss', 'daily loss',
        'trailing', 'leverage', 'lot size', 'trading days', 'payout', 'scaling',
        'news trading', 'weekend', 'ea allowed', 'copy trading', 'consistency']

    NOISE = ['cookie', 'javascript', 'var ', 'function(', 'window.', 'document.',
        'analytics', 'gtag', 'fbq', 'pixel', 'adsbygoogle', 'webpack', '__next',
        'chunk', 'module.exports', 'sourcemap', 'base64', 'data:image', 'font-face',
        'keyframes', 'charset', 'viewport', 'robots', 'canonical']

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,*/*",
            "Accept-Language": "en-US,en;q=0.9",
        })
        self.results = {"scraped": 0, "changes": 0, "errors": 0, "promos": 0}
        self._ai = None

    def _get_ai(self):
        if self._ai is None:
            if get_setting("ai_enabled", "off") == "on":
                from services.ai_summarizer import AISummarizer
                self._ai = AISummarizer()
                if not self._ai.enabled:
                    self._ai = False
            else:
                self._ai = False
        return self._ai if self._ai else None

    def _fetch(self, url):
        try:
            resp = self.session.get(url, timeout=REQUEST_TIMEOUT)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, 'html.parser')
            for tag in soup(['script', 'style', 'nav', 'footer', 'header', 'iframe',
                             'noscript', 'svg', 'path', 'meta', 'link', 'img', 'video',
                             'audio', 'canvas', 'form', 'input', 'button', 'select']):
                tag.decompose()
            for el in soup.find_all(attrs={"class": re.compile(r'cookie|banner|modal|popup|overlay|tracking', re.I)}):
                el.decompose()
            text = soup.get_text(separator='\n', strip=True)
            return soup, self._clean(text)
        except Exception as e:
            log_error(f"Fetch {url}: {e}", tag="SCRAPE")
            return None, None

    def _clean(self, text):
        lines = text.split('\n')
        out = []
        for line in lines:
            line = line.strip()
            if not line:
                continue
            line = re.sub(r'[^\x20-\x7E]', '', line)
            line = re.sub(r'\s+', ' ', line).strip()
            if len(line) < 4 or len(line) > 500:
                continue
            words = re.findall(r'[a-zA-Z]{2,}', line)
            if len(words) < 2:
                continue
            if any(n in line.lower() for n in self.NOISE):
                continue
            out.append(line[:300])
        return '\n'.join(out)

    def _hash(self, text):
        if not text:
            return None
        return hashlib.md5(re.sub(r'\s+', ' ', text.strip().lower()).encode()).hexdigest()

    def _get_old(self, slug, pt):
        try:
            conn = get_connection()
            query = "SELECT content, content_hash FROM firm_snapshots WHERE firm_slug=? AND page_type=?"
            row = conn.execute(query, (slug, pt)).fetchone()
            conn.close()
            return (row['content'], row['content_hash']) if row else (None, None)
        except Exception as e:
            log_error(f"DB Error: {e}", tag="SCRAPE")
            return None, None

    def _diff(self, old, new, name, pt):
        if not old or not new:
            return f"Initial scan: {name} {pt}", "content_update", None

        old_l = [l.strip() for l in old.split('\n') if l.strip()]
        new_l = [l.strip() for l in new.split('\n') if l.strip()]
        added, removed = [], []
        for line in difflib.unified_diff(old_l, new_l, lineterm=''):
            if line.startswith('+') and not line.startswith('+++'):
                l = line[1:].strip()
                if len(l) > 5:
                    added.append(l[:150])
            elif line.startswith('-') and not line.startswith('---'):
                l = line[1:].strip()
                if len(l) > 5:
                    removed.append(l[:150])

        if not added and not removed:
            return f"{name} {pt}: minor changes", "content_update", None

        all_t = ' '.join(added + removed).lower()
        promo = any(k in all_t for k in ['promo', 'discount', 'coupon', 'sale', '% off', 'bogo', 'bonus'])
        rules = any(k in all_t for k in self.RULES_KW)
        price = bool(re.search(r'\$[\d,]+|\d+%', all_t))

        ct = "new_promo" if promo else "pricing_change" if (pt == "pricing" or price) else "rules_change" if (pt == "rules" or rules) else "content_update"
        summary = self._summary(name, pt, ct, added, removed)

        ai_text = None
        ai = self._get_ai()
        if ai:
            try:
                snippet = "Added:\n" + "\n".join(added[:10]) + "\n\nRemoved:\n" + "\n".join(removed[:10])
                ai_text = ai.summarize_change(name, pt, snippet)
                log_info(f"AI: {name}/{pt}", tag="AI")
            except Exception as e:
                log_error(f"AI: {e}", tag="AI")

        return summary, ct, ai_text

    def _summary(self, name, pt, ct, added, removed):
        labels = {"pricing_change": "Pricing Update", "rules_change": "Rules Update",
                  "new_promo": "Promo Detected", "content_update": "Content Update"}
        parts = [labels.get(ct, "Update")]

        old_n, new_n = [], []
        for l in removed:
            old_n.extend(re.findall(r'\$[\d,]+(?:\.\d{2})?|\d+(?:\.\d+)?%', l))
        for l in added:
            new_n.extend(re.findall(r'\$[\d,]+(?:\.\d{2})?|\d+(?:\.\d+)?%', l))
        old_n = list(dict.fromkeys(old_n))[:4]
        new_n = list(dict.fromkeys(new_n))[:4]

        if old_n and new_n:
            parts.append(f"Values: {', '.join(old_n)} -> {', '.join(new_n)}")

        for kw in self.RULES_KW:
            if any(kw in a.lower() for a in added + removed):
                parts.append(f"'{kw}' section modified")
                break

        best = sorted([a for a in added if len(a) > 20], key=len, reverse=True)
        if best:
            parts.append(f"New: {best[0][:100]}")

        if len(parts) == 1:
            parts.append(f"{len(added)} additions, {len(removed)} removals")

        return "\n".join(parts[:4])

    def _promos(self, soup, text, slug, url):
        if not text:
            return
        pats = [
            r'(?:code|coupon|promo)\s*[:\s]+\s*["\']?([A-Z0-9]{4,20})["\']?',
            r'(?:use|enter|apply)\s+(?:code\s+)?["\']?([A-Z][A-Z0-9]{3,19})["\']?',
            r'([A-Z][A-Z0-9]{3,14})\s+(?:for|to\s+get)\s+\d+%',
            r'\b((?:BOGO|SAVE|SALE|DEAL|GET|VIP|BLACK|XMAS|NY|NEW)\d{1,5}[A-Z0-9]{0,10})\b',
        ]
        bl = {'HTTP','HTML','HTTPS','TRUE','FALSE','NULL','NONE','CODE','PROMO','ENTER',
              'APPLY','COUPON','FREE','REVIEW','TRADE','TRADER','TRADING','ACCOUNT',
              'FUNDED','FUNDING','PROFIT','TARGET','RULES','CHALLENGE','PHASE','STEP',
              'DAILY','TOTAL','LOSS','PAYOUT','DEMO','TEST'}
        found = set()
        for pat in pats:
            for m in re.finditer(pat, text, re.I):
                code = m.group(1).upper() if m.lastindex else m.group(0).upper()
                if len(code) >= 4 and code not in bl and any(c.isdigit() for c in code):
                    found.add(code)

        disc = ""
        for p in [r'(\d+%\s*off)', r'(\d+%\s*discount)', r'(save\s+\d+%)', r'(\$\d+\s*off)']:
            m = re.search(p, text, re.I)
            if m:
                disc = m.group(1)
                break

        for code in found:
            if save_promo(slug, code, disc or "See website", f"Found on {slug}", url):
                self.results["promos"] += 1
                log_info(f"Promo: {slug} {code} ({disc})", tag="SCRAPE")

    def scrape_firm(self, slug, cfg):
        pages = {"pricing": cfg.get("pricing_url"), "rules": cfg.get("rules_url"),
                 "homepage": cfg.get("url"), "blog": cfg.get("blog_url")}
        for pt, url in pages.items():
            if not url:
                continue
            soup, text = self._fetch(url)
            if not text:
                self.results["errors"] += 1
                continue
            self.results["scraped"] += 1
            nh = self._hash(text)
            old_c, old_h = self._get_old(slug, pt)
            changed = save_firm_snapshot(slug, pt, nh, text[:5000])
            if changed and old_h and old_h != nh:
                summ, ct, ai_t = self._diff(old_c, text[:5000], cfg['name'], pt)
                self.results["changes"] += 1
                save_change(slug, pt, ct, old_h, nh, summ, ai_analysis=ai_t)
                log_info(f"Change: {cfg['name']}/{pt} ({ct})", tag="DIFF")
            elif changed and not old_h:
                save_change(slug, pt, "content_update", None, nh, f"Initial scan: {cfg['name']} {pt}")
            if pt in ("pricing", "homepage"):
                self._promos(soup, text, slug, url)
            time.sleep(1)

    def scrape_all(self):
        log_info(f"Scraping {len(PROP_FIRMS)} firms...", tag="SCRAPE")
        self.results = {"scraped": 0, "changes": 0, "errors": 0, "promos": 0}
        for s, c in PROP_FIRMS.items():
            try:
                self.scrape_firm(s, c)
            except Exception as e:
                log_error(f"{s}: {e}", tag="SCRAPE")
                self.results["errors"] += 1
            time.sleep(2)
        log_info(f"Scrape complete: {self.results['scraped']}p {self.results['changes']}c {self.results['promos']}pr {self.results['errors']}e", tag="SCRAPE")
        return self.results
