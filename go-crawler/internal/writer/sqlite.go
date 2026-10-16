package writer

import (
	"context"
	"database/sql"
	"encoding/json"
	"fmt"
	"log"
	"net/url"
	"strings"
	"sync"
	"time"

	"go-crawler/internal/frontier"

	_ "modernc.org/sqlite"
)

// SQLiteBatchWriter persists CrawlRecords and related relations into SQLite in high-speed transactions
type SQLiteBatchWriter struct {
	db        *sql.DB
	auditID   string
	mu        sync.Mutex
	buffer    []*CrawlRecord
	batchSize int
	flushInt  time.Duration
	stopChan  chan struct{}
	wg        sync.WaitGroup
}

// NewSQLiteBatchWriter opens the SQLite database and sets up high-performance WAL pragmas
func NewSQLiteBatchWriter(dbPath string, auditID string, batchSize int, flushInterval time.Duration) (*SQLiteBatchWriter, error) {
	if dbPath == "" {
		return nil, nil
	}

	if batchSize <= 0 {
		batchSize = 500 // 500-record batches for high-speed 100k+ crawling
	}
	if flushInterval <= 0 {
		flushInterval = 1 * time.Second
	}

	db, err := sql.Open("sqlite", dbPath)
	if err != nil {
		return nil, fmt.Errorf("failed to open sqlite database at %s: %w", dbPath, err)
	}

	// High concurrency SQLite PRAGMAs tuned for 100k+ bulk operations
	pragmas := []string{
		"PRAGMA journal_mode = WAL;",
		"PRAGMA synchronous = NORMAL;",
		"PRAGMA cache_size = -131072;", // 128MB page cache
		"PRAGMA busy_timeout = 30000;",
		"PRAGMA temp_store = MEMORY;",
		"PRAGMA wal_autocheckpoint = 20000;",
		"PRAGMA mmap_size = 536870912;", // 512MB memory-mapped I/O
	}
	for _, p := range pragmas {
		_, _ = db.Exec(p)
	}

	// Limit connection pool to avoid lock contention on SQLite WAL
	db.SetMaxOpenConns(1)
	db.SetMaxIdleConns(1)

	w := &SQLiteBatchWriter{
		db:        db,
		auditID:   auditID,
		buffer:    make([]*CrawlRecord, 0, batchSize),
		batchSize: batchSize,
		flushInt:  flushInterval,
		stopChan:  make(chan struct{}),
	}

	w.wg.Add(1)
	go w.backgroundFlush()

	return w, nil
}

// WritePage enqueues a record into the batch buffer
func (w *SQLiteBatchWriter) WritePage(record *CrawlRecord) error {
	if w == nil || w.db == nil {
		return nil
	}
	w.mu.Lock()
	w.buffer = append(w.buffer, record)
	shouldFlush := len(w.buffer) >= w.batchSize
	w.mu.Unlock()

	if shouldFlush {
		return w.Flush()
	}
	return nil
}

func (w *SQLiteBatchWriter) backgroundFlush() {
	defer w.wg.Done()
	ticker := time.NewTicker(w.flushInt)
	defer ticker.Stop()

	for {
		select {
		case <-ticker.C:
			_ = w.Flush()
		case <-w.stopChan:
			_ = w.Flush()
			return
		}
	}
}

// Flush writes buffered records to SQLite in an atomic transaction
func (w *SQLiteBatchWriter) Flush() error {
	if w == nil || w.db == nil {
		return nil
	}
	w.mu.Lock()
	if len(w.buffer) == 0 {
		w.mu.Unlock()
		return nil
	}
	records := w.buffer
	w.buffer = make([]*CrawlRecord, 0, w.batchSize)
	w.mu.Unlock()

	return w.commitBatch(records)
}

