package fetcher

import (
	"context"
	"testing"
	"time"
)

func TestUTLSFetch(t *testing.T) {
	fetcher := NewUTLSHTTPFetcher("Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124.0", 10*time.Second)
	resp, err := fetcher.Fetch(context.Background(), "https://example.com")
	if err != nil {
		t.Logf("uTLS fetch returned error: %v", err)
		// Try fallback
		resp, err = fetcher.FallbackFetch(context.Background(), "https://example.com")
		if err != nil {
			t.Fatalf("Fallback fetch also failed: %v", err)
		}
	}

	t.Logf("Fetch response status: %d, body len: %d, final URL: %s", resp.StatusCode, len(resp.Body), resp.FinalURL)
}
