package writer

import (
	"database/sql"
	"go-crawler/internal/fetcher"
	"go-crawler/internal/parser"
	"os"
	"path/filepath"
	"testing"
	"time"

	_ "modernc.org/sqlite"
)

const testSchema = `
CREATE TABLE IF NOT EXISTS audits (
    id TEXT PRIMARY KEY,
    domain TEXT,
    url TEXT,
    status TEXT
);

CREATE TABLE IF NOT EXISTS pages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    audit_id TEXT,
    url TEXT,
    status_code INTEGER,
    content_type TEXT,
    response_time_ms REAL,
    html_size INTEGER,
    word_count INTEGER,
    title TEXT,
    meta_description TEXT,
    h1 TEXT,
    canonical_url TEXT,
    viewport TEXT,
    is_indexable BOOLEAN,
    crawl_depth INTEGER,
    redirect_url TEXT,
    redirect_chain TEXT,
    content_hash TEXT,
    raw_html_hash TEXT,
    rendered_html_hash TEXT,
    page_type TEXT,
    mime_type TEXT,
    parent_url TEXT,
    language TEXT,
    robots_meta TEXT,
    title_length INTEGER,
    meta_description_length INTEGER,
    meta_keywords TEXT,
    meta_keywords_length INTEGER,
    h1_count INTEGER DEFAULT 0,
    h1_length INTEGER,
    h2_count INTEGER DEFAULT 0,
    h2_length INTEGER,
    sentence_count INTEGER,
    avg_words_per_sentence REAL,
    text_ratio REAL,
    folder_depth INTEGER,
    http_version TEXT,
    size_bytes INTEGER,
    transferred_bytes INTEGER,
    total_transferred_bytes INTEGER,
    headers_json TEXT,
    content_near_duplicate_hash TEXT,
    crawl_timestamp TIMESTAMP,
    html_word_count INTEGER,
    html_title TEXT,
    html_h1 TEXT,
    html_meta_description TEXT,
    html_canonical TEXT,
    html_meta_robots TEXT,
    pretty_url TEXT,
    ugly_url TEXT,
    og_title TEXT,
    og_description TEXT,
    og_image TEXT,
    og_type TEXT,
    twitter_card TEXT,
    twitter_title TEXT,
    twitter_description TEXT,
    twitter_image TEXT,
    tls_protocol TEXT,
    server_header TEXT,
    form_count INTEGER DEFAULT 0,
    iframe_count INTEGER DEFAULT 0,
    created_at TIMESTAMP,
    x_robots_tag TEXT,
    http_canonical TEXT,
    UNIQUE(audit_id, url)
);

CREATE TABLE IF NOT EXISTS links (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    audit_id TEXT,
    source_page_id INTEGER,
    source_url TEXT,
    target_url TEXT,
    anchor_text TEXT,
    is_internal BOOLEAN,
    is_broken BOOLEAN,
    rel_attributes TEXT,
    link_type TEXT,
    nofollow BOOLEAN
);

CREATE TABLE IF NOT EXISTS images (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    audit_id TEXT,
    page_id INTEGER,
    page_url TEXT,
    src TEXT,
    alt_text TEXT,
    width INTEGER,
    height INTEGER,
    format TEXT,
    is_lazy_loaded BOOLEAN,
    has_dimensions BOOLEAN,
    is_broken BOOLEAN
);

CREATE TABLE IF NOT EXISTS headings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    page_id INTEGER,
    tag TEXT,
    text TEXT,
    order_index INTEGER
);

CREATE TABLE IF NOT EXISTS structured_data (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    audit_id TEXT,
    page_id INTEGER,
    page_url TEXT,
    format TEXT,
    schema_type TEXT,
    data_json TEXT,
    is_valid BOOLEAN
);

CREATE TABLE IF NOT EXISTS forms (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    audit_id TEXT,
    page_id INTEGER,
    page_url TEXT,
    action_url TEXT,
    method TEXT,
    form_id TEXT,
    has_password BOOLEAN DEFAULT 0,
    is_search BOOLEAN DEFAULT 0,
    is_insecure BOOLEAN DEFAULT 0
);

CREATE TABLE IF NOT EXISTS hreflang_tags (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    audit_id TEXT,
    page_id INTEGER,
    source_url TEXT,
    target_url TEXT,
    lang_code TEXT,
    is_reciprocal BOOLEAN,
    is_self BOOLEAN,
    error_type TEXT
);

CREATE TABLE IF NOT EXISTS pagination_tags (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    audit_id TEXT,
    page_id INTEGER,
    page_url TEXT,
    rel_type TEXT,
    target_url TEXT,
    source TEXT
);

CREATE TABLE IF NOT EXISTS sitemap_entries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    audit_id TEXT,
    page_id INTEGER,
    page_url TEXT,
    sitemap_url TEXT,
    lastmod TEXT,
    changefreq TEXT,
    priority REAL
);
`

