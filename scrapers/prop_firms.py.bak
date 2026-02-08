"""
PropFirmTracker Bot - Prop Firm Scraper
=========================================
Scrapes prop firm websites for pricing, rules, and promo changes.
Uses content hashing to detect changes efficiently.
"""

import hashlib
import re
import time
import requests
from bs4 import BeautifulSoup
from utils.logger import log_info, log_error, log_debug, log_warn
from database import save_firm_snapshot, save_change, save_promo
from config import USER_AGENT, REQUEST_TIMEOUT, PROP_FIRMS


class PropFirmScraper:
    """Scrapes prop firm websites and detects changes."""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        })
        self.results = {"scraped": 0, "changes": 0, "errors": 0, "promos": 0}

    def _fetch_page(self, url):
        """Fetch a web page and return parsed soup + raw text."""
        try:
            response = self.session.get(url, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')

            # Remove scripts, styles, nav, footer for cleaner text
            for tag in soup(['script', 'style', 'nav', 'footer', 'header', 'iframe', 'noscript']):
                tag.decompose()

            text = soup.get_text(separator='\n', strip=True)
            # Clean up excessive whitespace
            text = re.sub(r'\n{3,}', '\n\n', text)
            text = re.sub(r' {2,}', ' ', text)

            return soup, text
        except requests.RequestException as e:
            log_error(f"Failed to fetch {url}: {e}", tag="SCRAPE")
            return None, None

    def _hash_content(self, text):
        """Generate MD5 hash of content for comparison."""
        if not text:
            return None
        # Normalize whitespace before hashing to avoid false positives
        normalized = re.sub(r'\s+', ' ', text.strip().lower())
        if not normalized:
            return None
        return hashlib.md5(normalized.encode('utf-8')).hexdigest()

    def _extract_promos(self, soup, text, firm_slug, url):
        """Try to extract promo codes from page content."""
        if not text:
            return

        promo_patterns = [
            # "code SAVE25", "coupon WINTER2025", "promo: SALE50"
            r'(?:code|coupon)[:\s]+["\']?([A-Z0-9]{4,20})["\']?',
            # "promo code SAVE25"
            r'promo\s+code[:\s]+["\']?([A-Z0-9]{4,20})["\']?',
            # "use code SAVE25", "enter SALE50", "apply WINTER2025"
            r'(?:use|enter|apply)\s+(?:code\s+)?["\']?([A-Z][A-Z0-9]{3,19})["\']?',
            # "SAVE25 for 25% off"
            r'([A-Z][A-Z0-9]{3,14})\s+(?:for|to get)\s+(\d+%?\s*(?:off|discount))',
        ]

        discount_patterns = [
            r'(\d+%\s*off)',
            r'(save\s*\d+%)',
            r'(\d+%\s*discount)',
            r'(\$\d+\s*off)',
        ]

        # Common words to filter out (not promo codes)
        false_positives = {
            'HTTP', 'HTML', 'HTTPS', 'TRUE', 'FALSE', 'NULL', 'NONE',
            'CODE', 'PROMO', 'ENTER', 'APPLY', 'COUPON', 'FREE',
            'PLEASE', 'CLICK', 'HERE', 'YOUR', 'THIS', 'THAT',
            'WITH', 'FROM', 'HAVE', 'WILL', 'JUST', 'MORE',
            'ALSO', 'SOME', 'THAN', 'THEM', 'THEN', 'WHEN',
        }

        found_codes = set()
        for pattern in promo_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                code = match.group(1).upper()
                # Must have at least one digit OR be longer than 5 chars with mixed case
                has_digit = any(c.isdigit() for c in code)
                if (len(code) >= 4 and 
                    code not in false_positives and 
                    (has_digit or len(code) >= 6)):
                    found_codes.add(code)

        # Find discount amounts
        discount = ""
        for pattern in discount_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                discount = match.group(1)
                break

        for code in found_codes:
            saved = save_promo(
                firm_slug=firm_slug,
                promo_code=code,
                discount=discount or "Unknown",
                description=f"Promo code found on {firm_slug} website",
                source_url=url
            )
            if saved:
                self.results["promos"] += 1
                log_info(f"🎟️  New promo found: {firm_slug} — {code} ({discount})", tag="SCRAPE")

    def scrape_firm(self, firm_slug, firm_config):
        """Scrape all pages for a single firm."""
        log_info(f"Scraping {firm_config['name']}...", tag="SCRAPE")

        pages_to_scrape = {
            "pricing": firm_config.get("pricing_url"),
            "rules": firm_config.get("rules_url"),
            "homepage": firm_config.get("url"),
            "blog": firm_config.get("blog_url"),
        }

        for page_type, url in pages_to_scrape.items():
            if not url:
                continue

            soup, text = self._fetch_page(url)
            if not text:
                self.results["errors"] += 1
                continue

            self.results["scraped"] += 1
            content_hash = self._hash_content(text)

            # Save snapshot and check for changes
            changed = save_firm_snapshot(firm_slug, page_type, content_hash, text[:5000])  # Limit stored text

            if changed:
                self.results["changes"] += 1
                summary = f"{firm_config['name']} - {page_type} page has been updated"
                save_change(
                    firm_slug=firm_slug,
                    page_type=page_type,
                    change_type="content_update",
                    old_hash=None,
                    new_hash=content_hash,
                    summary=summary
                )

            # Always check for promos on pricing and homepage
            if page_type in ("pricing", "homepage"):
                self._extract_promos(soup, text, firm_slug, url)

            # Be polite — small delay between requests
            time.sleep(1)

    def scrape_all(self):
        """Scrape all configured prop firms."""
        log_info(f"Starting full scrape of {len(PROP_FIRMS)} prop firms...", tag="SCRAPE")
        self.results = {"scraped": 0, "changes": 0, "errors": 0, "promos": 0}

        for firm_slug, firm_config in PROP_FIRMS.items():
            try:
                self.scrape_firm(firm_slug, firm_config)
            except Exception as e:
                log_error(f"Error scraping {firm_slug}: {e}", tag="SCRAPE")
                self.results["errors"] += 1

            # Delay between firms
            time.sleep(2)

        log_info(
            f"Scrape complete — Pages: {self.results['scraped']} | "
            f"Changes: {self.results['changes']} | "
            f"Promos: {self.results['promos']} | "
            f"Errors: {self.results['errors']}",
            tag="SCRAPE"
        )
        return self.results
