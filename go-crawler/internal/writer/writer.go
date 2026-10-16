package writer

import (
	"go-crawler/internal/fetcher"
	"go-crawler/internal/parser"
	"time"
)

// CrawlRecord combines HTTP response and parsed HTML data for storage and streaming
type CrawlRecord struct {
	AuditID        string
	PageID         int64
	URL            string
	FinalURL       string
	StatusCode     int
	ContentType    string
	ResponseTimeMs float64
	SizeBytes      int64
	CrawlDepth     int
	ParentURL      string
	CrawlTimestamp time.Time
	Parsed         *parser.PageParseResult
	Response       *fetcher.FetchResponse
}

// SitemapEntry represents a URL extracted from an XML sitemap
type SitemapEntry struct {
	AuditID    string
	PageURL    string
	SitemapURL string
	LastMod    string
	ChangeFreq string
	Priority   float64
}

// Writer defines the persistence interface for crawled records
type Writer interface {
	WritePage(record *CrawlRecord) error
	WriteSitemapEntries(entries []SitemapEntry) error
	Flush() error
	Close() error
}
