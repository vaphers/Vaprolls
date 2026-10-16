-- PostgreSQL & TimescaleDB Schema for High-Scale SEO Auditing (10M - 100M URLs)

-- Attempt to enable TimescaleDB if installed
DO $$
BEGIN
    CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;
EXCEPTION WHEN OTHERS THEN
    RAISE NOTICE 'TimescaleDB extension not available, running on standard PostgreSQL.';
END $$;

-- 1. Audits Table
CREATE TABLE IF NOT EXISTS audits (
    id VARCHAR(64) PRIMARY KEY,
    domain VARCHAR(255) NOT NULL,
    url TEXT NOT NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'pending',
    started_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    total_pages BIGINT DEFAULT 0,
    total_issues BIGINT DEFAULT 0,
    health_score DOUBLE PRECISION DEFAULT 100.0,
    config JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 2. Crawl Checkpoints for crash recovery and resume
CREATE TABLE IF NOT EXISTS crawl_checkpoints (
    audit_id VARCHAR(64) PRIMARY KEY REFERENCES audits(id) ON DELETE CASCADE,
    pages_crawled BIGINT DEFAULT 0,
    queue_size BIGINT DEFAULT 0,
    errors_count BIGINT DEFAULT 0,
    bloom_file_path TEXT,
    badger_dir_path TEXT,
    status VARCHAR(32) DEFAULT 'running',
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 3. Pages Table (Partitioned by crawl_timestamp for TimescaleDB)
CREATE TABLE IF NOT EXISTS pages (
    crawl_timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    audit_id VARCHAR(64) NOT NULL,
    page_id BIGINT NOT NULL,
    url TEXT NOT NULL,
    url_hash CHAR(32) NOT NULL,
    final_url TEXT,
    status_code INT NOT NULL,
    content_type VARCHAR(128),
    response_time_ms DOUBLE PRECISION,
    size_bytes BIGINT DEFAULT 0,
    transferred_bytes BIGINT DEFAULT 0,
    word_count INT DEFAULT 0,
    crawl_depth INT DEFAULT 0,
    parent_url TEXT,
    
    -- Core SEO Fields
    title TEXT,
    title_length INT,
    meta_description TEXT,
    meta_description_length INT,
    meta_keywords TEXT,
    meta_keywords_length INT,
    meta_robots TEXT,
    canonical_url TEXT,
    viewport TEXT,
    language VARCHAR(32),
    is_indexable SMALLINT DEFAULT 1,
    indexability_status VARCHAR(64),
    
    -- Headings
    h1 TEXT,
    h1_count INT DEFAULT 0,
    h1_length INT DEFAULT 0,
    h2 TEXT,
    h2_count INT DEFAULT 0,
    h2_length INT DEFAULT 0,
    
    -- Link & Media Counts
    inlinks_count INT DEFAULT 0,
    outlinks_count INT DEFAULT 0,
    external_links_count INT DEFAULT 0,
    unique_inlinks INT DEFAULT 0,
    unique_outlinks INT DEFAULT 0,
    unique_external_outlinks INT DEFAULT 0,
    images_count INT DEFAULT 0,
    images_missing_alt INT DEFAULT 0,
    link_score DOUBLE PRECISION DEFAULT 0.0,
    internal_pagerank DOUBLE PRECISION DEFAULT 0.0,
    
    -- Content & Readability
    sentence_count INT DEFAULT 0,
    avg_words_per_sentence DOUBLE PRECISION DEFAULT 0.0,
    text_ratio DOUBLE PRECISION DEFAULT 0.0,
    flesch_reading_ease DOUBLE PRECISION DEFAULT 0.0,
    readability_label VARCHAR(64),
    content_hash CHAR(32),
    simhash VARCHAR(64),
    content_near_duplicate_hash VARCHAR(64),
    near_duplicate_count INT DEFAULT 0,
    closest_duplicate_url TEXT,
    closest_duplicate_similarity DOUBLE PRECISION DEFAULT 0.0,
    
    -- Redirects
    redirect_url TEXT,
    redirect_type VARCHAR(32),
    redirect_chain JSONB,
    redirect_chain_details JSONB,
    
    -- Technical & Security
    http_version VARCHAR(16),
    tls_protocol VARCHAR(32),
    server_header VARCHAR(128),
    x_robots_tag TEXT,
    http_canonical TEXT,
    mobile_alt_link TEXT,
    amp_html_link TEXT,
    security_headers JSONB,
    headers_json JSONB,
    cookies_json JSONB,
    
    -- Deep Payloads & OpenGraph
    og_title TEXT,
    og_description TEXT,
    og_image TEXT,
    og_type VARCHAR(64),
    twitter_card VARCHAR(64),
    twitter_title TEXT,
    twitter_description TEXT,
    twitter_image TEXT,
    
    links JSONB,
    images JSONB,
    resources JSONB,
    forms JSONB,
    iframes JSONB,
    structured_data JSONB,
    microdata JSONB,
    rdfa JSONB,
    hreflang JSONB,
    pagination JSONB,
    custom_extractions JSONB,
    custom_searches JSONB,
    plaintext_emails JSONB,
    
    -- Rendered / JS Comparison
    rendered_title TEXT,
    rendered_meta_description TEXT,
    rendered_h1 TEXT,
    rendered_canonical TEXT,
    rendered_meta_robots TEXT,
    rendered_word_count INT,
    js_errors INT DEFAULT 0,
    js_warnings INT DEFAULT 0,
    js_issues JSONB
);

-- Convert pages to Hypertable if TimescaleDB is present
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'timescaledb') THEN
        PERFORM create_hypertable('pages', 'crawl_timestamp', if_not_exists => TRUE);
        
        -- Enable TimescaleDB Columnar Compression
        ALTER TABLE pages SET (
            timescaledb.compress,
            timescaledb.compress_segmentby = 'audit_id',
            timescaledb.compress_orderby = 'crawl_timestamp DESC, page_id'
        );
        
        -- Automatically compress chunks older than 1 day
        PERFORM add_compression_policy('pages', INTERVAL '1 day', if_not_exists => TRUE);
    END IF;
EXCEPTION WHEN OTHERS THEN
    RAISE NOTICE 'Hypertable creation skipped: %', SQLERRM;
END $$;

-- Indexes for lightning analytical queries
CREATE INDEX IF NOT EXISTS idx_pages_audit_url ON pages (audit_id, url_hash);
CREATE INDEX IF NOT EXISTS idx_pages_audit_status ON pages (audit_id, status_code);
CREATE INDEX IF NOT EXISTS idx_pages_audit_depth ON pages (audit_id, crawl_depth);
CREATE INDEX IF NOT EXISTS idx_pages_audit_page_id ON pages (audit_id, page_id);
CREATE INDEX IF NOT EXISTS idx_pages_audit_indexable ON pages (audit_id, is_indexable);

-- 4. Audit Issues Table
CREATE TABLE IF NOT EXISTS issues (
    id BIGSERIAL PRIMARY KEY,
    audit_id VARCHAR(64) NOT NULL REFERENCES audits(id) ON DELETE CASCADE,
    page_id BIGINT,
    page_url TEXT,
    category VARCHAR(64) NOT NULL,
    issue_type VARCHAR(64) NOT NULL,
    severity VARCHAR(32) NOT NULL, -- 'critical', 'warning', 'info'
    title TEXT NOT NULL,
    description TEXT,
    recommendation TEXT,
    details JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_issues_audit_sev ON issues (audit_id, severity);
CREATE INDEX IF NOT EXISTS idx_issues_audit_cat ON issues (audit_id, category);

-- 5. Links Table (Optional auxiliary normalized table)
CREATE TABLE IF NOT EXISTS links (
    id BIGSERIAL PRIMARY KEY,
    audit_id VARCHAR(64) NOT NULL REFERENCES audits(id) ON DELETE CASCADE,
    source_page_id BIGINT,
    source_url TEXT NOT NULL,
    target_url TEXT NOT NULL,
    anchor_text TEXT,
    is_internal BOOLEAN DEFAULT TRUE,
    is_broken BOOLEAN DEFAULT FALSE,
    status_code INT,
    rel_attributes TEXT,
    link_type VARCHAR(32) DEFAULT 'a',
    nofollow BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_links_audit_src ON links (audit_id, source_url);
CREATE INDEX IF NOT EXISTS idx_links_audit_tgt ON links (audit_id, target_url);

-- 6. Images Table
CREATE TABLE IF NOT EXISTS images (
    id BIGSERIAL PRIMARY KEY,
    audit_id VARCHAR(64) NOT NULL REFERENCES audits(id) ON DELETE CASCADE,
    page_id BIGINT,
    page_url TEXT NOT NULL,
    src TEXT NOT NULL,
    alt_text TEXT,
    file_size BIGINT,
    width INT,
    height INT,
    format VARCHAR(32),
    is_lazy_loaded BOOLEAN DEFAULT FALSE,
    has_dimensions BOOLEAN DEFAULT FALSE,
    is_broken BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_images_audit ON images (audit_id, page_url);

-- 7. Sitemap Entries Table
CREATE TABLE IF NOT EXISTS sitemap_entries (
    id BIGSERIAL PRIMARY KEY,
    audit_id VARCHAR(64) NOT NULL REFERENCES audits(id) ON DELETE CASCADE,
    page_url TEXT NOT NULL,
    sitemap_url TEXT NOT NULL,
    lastmod TIMESTAMPTZ,
    changefreq VARCHAR(32),
    priority DOUBLE PRECISION,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_sitemap_entries_audit_page ON sitemap_entries (audit_id, page_url);

-- 8. Hreflang Tags Table
CREATE TABLE IF NOT EXISTS hreflang_tags (
    id BIGSERIAL PRIMARY KEY,
    audit_id VARCHAR(64) NOT NULL REFERENCES audits(id) ON DELETE CASCADE,
    page_id BIGINT,
    page_url TEXT NOT NULL,
    lang_code VARCHAR(32) NOT NULL,
    hreflang_url TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_hreflang_audit_url ON hreflang_tags (audit_id, page_url);

-- 9. Pagination Tags Table
CREATE TABLE IF NOT EXISTS pagination_tags (
    id BIGSERIAL PRIMARY KEY,
    audit_id VARCHAR(64) NOT NULL REFERENCES audits(id) ON DELETE CASCADE,
    page_id BIGINT,
    page_url TEXT NOT NULL,
    rel_type VARCHAR(16) NOT NULL,
    target_url TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_pagination_audit_url ON pagination_tags (audit_id, page_url);

-- 10. Headings Table
CREATE TABLE IF NOT EXISTS headings (
    id BIGSERIAL PRIMARY KEY,
    audit_id VARCHAR(64) NOT NULL REFERENCES audits(id) ON DELETE CASCADE,
    page_id BIGINT,
    page_url TEXT NOT NULL,
    level VARCHAR(4) NOT NULL,
    text TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_headings_audit_url ON headings (audit_id, page_url);

-- 11. Custom Extractions Table
CREATE TABLE IF NOT EXISTS custom_extractions (
    id BIGSERIAL PRIMARY KEY,
    audit_id VARCHAR(64) NOT NULL REFERENCES audits(id) ON DELETE CASCADE,
    page_id BIGINT,
    page_url TEXT NOT NULL,
    name VARCHAR(128) NOT NULL,
    value TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_extractions_audit ON custom_extractions (audit_id, page_url);

-- 12. Custom Search Matches Table
CREATE TABLE IF NOT EXISTS custom_search_matches (
    id BIGSERIAL PRIMARY KEY,
    audit_id VARCHAR(64) NOT NULL REFERENCES audits(id) ON DELETE CASCADE,
    page_id BIGINT,
    page_url TEXT NOT NULL,
    rule_name VARCHAR(128) NOT NULL,
    matched BOOLEAN DEFAULT FALSE,
    match_count INT DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_search_matches_audit ON custom_search_matches (audit_id, page_url);
