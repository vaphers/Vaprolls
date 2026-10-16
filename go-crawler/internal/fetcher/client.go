package fetcher

import (
	"bytes"
	"compress/gzip"
	"compress/zlib"
	"context"
	"crypto/tls"
	"fmt"
	"io"
	"net"
	"net/http"
	"net/url"
	"strings"
	"time"

	"github.com/andybalholm/brotli"
	utls "github.com/refraction-networking/utls"
	"golang.org/x/net/http2"
)

type redirectTrackerKey struct{}

func contextWithRedirectTracker(ctx context.Context) (context.Context, *[]string) {
	tracker := make([]string, 0, 4)
	return context.WithValue(ctx, redirectTrackerKey{}, &tracker), &tracker
}

func recordRedirect(req *http.Request, via []*http.Request) error {
	if len(via) >= 10 {
		return fmt.Errorf("stopped after 10 redirects")
	}
	if ptr, ok := req.Context().Value(redirectTrackerKey{}).(*[]string); ok && ptr != nil {
		if len(*ptr) == 0 && len(via) > 0 {
			*ptr = append(*ptr, via[0].URL.String())
		}
		*ptr = append(*ptr, req.URL.String())
	}
	return nil
}

// UTLSHTTPFetcher implements Fetcher with Chrome 120 TLS fingerprint impersonation
type UTLSHTTPFetcher struct {
	client         *http.Client
	fallbackClient *http.Client
	userAgent      string
	timeout        time.Duration
}

// Client returns the underlying http.Client for reuse
func (f *UTLSHTTPFetcher) Client() *http.Client {
	return f.client
}

// NewUTLSHTTPFetcher creates a fetcher using uTLS Chrome fingerprint
func NewUTLSHTTPFetcher(userAgent string, timeout time.Duration) *UTLSHTTPFetcher {
	if timeout <= 0 {
		timeout = 20 * time.Second
	}
	if userAgent == "" {
		userAgent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
	}

	dialer := &net.Dialer{
		Timeout:   10 * time.Second,
		KeepAlive: 30 * time.Second,
	}

	transport := &http.Transport{
		Proxy:                 http.ProxyFromEnvironment,
		DialContext:           dialer.DialContext,
		MaxIdleConns:          2000,
		MaxIdleConnsPerHost:   500,
		IdleConnTimeout:       90 * time.Second,
		TLSHandshakeTimeout:   10 * time.Second,
		ExpectContinueTimeout: 1 * time.Second,
		DialTLSContext: func(ctx context.Context, network, addr string) (net.Conn, error) {
			rawConn, err := dialer.DialContext(ctx, network, addr)
			if err != nil {
				return nil, err
			}

			host, _, err := net.SplitHostPort(addr)
			if err != nil {
				host = addr
			}

			uConn := utls.UClient(rawConn, &utls.Config{
				ServerName:         host,
				InsecureSkipVerify: true,
				NextProtos:         []string{"h2", "http/1.1"},
			}, utls.HelloChrome_120)

			if err := uConn.HandshakeContext(ctx); err != nil {
				_ = rawConn.Close()
				return nil, err
			}

			return uConn, nil
		},
	}

	_ = http2.ConfigureTransport(transport)

	client := &http.Client{
		Transport:     transport,
		Timeout:       timeout,
		CheckRedirect: recordRedirect,
	}

	fallbackTransport := &http.Transport{
		Proxy:                 http.ProxyFromEnvironment,
		DialContext:           dialer.DialContext,
		MaxIdleConns:          2000,
		MaxIdleConnsPerHost:   500,
		IdleConnTimeout:       90 * time.Second,
		TLSHandshakeTimeout:   10 * time.Second,
		ExpectContinueTimeout: 1 * time.Second,
	}

	_ = http2.ConfigureTransport(fallbackTransport)

	fallbackClient := &http.Client{
		Transport:     fallbackTransport,
		Timeout:       timeout,
		CheckRedirect: recordRedirect,
	}

	return &UTLSHTTPFetcher{
		client:         client,
		fallbackClient: fallbackClient,
		userAgent:      userAgent,
		timeout:        timeout,
	}
}

// Fetch requests the given URL with realistic browser headers and uTLS fingerprint
func (f *UTLSHTTPFetcher) Fetch(ctx context.Context, targetURL string) (*FetchResponse, error) {
	resp, err := f.doUTLSFetch(ctx, targetURL)
	if err == nil {
		return resp, nil
	}

	// Fallback to standard HTTP fetch if custom uTLS has protocol error
	return f.FallbackFetch(ctx, targetURL)
}

