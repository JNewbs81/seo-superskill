# Evidence, performance and opportunity gaps

Read for a full audit beyond static markup. Check current primary documentation before implementing search features; vocabulary validity and Google feature eligibility are different questions.

## Live delivery and maintenance

Run `python scripts/seo_livecheck.py https://example.com > live-report.json` for a small public site with a URL sitemap. It checks up to 100 same-origin sitemap URLs, canonical matching, HTTP and meta noindex indicators, same-origin CSS/scripts/images/icons and a real 404 probe. Explicit limits up to 500 are supported. It does not follow sitemap indexes, evaluate robots rules, validate every external link, render content or measure speed. Inspect its findings before changing routes. Preserve existing verification tags and deployment configuration. A 403 from an external resource may be bot protection; verify in a browser before labeling a link broken. A 200 may still be an error, parking or construction page; inspect content where it matters.

Check HTTP/HTTPS and www/apex variants for DNS, certificates and intentional redirects; never point an unprovisioned host at hosting that lacks its certificate/domain mapping. Avoid soft 404s and redirect chains. When changing cached permanent redirects, test an existing browser session as well as fresh HTTP requests; use versioned asset URLs where stale redirects otherwise prevent resources loading. Inventory incomplete location pages, external-resource freshness and content overlap. Keep local-resource phone numbers out of business contact markup.

## Performance evidence

Separate source hypotheses, one-session lab measurements and real-user field data. Seek mobile and desktop CrUX at page level, clearly labeling an origin fallback or insufficient data. Use PageSpeed Insights, Lighthouse or a browser trace when available. A quota/error is missing measurement, not a passing result; use available tools without bypassing browser restrictions or inventing scores.

Current good Core Web Vitals targets are p75 LCP <=2.5s, INP <=200ms and CLS <=0.1. Recheck https://web.dev/articles/vitals as these evolve. Record URL, tool/version, device/network conditions and date; compare equivalent before/after lab conditions. TBT is a lab diagnostic, not measured field INP. Field changes require new visits and aggregation time.

Optimize the actual bottleneck. Reserve image dimensions, use responsive images where oversized transfers are demonstrated, preserve lazy loading below the fold and avoid lazy loading the LCP image. Audit font delivery, render blocking and long tasks. Do not add speculative preloads, prerenders, dependencies or analytics solely for an audit score. Check mobile navigation, keyboard focus and reduced-motion support when relevant to page use.

## Search features and identity

Verify current Google support before recommending rich-result types. As of the October 2026 review, FAQ rich results ceased appearing May 7, 2026; HowTo rich results and sitelinks search boxes were also retired. Keep useful visible questions; do not sell FAQPage, HowTo or SearchAction as Google enhancements. Existing truthful schema need not be removed solely because a feature retired, but avoid adding redundant markup with no intended consumer. Source: https://developers.google.com/search/updates

For site-name preferences, use truthful homepage WebSite name, alternateName and URL consistent with visible branding. This is distinct from a Google Business Profile name and does not rename the business listing. Source: https://developers.google.com/search/docs/appearance/site-names

Use collection/item-list schema for real curated directories only when it accurately represents the visible list; it is not a promised Google rich result. Preserve matching business identity across templates.

## Query, competitor and authority evidence

Map actual Search Console query/page data to intent before prioritizing new articles. Separate missing data, low impressions, weak CTR and wrong landing pages; a new site needs time to produce evidence. Distinguish observed queries from topic hypotheses and avoid overlapping pages. Identify search competitors from shared results, not only known business competitors. Label manual search observations, first-party data and third-party estimates separately; do not invent volume, difficulty, backlinks, rankings or competitor traffic.

When available, Semrush or another documented provider can supplement keyword gaps, content gaps and referring-domain evidence; require the actual connector/export and disclose metered queries. Without it, use first-party reports and manual source inspection and state the limitation. Prefer earned, relevant local citations and factual profile consistency; never buy spam links, fabricate reviews, trade fake references between commonly owned businesses or create duplicate business listings. Do not claim llms.txt, keyword-density targets or bulk AI articles are ranking factors.
