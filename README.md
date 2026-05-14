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
python scripts/seo_supercheck.py dist --json
```

The checker exits with status `1` when critical issues are found.

## Scope

This tool is intentionally conservative. It catches common mechanical SEO issues and gives Codex a repeatable baseline before and after implementation work. It does not replace Search Console, analytics, rank tracking, crawl logs, or manual SERP research.

## License

MIT

