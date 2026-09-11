SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS audits (
    id TEXT PRIMARY KEY,
    domain TEXT,
    url TEXT,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    status TEXT,
    total_pages INTEGER,
    total_issues INTEGER,
    health_score REAL,
    config_json TEXT
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
    internal_pagerank REAL DEFAULT 0.0,
    raw_html_hash TEXT,
    rendered_html_hash TEXT,
    gsc_clicks INTEGER DEFAULT 0,
    gsc_impressions INTEGER DEFAULT 0,
    gsc_ctr REAL DEFAULT 0.0,
    gsc_position REAL DEFAULT 0.0,
    log_hits_count INTEGER DEFAULT 0,
    log_last_visit TIMESTAMP,
    created_at TIMESTAMP,
    FOREIGN KEY(audit_id) REFERENCES audits(id),
    UNIQUE(audit_id, url)
);
CREATE INDEX IF NOT EXISTS idx_pages_audit_id ON pages(audit_id);
CREATE INDEX IF NOT EXISTS idx_pages_url ON pages(url);

CREATE TABLE IF NOT EXISTS issues (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    audit_id TEXT,
    page_id INTEGER,
    url TEXT,
    category TEXT,
    severity TEXT,
    issue_type TEXT,
    message TEXT,
    recommendation TEXT,
    element TEXT,
    created_at TIMESTAMP,
    FOREIGN KEY(audit_id) REFERENCES audits(id),
    FOREIGN KEY(page_id) REFERENCES pages(id)
);
CREATE INDEX IF NOT EXISTS idx_issues_audit_id ON issues(audit_id);
CREATE INDEX IF NOT EXISTS idx_issues_page_id ON issues(page_id);
CREATE INDEX IF NOT EXISTS idx_issues_audit_sev ON issues(audit_id, severity);
CREATE INDEX IF NOT EXISTS idx_issues_audit_type ON issues(audit_id, issue_type);

CREATE TABLE IF NOT EXISTS links (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    audit_id TEXT,
    source_page_id INTEGER,
    source_url TEXT,
    target_url TEXT,
    anchor_text TEXT,
    is_internal BOOLEAN,
    is_broken BOOLEAN,
    status_code INTEGER,
    rel_attributes TEXT,
    link_type TEXT,
    nofollow BOOLEAN,
    FOREIGN KEY(audit_id) REFERENCES audits(id),
    FOREIGN KEY(source_page_id) REFERENCES pages(id)
);
CREATE INDEX IF NOT EXISTS idx_links_audit_id ON links(audit_id);
CREATE INDEX IF NOT EXISTS idx_links_source_page_id ON links(source_page_id);

CREATE TABLE IF NOT EXISTS images (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    audit_id TEXT,
    page_id INTEGER,
    page_url TEXT,
    src TEXT,
    alt_text TEXT,
    file_size INTEGER,
    width INTEGER,
    height INTEGER,
    format TEXT,
    is_lazy_loaded BOOLEAN,
    has_dimensions BOOLEAN,
    is_broken BOOLEAN,
    FOREIGN KEY(audit_id) REFERENCES audits(id),
    FOREIGN KEY(page_id) REFERENCES pages(id)
);
CREATE INDEX IF NOT EXISTS idx_images_audit_id ON images(audit_id);
CREATE INDEX IF NOT EXISTS idx_images_page_id ON images(page_id);

CREATE TABLE IF NOT EXISTS keywords (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    audit_id TEXT,
    page_id INTEGER,
    page_url TEXT,
    keyword TEXT,
    frequency INTEGER,
    density REAL,
    in_title BOOLEAN,
    in_h1 BOOLEAN,
    in_meta_description BOOLEAN,
    in_url BOOLEAN,
    ngram_size INTEGER,
    FOREIGN KEY(audit_id) REFERENCES audits(id),
    FOREIGN KEY(page_id) REFERENCES pages(id)
);
CREATE INDEX IF NOT EXISTS idx_keywords_audit_id ON keywords(audit_id);
CREATE INDEX IF NOT EXISTS idx_keywords_page_id ON keywords(page_id);

CREATE TABLE IF NOT EXISTS headings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    page_id INTEGER,
    tag TEXT,
    text TEXT,
    order_index INTEGER,
    FOREIGN KEY(page_id) REFERENCES pages(id)
);
CREATE INDEX IF NOT EXISTS idx_headings_page_id ON headings(page_id);

