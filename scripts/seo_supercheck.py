#!/usr/bin/env python3
"""Deterministic SEO checker for static HTML outputs."""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urlparse, urlunparse
from xml.etree import ElementTree


HEADING_TAGS = {"h1", "h2", "h3", "h4", "h5", "h6"}
HTML_SUFFIXES = {".html", ".htm"}
INDEX_NAMES = {"index.html", "index.htm"}


class PageParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.in_title = False
        self.in_heading: str | None = None
        self.in_jsonld = False
        self.current_jsonld: list[str] = []
        self.title_parts: list[str] = []
        self.headings: list[dict[str, str]] = []
        self.meta: list[dict[str, str]] = []
        self.links: list[dict[str, str]] = []
        self.anchors: list[dict[str, str]] = []
        self.images: list[dict[str, str]] = []
        self.html_attrs: dict[str, str] = {}
        self.jsonld_scripts: list[str] = []

    def handle_starttag(self, tag, attrs):
        attrs_dict = {k.lower(): (v or "") for k, v in attrs}
        tag = tag.lower()
        if tag == "html":
            self.html_attrs = attrs_dict
        elif tag == "title":
            self.in_title = True
        elif tag in HEADING_TAGS:
            self.in_heading = tag
            self.headings.append({"tag": tag, "text": ""})
        elif tag == "meta":
            self.meta.append(attrs_dict)
        elif tag == "link":
            self.links.append(attrs_dict)
        elif tag == "a":
            self.anchors.append(attrs_dict)
        elif tag == "img":
            self.images.append(attrs_dict)
        elif tag == "script" and attrs_dict.get("type", "").lower() == "application/ld+json":
            self.in_jsonld = True
            self.current_jsonld = []

    def handle_endtag(self, tag):
        tag = tag.lower()
        if tag == "title":
            self.in_title = False
        elif tag == self.in_heading:
            self.in_heading = None
        elif tag == "script" and self.in_jsonld:
            self.in_jsonld = False
            self.jsonld_scripts.append("".join(self.current_jsonld))
            self.current_jsonld = []

    def handle_data(self, data):
        if self.in_title:
            self.title_parts.append(data)
        if self.in_heading and self.headings:
            self.headings[-1]["text"] += data
        if self.in_jsonld:
            self.current_jsonld.append(data)


