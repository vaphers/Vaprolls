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
    page_type TEXT,
    mime_type TEXT,
    parent_url TEXT,
    language TEXT,
    robots_meta TEXT,
    title_length INTEGER,
    title_pixel_width INTEGER,
    meta_description_length INTEGER,
    meta_desc_pixel_width INTEGER,
    meta_keywords TEXT,
    meta_keywords_length INTEGER,
    h1_count INTEGER DEFAULT 0,
    h1_length INTEGER,
    h2_count INTEGER DEFAULT 0,
    h2_length INTEGER,
    sentence_count INTEGER,
    avg_words_per_sentence REAL,
    text_ratio REAL,
    flesch_reading_ease REAL,
    readability_label TEXT,
    folder_depth INTEGER,
    http_version TEXT,
    mobile_alt_link TEXT,
    size_bytes INTEGER,
    transferred_bytes INTEGER,
    total_transferred_bytes INTEGER,
    redirect_type TEXT,
    unique_inlinks INTEGER DEFAULT 0,
    unique_outlinks INTEGER DEFAULT 0,
    unique_external_outlinks INTEGER DEFAULT 0,
    link_score REAL DEFAULT 0.0,
    headers_json TEXT,
    cookies_json TEXT,
    content_near_duplicate_hash TEXT,
    near_duplicate_count INTEGER DEFAULT 0,
    closest_duplicate_url TEXT,
    closest_duplicate_similarity REAL,
    psi_status TEXT,
    psi_mobile_score REAL,
    psi_desktop_score REAL,
    accessibility_violations_total INTEGER DEFAULT 0,
    accessibility_best_practice INTEGER DEFAULT 0,
    accessibility_wcag_2_0_a INTEGER DEFAULT 0,
    accessibility_wcag_2_0_aa INTEGER DEFAULT 0,
    accessibility_wcag_2_0_aaa INTEGER DEFAULT 0,
    accessibility_wcag_2_1_aa INTEGER DEFAULT 0,
    accessibility_wcag_2_2_aa INTEGER DEFAULT 0,
    crawl_timestamp TIMESTAMP,
    html_word_count INTEGER,
    rendered_word_count INTEGER,
    word_count_change INTEGER,
    js_word_count_pct REAL,
    html_title TEXT,
    rendered_title TEXT,
    html_h1 TEXT,
    rendered_h1 TEXT,
    html_meta_description TEXT,
    rendered_meta_description TEXT,
    html_canonical TEXT,
    rendered_canonical TEXT,
    html_meta_robots TEXT,
    rendered_meta_robots TEXT,
    js_errors INTEGER DEFAULT 0,
    js_warnings INTEGER DEFAULT 0,
    js_info INTEGER DEFAULT 0,
    js_debug INTEGER DEFAULT 0,
    js_issues TEXT,
    pretty_url TEXT,
    ugly_url TEXT,
    x_robots_tag TEXT,
    http_canonical TEXT,
    amp_html_link TEXT,
    og_title TEXT,
    og_description TEXT,
    og_image TEXT,
    og_type TEXT,
    twitter_card TEXT,
    twitter_title TEXT,
    twitter_description TEXT,
    twitter_image TEXT,
    hsts_header TEXT,
    csp_header TEXT,
    x_content_type_options TEXT,
    x_frame_options TEXT,
    referrer_policy TEXT,
    permissions_policy TEXT,
    tls_protocol TEXT,
    server_header TEXT,
    redirect_chain_details TEXT,
    form_count INTEGER DEFAULT 0,
    iframe_count INTEGER DEFAULT 0,
    has_mixed_content BOOLEAN DEFAULT 0,
    microdata_json TEXT,
    rdfa_json TEXT,
    plaintext_emails_json TEXT,
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
    unique_js_inlinks INTEGER DEFAULT 0,
    unique_js_outlinks INTEGER DEFAULT 0,
    FOREIGN KEY(audit_id) REFERENCES audits(id),
    FOREIGN KEY(source_page_id) REFERENCES pages(id)
);
CREATE INDEX IF NOT EXISTS idx_links_audit_id ON links(audit_id);
CREATE INDEX IF NOT EXISTS idx_links_source_page_id ON links(source_page_id);
CREATE INDEX IF NOT EXISTS idx_links_audit_target ON links(audit_id, target_url);
CREATE INDEX IF NOT EXISTS idx_links_audit_source ON links(audit_id, source_page_id);
CREATE INDEX IF NOT EXISTS idx_links_audit_internal_target ON links(audit_id, is_internal, target_url);

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

