package writer

import (
	"context"
	"crypto/md5"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"log"
	"strings"
	"sync"
	"time"

	"github.com/jackc/pgx/v5"
	"github.com/jackc/pgx/v5/pgxpool"
)

// PostgresBatchWriter writes CrawlRecords in high-speed batches using pgx.CopyFrom
type PostgresBatchWriter struct {
	pool      *pgxpool.Pool
	mu        sync.Mutex
	buffer    []*CrawlRecord
	batchSize int
	flushInt  time.Duration
	stopChan  chan struct{}
	wg        sync.WaitGroup
}

// NewPostgresBatchWriter connects to PostgreSQL and starts a background flush loop
func NewPostgresBatchWriter(ctx context.Context, dsn string, batchSize int, flushInterval time.Duration) (*PostgresBatchWriter, error) {
	if dsn == "" {
		return nil, nil // No postgres configured
	}

	if batchSize <= 0 {
		batchSize = 2000
	}
	if flushInterval <= 0 {
		flushInterval = 2 * time.Second
	}

	cfg, err := pgxpool.ParseConfig(dsn)
	if err != nil {
		return nil, fmt.Errorf("invalid postgres dsn: %w", err)
	}
	cfg.MaxConns = 25
	cfg.MinConns = 5

	pool, err := pgxpool.NewWithConfig(ctx, cfg)
	if err != nil {
		return nil, fmt.Errorf("failed to connect to postgres: %w", err)
	}

	w := &PostgresBatchWriter{
		pool:      pool,
		buffer:    make([]*CrawlRecord, 0, batchSize),
		batchSize: batchSize,
		flushInt:  flushInterval,
		stopChan:  make(chan struct{}),
	}

	w.wg.Add(1)
	go w.backgroundFlush()

	return w, nil
}

// Pool returns the underlying connection pool
func (w *PostgresBatchWriter) Pool() *pgxpool.Pool {
	if w == nil {
		return nil
	}
	return w.pool
}

