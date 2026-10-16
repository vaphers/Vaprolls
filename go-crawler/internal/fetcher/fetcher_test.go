package fetcher

import (
	"context"
	"net/http"
	"net/http/httptest"
	"testing"
	"time"
)

func TestPerDomainLimiter(t *testing.T) {
	limiter := NewPerDomainLimiter(2, 50*time.Millisecond)
	ctx := context.Background()

	release1, err := limiter.Acquire(ctx, "example.com")
	if err != nil {
		t.Fatalf("Acquire 1 failed: %v", err)
	}

	release2, err := limiter.Acquire(ctx, "example.com")
	if err != nil {
		t.Fatalf("Acquire 2 failed: %v", err)
	}

	// Slot 3 should block until slot 1 or 2 is released
	doneChan := make(chan struct{})
	go func() {
		release3, err := limiter.Acquire(ctx, "example.com")
		if err == nil {
			release3()
		}
		close(doneChan)
	}()

	select {
	case <-doneChan:
		t.Errorf("Slot 3 should have blocked")
	case <-time.After(20 * time.Millisecond):
		// Expected
	}

	release1()
	release2()

	select {
	case <-doneChan:
		// Success, unblocked
	case <-time.After(200 * time.Millisecond):
		t.Errorf("Slot 3 timed out waiting to acquire")
	}
}

func TestURLFilter(t *testing.T) {
	filter := NewURLFilter(
		"example.com",
		[]string{"blog.example.com"},
		false,
		5,
		nil,
		nil,
		[]string{"https://example.com/blocked"},
		[]string{"https://example.com/allowed-special"},
	)

	if !filter.IsInternalURL("https://example.com/about") {
		t.Errorf("expected internal")
	}
	if filter.IsInternalURL("https://google.com/about") {
		t.Errorf("expected external")
	}
	if !filter.ShouldCrawl("https://example.com/about", 1) {
		t.Errorf("expected ShouldCrawl=true")
	}
	if filter.ShouldCrawl("https://example.com/blocked", 1) {
		t.Errorf("expected blocked URL to be rejected")
	}
	if !filter.ShouldCrawl("https://example.com/allowed-special", 1) {
		t.Errorf("expected allowed URL to pass")
	}
	if filter.ShouldCrawl("https://example.com/wp-admin/post.php", 1) {
		t.Errorf("expected admin path to be rejected")
	}
	if filter.ShouldCrawl("https://example.com/file.pdf", 1) {
		t.Errorf("expected pdf extension to be rejected")
	}
}

func TestRobotsManager(t *testing.T) {
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path == "/robots.txt" {
			w.WriteHeader(http.StatusOK)
			_, _ = w.Write([]byte("User-agent: *\nDisallow: /private/\nAllow: /private/public/\nCrawl-delay: 1\nSitemap: https://example.com/sitemap.xml\n"))
		} else {
			w.WriteHeader(http.StatusNotFound)
		}
	}))
	defer server.Close()

	mgr := NewRobotsManager(server.Client())
	data, err := mgr.FetchAndParse(server.URL)
	if err != nil {
		t.Fatalf("Robots fetch failed: %v", err)
	}

	if data.IsAllowed("Googlebot", "/private/secret") {
		t.Errorf("expected /private/secret to be disallowed")
	}
	if !data.IsAllowed("Googlebot", "/private/public/page") {
		t.Errorf("expected /private/public/page to be allowed")
	}
	if data.CrawlDelay != 1*time.Second {
		t.Errorf("expected crawl delay 1s, got %v", data.CrawlDelay)
	}
}
