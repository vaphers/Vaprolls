# Analysis Pipeline Specification

## 1. Module Overview

The `analyzers/` package executes technical, structural, semantic, and accessibility inspections on crawled pages, HTTP responses, and asset graphs.

Following content acquisition, analyzers evaluate records stored in the SQLite database and populate diagnostic findings into the `issues` table, as well as specialized relational tables (`headings`, `performance_metrics`, `hreflang_tags`, `structured_data`, `accessibility_violations`, etc.).

Related documentation:
- Crawl ingestion: [Crawler Engine](crawler_engine.md)
- Storage schema: [Database Architecture](database_architecture.md)
- Dataset structure: [URL Dataset Specification](url_dataset_specification.md)
- Workspace interface: [Frontend Workspace](frontend_workspace.md)

---

## 2. Complete Analyzer Catalog

The system implements 20 specialized analyzers categorized into six functional areas:

```
[Analysis Pipeline]
  ├── Core Crawl & Directives
  │     ├── Technical Analyzer (analyzers/technical.py)
  │     ├── Robots Auditor (analyzers/robots_auditor.py)
  │     └── Sitemap Auditor (analyzers/sitemap_auditor.py)
  ├── On-Page & Content
  │     ├── On-Page Analyzer (analyzers/onpage.py)
  │     ├── Content Analyzer (analyzers/content.py)
  │     ├── Keyword Analyzer (analyzers/keywords.py)
  │     └── Social Meta Analyzer (analyzers/social_meta.py)
  ├── Link Architecture & Equity
  │     ├── Link Analyzer (analyzers/links.py)
  │     └── PageRank Engine (analyzers/pagerank.py)
  ├── Performance & Rendering
  │     ├── Performance & CWV Analyzer (analyzers/performance.py)
  │     ├── JavaScript SEO Analyzer (analyzers/js_seo.py)
  │     └── Mobile Responsiveness Analyzer (analyzers/mobile.py)
  ├── Media & Structured Data
  │     ├── Media & Image Analyzer (analyzers/images.py)
  │     ├── Structured Data Analyzer (analyzers/structured_data.py)
  │     └── Custom Search & Extractions (analyzers/custom_search.py)
  └── Security, Accessibility & Internationalization
        ├── Security Analyzer (analyzers/security.py)
        ├── Security Headers Analyzer (analyzers/security_headers.py)
        ├── Accessibility / WCAG Analyzer (analyzers/accessibility.py)
        ├── Hreflang Analyzer (analyzers/hreflang.py)
        ├── Pagination Auditor (analyzers/pagination_auditor.py)
        └── Site-Wide Aggregator (analyzers/sitewide.py)
```

---

## 3. Analyzer Specifications

### 3.1 Technical Analyzer (`analyzers/technical.py`)
Audits protocol, server response, and indexability factors:
- **Status Code Mapping**: Categorizes responses into 2xx, 3xx, 4xx, and 5xx classes.
- **Indexability Determination**:
  - Checks HTTP response headers for `X-Robots-Tag: noindex, nofollow, none`.
  - Checks HTML meta robots declarations.
  - Flags non-canonical pages where `<link rel="canonical">` points to an external or alternate URL.
- **Canonical Parity**: Detects missing canonicals, multiple canonical tags, self-referential canonicals, relative canonical URLs, and cross-domain canonical links.
- **MIME & Document Weight**: Validates content-type headers and flags oversized HTML payloads exceeding recommended thresholds.

### 3.2 Robots Auditor (`analyzers/robots_auditor.py`)
Validates robot exclusion files and directives:
- Tests syntax and directive order in `robots.txt`.
- Flags missing `robots.txt`, unparseable lines, empty User-Agent blocks, and missing Sitemap declarations.
- Evaluates path coverage to detect pages unintentionally blocked from search engine indexers.

### 3.3 Sitemap Auditor (`analyzers/sitemap_auditor.py`)
Audits XML sitemaps discovered via robots.txt or direct configuration:
- Cross-references sitemap URLs against crawled pages to identify orphan pages (pages in sitemaps not linked internally, or vice-versa).
- Checks status codes of sitemap URLs, flagging non-200 URLs (404, 301, 500) included in sitemaps.
- Evaluates `lastmod` timestamps for staleness or future dates.
- Checks sitemap file size and URL count compliance (maximum 50,000 URLs or 50MB uncompressed).

### 3.4 On-Page Analyzer (`analyzers/onpage.py`)
Evaluates core HTML metadata elements:
- **Title Tags**: Checks for missing titles, empty titles, character length (recommended 30-60 characters), pixel width approximations, and duplicate title tags across pages.
- **Meta Descriptions**: Identifies missing descriptions, short descriptions (< 100 characters), long descriptions (> 160 characters), and sitewide duplicates.
- **Heading Hierarchy**:
  - Evaluates H1 tags: missing H1, multiple H1 tags per page, duplicate H1 content, and length.
  - Parses full arrays of H2 through H6 headings, auditing structural document outline order.
