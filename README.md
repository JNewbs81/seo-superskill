# SEO SuperSkill

SEO SuperSkill is a Codex skill and small command-line checker for practical SEO work in codebases.

It helps with:

- Technical SEO audits
- On-page metadata and heading checks
- JSON-LD structured data validation
- Robots.txt and sitemap sanity checks
- Local SEO implementation guidance
- Programmatic SEO planning
- Answer-engine optimization
- Editorial guides and useful topic clusters
- Live production HTTP checks
- Evidence-based performance, query and competitor gap analysis

It intentionally stays inside SEO. It is not a paid ads, generic copywriting, social media, or general analytics skill.

## Install

Copy this folder into your Codex skills directory:

```bash
~/.codex/skills/seo-superskill
```

Codex will discover the skill from `SKILL.md`.

## Checker

Run the static HTML checker against a single file or a built output directory:

```bash
python scripts/seo_supercheck.py dist
python scripts/seo_supercheck.py dist --base-url https://example.com --json
```

The checker exits with status `1` when critical issues are found.

Checks include:

- Missing or duplicate titles, descriptions, H1s, and canonicals
- Robots noindex/nofollow/nosnippet directives
- Robots.txt whole-site blocks and unsupported noindex directives
- Sitemap parse errors, duplicate URLs, invalid URLs, and 50,000 URL limit
- JSON-LD syntax, multiple JSON-LD scripts, arrays, and `@graph`
- Heading hierarchy jumps
- Missing image alt attributes
- Hreflang duplicates and relative hreflang URLs
- Local broken links in static output
- Sitemap/noindex conflicts

## Live checker

For a public HTTPS site with a same-origin URL sitemap:

```bash
python scripts/seo_livecheck.py https://newberrybail.com > live-report.json
```

The live checker checks up to 100 sitemap URLs by default (explicit limits up to 500), canonical matching, potential HTTP/meta noindex directives, same-origin assets, robots/sitemap delivery and a nonexistent-page 404 probe. It exits with status `1` on detected delivery/indexability failures. Redirect warnings are reported separately. It does not traverse sitemap indexes; select a child URL sitemap workflow for larger sites. Reports include response headers and should be reviewed before sharing.

This is a read-only HTTP check, not an indexing submission, browser-rendering test or Core Web Vitals measurement. A passing check does not prove rankings, rich-result eligibility or Google indexing.

## Extended guidance

- `references/editorial-seo.md`: useful articles, factual sourcing, internal links and maintenance.
- `references/evidence-and-gaps.md`: lab versus field performance, current Google feature eligibility, site identity, domain variants, and query/competitor evidence.
- `references/standards.md`: maintained primary-source references.

Use each site's own verified business information. The reusable skill contains no Amy-specific contact details or deployment credentials.

## Scope

This tool is intentionally conservative. It catches common mechanical SEO issues and gives Codex a repeatable baseline before and after implementation work. It does not replace Search Console, analytics, rank tracking, crawl logs, or manual SERP research.

## License

MIT
