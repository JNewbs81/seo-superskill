#!/usr/bin/env python3
"""Small deterministic SEO checker for static HTML outputs."""

from __future__ import annotations

import argparse
import json
import re
import sys
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse
from xml.etree import ElementTree


class PageParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.in_title = False
        self.in_heading = None
        self.in_jsonld = False
        self.title_parts = []
        self.headings = []
        self.meta = []
        self.links = []
        self.images = []
        self.html_attrs = {}
        self.jsonld_parts = []

    def handle_starttag(self, tag, attrs):
        attrs_dict = {k.lower(): (v or "") for k, v in attrs}
        tag = tag.lower()
        if tag == "html":
            self.html_attrs = attrs_dict
        elif tag == "title":
            self.in_title = True
        elif tag in {"h1", "h2", "h3", "h4", "h5", "h6"}:
            self.in_heading = tag
            self.headings.append({"tag": tag, "text": ""})
        elif tag == "meta":
            self.meta.append(attrs_dict)
        elif tag == "link":
            self.links.append(attrs_dict)
        elif tag == "img":
            self.images.append(attrs_dict)
        elif tag == "script" and attrs_dict.get("type", "").lower() == "application/ld+json":
            self.in_jsonld = True

    def handle_endtag(self, tag):
        tag = tag.lower()
        if tag == "title":
            self.in_title = False
        elif tag == self.in_heading:
            self.in_heading = None
        elif tag == "script" and self.in_jsonld:
            self.in_jsonld = False

    def handle_data(self, data):
        if self.in_title:
            self.title_parts.append(data)
        if self.in_heading and self.headings:
            self.headings[-1]["text"] += data
        if self.in_jsonld:
            self.jsonld_parts.append(data)


