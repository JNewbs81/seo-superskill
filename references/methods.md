# SEO SuperSkill Methods

## Modes

### Technical Audit

Check crawlability, indexability, metadata, status codes, redirects, canonical tags, heading structure, images, structured data, sitemap, robots.txt, mobile rendering, and major performance issues that affect rendering or UX.

Report in priority order:
- Critical: blocks crawling, indexing, rendering, or primary ranking signals.
- Warning: weakens snippets, relevance, internal discovery, schema eligibility, or page quality.
- Opportunity: improves CTR, topical authority, AEO, or conversion after fundamentals are healthy.

### On-Page Optimization

For each target page:
- One primary intent and one primary query cluster.
- Title: unique, specific, primary phrase near the front, usually 50-60 chars.
- Description: unique, benefit-oriented, truthful, usually 140-160 chars.
- H1: matches intent without stuffing.
- Headings: organize the answer, do not decorate.
- Body: answer the query early, then add supporting detail.
- Internal links: link to and from related pages with natural anchor text.
- Images: meaningful filenames when feasible and useful alt text.

### Structured Data

Use JSON-LD. Select schema based on visible content:
- `LocalBusiness` or subtype for real business/location pages.
- `Organization` for company identity.
- `WebSite` with `SearchAction` when site search exists.
- `BreadcrumbList` for breadcrumb navigation.
- `FAQPage` only when visible FAQs are present.
- `Article`/`BlogPosting` for editorial pages.
- `Product` only for actual product offers.
- `Service` for service pages when details are visible.

Validate JSON syntax locally. When internet/browser access is available, use Google Rich Results Test or Schema.org validator for important pages.

### Local SEO

For local service businesses:
- Keep NAP (name, address, phone) consistent across site and schema.
- Use real service areas and locations only.
- Build city/county pages only when each page has unique local usefulness.
- Add local proof: office/service area details, courts/jails served, local process notes, testimonials if real and policy-compliant, driving/contact details.
- Use `LocalBusiness`, relevant subtype if available, `areaServed`, `telephone`, `address`, `openingHours`, `sameAs`, and `hasMap` when true.

### Programmatic SEO

Common playbooks:
- Locations: `[service] in [city]`
- Directories: `[category] tools/services`
- Comparisons: `[x] vs [y]`, `[x] alternatives`
- Integrations: `[product] [integration]`
- Templates/examples: `[type] template`, `[type] examples`
- Glossaries: `what is [term]`
- Persona/industry pages: `[service] for [audience]`

Quality gate before launch:
- Real demand exists.
- Each page has unique data or useful analysis.
- URL pattern is stable and human-readable.
- Template handles missing data without blank/thin sections.
- Related pages are linked.
- Canonical/noindex rules are explicit.
- Sitemap generation is based on the same canonical page inventory.

### AEO / Answer Engine Optimization

Make answer extraction easy:
- Put a concise answer near the top of the relevant section.
- Use direct question headings for FAQs where natural.
- Use lists/tables for comparisons and procedural answers.
- Cite authoritative sources when factual claims depend on external data.
- Keep important content crawlable in rendered HTML.
- Use FAQ/HowTo schema only when the visible page truly contains that content.

## Verification

Use `scripts/seo_supercheck.py` on static HTML or production build output:

```bash
python /Users/joshuanewberry/.codex/skills/seo-superskill/scripts/seo_supercheck.py dist
python /Users/joshuanewberry/.codex/skills/seo-superskill/scripts/seo_supercheck.py dist --json
```

For local apps:
- Build first when the framework has static output.
- Otherwise run the dev/preview server and inspect rendered HTML with browser automation.
- Check that metadata is present in the initial response/rendered head, not only after user interaction.