const pageInsertQuery = `
	INSERT INTO pages (
		audit_id, url, status_code, content_type, response_time_ms, html_size, word_count,
		title, meta_description, h1, canonical_url, viewport, is_indexable, crawl_depth,
		redirect_url, redirect_chain, content_hash, raw_html_hash, rendered_html_hash,
		page_type, mime_type, parent_url, language, robots_meta, title_length,
		meta_description_length, meta_keywords, meta_keywords_length, h1_count, h1_length,
		h2_count, h2_length, sentence_count, avg_words_per_sentence, text_ratio,
		folder_depth, http_version, size_bytes, transferred_bytes, total_transferred_bytes,
		headers_json, content_near_duplicate_hash, crawl_timestamp, html_word_count,
		html_title, html_h1, html_meta_description, html_canonical, html_meta_robots,
		pretty_url, ugly_url, og_title, og_description, og_image, og_type,
		twitter_card, twitter_title, twitter_description, twitter_image,
		tls_protocol, server_header, form_count, iframe_count, created_at,
		x_robots_tag, http_canonical
	) VALUES (
		?, ?, ?, ?, ?, ?, ?,
		?, ?, ?, ?, ?, ?, ?,
		?, ?, ?, ?, ?,
		?, ?, ?, ?, ?, ?,
		?, ?, ?, ?, ?,
		?, ?, ?, ?, ?,
		?, ?, ?, ?, ?,
		?, ?, ?, ?,
		?, ?, ?, ?, ?,
		?, ?, ?, ?, ?, ?,
		?, ?, ?, ?,
		?, ?, ?, ?, ?,
		?, ?
	)
	ON CONFLICT(audit_id, url) DO UPDATE SET
		status_code=excluded.status_code,
		content_type=excluded.content_type,
		response_time_ms=excluded.response_time_ms,
		html_size=excluded.html_size,
		word_count=excluded.word_count,
		title=excluded.title,
		meta_description=excluded.meta_description,
		h1=excluded.h1,
		canonical_url=excluded.canonical_url,
		viewport=excluded.viewport,
		is_indexable=excluded.is_indexable,
		crawl_depth=excluded.crawl_depth,
		redirect_url=excluded.redirect_url,
		redirect_chain=excluded.redirect_chain,
		content_hash=excluded.content_hash,
		title_length=excluded.title_length,
		meta_description_length=excluded.meta_description_length,
		meta_keywords=excluded.meta_keywords,
		h1_count=excluded.h1_count,
		h2_count=excluded.h2_count,
		sentence_count=excluded.sentence_count,
		avg_words_per_sentence=excluded.avg_words_per_sentence,
		text_ratio=excluded.text_ratio,
		headers_json=excluded.headers_json,
		crawl_timestamp=excluded.crawl_timestamp,
		pretty_url=excluded.pretty_url,
		og_title=excluded.og_title,
		og_description=excluded.og_description,
		og_image=excluded.og_image,
		twitter_card=excluded.twitter_card,
		twitter_title=excluded.twitter_title,
		twitter_description=excluded.twitter_description,
		tls_protocol=excluded.tls_protocol,
		server_header=excluded.server_header,
		x_robots_tag=excluded.x_robots_tag,
		http_canonical=excluded.http_canonical
	RETURNING id;
`