CREATE TABLE IF NOT EXISTS resources (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    audit_id TEXT,
    page_id INTEGER,
    url TEXT,
    resource_type TEXT,
    size INTEGER,
    is_render_blocking BOOLEAN,
    is_minified BOOLEAN,
    cache_control TEXT,
    FOREIGN KEY(audit_id) REFERENCES audits(id),
    FOREIGN KEY(page_id) REFERENCES pages(id)
);
CREATE INDEX IF NOT EXISTS idx_resources_audit_id ON resources(audit_id);
CREATE INDEX IF NOT EXISTS idx_resources_page_id ON resources(page_id);

CREATE TABLE IF NOT EXISTS structured_data (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    audit_id TEXT,
    page_id INTEGER,
    page_url TEXT,
    format TEXT,
    schema_type TEXT,
    data_json TEXT,
    is_valid BOOLEAN,
    errors TEXT,
    FOREIGN KEY(audit_id) REFERENCES audits(id),
    FOREIGN KEY(page_id) REFERENCES pages(id)
);
CREATE INDEX IF NOT EXISTS idx_structured_data_audit_id ON structured_data(audit_id);
CREATE INDEX IF NOT EXISTS idx_structured_data_page_id ON structured_data(page_id);

CREATE TABLE IF NOT EXISTS performance_metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    audit_id TEXT,
    page_id INTEGER,
    page_url TEXT,
    lcp_ms REAL,
    inp_ms REAL,
    cls REAL,
    fcp_ms REAL,
    ttfb_ms REAL,
    speed_index REAL,
    performance_score REAL,
    total_page_size INTEGER,
    total_requests INTEGER,
    dom_nodes INTEGER,
    lighthouse_json TEXT,
    FOREIGN KEY(audit_id) REFERENCES audits(id),
    FOREIGN KEY(page_id) REFERENCES pages(id)
);
CREATE INDEX IF NOT EXISTS idx_performance_metrics_audit_id ON performance_metrics(audit_id);
CREATE INDEX IF NOT EXISTS idx_performance_metrics_page_id ON performance_metrics(page_id);

CREATE TABLE IF NOT EXISTS custom_extractions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    audit_id TEXT,
    page_id INTEGER,
    page_url TEXT,
    rule_name TEXT,
    extracted_value TEXT,
    created_at TIMESTAMP,
    FOREIGN KEY(audit_id) REFERENCES audits(id),
    FOREIGN KEY(page_id) REFERENCES pages(id)
);
CREATE INDEX IF NOT EXISTS idx_custom_extractions_audit_id ON custom_extractions(audit_id);
CREATE INDEX IF NOT EXISTS idx_custom_extractions_page_id ON custom_extractions(page_id);

CREATE TABLE IF NOT EXISTS custom_search_matches (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    audit_id TEXT,
    page_id INTEGER,
    page_url TEXT,
    search_name TEXT,
    matched BOOLEAN,
    snippet TEXT,
    created_at TIMESTAMP,
    FOREIGN KEY(audit_id) REFERENCES audits(id),
    FOREIGN KEY(page_id) REFERENCES pages(id)
);
CREATE INDEX IF NOT EXISTS idx_custom_search_matches_audit_id ON custom_search_matches(audit_id);

CREATE TABLE IF NOT EXISTS hreflang_tags (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    audit_id TEXT,
    page_id INTEGER,
    source_url TEXT,
    target_url TEXT,
    lang_code TEXT,
    is_reciprocal BOOLEAN,
    is_self BOOLEAN,
    error_type TEXT,
    FOREIGN KEY(audit_id) REFERENCES audits(id),
    FOREIGN KEY(page_id) REFERENCES pages(id)
);
CREATE INDEX IF NOT EXISTS idx_hreflang_tags_audit_id ON hreflang_tags(audit_id);
CREATE INDEX IF NOT EXISTS idx_hreflang_tags_source_url ON hreflang_tags(source_url);

CREATE TABLE IF NOT EXISTS log_visits (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    audit_id TEXT,
    url TEXT,
    bot_type TEXT,
    ip_address TEXT,
    status_code INTEGER,
    timestamp TIMESTAMP,
    FOREIGN KEY(audit_id) REFERENCES audits(id)
);
CREATE INDEX IF NOT EXISTS idx_log_visits_audit_id ON log_visits(audit_id);
CREATE INDEX IF NOT EXISTS idx_log_visits_url ON log_visits(url);

CREATE TABLE IF NOT EXISTS gsc_data (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    audit_id TEXT,
    url TEXT,
    clicks INTEGER,
    impressions INTEGER,
    ctr REAL,
    position REAL,
    FOREIGN KEY(audit_id) REFERENCES audits(id)
);
CREATE INDEX IF NOT EXISTS idx_gsc_data_audit_id ON gsc_data(audit_id);
CREATE INDEX IF NOT EXISTS idx_gsc_data_url ON gsc_data(url);
"""
