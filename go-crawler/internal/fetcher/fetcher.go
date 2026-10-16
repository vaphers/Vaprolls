package fetcher

import (
	"context"
)

// FetchResponse contains the raw network response metadata and body
type FetchResponse struct {
	URL            string            `json:"url"`
	FinalURL       string            `json:"final_url"`
	StatusCode     int               `json:"status_code"`
	Headers        map[string]string `json:"headers"`
	Body           []byte            `json:"-"`
	ContentType    string            `json:"content_type"`
	ResponseTimeMs float64           `json:"response_time_ms"`
	RedirectChain  []string          `json:"redirect_chain"`
	HTTPVersion    string            `json:"http_version"`
	TLSProtocol    string            `json:"tls_protocol"`
	ServerHeader   string            `json:"server_header"`
	SizeBytes      int64             `json:"size_bytes"`
}

// Fetcher defines the interface for executing HTTP requests
type Fetcher interface {
	Fetch(ctx context.Context, rawURL string) (*FetchResponse, error)
}