func TestSQLiteBatchWriterDataPopulation(t *testing.T) {
	tempDir := t.TempDir()
	dbPath := filepath.Join(tempDir, "test_audit.db")

	db, err := sql.Open("sqlite", dbPath)
	if err != nil {
		t.Fatalf("Failed to open test sqlite db: %v", err)
	}
	if _, err := db.Exec(testSchema); err != nil {
		t.Fatalf("Failed to init test schema: %v", err)
	}
	db.Close()

	auditID := "test-audit-pop"
	writer, err := NewSQLiteBatchWriter(dbPath, auditID, 10, 500*time.Millisecond)
	if err != nil {
		t.Fatalf("Failed to create SQLiteBatchWriter: %v", err)
	}

	record := &CrawlRecord{
		AuditID:        auditID,
		PageID:         1,
		URL:            "https://example.com/blog/article",
		FinalURL:       "https://example.com/blog/article",
		StatusCode:     200,
		ContentType:    "text/html; charset=utf-8",
		ResponseTimeMs: 145.2,
		SizeBytes:      4096,
		CrawlDepth:     1,
		ParentURL:      "https://example.com",
		CrawlTimestamp: time.Now(),
		Response: &fetcher.FetchResponse{
			HTTPVersion:  "HTTP/2.0",
			TLSProtocol:  "TLS 1.3",
			ServerHeader: "cloudflare",
			Headers: map[string]string{
				"x-robots-tag": "index, follow",
				"link":         `<https://example.com/canonical-article>; rel="canonical"`,
			},
		},
		Parsed: &parser.PageParseResult{
			Title:           "Test Article",
			TitleLength:     12,
			MetaDescription: "Test description",
			CanonicalURL:    "https://example.com/canonical-article",
			H1:              "Main Article Title",
			H1Count:         1,
			WordCount:       250,
			SentenceCount:   15,
			H1H6: map[string][]string{
				"h1": {"Main Article Title"},
				"h2": {"Section 1", "Section 2"},
			},
			Links: []parser.LinkData{
				{
					Tag:        "a",
					HREF:       "/about", // relative HREF to test normalization
					Text:       "About Us",
					IsInternal: true,
				},
				{
					Tag:        "a",
					HREF:       "https://external.com/partner",
					Text:       "Partner",
					IsInternal: false,
					NoFollow:   true,
				},
			},
			Images: []parser.ImageData{
				{
					Src:          "/images/logo.png", // relative Src to test normalization
					Alt:          "Company Logo",
					Width:        200,
					Height:       50,
					Format:       "png",
					IsLazyLoaded: true,
				},
			},
			HreflangTags: []parser.HreflangData{
				{
					LangCode:  "es",
					TargetURL: "/es/blog/article",
				},
				{
					LangCode:  "en",
					TargetURL: "https://example.com/blog/article",
				},
			},
			PaginationTags: []parser.PaginationData{
				{
					RelType:   "next",
					TargetURL: "/blog/article?page=2",
					Source:    "html",
				},
			},
			Forms: []parser.FormData{
				{
					Action:   "/subscribe",
					Method:   "POST",
					ID:       "newsletter-form",
					IsSearch: false,
				},
			},
		},
	}

	if err := writer.WritePage(record); err != nil {
		t.Fatalf("WritePage failed: %v", err)
	}

	// Also test sitemap write
	sitemaps := []SitemapEntry{
		{
			AuditID:    auditID,
			PageURL:    "https://example.com/blog/article",
			SitemapURL: "https://example.com/sitemap.xml",
			LastMod:    "2026-10-15",
			ChangeFreq: "weekly",
			Priority:   0.8,
		},
	}
	if err := writer.WriteSitemapEntries(sitemaps); err != nil {
		t.Fatalf("WriteSitemapEntries failed: %v", err)
	}

	if err := writer.Flush(); err != nil {
		t.Fatalf("Flush failed: %v", err)
	}
	if err := writer.Close(); err != nil {
		t.Fatalf("Close failed: %v", err)
	}

	// Verify directly in SQLite
	checkDB, err := sql.Open("sqlite", dbPath)
	if err != nil {
		t.Fatalf("Failed to open check DB: %v", err)
	}
	defer checkDB.Close()

	// 1. Verify Pages table (including x_robots_tag and http_canonical)
	var title, xRobots, httpCanon string
	var isIndexable int
	err = checkDB.QueryRow("SELECT title, x_robots_tag, http_canonical, is_indexable FROM pages WHERE audit_id = ?", auditID).Scan(&title, &xRobots, &httpCanon, &isIndexable)
	if err != nil {
		t.Fatalf("Failed to query pages: %v", err)
	}
	if title != "Test Article" {
		t.Errorf("Expected title 'Test Article', got %q", title)
	}
	if xRobots != "index, follow" {
		t.Errorf("Expected x_robots_tag 'index, follow', got %q", xRobots)
	}
	if httpCanon != "https://example.com/canonical-article" {
		t.Errorf("Expected http_canonical 'https://example.com/canonical-article', got %q", httpCanon)
	}
	if isIndexable != 1 {
		t.Errorf("Expected is_indexable 1, got %d", isIndexable)
	}

	// 2. Verify Links table: target_url MUST be absolute!
	var internalTarget string
	err = checkDB.QueryRow("SELECT target_url FROM links WHERE audit_id = ? AND is_internal = 1", auditID).Scan(&internalTarget)
	if err != nil {
		t.Fatalf("Failed to query internal link: %v", err)
	}
	if internalTarget != "https://example.com/about" {
		t.Errorf("Expected normalized absolute target_url 'https://example.com/about', got %q", internalTarget)
	}

	// 3. Verify Images table: src MUST be absolute!
	var imgSrc string
	err = checkDB.QueryRow("SELECT src FROM images WHERE audit_id = ?", auditID).Scan(&imgSrc)
	if err != nil {
		t.Fatalf("Failed to query images: %v", err)
	}
	if imgSrc != "https://example.com/images/logo.png" {
		t.Errorf("Expected normalized absolute img src 'https://example.com/images/logo.png', got %q", imgSrc)
	}

	// 4. Verify Hreflang table: must have 2 tags, with is_self correctly calculated
	var esTarget string
	var enIsSelf int
	err = checkDB.QueryRow("SELECT target_url FROM hreflang_tags WHERE audit_id = ? AND lang_code = 'es'", auditID).Scan(&esTarget)
	if err != nil {
		t.Fatalf("Failed to query es hreflang: %v", err)
	}
	if esTarget != "https://example.com/es/blog/article" {
		t.Errorf("Expected normalized es hreflang 'https://example.com/es/blog/article', got %q", esTarget)
	}

	err = checkDB.QueryRow("SELECT is_self FROM hreflang_tags WHERE audit_id = ? AND lang_code = 'en'", auditID).Scan(&enIsSelf)
	if err != nil {
		t.Fatalf("Failed to query en hreflang: %v", err)
	}
	if enIsSelf != 1 {
		t.Errorf("Expected en hreflang is_self = 1, got %d", enIsSelf)
	}

	// 5. Verify Pagination table
	var pagTarget, pagRel string
	err = checkDB.QueryRow("SELECT target_url, rel_type FROM pagination_tags WHERE audit_id = ?", auditID).Scan(&pagTarget, &pagRel)
	if err != nil {
		t.Fatalf("Failed to query pagination: %v", err)
	}
	if pagRel != "next" || pagTarget != "https://example.com/blog/article?page=2" {
		t.Errorf("Expected next pagination 'https://example.com/blog/article?page=2', got rel=%q, target=%q", pagRel, pagTarget)
	}

	// 6. Verify Sitemap entries table
	var smPageURL, smURL string
	var priority float64
	err = checkDB.QueryRow("SELECT page_url, sitemap_url, priority FROM sitemap_entries WHERE audit_id = ?", auditID).Scan(&smPageURL, &smURL, &priority)
	if err != nil {
		t.Fatalf("Failed to query sitemap_entries: %v", err)
	}
	if smPageURL != "https://example.com/blog/article" || smURL != "https://example.com/sitemap.xml" || priority != 0.8 {
		t.Errorf("Unexpected sitemap entry: page=%q, sitemap=%q, priority=%f", smPageURL, smURL, priority)
	}

	_ = os.RemoveAll(tempDir)
}
