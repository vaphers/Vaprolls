package worker

import (
	"context"
	"go-crawler/internal/config"
	"go-crawler/internal/fetcher"
	"go-crawler/internal/frontier"
	"go-crawler/internal/parser"
	"os"
	"testing"
	"time"
)

func TestWorkerPipeline(t *testing.T) {
	dataDir := t.TempDir()
	front, err := frontier.NewBadgerFrontier(dataDir, "test-worker", 1000)
	if err != nil {
		t.Fatalf("NewBadgerFrontier failed: %v", err)
	}
	defer front.Close()

	norm := frontier.NormalizeURL("https://example.com", "https://example.com")
	_, err = front.Push(frontier.QueueItem{URL: norm, Depth: 0, AddedAt: time.Now()})
	if err != nil {
		t.Fatalf("Push failed: %v", err)
	}

	httpFetcher := fetcher.NewUTLSHTTPFetcher("TestAgent/1.0", 15*time.Second)
	streamParser := parser.NewStreamParser()
	urlFilter := fetcher.NewURLFilter("example.com", nil, false, 5, nil, nil, nil, nil)

	pipe := NewPipeline(httpFetcher, streamParser, urlFilter, front, nil, nil, "test-worker")
	cfg := config.DefaultConfig()
	cfg.MaxPages = 1
	limiter := fetcher.NewPerDomainLimiter(2, 50*time.Millisecond)

	pool := NewWorkerPool(cfg, front, pipe, limiter, nil, nil, nil)
	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()

	err = pool.Start(ctx)
	if err != nil {
		t.Fatalf("pool.Start failed: %v", err)
	}

	if pool.pagesCrawled != 1 {
		t.Errorf("Expected 1 page crawled, got %d (errors: %d)", pool.pagesCrawled, pool.crawlErrors)
	}
	_ = os.RemoveAll(dataDir)
}

func TestSitemapModePipeline(t *testing.T) {
	dataDir := t.TempDir()
	front, err := frontier.NewBadgerFrontier(dataDir, "test-sitemap-worker", 1000)
	if err != nil {
		t.Fatalf("NewBadgerFrontier failed: %v", err)
	}
	defer front.Close()

	httpFetcher := fetcher.NewUTLSHTTPFetcher("TestAgent/1.0", 15*time.Second)
	streamParser := parser.NewStreamParser()
	urlFilter := fetcher.NewURLFilter("example.com", nil, false, 5, nil, nil, nil, nil)

	pipe := NewPipeline(httpFetcher, streamParser, urlFilter, front, nil, nil, "test-sitemap-worker")
	pipe.CrawlMode = "sitemap" // Sitemap mode strictly prevents pushing discovered child links

	// Process page with sitemap mode
	rec, discovered, err := pipe.ProcessURL(context.Background(), &frontier.QueueItem{
		URL:   "https://example.com",
		Depth: 0,
	}, 1)

	if err != nil {
		t.Fatalf("ProcessURL failed: %v", err)
	}
	if rec == nil {
		t.Fatalf("Expected non-nil CrawlRecord")
	}
	if discovered != 0 {
		t.Errorf("Expected 0 discovered child links in sitemap mode, got %d", discovered)
	}
	_ = os.RemoveAll(dataDir)
}