func (w *SQLiteBatchWriter) commitBatch(records []*CrawlRecord) error {
	if len(records) == 0 {
		return nil
	}

	ctx, cancel := context.WithTimeout(context.Background(), 45*time.Second)
	defer cancel()

	tx, err := w.db.BeginTx(ctx, nil)
	if err != nil {
		log.Printf("[SQLiteBatchWriter] BeginTx error: %v", err)
		return err
	}
	defer func() {
		_ = tx.Rollback()
	}()

	// Pre-compile all SQL statements ONCE per batch for maximum speed
	pageStmt, err := tx.PrepareContext(ctx, pageInsertQuery)
	if err != nil {
		log.Printf("[SQLiteBatchWriter] Prepare pageStmt error: %v", err)
		return err
	}
	defer pageStmt.Close()

	linkStmt, err := tx.PrepareContext(ctx, `
		INSERT INTO links (audit_id, source_page_id, source_url, target_url, anchor_text, is_internal, is_broken, rel_attributes, link_type, nofollow)
		VALUES (?, ?, ?, ?, ?, ?, 0, ?, ?, ?)
	`)
	if err == nil {
		defer linkStmt.Close()
	}

	imgStmt, err := tx.PrepareContext(ctx, `
		INSERT INTO images (audit_id, page_id, page_url, src, alt_text, width, height, format, is_lazy_loaded, has_dimensions, is_broken)
		VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0)
	`)
	if err == nil {
		defer imgStmt.Close()
	}

	headStmt, err := tx.PrepareContext(ctx, `
		INSERT INTO headings (page_id, tag, text, order_index)
		VALUES (?, ?, ?, ?)
	`)
	if err == nil {
		defer headStmt.Close()
	}

	sdStmt, err := tx.PrepareContext(ctx, `
		INSERT INTO structured_data (audit_id, page_id, page_url, format, schema_type, data_json, is_valid)
		VALUES (?, ?, ?, 'json-ld', ?, ?, 1)
	`)
	if err == nil {
		defer sdStmt.Close()
	}

	formStmt, err := tx.PrepareContext(ctx, `
		INSERT INTO forms (audit_id, page_id, page_url, action_url, method, form_id, has_password, is_search, is_insecure)
		VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
	`)
	if err == nil {
		defer formStmt.Close()
	}

	hreflangStmt, err := tx.PrepareContext(ctx, `
		INSERT INTO hreflang_tags (audit_id, page_id, source_url, target_url, lang_code, is_reciprocal, is_self, error_type)
		VALUES (?, ?, ?, ?, ?, 1, ?, NULL)
	`)
	if err == nil {
		defer hreflangStmt.Close()
	}

	paginationStmt, err := tx.PrepareContext(ctx, `
		INSERT INTO pagination_tags (audit_id, page_id, page_url, rel_type, target_url, source)
		VALUES (?, ?, ?, ?, ?, ?)
	`)
	if err == nil {
		defer paginationStmt.Close()
	}

	// Insert all records in the batch using the pre-compiled statements
	for _, rec := range records {
		pageID, err := w.executeInsertPage(ctx, tx, pageStmt, rec)
		if err != nil {
			continue
		}
		if pageID > 0 && rec.Parsed != nil {
			if linkStmt != nil {
				w.executeInsertLinks(ctx, linkStmt, rec, pageID)
			}
			if imgStmt != nil {
				w.executeInsertImages(ctx, imgStmt, rec, pageID)
			}
			if headStmt != nil {
				w.executeInsertHeadings(ctx, headStmt, rec, pageID)
			}
			if sdStmt != nil {
				w.executeInsertStructuredData(ctx, sdStmt, rec, pageID)
			}
			if formStmt != nil {
				w.executeInsertForms(ctx, formStmt, rec, pageID)
			}
			if hreflangStmt != nil {
				w.executeInsertHreflang(ctx, hreflangStmt, rec, pageID)
			}
			if paginationStmt != nil {
				w.executeInsertPagination(ctx, paginationStmt, rec, pageID)
			}
		}
	}

	if err := tx.Commit(); err != nil {
		log.Printf("[SQLiteBatchWriter] Commit error: %v", err)
		return err
	}

	return nil
}

