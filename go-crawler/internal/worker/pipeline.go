package worker

import (
	"bytes"
	"context"
	"fmt"
	"go-crawler/internal/fetcher"
	"go-crawler/internal/frontier"
	"go-crawler/internal/parser"
	"go-crawler/internal/writer"
	"net/url"
	"strings"
	"time"
)

// Pipeline executes the single URL crawl cycle: Fetch -> Parse -> Discover Links -> Write
type Pipeline struct {
	Fetcher   fetcher.Fetcher
	Parser    *parser.StreamParser
	Filter    *fetcher.URLFilter
	Frontier  frontier.Frontier
	Writer    writer.Writer
	Streamer  *writer.GRPCStreamer
	AuditID   string
	CrawlMode string
}

// NewPipeline creates a new crawl pipeline
func NewPipeline(
	f fetcher.Fetcher,
	p *parser.StreamParser,
	filter *fetcher.URLFilter,
	front frontier.Frontier,
	w writer.Writer,
	streamer *writer.GRPCStreamer,
	auditID string,
) *Pipeline {
	return &Pipeline{
		Fetcher:  f,
		Parser:   p,
		Filter:   filter,
		Frontier: front,
		Writer:   w,
		Streamer: streamer,
		AuditID:  auditID,
	}
}

// ProcessURL processes a single queued URL
func (p *Pipeline) ProcessURL(ctx context.Context, item *frontier.QueueItem, pageID int64) (*writer.CrawlRecord, int, error) {
	// 1. Fetch page via uTLS client
	resp, err := p.Fetcher.Fetch(ctx, item.URL)
	if err != nil {
		_ = p.Frontier.MarkFailed(item.URL, err.Error())
		return nil, 0, fmt.Errorf("fetch error: %w", err)
	}

	record := &writer.CrawlRecord{
		AuditID:        p.AuditID,
		PageID:         pageID,
		URL:            item.URL,
		FinalURL:       resp.FinalURL,
		StatusCode:     resp.StatusCode,
		ContentType:    resp.ContentType,
		ResponseTimeMs: resp.ResponseTimeMs,
		SizeBytes:      resp.SizeBytes,
		CrawlDepth:     item.Depth,
		ParentURL:      item.ParentURL,
		CrawlTimestamp: time.Now(),
		Response:       resp,
	}

	var discoveredCount int
	isHTML := strings.Contains(strings.ToLower(resp.ContentType), "html") || len(resp.ContentType) == 0

	// 2. Parse HTML if valid content
	if isHTML && len(resp.Body) > 0 {
		parsed, err := p.Parser.Parse(bytes.NewReader(resp.Body), resp.FinalURL)
		if err == nil && parsed != nil {
			record.Parsed = parsed

			// 3. Discover and queue child links ONLY in spider mode (sitemap and list modes do not spider outlinks)
			if p.CrawlMode != "sitemap" && p.CrawlMode != "list" {
				var frontierBatch []frontier.QueueItem
				for _, link := range parsed.Links {
					if link.HREF == "" || strings.HasPrefix(link.HREF, "javascript:") || strings.HasPrefix(link.HREF, "mailto:") {
						continue
					}

					normLink := frontier.NormalizeURL(link.HREF, resp.FinalURL)
					if normLink == "" {
						continue
					}

					// Check filter and scope
					if p.Filter.ShouldCrawl(normLink, item.Depth+1) {
						frontierBatch = append(frontierBatch, frontier.QueueItem{
							URL:       normLink,
							Depth:     item.Depth + 1,
							ParentURL: resp.FinalURL,
							AddedAt:   time.Now(),
						})
					}
				}

				if len(frontierBatch) > 0 {
					added, err := p.Frontier.PushBatch(frontierBatch)
					if err == nil {
						discoveredCount = added
					}
				}
			}
		}
	}

	// 4. Ingest into PostgreSQL batch buffer (if writer configured)
	if p.Writer != nil {
		_ = p.Writer.WritePage(record)
	}

	// 5. Stream event to Python client
	if p.Streamer != nil {
		_ = p.Streamer.SendPageResult(record)
	}

	// 6. Mark completed in frontier
	_ = p.Frontier.MarkCompleted(item.URL)

	return record, discoveredCount, nil
}

// ExtractHost parses the hostname from a URL
func ExtractHost(rawURL string) string {
	u, err := url.Parse(rawURL)
	if err != nil {
		return ""
	}
	h := strings.ToLower(u.Hostname())
	return strings.TrimPrefix(h, "www.")
}
