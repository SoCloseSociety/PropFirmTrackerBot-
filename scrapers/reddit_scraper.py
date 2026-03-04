import re, time, random, requests, xml.etree.ElementTree as ET
from html import unescape
from urllib.parse import urlparse, urljoin
from utils.logger import log_info, log_error, log_warn
from database import save_reddit_mention, save_scam_alert
from config import PROP_FIRMS, REDDIT_SUBREDDITS, REQUEST_TIMEOUT

class RedditScraper:
    ATOM="{http://www.w3.org/2005/Atom}"
    UAS=["Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/131.0.0.0 Safari/537.36",
         "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/131.0.0.0",
         "Mozilla/5.0 (X11; Linux x86_64; rv:133.0) Gecko/20100101 Firefox/133.0"]

    def __init__(self):
        self.session=requests.Session()
        self.results={"posts_found":0,"mentions":0,"scam_alerts":0,"errors":0}

    def _hdr(self):
        return {"User-Agent":random.choice(self.UAS),"Accept":"application/xml,*/*",
                "Accept-Language":"en-US,en;q=0.9","Referer":"https://www.google.com/"}

    def _is_valid_url(self, url):
        try:
            result = urlparse(url)
            return all([result.scheme, result.netloc])
        except ValueError:
            return False

    def _get(self, sub):
        base_url="https://www.reddit.com/r/{sub}/new/.rss"
        if not self._is_valid_url(base_url):
            log_error(f"Invalid URL: {base_url}", tag="SCRAPE")
            self.results["errors"]+=1
            return []
        try:
            r=self.session.get(base_url, headers=self._hdr(), timeout=REQUEST_TIMEOUT)
            if r.status_code==429: time.sleep(int(r.headers.get('Retry-After',15))); r=self.session.get(base_url,headers=self._hdr(),timeout=REQUEST_TIMEOUT)
            if r.status_code!=200: log_warn(f"r/{sub}: {r.status_code}", tag="SCRAPE"); self.results["errors"]+=1; return []
            return self._parse(r.text, sub)
        except Exception as e: log_error(f"r/{sub}: {e}", tag="SCRAPE"); self.results["errors"]+=1; return []

    def _parse(self, xml, sub):
        posts=[]
        try:
            for e in ET.fromstring(xml).findall(f"{self.ATOM}entry"):
                t=e.find(f"{self.ATOM}title"); l=e.find(f"{self.ATOM}link"); c=e.find(f"{self.ATOM}content")
                title=t.text if t is not None else ""
                link=l.get("href","") if l is not None else ""
                body=re.sub(r'\s+',' ',re.sub(r'<[^>]+>',' ',unescape(c.text or \'\')).strip()[:2000] if c is not None else ""
                posts.append({"title":title,"selftext":body,"url":link})
        except Exception as e: log_error(f"RSS parse r/{sub}: {e}", tag="SCRAPE")
        return posts

    def _firms(self, txt):
        tl=txt.lower(); found=[]; m={}
        for s,c in PROP_FIRMS.items():
            ns=[c['name'].lower(),s.replace('_',' ')]
            ns.extend({"ftmo":["ftmo"],"fundednext":["funded next"],"the5ers":["the5ers","5ers"],
                "myfundedfx":["my funded fx"],"topstep":["top step"],"apex_trader":["apex trader","apex funding"],
                "e8_funding":["e8 funding","e8markets"],"fundingpips":["funding pips"],
                "goatfunded":["goat funded"],"blueberry_funded":["blueberry funded"]}.get(s,[]))
            for n in ns: m[n]=s
        for n,s in m.items():
            if n in tl and s not in found: found.append(s)
        return found

    def _scam(self, txt):
        tl=txt.lower()
        kw=[k for k in ['scam','fraud','ponzi','rug pull',"won't pay","refused payout","denied payout",
            'stole','stolen','stay away','shutdown','bankrupt','no payout','fake reviews','rigged'] if k in tl]
        hi=['scam','fraud','ponzi','stole','stolen','bankrupt']
        return {"hit":bool(kw),"sev":"high" if any(k in tl for k in hi) else "medium"}

    def _sent(self, txt):
        tl=txt.lower()
        p=sum(1 for w in ['great','excellent','recommend','best','amazing','legit','reliable','fast payout'] if w in tl)
        n=sum(1 for w in ['terrible','worst','avoid','scam','horrible','slow payout','disappointed'] if w in tl)
        return "negative" if n>p else "positive" if p>n else "neutral"

    def scrape_sub(self, sub):
        log_info(f"Scraping r/{sub}...", tag="SCRAPE")
        posts=self._get(sub); self.results["posts_found"]+=len(posts)
        for p in posts:
            full=f"{p['title']} {p['selftext']}"; firms=self._firms(full)
            if not firms and any(k in full.lower() for k in ['prop firm','funded account','prop trading']): firms=['general']
            for slug in firms:
                save_reddit_mention(slug, sub, p['title'][:200], p['url'], 0, self._sent(full))
                self.results["mentions"]+=1
                sc=self._scam(full)
                if sc["hit"] and slug!='general':
                    save_scam_alert(slug,"reddit_scam",sc["sev"],f"r/{sub}: {p['title'][:150]}",p['url'])
                    self.results["scam_alerts"]+=1

    def scrape_all(self):
        log_info(f"Reddit RSS ({len(REDDIT_SUBREDDITS)} subs)...", tag="SCRAPE")
        self.results={"posts_found":0,"mentions":0,"scam_alerts":0,"errors":0}
        for sub in REDDIT_SUBREDDITS:
            try: self.scrape_sub(sub)
            except Exception as e: log_error(f"r/{sub}: {e}", tag="SCRAPE"); self.results["errors"]+=1
            time.sleep(random.uniform(3,6))
        log_info(f"Reddit: {self.results['posts_found']}p {self.results['mentions']}m {self.results['errors']}e", tag="SCRAPE")
        return self.results