def clean(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def normalize_url(url: str) -> str:
    parsed = urlparse(clean(url))
    scheme = parsed.scheme.lower()
    netloc = parsed.netloc.lower()
    path = re.sub(r"/{2,}", "/", parsed.path or "/")
    if path != "/" and path.endswith("/"):
        path = path[:-1]
    return urlunparse((scheme, netloc, path, "", parsed.query, ""))


def meta_content(page: PageParser, *, name=None, prop=None) -> str:
    for item in page.meta:
        if name and item.get("name", "").lower() == name.lower():
            return clean(item.get("content", ""))
        if prop and item.get("property", "").lower() == prop.lower():
            return clean(item.get("content", ""))
    return ""


def meta_contents(page: PageParser, *, name=None, prop=None) -> list[str]:
    values = []
    for item in page.meta:
        if name and item.get("name", "").lower() == name.lower():
            values.append(clean(item.get("content", "")))
        if prop and item.get("property", "").lower() == prop.lower():
            values.append(clean(item.get("content", "")))
    return values


def link_values(page: PageParser, rel: str, attr="href") -> list[str]:
    values = []
    for item in page.links:
        rels = {part.lower() for part in item.get("rel", "").split()}
        if rel.lower() in rels:
            values.append(clean(item.get(attr, "")))
    return values


def add(findings, level, message):
    if level != "healthy":
        findings[:] = [finding for finding in findings if finding["level"] != "healthy"]
    findings.append({"level": level, "message": message})


def jsonld_types(value) -> list[str]:
    if isinstance(value, list):
        types = []
        for item in value:
            types.extend(jsonld_types(item))
        return types
    if not isinstance(value, dict):
        return []
    types = []
    raw_type = value.get("@type")
    if isinstance(raw_type, list):
        types.extend(str(item) for item in raw_type)
    elif raw_type:
        types.append(str(raw_type))
    graph = value.get("@graph")
    if graph:
        types.extend(jsonld_types(graph))
    return types


def heading_level(tag: str) -> int:
    return int(tag[1])


def analyze_heading_hierarchy(page: PageParser, findings):
    last_level = 0
    for heading in page.headings:
        text = clean(heading["text"])
        if not text:
            add(findings, "warning", f"Empty {heading['tag'].upper()} heading.")
            continue
        level = heading_level(heading["tag"])
        if last_level and level > last_level + 1:
            add(findings, "warning", f"Heading hierarchy jumps from H{last_level} to H{level}.")
        last_level = level


def local_link_target(root: Path, page_path: Path, href: str) -> Path | None:
    href = clean(href)
    if not href or href.startswith(("#", "mailto:", "tel:", "javascript:")):
        return None
    parsed = urlparse(href)
    if parsed.scheme or parsed.netloc:
        return None
    raw_path = parsed.path
    if not raw_path:
        return None
    base = root if raw_path.startswith("/") else page_path.parent
    target = (base / raw_path.lstrip("/")).resolve()
    if raw_path.endswith("/"):
        return target / "index.html"
    if target.suffix:
        return target
    return target.with_suffix(".html")


def analyze_html(path: Path, root: Path):
    parser = PageParser()
    try:
        parser.feed(path.read_text(encoding="utf-8", errors="replace"))
    except Exception as exc:
        return {"file": str(path), "findings": [{"level": "critical", "message": f"Could not parse HTML: {exc}"}]}

    findings: list[dict[str, str]] = []
    title = clean("".join(parser.title_parts))
    descriptions = meta_contents(parser, name="description")
    desc = descriptions[0] if descriptions else ""
    canonicals = link_values(parser, "canonical")
    canonical = canonicals[0] if canonicals else ""
    robots = meta_content(parser, name="robots").lower()
    googlebot = meta_content(parser, name="googlebot").lower()
    h1s = [h for h in parser.headings if h["tag"] == "h1" and clean(h["text"])]

    if not parser.html_attrs.get("lang"):
        add(findings, "critical", "Missing html lang attribute.")
    if not meta_content(parser, name="viewport"):
        add(findings, "warning", "Missing viewport meta tag.")
    if not any("charset" in item for item in parser.meta):
        add(findings, "warning", "Missing charset meta tag.")

    if not title:
        add(findings, "critical", "Missing title tag.")
    elif len(title) < 30 or len(title) > 65:
        add(findings, "warning", f"Title length is {len(title)} chars; target roughly 50-60.")

    if not desc:
        add(findings, "critical", "Missing meta description.")
    elif len(desc) < 80 or len(desc) > 170:
        add(findings, "warning", f"Meta description length is {len(desc)} chars; target roughly 140-160.")
    if len(descriptions) > 1:
        add(findings, "warning", f"Multiple meta descriptions found: {len(descriptions)}.")

    if len(h1s) == 0:
        add(findings, "critical", "Missing H1.")
    elif len(h1s) > 1:
        add(findings, "warning", f"Multiple H1s found: {len(h1s)}.")
    analyze_heading_hierarchy(parser, findings)

    if not canonical:
        add(findings, "warning", "Missing canonical link.")
    elif not urlparse(canonical).scheme:
        add(findings, "warning", "Canonical URL should usually be absolute.")
    if len(canonicals) > 1:
        add(findings, "warning", f"Multiple canonical links found: {len(canonicals)}.")

    robots_directives = {part.strip() for value in [robots, googlebot] for part in value.split(",") if part.strip()}
    if "noindex" in robots_directives or "none" in robots_directives:
        add(findings, "critical", "Page contains a robots noindex directive.")
    if "nofollow" in robots_directives or "none" in robots_directives:
        add(findings, "warning", "Page contains a robots nofollow directive.")
    if "nosnippet" in robots_directives:
        add(findings, "opportunity", "Page contains nosnippet, which can limit search result and AI overview snippets.")

    missing_alt = [img.get("src", "(inline image)") for img in parser.images if "alt" not in img]
    empty_alt = [img.get("src", "(inline image)") for img in parser.images if img.get("alt") == ""]
    if missing_alt:
        add(findings, "critical", f"{len(missing_alt)} image(s) missing alt attribute.")
    if empty_alt:
        add(findings, "opportunity", f"{len(empty_alt)} image(s) have empty alt; verify they are decorative.")

    for field in ["og:title", "og:description", "og:image", "og:url"]:
        if not meta_content(parser, prop=field):
            add(findings, "opportunity", f"Missing Open Graph tag: {field}.")
    for field in ["twitter:card", "twitter:title", "twitter:description"]:
        if not meta_content(parser, name=field):
            add(findings, "opportunity", f"Missing Twitter tag: {field}.")

    hreflangs = [item for item in parser.links if "alternate" in item.get("rel", "").lower().split() and item.get("hreflang")]
    seen_hreflang = set()
    for item in hreflangs:
        hreflang = item.get("hreflang", "").lower()
        href = clean(item.get("href", ""))
        if hreflang in seen_hreflang:
            add(findings, "warning", f"Duplicate hreflang value: {hreflang}.")
        seen_hreflang.add(hreflang)
        if href and not urlparse(href).scheme:
            add(findings, "warning", f"hreflang URL for {hreflang} should be absolute.")

    jsonld_found = False
    schema_types: list[str] = []
    for index, script in enumerate(parser.jsonld_scripts, start=1):
        body = clean(script)
        if not body:
            add(findings, "warning", f"JSON-LD script {index} is empty.")
            continue
        jsonld_found = True
        try:
            parsed = json.loads(body)
        except json.JSONDecodeError as exc:
            add(findings, "critical", f"Invalid JSON-LD script {index}: {exc.msg}.")
            continue
        schema_types.extend(jsonld_types(parsed))
        if isinstance(parsed, dict) and not parsed.get("@context"):
            add(findings, "warning", f"JSON-LD script {index} is missing @context.")
    if not jsonld_found:
        add(findings, "opportunity", "No JSON-LD structured data found.")

    broken_local_links = []
    for anchor in parser.anchors:
        target = local_link_target(root, path, anchor.get("href", ""))
        if target and not target.exists():
            broken_local_links.append(anchor.get("href", ""))
    if broken_local_links:
        add(findings, "critical", f"{len(broken_local_links)} local link(s) point to missing files.")

    if not findings:
        add(findings, "healthy", "No basic SEO issues found.")

    return {
        "file": str(path),
        "title": title,
        "description": desc,
        "canonical": canonical,
        "robots": robots,
        "h1_count": len(h1s),
        "schema_types": sorted(set(schema_types)),
        "findings": findings,
    }


def parse_robots_groups(text: str) -> list[dict[str, list[str]]]:
    groups: list[dict[str, list[str]]] = []
    current: dict[str, list[str]] | None = None
    for raw_line in text.splitlines():
        line = raw_line.split("#", 1)[0].strip()
        if not line or ":" not in line:
            continue
        key, value = [part.strip() for part in line.split(":", 1)]
        key = key.lower()
        if key == "user-agent":
            if current is None or current.get("rules"):
                current = {"agents": [], "rules": []}
                groups.append(current)
            current["agents"].append(value.lower())
        elif key in {"allow", "disallow", "noindex"}:
            if current is None:
                current = {"agents": ["*"], "rules": []}
                groups.append(current)
            current["rules"].append(f"{key}:{value}")
    return groups


def analyze_robots(root: Path):
    path = root / "robots.txt"
    if not path.exists():
        return {"file": str(path), "findings": [{"level": "warning", "message": "robots.txt not found."}]}
    text = path.read_text(encoding="utf-8", errors="replace")
    findings: list[dict[str, str]] = []
    groups = parse_robots_groups(text)
    for group in groups:
        agents = set(group["agents"])
        if "*" not in agents and "googlebot" not in agents:
            continue
        for rule in group["rules"]:
            directive, value = rule.split(":", 1)
            value = value.strip()
            if directive == "disallow" and value == "/":
                add(findings, "critical", f"robots.txt disallows the entire site for {', '.join(sorted(agents))}.")
            if directive == "noindex":
                add(findings, "warning", "robots.txt contains a noindex directive; use robots meta or X-Robots-Tag instead.")
    if not re.search(r"(?im)^\s*sitemap:\s*https?://\S+", text):
        add(findings, "opportunity", "robots.txt does not declare an absolute sitemap URL.")
    if not findings:
        add(findings, "healthy", "robots.txt basic checks passed.")
    return {"file": str(path), "findings": findings}


def analyze_sitemap(root: Path):
    candidates = [root / "sitemap.xml", root / "sitemap_index.xml"]
    path = next((p for p in candidates if p.exists()), None)
    if not path:
        return {"file": str(root / "sitemap.xml"), "sitemap_urls": [], "findings": [{"level": "warning", "message": "sitemap.xml not found."}]}
    findings: list[dict[str, str]] = []
    locs: list[str] = []
    try:
        tree = ElementTree.parse(path)
        locs = [clean(el.text or "") for el in tree.iter() if el.tag.endswith("loc") and clean(el.text or "")]
        if not locs:
            add(findings, "critical", "Sitemap has no loc entries.")
        invalid = [loc for loc in locs if urlparse(loc).scheme not in {"http", "https"}]
        if invalid:
            add(findings, "warning", f"{len(invalid)} sitemap URL(s) are not absolute HTTP(S) URLs.")
        duplicates = len(locs) - len({normalize_url(loc) for loc in locs})
        if duplicates:
            add(findings, "warning", f"{duplicates} duplicate sitemap URL(s) found.")
        if len(locs) > 50000:
            add(findings, "critical", "Sitemap exceeds 50,000 URL limit.")
    except Exception as exc:
        add(findings, "critical", f"Could not parse sitemap XML: {exc}.")
    if not findings:
        add(findings, "healthy", "Sitemap basic checks passed.")
    return {"file": str(path), "sitemap_urls": locs, "findings": findings}


def collect_html(target: Path) -> list[Path]:
    if target.is_file():
        return [target] if target.suffix.lower() in HTML_SUFFIXES else []
    return sorted([p for p in target.rglob("*") if p.suffix.lower() in HTML_SUFFIXES])


def add_sitewide_duplicate_findings(results, field: str, level: str, label: str):
    buckets = defaultdict(list)
    for result in results:
        value = clean(result.get(field, ""))
        if value:
            key = normalize_url(value) if field == "canonical" else value.lower()
            buckets[key].append(result)
    for value, pages in buckets.items():
        if len(pages) < 2:
            continue
        files = ", ".join(Path(page["file"]).name for page in pages[:5])
        for page in pages:
            add(page["findings"], level, f"Duplicate {label} shared by {len(pages)} pages: {files}.")


def local_url_for_file(root: Path, path: Path, base_url: str | None) -> str | None:
    if not base_url:
        return None
    relative = path.relative_to(root).as_posix()
    if Path(relative).name in INDEX_NAMES:
        relative = str(Path(relative).parent).replace(".", "").strip("/")
        suffix = f"{relative}/" if relative else ""
    else:
        suffix = relative
    return urljoin(base_url.rstrip("/") + "/", suffix)


def add_sitewide_findings(results, sitemap_result, root: Path, base_url: str | None):
    add_sitewide_duplicate_findings(results, "title", "warning", "title")
    add_sitewide_duplicate_findings(results, "description", "warning", "meta description")
    add_sitewide_duplicate_findings(results, "canonical", "critical", "canonical URL")

    sitemap_urls = {normalize_url(url) for url in sitemap_result.get("sitemap_urls", [])}
    if not sitemap_urls:
        return
    for result in results:
        canonical = result.get("canonical")
        if canonical and normalize_url(canonical) in sitemap_urls and "noindex" in result.get("robots", "").lower():
            add(result["findings"], "critical", "Page is in sitemap but has robots noindex.")
        expected_url = local_url_for_file(root, Path(result["file"]), base_url)
        canonical_in_sitemap = canonical and normalize_url(canonical) in sitemap_urls
        if expected_url and normalize_url(expected_url) not in sitemap_urls and not canonical_in_sitemap:
            add(result["findings"], "opportunity", "Page is not represented in sitemap for the configured base URL.")


def print_text_report(results):
    totals = defaultdict(int)
    for result in results:
        for finding in result["findings"]:
            totals[finding["level"]] += 1

    print("SEO Supercheck")
    print(f"Critical: {totals['critical']}  Warning: {totals['warning']}  Opportunity: {totals['opportunity']}  Healthy: {totals['healthy']}")
    for result in results:
        print(f"\n{result['file']}")
        if result.get("title"):
            print(f"  title: {result['title']}")
        if result.get("canonical"):
            print(f"  canonical: {result['canonical']}")
        if result.get("schema_types"):
            print(f"  schema: {', '.join(result['schema_types'])}")
        for finding in result["findings"]:
            print(f"  [{finding['level']}] {finding['message']}")


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("target", help="HTML file or directory containing built/static HTML")
    parser.add_argument("--base-url", help="Public base URL used to compare local files to sitemap URLs")
    parser.add_argument("--json", action="store_true", help="Emit JSON")
    args = parser.parse_args(argv)

    target = Path(args.target).expanduser().resolve()
    if not target.exists():
        print(f"Target not found: {target}", file=sys.stderr)
        return 2

    root = target if target.is_dir() else target.parent
    html_files = collect_html(target)
    results = [analyze_html(path, root) for path in html_files]
    if not html_files:
        results.append({"file": str(target), "findings": [{"level": "warning", "message": "No HTML files found."}]})

    robots_result = analyze_robots(root)
    sitemap_result = analyze_sitemap(root)
    add_sitewide_findings(results, sitemap_result, root, args.base_url)
    results.extend([robots_result, sitemap_result])

    if args.json:
        print(json.dumps(results, indent=2))
    else:
        print_text_report(results)

    has_critical = any(f["level"] == "critical" for r in results for f in r["findings"])
    return 1 if has_critical else 0


if __name__ == "__main__":
    raise SystemExit(main())
