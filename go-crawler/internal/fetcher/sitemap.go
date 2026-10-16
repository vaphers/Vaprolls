package fetcher

import (
	"compress/gzip"
	"context"
	"encoding/xml"
	"io"
	"net/http"
	"strings"
	"time"
)

// SitemapItem represents a single URL found in an XML sitemap
type SitemapItem struct {
	Loc        string  `xml:"loc"`
	LastMod    string  `xml:"lastmod"`
	ChangeFreq string  `xml:"changefreq"`
	Priority   float64 `xml:"priority"`
	SitemapURL string  `xml:"-"`
}

type xmlURLSet struct {
	XMLName xml.Name      `xml:"urlset"`
	URLs    []SitemapItem `xml:"url"`
}

type xmlSitemapIndex struct {
	XMLName  xml.Name `xml:"sitemapindex"`
	Sitemaps []struct {
		Loc string `xml:"loc"`
	} `xml:"sitemap"`
}

// SitemapParser fetches and parses XML sitemaps and sitemap indexes
type SitemapParser struct {
	client    *http.Client
	userAgent string
}

// NewSitemapParser creates a new XML sitemap parser
func NewSitemapParser(client *http.Client, userAgent string) *SitemapParser {
	if client == nil {
		client = &http.Client{Timeout: 20 * time.Second}
	}
	if userAgent == "" {
		userAgent = "Mozilla/5.0 (compatible; SEOAuditor/2.0)"
	}
	return &SitemapParser{
		client:    client,
		userAgent: userAgent,
	}
}

// FetchAndParse fetches a sitemap URL and returns all discovered page entries
func (p *SitemapParser) FetchAndParse(ctx context.Context, sitemapURL string, maxDepth int) ([]SitemapItem, error) {
	if maxDepth < 0 {
		return nil, nil
	}

	req, err := http.NewRequestWithContext(ctx, "GET", sitemapURL, nil)
	if err != nil {
		return nil, err
	}
	req.Header.Set("User-Agent", p.userAgent)
	req.Header.Set("Accept", "application/xml,text/xml,*/*;q=0.9")

	resp, err := p.client.Do(req)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()

	if resp.StatusCode < 200 || resp.StatusCode >= 400 {
		return nil, nil
	}

	var reader io.Reader = resp.Body
	if strings.HasSuffix(strings.ToLower(sitemapURL), ".gz") {
		gz, err := gzip.NewReader(resp.Body)
		if err == nil {
			defer gz.Close()
			reader = gz
		}
	}

	// Read up to 25MB of XML
	body, err := io.ReadAll(io.LimitReader(reader, 25*1024*1024))
	if err != nil && err != io.EOF {
		return nil, err
	}

	// 1. Try parsing as sitemap index
	var index xmlSitemapIndex
	if err := xml.Unmarshal(body, &index); err == nil && len(index.Sitemaps) > 0 {
		var allItems []SitemapItem
		// Recursively follow child sitemaps (up to first 10 to keep start phase fast)
		limit := len(index.Sitemaps)
		if limit > 10 {
			limit = 10
		}
		for i := 0; i < limit; i++ {
			subURL := strings.TrimSpace(index.Sitemaps[i].Loc)
			if subURL != "" && subURL != sitemapURL {
				items, _ := p.FetchAndParse(ctx, subURL, maxDepth-1)
				allItems = append(allItems, items...)
			}
		}
		return allItems, nil
	}

	// 2. Try parsing as standard urlset
	var urlSet xmlURLSet
	if err := xml.Unmarshal(body, &urlSet); err == nil {
		for i := range urlSet.URLs {
			urlSet.URLs[i].Loc = strings.TrimSpace(urlSet.URLs[i].Loc)
			urlSet.URLs[i].SitemapURL = sitemapURL
		}
		return urlSet.URLs, nil
	}

	return nil, nil
}