// WritePage enqueues a record into the batch buffer
func (w *PostgresBatchWriter) WritePage(record *CrawlRecord) error {
	if w == nil {
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

func (w *PostgresBatchWriter) backgroundFlush() {
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

// Flush writes the buffered records to PostgreSQL via pgx.CopyFrom
func (w *PostgresBatchWriter) Flush() error {
	if w == nil {
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

	return w.copyBatch(records)
}

func (w *PostgresBatchWriter) copyBatch(records []*CrawlRecord) error {
	ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
	defer cancel()

	columns := []string{
		"crawl_timestamp", "audit_id", "page_id", "url", "url_hash", "final_url",
		"status_code", "content_type", "response_time_ms", "size_bytes", "word_count",
		"crawl_depth", "parent_url", "title", "title_length", "meta_description",
		"meta_description_length", "meta_keywords", "meta_robots", "canonical_url",
		"viewport", "language", "is_indexable", "h1", "h1_count", "h1_length",
		"h2", "h2_count", "h2_length", "sentence_count", "avg_words_per_sentence",
		"text_ratio", "content_hash", "simhash", "http_version", "tls_protocol",
		"server_header", "links", "images", "structured_data", "og_tags",
		"twitter_tags", "forms", "iframes",
	}

	rows := make([][]any, 0, len(records))

	for _, rec := range records {
		urlHashHex := md5Hex(rec.URL)
		var p = rec.Parsed

		title := ""
		titleLen := 0
		metaDesc := ""
		metaDescLen := 0
		metaKw := ""
		metaRobots := ""
		canonical := ""
		viewport := ""
		lang := ""
		isIndexable := 1
		h1 := ""
		h1Count := 0
		h1Len := 0
		h2 := ""
		h2Count := 0
		h2Len := 0
		words := 0
		sentences := 0
		avgWords := 0.0
		textRatio := 0.0
		contentHash := ""
		simhash := ""
		var linksJSON, imgsJSON, sdJSON, ogJSON, twJSON, formsJSON, iframesJSON []byte

		if p != nil {
			title = p.Title
			titleLen = p.TitleLength
			metaDesc = p.MetaDescription
			metaDescLen = p.MetaDescriptionLength
			metaKw = p.MetaKeywords
			metaRobots = p.MetaRobots
			canonical = p.CanonicalURL
			viewport = p.Viewport
			lang = p.Language
			h1 = p.H1
			h1Count = p.H1Count
			h1Len = p.H1Length
			h2 = p.H2
			h2Count = p.H2Count
			h2Len = p.H2Length
			words = p.WordCount
			sentences = p.SentenceCount
			avgWords = p.AvgWordsPerSentence
			textRatio = p.TextRatio
			contentHash = p.ContentHash
			simhash = p.SimHash

			linksJSON, _ = json.Marshal(p.Links)
			imgsJSON, _ = json.Marshal(p.Images)
			sdJSON, _ = json.Marshal(p.StructuredData)
			ogJSON, _ = json.Marshal(p.OGTags)
			twJSON, _ = json.Marshal(p.TwitterTags)
			formsJSON, _ = json.Marshal(p.Forms)
			iframesJSON, _ = json.Marshal(p.Iframes)
		}

		httpVer := ""
		tlsProto := ""
		serverHdr := ""
		if rec.Response != nil {
			httpVer = rec.Response.HTTPVersion
			tlsProto = rec.Response.TLSProtocol
			serverHdr = rec.Response.ServerHeader
		}

		ts := rec.CrawlTimestamp
		if ts.IsZero() {
			ts = time.Now()
		}

		rows = append(rows, []any{
			ts, rec.AuditID, rec.PageID, rec.URL, urlHashHex, rec.FinalURL,
			rec.StatusCode, rec.ContentType, rec.ResponseTimeMs, rec.SizeBytes, words,
			rec.CrawlDepth, rec.ParentURL, title, titleLen, metaDesc,
			metaDescLen, metaKw, metaRobots, canonical,
			viewport, lang, isIndexable, h1, h1Count, h1Len,
			h2, h2Count, h2Len, sentences, avgWords,
			textRatio, contentHash, simhash, httpVer, tlsProto,
			serverHdr, linksJSON, imgsJSON, sdJSON, ogJSON,
			twJSON, formsJSON, iframesJSON,
		})
	}

	_, err := w.pool.CopyFrom(ctx, pgx.Identifier{"pages"}, columns, pgx.CopyFromRows(rows))
	if err != nil {
		log.Printf("[PostgresBatchWriter] CopyFrom error: %v, attempting resilient fallback insert", err)
		return w.fallbackInsert(ctx, columns, rows)
	}

	return nil
}

func (w *PostgresBatchWriter) fallbackInsert(ctx context.Context, columns []string, rows [][]any) error {
	colStr := strings.Join(columns, ", ")
	placeholders := make([]string, len(columns))
	for i := range placeholders {
		placeholders[i] = fmt.Sprintf("$%d", i+1)
	}
	query := fmt.Sprintf("INSERT INTO pages (%s) VALUES (%s)", colStr, strings.Join(placeholders, ", "))

	batch := &pgx.Batch{}
	for _, row := range rows {
		batch.Queue(query, row...)
	}

	br := w.pool.SendBatch(ctx, batch)
	defer br.Close()

	for range rows {
		if _, err := br.Exec(); err != nil {
			// Collision or validation issue on a single row - log and proceed so entire batch isn't lost
			log.Printf("[PostgresBatchWriter] Fallback insert row warning: %v", err)
		}
	}
	return nil
}

func md5Hex(s string) string {
	h := md5.New()
	h.Write([]byte(s))
	return hex.EncodeToString(h.Sum(nil))
}

// WriteSitemapEntries writes discovered sitemap entries to PostgreSQL table sitemap_entries
func (w *PostgresBatchWriter) WriteSitemapEntries(entries []SitemapEntry) error {
	if w == nil || len(entries) == 0 {
		return nil
	}
	ctx, cancel := context.WithTimeout(context.Background(), 15*time.Second)
	defer cancel()

	columns := []string{"audit_id", "page_url", "sitemap_url", "lastmod", "changefreq", "priority"}
	rows := make([][]any, 0, len(entries))
	for _, e := range entries {
		var lm any = nil
		if e.LastMod != "" {
			lm = e.LastMod
		}
		rows = append(rows, []any{
			e.AuditID,
			e.PageURL,
			e.SitemapURL,
			lm,
			e.ChangeFreq,
			e.Priority,
		})
	}

	_, err := w.pool.CopyFrom(ctx, pgx.Identifier{"sitemap_entries"}, columns, pgx.CopyFromRows(rows))
	if err != nil {
		log.Printf("[PostgresBatchWriter] CopyFrom sitemap_entries notice: %v", err)
	}
	return err
}

// Close flushes buffered rows and shuts down pool
func (w *PostgresBatchWriter) Close() error {
	if w == nil {
		return nil
	}
	close(w.stopChan)
	w.wg.Wait()
	w.pool.Close()
	return nil
}
