#!/usr/bin/env python3
"""Read-only live checks for a bounded, same-origin canonical sitemap (stdlib only)."""
import argparse
import json
from concurrent.futures import ThreadPoolExecutor
from html.parser import HTMLParser
from urllib.error import HTTPError
from urllib.parse import urljoin, urlsplit
from urllib.request import Request, urlopen
from xml.etree import ElementTree as ET

class Page(HTMLParser):
    def __init__(self):
        super().__init__(); self.canonicals=[]; self.robots=[]; self.assets=set()
    def handle_starttag(self, tag, attrs):
        a=dict(attrs)
        if tag=='link':
            rel=a.get('rel','').split()
            if 'canonical' in rel: self.canonicals.append(a.get('href',''))
            if 'stylesheet' in rel or 'icon' in rel: self.assets.add(a.get('href',''))
        if tag=='meta' and a.get('name','').lower() in ('robots','googlebot'):
            self.robots.append(a.get('content',''))
        if tag in ('img','script') and a.get('src'): self.assets.add(a['src'])

def fetch(url):
    try:
        with urlopen(Request(url, headers={'User-Agent':'SEO-SuperSkill-LiveCheck/1.0'}),timeout=20) as r:
            return {'url':url,'status':r.status,'final_url':r.url,'headers':dict(r.headers),'body':r.read(4*1024*1024).decode('utf8','replace')}
    except HTTPError as e:
        return {'url':url,'status':e.code,'final_url':e.url,'headers':dict(e.headers),'body':''}
    except Exception as e: return {'url':url,'error':str(e),'body':''}

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('base_url'); ap.add_argument('--limit',type=int,default=100)
    args=ap.parse_args(); base=args.base_url.rstrip('/')+'/'
    origin=urlsplit(base)
    if origin.scheme!='https' or origin.username or origin.password: ap.error('Use a public HTTPS base URL without credentials.')
    same=lambda u:(urlsplit(u).scheme,urlsplit(u).netloc)==(origin.scheme,origin.netloc)
    sitemap=fetch(urljoin(base,'sitemap.xml')); robots=fetch(urljoin(base,'robots.txt'))
    if sitemap.get('status')!=200: raise SystemExit('Sitemap unavailable: '+str(sitemap.get('status',sitemap.get('error'))))
    xml=ET.fromstring(sitemap['body'])
    if xml.tag.endswith('sitemapindex'): raise SystemExit('Sitemap indexes require choosing a child URL sitemap; not traversed automatically.')
    urls=[e.text.strip() for e in xml.iter() if e.tag.split('}')[-1]=='loc' and e.text]
    if not 1<=args.limit<=500 or len(urls)>args.limit: raise SystemExit('Sitemap exceeds limit; choose an explicit limit up to 500.')
    if any(not same(u) for u in urls): raise SystemExit('Sitemap contains cross-origin URLs; not fetched.')
    pages=[]; assets=set()
    with ThreadPoolExecutor(max_workers=4) as pool:
        for r in pool.map(fetch,urls):
            p=Page(); p.feed(r.pop('body')); issues=[]
            if r.get('status')!=200: issues.append('Canonical page does not return 200.')
            if r.get('final_url')!=r['url']: issues.append('Sitemap URL redirects; inspect canonical destination.')
            if p.canonicals!=[r['url']]: issues.append('Canonical absent, duplicated, or different from sitemap URL.')
            headers={k.lower():v for k,v in r.get('headers',{}).items()}
            directives=' '.join(p.robots+[headers.get('x-robots-tag','')]).lower()
            if 'noindex' in directives or 'none' in directives.split(): issues.append('Potential noindex directive; inspect crawler-specific scope.')
            assets.update(u for a in p.assets if same(u:=urljoin(r['url'],a)))
            pages.append({**r,'canonicals':p.canonicals,'issues':issues})
        asset_rows=[]
        for r in pool.map(fetch,sorted(assets)):
            r.pop('body'); r['issues']=[]
            content_type=next((v for k,v in r.get('headers',{}).items() if k.lower()=='content-type'),'').lower()
            if r.get('status')!=200: r['issues'].append('Asset unavailable.')
            if 'text/html' in content_type: r['issues'].append('Expected asset returned HTML; inspect fallback or MIME configuration.')
            asset_rows.append(r)
    missing=fetch(urljoin(base,'seo-livecheck-nonexistent-page-404/'));missing.pop('body')
    result={'scope':'HTTP and HTML only; no ranking, rich-result, robots-policy, rendered or Core Web Vitals assessment',
            'pages_checked':len(pages),'duplicate_sitemap_urls':len(urls)-len(set(urls)),
            'sitemap':{k:v for k,v in sitemap.items() if k!='body'},
            'delivery_warnings':[r['url']+' redirects to '+r['final_url'] for r in [robots,sitemap]+asset_rows if r.get('final_url') and r['url']!=r['final_url']],
            'robots':{k:v for k,v in robots.items() if k!='body'},'robots_text':robots.get('body',''),
            'pages':pages,'same_origin_assets':asset_rows,'missing_page_probe':missing}
    print(json.dumps(result,indent=2))
    return int(any(p['issues'] for p in pages) or any(r['issues'] for r in asset_rows) or missing.get('status')!=404 or robots.get('status')!=200)

if __name__=='__main__': raise SystemExit(main())