func (w *SQLiteBatchWriter) executeInsertPage(ctx context.Context, tx *sql.Tx, stmt *sql.Stmt, rec *CrawlRecord) (int64, error) {
	p := rec.Parsed
	u := rec.FinalURL
	if u == "" {
		u = rec.URL
	}

	var title, metaDesc, metaKw, metaRobots, canonical, viewport, lang, h1 string
	var titleLen, metaDescLen, metaKwLen, h1Count, h1Len, h2Count, h2Len, wordCount, sentCount int
	var avgWords, textRatio float64
	var contentHash, simhash string
	var formCount, iframeCount int
	isIndexable := 1

	if rec.StatusCode >= 400 || rec.StatusCode == 0 {
		isIndexable = 0
	}

	var ogTitle, ogDesc, ogImg, ogType string
	var twCard, twTitle, twDesc, twImg string

	if p != nil {
		title = p.Title
		titleLen = p.TitleLength
		metaDesc = p.MetaDescription
		metaDescLen = p.MetaDescriptionLength
		metaKw = p.MetaKeywords
		metaKwLen = p.MetaKeywordsLength
		metaRobots = p.MetaRobots
		canonical = p.CanonicalURL
		viewport = p.Viewport
		lang = p.Language
		h1 = p.H1
		h1Count = p.H1Count
		h1Len = p.H1Length
		h2Count = p.H2Count
		h2Len = p.H2Length
		wordCount = p.WordCount
		sentCount = p.SentenceCount
		avgWords = p.AvgWordsPerSentence
		textRatio = p.TextRatio
		contentHash = p.ContentHash
		simhash = p.SimHash
		formCount = len(p.Forms)
		iframeCount = len(p.Iframes)

		if strings.Contains(strings.ToLower(metaRobots), "noindex") {
			isIndexable = 0
		}

		if p.OGTags != nil {
			ogTitle = p.OGTags["og:title"]
			ogDesc = p.OGTags["og:description"]
			ogImg = p.OGTags["og:image"]
			ogType = p.OGTags["og:type"]
		}
		if p.TwitterTags != nil {
			twCard = p.TwitterTags["twitter:card"]
			twTitle = p.TwitterTags["twitter:title"]
			twDesc = p.TwitterTags["twitter:description"]
			twImg = p.TwitterTags["twitter:image"]
		}
	}

	httpVer, tlsProto, serverHdr := "", "", ""
	var headersJSON, xRobotsTag, httpCanonical string
	if rec.Response != nil {
		httpVer = rec.Response.HTTPVersion
		tlsProto = rec.Response.TLSProtocol
		serverHdr = rec.Response.ServerHeader
		if rec.Response.Headers != nil {
			if hj, err := json.Marshal(rec.Response.Headers); err == nil {
				headersJSON = string(hj)
			}
			if v, ok := rec.Response.Headers["x-robots-tag"]; ok {
				xRobotsTag = v
				if strings.Contains(strings.ToLower(v), "noindex") {
					isIndexable = 0
				}
			}
			if v, ok := rec.Response.Headers["link"]; ok {
				lowV := strings.ToLower(v)
				if strings.Contains(lowV, "rel=\"canonical\"") || strings.Contains(lowV, "rel=canonical") {
					start := strings.Index(v, "<")
					end := strings.Index(v, ">")
					if start != -1 && end != -1 && end > start {
						rawCanon := strings.TrimSpace(v[start+1 : end])
						if resolved := frontier.NormalizeURL(rawCanon, u); resolved != "" {
							httpCanonical = resolved
						} else {
							httpCanonical = rawCanon
						}
					}
				}
			}
		}
	}

	folderDepth := 0
	prettyURL := u
	if pu, err := url.Parse(u); err == nil {
		parts := strings.Split(strings.Trim(pu.Path, "/"), "/")
		var cleanParts []string
		for _, part := range parts {
			if part != "" {
				cleanParts = append(cleanParts, part)
			}
		}
		folderDepth = len(cleanParts)
		prettyURL = fmt.Sprintf("%s://%s%s", pu.Scheme, pu.Host, pu.Path)
	}

	nowISO := time.Now().UTC().Format(time.RFC3339)

	var redirectURL sql.NullString
	if rec.FinalURL != "" && rec.FinalURL != rec.URL {
		redirectURL = sql.NullString{String: rec.FinalURL, Valid: true}
	}

	var redirectChainJSON sql.NullString
	if rec.Response != nil && len(rec.Response.RedirectChain) > 0 {
		if rcb, err := json.Marshal(rec.Response.RedirectChain); err == nil {
			redirectChainJSON = sql.NullString{String: string(rcb), Valid: true}
		}
	}

	var pageID int64
	err := stmt.QueryRowContext(ctx,
		rec.AuditID, rec.URL, rec.StatusCode, rec.ContentType, rec.ResponseTimeMs, rec.SizeBytes, wordCount,
		title, metaDesc, h1, canonical, viewport, isIndexable, rec.CrawlDepth,
		redirectURL, redirectChainJSON, contentHash, contentHash, contentHash,
		"html", rec.ContentType, rec.ParentURL, lang, metaRobots, titleLen,
		metaDescLen, metaKw, metaKwLen, h1Count, h1Len,
		h2Count, h2Len, sentCount, avgWords, textRatio,
		folderDepth, httpVer, rec.SizeBytes, rec.SizeBytes, rec.SizeBytes,
		headersJSON, simhash, nowISO, wordCount,
		title, h1, metaDesc, canonical, metaRobots,
		prettyURL, u, ogTitle, ogDesc, ogImg, ogType,
		twCard, twTitle, twDesc, twImg,
		tlsProto, serverHdr, formCount, iframeCount, nowISO,
		xRobotsTag, httpCanonical,
	).Scan(&pageID)

	if err != nil {
		_ = tx.QueryRowContext(ctx, "SELECT id FROM pages WHERE audit_id = ? AND url = ?", rec.AuditID, rec.URL).Scan(&pageID)
		if pageID > 0 {
			return pageID, nil
		}
		return 0, err
	}

	return pageID, nil
}

