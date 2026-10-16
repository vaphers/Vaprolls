package fetcher

import (
	"bufio"
	"io"
	"net/http"
	"net/url"
	"strconv"
	"strings"
	"sync"
	"time"
)

// RobotsRule defines allow/disallow patterns
type RobotsRule struct {
	UserAgent string
	Disallow  []string
	Allow     []string
}

// RobotsData stores parsed rules for a domain
type RobotsData struct {
	Rules      []RobotsRule
	CrawlDelay time.Duration
	Sitemaps   []string
	FetchedAt  time.Time
}

// RobotsManager caches and evaluates robots.txt across domains
type RobotsManager struct {
	mu        sync.RWMutex
	cache     map[string]*RobotsData
	client    *http.Client
	UserAgent string
}

// NewRobotsManager creates a robots.txt manager
func NewRobotsManager(client *http.Client) *RobotsManager {
	if client == nil {
		client = &http.Client{Timeout: 10 * time.Second}
	}
	return &RobotsManager{
		cache:  make(map[string]*RobotsData),
		client: client,
	}
}

// FetchAndParse fetches and parses robots.txt for a host
func (m *RobotsManager) FetchAndParse(baseURL string) (*RobotsData, error) {
	u, err := url.Parse(baseURL)
	if err != nil {
		return nil, err
	}

	hostKey := strings.ToLower(u.Host)

	m.mu.RLock()
	if cached, ok := m.cache[hostKey]; ok {
		m.mu.RUnlock()
		return cached, nil
	}
	m.mu.RUnlock()

	robotsURL := u.Scheme + "://" + u.Host + "/robots.txt"
	req, err := http.NewRequest("GET", robotsURL, nil)
	if err != nil {
		return nil, err
	}
	ua := m.UserAgent
	if ua == "" {
		ua = "Mozilla/5.0 (compatible; SEOAuditor/2.0)"
	}
	req.Header.Set("User-Agent", ua)

	resp, err := m.client.Do(req)
	if err != nil || resp.StatusCode >= 400 {
		// If 404 or unreachable, allow all
		data := &RobotsData{FetchedAt: time.Now()}
		m.mu.Lock()
		m.cache[hostKey] = data
		m.mu.Unlock()
		if resp != nil && resp.Body != nil {
			_ = resp.Body.Close()
		}
		return data, nil
	}
	defer resp.Body.Close()

	data := parseRobotsTXT(resp.Body)
	data.FetchedAt = time.Now()

	m.mu.Lock()
	m.cache[hostKey] = data
	m.mu.Unlock()

	return data, nil
}

func parseRobotsTXT(r io.Reader) *RobotsData {
	scanner := bufio.NewScanner(r)
	data := &RobotsData{}

	var currentUA string
	currentRule := RobotsRule{UserAgent: "*"}

	for scanner.Scan() {
		line := strings.TrimSpace(scanner.Text())
		if line == "" || strings.HasPrefix(line, "#") {
			continue
		}

		parts := strings.SplitN(line, ":", 2)
		if len(parts) < 2 {
			continue
		}

		directive := strings.ToLower(strings.TrimSpace(parts[0]))
		value := strings.TrimSpace(parts[1])

		switch directive {
		case "user-agent":
			if currentUA != "" && (len(currentRule.Disallow) > 0 || len(currentRule.Allow) > 0) {
				data.Rules = append(data.Rules, currentRule)
			}
			currentUA = strings.ToLower(value)
			currentRule = RobotsRule{UserAgent: currentUA}

		case "disallow":
			if value != "" {
				currentRule.Disallow = append(currentRule.Disallow, value)
			}

		case "allow":
			if value != "" {
				currentRule.Allow = append(currentRule.Allow, value)
			}

		case "crawl-delay":
			if sec, err := strconv.ParseFloat(value, 64); err == nil && sec > 0 {
				data.CrawlDelay = time.Duration(sec * float64(time.Second))
			}

		case "sitemap":
			if value != "" {
				data.Sitemaps = append(data.Sitemaps, value)
			}
		}
	}

	if currentUA != "" && (len(currentRule.Disallow) > 0 || len(currentRule.Allow) > 0) {
		data.Rules = append(data.Rules, currentRule)
	}

	return data
}

// IsAllowed checks whether a path can be crawled by a given userAgent
func (d *RobotsData) IsAllowed(userAgent, path string) bool {
	if d == nil || len(d.Rules) == 0 {
		return true
	}

	uaLower := strings.ToLower(userAgent)
	var matchedRule *RobotsRule

	for i := range d.Rules {
		r := &d.Rules[i]
		if r.UserAgent != "*" && strings.Contains(uaLower, r.UserAgent) {
			matchedRule = r
			break
		}
	}

	if matchedRule == nil {
		for i := range d.Rules {
			if d.Rules[i].UserAgent == "*" {
				matchedRule = &d.Rules[i]
				break
			}
		}
	}

	if matchedRule == nil {
		return true
	}

	// Longest prefix match wins between Allow and Disallow
	longestMatch := 0
	allowed := true

	for _, p := range matchedRule.Disallow {
		if strings.HasPrefix(path, p) && len(p) > longestMatch {
			longestMatch = len(p)
			allowed = false
		}
	}

	for _, p := range matchedRule.Allow {
		if strings.HasPrefix(path, p) && len(p) >= longestMatch {
			longestMatch = len(p)
			allowed = true
		}
	}

	return allowed
}