def clean(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def meta_content(page: PageParser, *, name=None, prop=None):
    for item in page.meta:
        if name and item.get("name", "").lower() == name.lower():
            return clean(item.get("content", ""))
        if prop and item.get("property", "").lower() == prop.lower():
            return clean(item.get("content", ""))
    return ""


def link_href(page: PageParser, rel: str):
    for item in page.links:
        rels = {part.lower() for part in item.get("rel", "").split()}
        if rel.lower() in rels:
            return clean(item.get("href", ""))
    return ""


def add(findings, level, message):
    findings.append({"level": level, "message": message})


def analyze_html(path: Path):
    parser = PageParser()
    try:
        parser.feed(path.read_text(encoding="utf-8", errors="replace"))
    except Exception as exc:
        return {"file": str(path), "findings": [{"level": "critical", "message": f"Could not parse HTML: {exc}"}]}

    findings = []
    title = clean("".join(parser.title_parts))
    desc = meta_content(parser, name="description")
    canonical = link_href(parser, "canonical")
    h1s = [h for h in parser.headings if h["tag"] == "h1" and clean(h["text"])]

    if not parser.html_attrs.get("lang"):
        add(findings, "critical", "Missing html lang attribute.")
    if not title:
        add(findings, "critical", "Missing title tag.")
    elif len(title) < 30 or len(title) > 65:
        add(findings, "warning", f"Title length is {len(title)} chars; target roughly 50-60.")
    if not desc:
        add(findings, "critical", "Missing meta description.")
    elif len(desc) < 80 or len(desc) > 170:
        add(findings, "warning", f"Meta description length is {len(desc)} chars; target roughly 140-160.")
    if len(h1s) == 0:
        add(findings, "critical", "Missing H1.")
    elif len(h1s) > 1:
        add(findings, "warning", f"Multiple H1s found: {len(h1s)}.")
    if not canonical:
        add(findings, "warning", "Missing canonical link.")
    elif not urlparse(canonical).scheme:
        add(findings, "warning", "Canonical URL should usually be absolute.")
    if not meta_content(parser, name="viewport"):
        add(findings, "warning", "Missing viewport meta tag.")

    missing_alt = [img.get("src", "(inline image)") for img in parser.images if "alt" not in img]
    if missing_alt:
        add(findings, "critical", f"{len(missing_alt)} image(s) missing alt attribute.")

    for field in ["og:title", "og:description", "og:image", "og:url"]:
        if not meta_content(parser, prop=field):
            add(findings, "opportunity", f"Missing Open Graph tag: {field}.")
    for field in ["twitter:card", "twitter:title", "twitter:description"]:
        if not meta_content(parser, name=field):
            add(findings, "opportunity", f"Missing Twitter tag: {field}.")

    if parser.jsonld_parts:
        try:
            json.loads(clean("".join(parser.jsonld_parts)))
        except json.JSONDecodeError as exc:
            add(findings, "critical", f"Invalid JSON-LD: {exc.msg}.")
    else:
        add(findings, "opportunity", "No JSON-LD structured data found.")

    if not findings:
        add(findings, "healthy", "No basic SEO issues found.")

    return {
        "file": str(path),
        "title": title,
        "description": desc,
        "canonical": canonical,
        "h1_count": len(h1s),
        "findings": findings,
    }


def analyze_robots(root: Path):
    path = root / "robots.txt"
    if not path.exists():
        return {"file": str(path), "findings": [{"level": "warning", "message": "robots.txt not found."}]}
    text = path.read_text(encoding="utf-8", errors="replace")
    findings = []
    if re.search(r"(?im)^\s*disallow:\s*/\s*$", text):
        add(findings, "critical", "robots.txt disallows the entire site.")
    if not re.search(r"(?im)^\s*sitemap:\s*\S+", text):
        add(findings, "opportunity", "robots.txt does not declare a sitemap.")
    if not findings:
        add(findings, "healthy", "robots.txt basic checks passed.")
    return {"file": str(path), "findings": findings}


def analyze_sitemap(root: Path):
    candidates = [root / "sitemap.xml", root / "sitemap_index.xml"]
    path = next((p for p in candidates if p.exists()), None)
    if not path:
        return {"file": str(root / "sitemap.xml"), "findings": [{"level": "warning", "message": "sitemap.xml not found."}]}
    findings = []
    try:
        tree = ElementTree.parse(path)
        locs = [el.text for el in tree.iter() if el.tag.endswith("loc") and el.text]
        if not locs:
            add(findings, "critical", "Sitemap has no loc entries.")
        bad = [loc for loc in locs if not urlparse(loc).scheme]
        if bad:
            add(findings, "warning", f"{len(bad)} sitemap URL(s) are not absolute.")
    except Exception as exc:
        add(findings, "critical", f"Could not parse sitemap XML: {exc}.")
    if not findings:
        add(findings, "healthy", "Sitemap basic checks passed.")
    return {"file": str(path), "findings": findings}


def collect_html(target: Path):
    if target.is_file():
        return [target] if target.suffix.lower() in {".html", ".htm"} else []
    return sorted([p for p in target.rglob("*") if p.suffix.lower() in {".html", ".htm"}])


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("target", help="HTML file or directory containing built/static HTML")
    parser.add_argument("--json", action="store_true", help="Emit JSON")
    args = parser.parse_args(argv)

    target = Path(args.target).expanduser().resolve()
    if not target.exists():
        print(f"Target not found: {target}", file=sys.stderr)
        return 2

    root = target if target.is_dir() else target.parent
    results = [analyze_html(path) for path in collect_html(target)]
    results.append(analyze_robots(root))
    results.append(analyze_sitemap(root))

    if args.json:
        print(json.dumps(results, indent=2))
    else:
        for result in results:
            print(f"\n{result['file']}")
            for finding in result["findings"]:
                print(f"  [{finding['level']}] {finding['message']}")

    has_critical = any(f["level"] == "critical" for r in results for f in r["findings"])
    return 1 if has_critical else 0


if __name__ == "__main__":
    raise SystemExit(main())