- **Meta Keywords**: Detects obsolete or excessive meta keyword tags.

### 3.5 Content & Readability Analyzer (`analyzers/content.py`)
Evaluates textual depth and duplicate content risk:
- **Word & Sentence Counts**: Tokenizes visible text, calculating total word count, sentence count, and average words per sentence.
- **Thin Content Detection**: Flags pages with fewer than 250 or 500 words of body copy.
- **Text-to-HTML Ratio**: Calculates the proportion of visible text against total markup size, flagging ratios under 10%.
- **Readability Scoring**: Calculates Flesch Reading Ease scores and assigns standard grade-level readability labels (Very Easy, Easy, Standard, Difficult, Very Confusing).
- **Near-Duplicate Detection**: Uses 64-bit SimHash fingerprints to calculate Hamming distances between page bodies, detecting pages with near-identical copy (> 85% similarity).

### 3.6 Keyword Analyzer (`analyzers/keywords.py`)
Analyzes keyword distribution and on-page prominence:
- Extracts single words, 2-grams, and 3-grams with stop-word removal.
- Calculates keyword frequency and density across title, headings, meta tags, and body copy.
- Flags keyword stuffing (density > 5%).
- Classifies keyword search intent (Informational, Navigational, Commercial, Transactional).

### 3.7 Social Meta Analyzer (`analyzers/social_meta.py`)
Audits Open Graph and Twitter Card tags:
- Evaluates `og:title`, `og:description`, `og:image`, `og:url`, and `og:type`.
- Evaluates `twitter:card`, `twitter:title`, `twitter:description`, and `twitter:image`.
- Flags missing images, non-absolute image URLs, missing required properties, or mismatched social titles compared to HTML titles.

### 3.8 Link Analyzer (`analyzers/links.py`)
Maps the complete internal and external hyperlink graph:
- **Link Classification**: Categorizes all `<a href>` anchors into Internal and External targets.
- **Broken Links**: Identifies internal and external links pointing to 4xx and 5xx responses.
- **Anchor Text Inspection**: Identifies generic anchor text ("click here", "read more", "link"), empty anchor tags, and excessively long anchor text.
- **Rel Directives**: Tracks `rel="nofollow"`, `rel="sponsored"`, `rel="ugc"`, and `rel="noopener/noreferrer"`.
- **Inlink and Outlink Aggregation**: Computes unique inlink counts, unique outlink counts, and external link ratios per page.

### 3.9 Internal PageRank Engine (`analyzers/pagerank.py`)
Calculates link equity distribution across the internal network:
- Implements the mathematical PageRank power-iteration algorithm using a standard damping factor ($d = 0.85$).
- Handles dangling nodes (pages with no outbound internal links) by distributing residual probability uniformly.
- Normalizes scores on a 0.0 to 100.0 scale.
- Identifies equity traps (low-value utility pages like `/privacy-policy` or `/login` receiving high link equity).
- Identifies high-priority orphan or near-orphan pages (depth 1 pages receiving very low internal authority).

### 3.10 Performance Analyzer (`analyzers/performance.py`)
Audits load characteristics and Web Vitals metrics:
- **Server Timing**: Measures Time to First Byte (TTFB) and total server response time in milliseconds.
- **Threshold Warnings**: Flags slow pages (> 1,000ms response time) and critical latency (> 3,000ms).
- **Core Web Vitals**: When configured, captures Largest Contentful Paint (LCP), Interaction to Next Paint (INP), First Contentful Paint (FCP), and Cumulative Layout Shift (CLS).
- **CrUX & PageSpeed Integration**: Connects to the Chrome User Experience Report API and PageSpeed Insights API when API credentials are provided.

### 3.11 JavaScript SEO Analyzer (`analyzers/js_seo.py`)
Compares static raw HTML against Playwright-rendered dynamic DOM:
- Compares raw HTML word count vs. rendered word count, calculating the percentage of content dependent on client-side JavaScript.
- Compares metadata modifications (title, H1, meta description, canonical, robots directives altered or inserted dynamically by JavaScript).
- Captures browser console logs during rendering, categorizing errors, warnings, and unhandled exceptions.

### 3.12 Mobile Responsiveness Analyzer (`analyzers/mobile.py`)
Inspects mobile viewport configuration:
- Audits `<meta name="viewport">` presence and attributes.
- Flags missing viewports, fixed-width viewports (e.g. `width=1024`), or disabled user scaling (`user-scalable=no`, `maximum-scale=1.0`).
- Checks for alternate mobile links (`<link rel="alternate" media="...">`) and AMP HTML tags.