func (w *SQLiteBatchWriter) executeInsertLinks(ctx context.Context, stmt *sql.Stmt, rec *CrawlRecord, pageID int64) {
	if rec.Parsed == nil || len(rec.Parsed.Links) == 0 {
		return
	}
	for _, l := range rec.Parsed.Links {
		isInternal := 0
		if l.IsInternal {
			isInternal = 1
		}
		noFollow := 0
		if l.NoFollow {
			noFollow = 1
		}
		targetURL := l.HREF
		if resolved := frontier.NormalizeURL(l.HREF, rec.FinalURL); resolved != "" {
			targetURL = resolved
		}
		_, _ = stmt.ExecContext(ctx, rec.AuditID, pageID, rec.FinalURL, targetURL, l.Text, isInternal, l.Rel, l.Tag, noFollow)
	}
}

func (w *SQLiteBatchWriter) executeInsertImages(ctx context.Context, stmt *sql.Stmt, rec *CrawlRecord, pageID int64) {
	if rec.Parsed == nil || len(rec.Parsed.Images) == 0 {
		return
	}
	for _, img := range rec.Parsed.Images {
		lazy := 0
		if img.IsLazyLoaded {
			lazy = 1
		}
		hasDims := 0
		if img.Width > 0 && img.Height > 0 {
			hasDims = 1
		}
		srcURL := img.Src
		if resolved := frontier.NormalizeURL(img.Src, rec.FinalURL); resolved != "" {
			srcURL = resolved
		}
		_, _ = stmt.ExecContext(ctx, rec.AuditID, pageID, rec.FinalURL, srcURL, img.Alt, img.Width, img.Height, img.Format, lazy, hasDims)
	}
}

func (w *SQLiteBatchWriter) executeInsertHeadings(ctx context.Context, stmt *sql.Stmt, rec *CrawlRecord, pageID int64) {
	if rec.Parsed == nil || len(rec.Parsed.H1H6) == 0 {
		return
	}
	idx := 0
	for _, tag := range []string{"h1", "h2", "h3", "h4", "h5", "h6"} {
		if list, ok := rec.Parsed.H1H6[tag]; ok {
			for _, hText := range list {
				_, _ = stmt.ExecContext(ctx, pageID, tag, hText, idx)
				idx++
			}
		}
	}
}

func (w *SQLiteBatchWriter) executeInsertStructuredData(ctx context.Context, stmt *sql.Stmt, rec *CrawlRecord, pageID int64) {
	if rec.Parsed == nil || len(rec.Parsed.StructuredData) == 0 {
		return
	}
	for _, sd := range rec.Parsed.StructuredData {
		schemaType := "Unknown"
		var parsed map[string]any
		if err := json.Unmarshal([]byte(sd), &parsed); err == nil {
			if t, ok := parsed["@type"].(string); ok {
				schemaType = t
			}
		}
		_, _ = stmt.ExecContext(ctx, rec.AuditID, pageID, rec.FinalURL, schemaType, sd)
	}
}