func (f *UTLSHTTPFetcher) doUTLSFetch(ctx context.Context, targetURL string) (*FetchResponse, error) {
	reqCtx, tracker := contextWithRedirectTracker(ctx)
	req, err := http.NewRequestWithContext(reqCtx, "GET", targetURL, nil)
	if err != nil {
		return nil, err
	}

	parsedURL, _ := url.Parse(targetURL)
	host := ""
	if parsedURL != nil {
		host = parsedURL.Host
	}

	// Chrome-ordered request headers
	req.Header.Set("Host", host)
	req.Header.Set("User-Agent", f.userAgent)
	req.Header.Set("Accept", "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7")
	req.Header.Set("Accept-Language", "en-US,en;q=0.9")
	req.Header.Set("Accept-Encoding", "gzip, deflate, br")
	req.Header.Set("Sec-Ch-Ua", `"Chromium";v="124", "Google Chrome";v="124", "Not-A.Brand";v="99"`)
	req.Header.Set("Sec-Ch-Ua-Mobile", "?0")
	req.Header.Set("Sec-Ch-Ua-Platform", `"Windows"`)
	req.Header.Set("Sec-Fetch-Dest", "document")
	req.Header.Set("Sec-Fetch-Mode", "navigate")
	req.Header.Set("Sec-Fetch-Site", "none")
	req.Header.Set("Sec-Fetch-User", "?1")
	req.Header.Set("Upgrade-Insecure-Requests", "1")

	start := time.Now()
	resp, err := f.client.Do(req)
	elapsedMs := float64(time.Since(start).Microseconds()) / 1000.0

	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()

	// Decompress body
	var bodyReader io.Reader = resp.Body
	encoding := strings.ToLower(resp.Header.Get("Content-Encoding"))
	switch {
	case strings.Contains(encoding, "gzip"):
		if gz, err := gzip.NewReader(resp.Body); err == nil {
			defer gz.Close()
			bodyReader = gz
		}
	case strings.Contains(encoding, "br"):
		bodyReader = brotli.NewReader(resp.Body)
	case strings.Contains(encoding, "deflate"):
		if zr, err := zlib.NewReader(resp.Body); err == nil {
			defer zr.Close()
			bodyReader = zr
		}
	}

	bodyBytes, err := io.ReadAll(io.LimitReader(bodyReader, 10*1024*1024)) // 10MB limit
	if err != nil && !errorsIsEOF(err) {
		return nil, err
	}

	headersMap := make(map[string]string, len(resp.Header))
	for k, vs := range resp.Header {
		headersMap[strings.ToLower(k)] = strings.Join(vs, ", ")
	}

	finalURL := targetURL
	if resp.Request != nil && resp.Request.URL != nil {
		finalURL = resp.Request.URL.String()
	}

	var redirectChain []string
	if tracker != nil && len(*tracker) > 0 {
		redirectChain = *tracker
	} else if finalURL != targetURL {
		redirectChain = []string{targetURL, finalURL}
	}

	tlsProtocol := ""
	if resp.TLS != nil {
		switch resp.TLS.Version {
		case tls.VersionTLS13:
			tlsProtocol = "TLS 1.3"
		case tls.VersionTLS12:
			tlsProtocol = "TLS 1.2"
		default:
			tlsProtocol = fmt.Sprintf("TLS %x", resp.TLS.Version)
		}
	}

	return &FetchResponse{
		URL:            targetURL,
		FinalURL:       finalURL,
		StatusCode:     resp.StatusCode,
		Headers:        headersMap,
		Body:           bodyBytes,
		ContentType:    resp.Header.Get("Content-Type"),
		ResponseTimeMs: elapsedMs,
		RedirectChain:  redirectChain,
		HTTPVersion:    resp.Proto,
		TLSProtocol:    tlsProtocol,
		ServerHeader:   resp.Header.Get("Server"),
		SizeBytes:      int64(len(bodyBytes)),
	}, nil
}

func errorsIsEOF(err error) bool {
	return err == io.EOF || err == io.ErrUnexpectedEOF
}

// FallbackFetch attempts standard fetch without custom uTLS if uTLS handshake fails
func (f *UTLSHTTPFetcher) FallbackFetch(ctx context.Context, targetURL string) (*FetchResponse, error) {
	reqCtx, tracker := contextWithRedirectTracker(ctx)
	req, err := http.NewRequestWithContext(reqCtx, "GET", targetURL, nil)
	if err != nil {
		return nil, err
	}
	req.Header.Set("User-Agent", f.userAgent)

	start := time.Now()
	resp, err := f.fallbackClient.Do(req)
	elapsedMs := float64(time.Since(start).Microseconds()) / 1000.0
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()

	buf := new(bytes.Buffer)
	_, _ = io.Copy(buf, io.LimitReader(resp.Body, 10*1024*1024))

	headersMap := make(map[string]string)
	for k, vs := range resp.Header {
		headersMap[strings.ToLower(k)] = strings.Join(vs, ", ")
	}

	finalURL := targetURL
	if resp.Request != nil && resp.Request.URL != nil {
		finalURL = resp.Request.URL.String()
	}

	var redirectChain []string
	if tracker != nil && len(*tracker) > 0 {
		redirectChain = *tracker
	} else if finalURL != targetURL {
		redirectChain = []string{targetURL, finalURL}
	}

	return &FetchResponse{
		URL:            targetURL,
		FinalURL:       finalURL,
		StatusCode:     resp.StatusCode,
		Headers:        headersMap,
		Body:           buf.Bytes(),
		ContentType:    resp.Header.Get("Content-Type"),
		ResponseTimeMs: elapsedMs,
		RedirectChain:  redirectChain,
		HTTPVersion:    resp.Proto,
		ServerHeader:   resp.Header.Get("Server"),
		SizeBytes:      int64(buf.Len()),
	}, nil
}