### 3.13 Media and Image Analyzer (`analyzers/images.py`)
Audits all image declarations:
- Identifies missing alt attributes, empty alt attributes, and excessively long alt text (> 125 characters).
- Checks for explicit `width` and `height` dimensions to prevent Cumulative Layout Shift (CLS).
- Flags uncompressed or legacy formats (BMP, TIFF, unoptimized PNG/JPEG) that should be converted to WebP or AVIF.
- Identifies non-descriptive filenames (e.g. `img_001.jpg`, `screenshot.png`).
- Audits lazy loading implementation (`loading="lazy"`).

### 3.14 Structured Data Analyzer (`analyzers/structured_data.py`)
Validates semantic markup schemas:
- Parses JSON-LD `<script type="application/ld+json">`, Microdata, and RDFa declarations.
- Validates schema.org entity types (Product, Organization, Article, LocalBusiness, BreadcrumbList, FAQPage, Recipe, Event).
- Flags syntax errors, missing mandatory schema properties, and invalid nested types.

### 3.15 Custom Search & Extraction (`analyzers/custom_search.py`)
Executes user-defined extraction and search rules configured in `config.py`:
- **Custom Search**: Searches page source for literal substrings or regex patterns using `contains` or `does_not_contain` conditions (e.g. verifying Google Analytics tags, tracking snippets, or deprecated scripts).
- **Custom Extraction**: Extracts targeted content using CSS selectors, XPath expressions, or regular expressions (e.g. scraping product prices, SKUs, or author names).

### 3.16 Security Analyzer (`analyzers/security.py`)
Identifies protocol and privacy risks:
- Flags insecure HTTP URLs on predominantly HTTPS domains.
- Detects mixed content (HTTPS pages referencing insecure HTTP images, scripts, stylesheets, or iframes).
- Audits forms to identify insecure form actions (`http://` targets) and unencrypted password fields.
- Scans page HTML for exposed plaintext email addresses vulnerable to scraping.

### 3.17 Security Headers Analyzer (`analyzers/security_headers.py`)
Audits server HTTP response headers against modern security standards:
- **HSTS**: `Strict-Transport-Security` presence, `max-age`, and `includeSubDomains`.
- **CSP**: `Content-Security-Policy` presence and unsafe directives (`unsafe-inline`, `unsafe-eval`).
- **Clickjacking Protection**: `X-Frame-Options` (`DENY` or `SAMEORIGIN`).
- **MIME Sniffing**: `X-Content-Type-Options: nosniff`.
- **Referrer Policy**: `Referrer-Policy` settings.
- **Permissions Policy**: `Permissions-Policy` feature restrictions.
- **Server Information Disclosure**: Flags headers that expose underlying server versions (`Server`, `X-Powered-By`).

### 3.18 Accessibility / WCAG Analyzer (`analyzers/accessibility.py`)
Audits accessibility compliance against WCAG 2.0, 2.1, and 2.2 criteria:
- Categorizes issues across Level A, Level AA, Level AAA, and general Best Practices.
- Audits missing form input labels, button text, link text, language declarations (`<html lang="...">`), document title tags, heading skips, ARIA roles, and duplicate element IDs.

### 3.19 Internationalization & Hreflang Analyzer (`analyzers/hreflang.py`)
Validates multi-language and multi-regional implementations:
- Parses `<link rel="hreflang">` HTML elements and HTTP `Link` headers.
- Audits language and region code validity (ISO 639-1 and ISO 3166-1 alpha-2).
- Validates bidirectional return tags (confirming page A links to page B, and page B links back to page A).
- Checks for self-referential hreflang tags and `x-default` fallbacks.
- Flags hreflang tags pointing to non-canonical or non-200 URLs.

### 3.20 Pagination Auditor (`analyzers/pagination_auditor.py`)
Audits sequential and paginated series:
- Parses `rel="next"` and `rel="prev"` link relationships.
- Audits canonicalization on paginated series (ensuring page 2 canonicalizes to itself or a view-all page, rather than incorrectly canonicalizing to page 1).
- Detects broken sequence chains, looping pagination, and orphan paginated pages.

### 3.21 Site-Wide Aggregator (`analyzers/sitewide.py`)
Synthesizes audit findings after all page-level analyzers complete:
- Calculates site health score using weighted deduction penalties:
  $$\text{Health Score} = \max\left(0, 100 - (\text{Critical Issues} \times 2.0) - (\text{Warnings} \times 0.5)\right)$$
- Aggregates issue distributions by category and severity.
- Compiles domain-wide summary statistics (total pages, crawl depth distribution, response time distribution, indexable ratio).