func (w *SQLiteBatchWriter) executeInsertForms(ctx context.Context, stmt *sql.Stmt, rec *CrawlRecord, pageID int64) {
	if rec.Parsed == nil || len(rec.Parsed.Forms) == 0 {
		return
	}
	for _, f := range rec.Parsed.Forms {
		hasPw := 0
		if f.HasPassword {
			hasPw = 1
		}
		isSearch := 0
		if f.IsSearch {
			isSearch = 1
		}
		isInsec := 0
		if f.IsInsecure {
			isInsec = 1
		}
		_, _ = stmt.ExecContext(ctx, rec.AuditID, pageID, rec.FinalURL, f.Action, f.Method, f.ID, hasPw, isSearch, isInsec)
	}
}

func (w *SQLiteBatchWriter) executeInsertHreflang(ctx context.Context, stmt *sql.Stmt, rec *CrawlRecord, pageID int64) {
	if rec.Parsed == nil || len(rec.Parsed.HreflangTags) == 0 {
		return
	}
	for _, h := range rec.Parsed.HreflangTags {
		targetURL := h.TargetURL
		if resolved := frontier.NormalizeURL(h.TargetURL, rec.FinalURL); resolved != "" {
			targetURL = resolved
		}
		isSelf := 0
		if targetURL == rec.FinalURL {
			isSelf = 1
		}
		_, _ = stmt.ExecContext(ctx, rec.AuditID, pageID, rec.FinalURL, targetURL, h.LangCode, isSelf)
	}
}

func (w *SQLiteBatchWriter) executeInsertPagination(ctx context.Context, stmt *sql.Stmt, rec *CrawlRecord, pageID int64) {
	if rec.Parsed == nil || len(rec.Parsed.PaginationTags) == 0 {
		return
	}
	for _, p := range rec.Parsed.PaginationTags {
		targetURL := p.TargetURL
		if resolved := frontier.NormalizeURL(p.TargetURL, rec.FinalURL); resolved != "" {
			targetURL = resolved
		}
		src := p.Source
		if src == "" {
			src = "html"
		}
		_, _ = stmt.ExecContext(ctx, rec.AuditID, pageID, rec.FinalURL, p.RelType, targetURL, src)
	}
}

// WriteSitemapEntries persists discovered sitemap URLs to the sitemap_entries table
func (w *SQLiteBatchWriter) WriteSitemapEntries(entries []SitemapEntry) error {
	if w == nil || w.db == nil || len(entries) == 0 {
		return nil
	}
	ctx, cancel := context.WithTimeout(context.Background(), 20*time.Second)
	defer cancel()

	tx, err := w.db.BeginTx(ctx, nil)
	if err != nil {
		return err
	}
	defer func() {
		_ = tx.Rollback()
	}()

	stmt, err := tx.PrepareContext(ctx, `
		INSERT INTO sitemap_entries (audit_id, page_id, page_url, sitemap_url, lastmod, changefreq, priority)
		VALUES (?, NULL, ?, ?, ?, ?, ?)
	`)
	if err != nil {
		return err
	}
	defer stmt.Close()

	for _, e := range entries {
		var lastmod sql.NullString
		if e.LastMod != "" {
			lastmod = sql.NullString{String: e.LastMod, Valid: true}
		}
		var changefreq sql.NullString
		if e.ChangeFreq != "" {
			changefreq = sql.NullString{String: e.ChangeFreq, Valid: true}
		}
		var priority sql.NullFloat64
		if e.Priority > 0 {
			priority = sql.NullFloat64{Float64: e.Priority, Valid: true}
		}
		_, _ = stmt.ExecContext(ctx, e.AuditID, e.PageURL, e.SitemapURL, lastmod, changefreq, priority)
	}

	return tx.Commit()
}

// Close flushes buffered rows and shuts down the database connection
func (w *SQLiteBatchWriter) Close() error {
	if w == nil || w.db == nil {
		return nil
	}
	close(w.stopChan)
	w.wg.Wait()
	_ = w.Flush()
	return w.db.Close()
}