CREATE TABLE IF NOT EXISTS pagination_tags (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    audit_id TEXT,
    page_id INTEGER,
    page_url TEXT,
    rel_type TEXT,
    target_url TEXT,
    source TEXT,
    FOREIGN KEY(audit_id) REFERENCES audits(id),
    FOREIGN KEY(page_id) REFERENCES pages(id)
);
CREATE INDEX IF NOT EXISTS idx_pagination_tags_audit_id ON pagination_tags(audit_id);
CREATE INDEX IF NOT EXISTS idx_pagination_tags_page_id ON pagination_tags(page_id);

CREATE TABLE IF NOT EXISTS accessibility_violations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    audit_id TEXT,
    page_id INTEGER,
    page_url TEXT,
    rule_id TEXT,
    description TEXT,
    impact TEXT,
    wcag_tags TEXT,
    html_snippet TEXT,
    target_selector TEXT,
    FOREIGN KEY(audit_id) REFERENCES audits(id),
    FOREIGN KEY(page_id) REFERENCES pages(id)
);
CREATE INDEX IF NOT EXISTS idx_access_viol_audit_id ON accessibility_violations(audit_id);
CREATE INDEX IF NOT EXISTS idx_access_viol_page_id ON accessibility_violations(page_id);

CREATE TABLE IF NOT EXISTS console_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    audit_id TEXT,
    page_id INTEGER,
    page_url TEXT,
    level TEXT,
    message TEXT,
    source TEXT,
    line_number INTEGER,
    timestamp TIMESTAMP,
    FOREIGN KEY(audit_id) REFERENCES audits(id),
    FOREIGN KEY(page_id) REFERENCES pages(id)
);
CREATE INDEX IF NOT EXISTS idx_console_logs_audit_id ON console_logs(audit_id);
CREATE INDEX IF NOT EXISTS idx_console_logs_page_id ON console_logs(page_id);

CREATE TABLE IF NOT EXISTS sitemap_entries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    audit_id TEXT,
    page_id INTEGER,
    page_url TEXT,
    sitemap_url TEXT,
    lastmod TEXT,
    changefreq TEXT,
    priority REAL,
    FOREIGN KEY(audit_id) REFERENCES audits(id),
    FOREIGN KEY(page_id) REFERENCES pages(id)
);
CREATE INDEX IF NOT EXISTS idx_sitemap_entries_audit_id ON sitemap_entries(audit_id);
CREATE INDEX IF NOT EXISTS idx_sitemap_entries_page_id ON sitemap_entries(page_id);

CREATE TABLE IF NOT EXISTS crawl_frontier (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    audit_id TEXT,
    url TEXT,
    depth INTEGER DEFAULT 0,
    parent_url TEXT,
    status TEXT DEFAULT 'pending',
    created_at TIMESTAMP,
    FOREIGN KEY(audit_id) REFERENCES audits(id),
    UNIQUE(audit_id, url)
);
CREATE INDEX IF NOT EXISTS idx_frontier_audit_status ON crawl_frontier(audit_id, status);
CREATE INDEX IF NOT EXISTS idx_frontier_audit_depth ON crawl_frontier(audit_id, depth);

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
    is_insecure BOOLEAN DEFAULT 0,
    created_at TIMESTAMP,
    FOREIGN KEY(audit_id) REFERENCES audits(id),
    FOREIGN KEY(page_id) REFERENCES pages(id)
);
CREATE INDEX IF NOT EXISTS idx_forms_audit_id ON forms(audit_id);
CREATE INDEX IF NOT EXISTS idx_forms_page_id ON forms(page_id);

CREATE TABLE IF NOT EXISTS external_links (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    audit_id TEXT,
    source_page_id INTEGER,
    source_url TEXT,
    target_url TEXT,
    anchor_text TEXT,
    rel_attributes TEXT,
    status_code INTEGER,
    is_broken BOOLEAN DEFAULT 0,
    created_at TIMESTAMP,
    FOREIGN KEY(audit_id) REFERENCES audits(id),
    FOREIGN KEY(source_page_id) REFERENCES pages(id)
);
CREATE INDEX IF NOT EXISTS idx_external_links_audit_id ON external_links(audit_id);
"""

