# Analysis Pipeline Specification

## 1. Module Overview

The `analyzers/` package executes technical, structural, and semantic inspections on fetched HTML payloads and HTTP responses. Analyzers run synchronously within worker threads immediately following content acquisition, storing normalized records in the persistence layer.

Related documentation:
- Crawl ingestion: [Crawler Engine](crawler_engine.md)
- Storage schema: [Database Architecture](database_architecture.md)
- UI Presentation: [Frontend Workspace](frontend_workspace.md)

---

## 2. Individual Analyzer Specifications

### 2.1 Technical Analyzer (`analyzers/technical.py`)
Responsible for protocol, server, and direct indexing factors:
- **HTTP Status Code Mapping**: Categorizes status codes into classes (2xx Success, 3xx Redirect, 4xx Client Error, 5xx Server Error).
- **Indexability Determination**:
  - Checks HTTP response headers for `X-Robots-Tag: noindex`.
  - Checks HTML DOM for `<meta name="robots" content="...noindex...">`.
  - Compares the canonical link element against the current URL. If canonical URL points elsewhere, indexability is marked as `Non-Indexable (Canonicalised)`.
- **MIME Type Validation**: Distinguishes valid HTML documents from misconfigured binary payloads.

### 2.2 On-Page Analyzer (`analyzers/onpage.py`)
Extracts visible textual metadata and heading structures:
- **Title Tag**: Extracts text, computes character length, and evaluates length against optimal bounds (30 to 60 characters).
- **Meta Description**: Extracts content, computes character length, and evaluates against bounds (120 to 160 characters).
- **Heading Hierarchy**:
  - Captures primary H1 tags. Flags missing H1 or multiple H1 instances.
  - Extracts full arrays of H2 and H3 heading elements to assess document outline balance.
- **Word Count**: Strips `<script>`, `<style>`, `<nav>`, and structural boilerplate; tokenizes visible body text to calculate word counts.

### 2.3 Link Analyzer (`analyzers/links.py`)
Constructs directed edges representing site architecture:
- **Anchor Parsing**: Identifies all `<a href="...">` elements.
- **Target Classification**: Resolves relative paths to absolute URLs; determines whether target belongs to the same domain (`Internal`) or external domains (`External`).
- **Rel Directives**: Evaluates `rel="nofollow"`, `rel="sponsored"`, and `rel="ugc"`.
- **Broken Link Detection**: Associates destination URLs with known 4xx/5xx status codes.

### 2.4 Media and Image Analyzer (`analyzers/images.py`)
Audits all `<img>`, `<picture>`, and `<source>` declarations:
- **Source Resolution**: Extracts `src`, `data-src`, and responsive `srcset` candidates.
- **Alternative Text**: Flags missing, empty, or duplicate `alt` attributes.
- **Performance Characteristics**: Evaluates dimensional attributes (`width`, `height`), flags missing dimensions (which cause layout shifts), and records `loading="lazy"` attributes.

### 2.5 Structured Data Analyzer (`analyzers/structured_data.py`)
Identifies and verifies semantic markup:
- **JSON-LD Parsing**: Locates all `<script type="application/ld+json">` blocks, parses JSON syntax, and validates schema `@type` hierarchies (e.g. `Product`, `Organization`, `Article`, `BreadcrumbList`).
- **Syntax Validation**: Flags malformed JSON or schema structures missing critical mandatory properties.

### 2.6 Performance and Core Web Vitals (`analyzers/performance.py`)
Extracts server timing and page performance characteristics:
- **Time to First Byte (TTFB)**: Measures elapsed milliseconds from request initiation to first byte received.
- **Document Payload Weight**: Measures raw HTML transfer size in bytes.
- **Core Web Vitals Estimation**: When enabled, runs headless instrumentation to capture Largest Contentful Paint (LCP), Interaction to Next Paint (INP), and Cumulative Layout Shift (CLS).
