package fetcher

import (
	"net/url"
	"path"
	"regexp"
	"strings"
)

var (
	serverAdminPrefixes = []string{
		"/wp-admin", "/wp-login", "/wp-includes", "/wp-content/plugins",
		"/xmlrpc.php", "/wp-cron.php", "/readme.html", "/license.txt",
		"/admin", "/administrator", "/cpanel", "/whm", "/phpmyadmin",
		"/webmail", "/server-status", "/server-info", "/cgi-bin",
		"/.git", "/.env", "/.htaccess", "/.user.ini", "/web.config",
	}

	cdnPatterns = []string{
		"/cdn-cgi/", "/cdn/", "/cdn-assets/", "/wp-content/uploads/cache/",
	}

	actionTraps = []string{
		"action=login", "action=logout", "action=register",
		"add-to-cart=", "wc-ajax=", "wp_service_worker=",
	}

	cdnSubdomains = []string{
		"cdn.", "assets.", "static.", "media.", "images.", "img.",
	}

	ignoredExtensions = map[string]struct{}{
		"pdf": {}, "zip": {}, "gz": {}, "tar": {}, "bz2": {}, "7z": {}, "rar": {}, "exe": {}, "dmg": {}, "iso": {}, "bin": {},
		"doc": {}, "docx": {}, "xls": {}, "xlsx": {}, "ppt": {}, "pptx": {}, "csv": {}, "txt": {}, "md": {}, "markdown": {},
		"jpg": {}, "jpeg": {}, "png": {}, "gif": {}, "svg": {}, "webp": {}, "avif": {}, "ico": {}, "bmp": {}, "tif": {}, "tiff": {},
		"mp4": {}, "mp3": {}, "wav": {}, "webm": {}, "ogg": {}, "avi": {}, "mov": {}, "wmv": {}, "m4v": {},
		"css": {}, "js": {}, "json": {}, "xml": {}, "map": {}, "woff": {}, "woff2": {}, "ttf": {}, "eot": {}, "otf": {},
		"yaml": {}, "yml": {}, "rss": {}, "atom": {},
	}
)

// URLFilter handles domain scope and spider trap filtering
type URLFilter struct {
	BaseDomain      string
	AllowedDomains  []string
	CrawlSubdomains bool
	MaxDepth        int
	IncludeRegex    []*regexp.Regexp
	ExcludeRegex    []*regexp.Regexp
	BlockURLs       map[string]struct{}
	AllowURLs       map[string]struct{}
}

// NewURLFilter creates a new URLFilter from domain settings
func NewURLFilter(baseDomain string, allowedDomains []string, crawlSubdomains bool, maxDepth int, includePatterns, excludePatterns []string, blockURLs, allowURLs []string) *URLFilter {
	d := strings.ToLower(baseDomain)
	d = strings.TrimPrefix(d, "www.")

	var inc []*regexp.Regexp
	for _, p := range includePatterns {
		if strings.TrimSpace(p) != "" {
			if r, err := regexp.Compile(p); err == nil {
				inc = append(inc, r)
			}
		}
	}

	var exc []*regexp.Regexp
	for _, p := range excludePatterns {
		if strings.TrimSpace(p) != "" {
			if r, err := regexp.Compile(p); err == nil {
				exc = append(exc, r)
			}
		}
	}

	bMap := make(map[string]struct{}, len(blockURLs))
	for _, u := range blockURLs {
		bMap[strings.TrimRight(u, "/")] = struct{}{}
	}

	aMap := make(map[string]struct{}, len(allowURLs))
	for _, u := range allowURLs {
		aMap[strings.TrimRight(u, "/")] = struct{}{}
	}

	return &URLFilter{
		BaseDomain:      d,
		AllowedDomains:  allowedDomains,
		CrawlSubdomains: crawlSubdomains,
		MaxDepth:        maxDepth,
		IncludeRegex:    inc,
		ExcludeRegex:    exc,
		BlockURLs:       bMap,
		AllowURLs:       aMap,
	}
}

// IsInternalURL checks whether the URL belongs to the target domain or allowed scopes
func (f *URLFilter) IsInternalURL(rawURL string) bool {
	parsed, err := url.Parse(rawURL)
	if err != nil {
		return false
	}

	host := strings.ToLower(parsed.Hostname())
	host = strings.TrimPrefix(host, "www.")

	if host == f.BaseDomain {
		return true
	}

	if f.CrawlSubdomains {
		if strings.HasSuffix(host, "."+f.BaseDomain) || strings.HasSuffix(f.BaseDomain, "."+host) {
			return true
		}
	}

	for _, allowed := range f.AllowedDomains {
		a := strings.ToLower(allowed)
		a = strings.TrimPrefix(a, "www.")
		if host == a || strings.HasSuffix(host, "."+a) {
			return true
		}
	}

	return false
}

// ShouldCrawl tests all filtering and anti-trap rules
func (f *URLFilter) ShouldCrawl(rawURL string, depth int) bool {
	trimmed := strings.TrimRight(rawURL, "/")

	// Explicit allow list bypasses filters
	if _, ok := f.AllowURLs[trimmed]; ok {
		return true
	}

	// Explicit block list
	if _, ok := f.BlockURLs[trimmed]; ok {
		return false
	}

	if !f.IsInternalURL(rawURL) {
		return false
	}

	if f.MaxDepth > 0 && depth > f.MaxDepth {
		return false
	}

	// Regex check
	if len(f.IncludeRegex) > 0 {
		matched := false
		for _, r := range f.IncludeRegex {
			if r.MatchString(rawURL) {
				matched = true
				break
			}
		}
		if !matched {
			return false
		}
	}

	for _, r := range f.ExcludeRegex {
		if r.MatchString(rawURL) {
			return false
		}
	}

	parsed, err := url.Parse(rawURL)
	if err != nil {
		return false
	}

	scheme := strings.ToLower(parsed.Scheme)
	if scheme == "mailto" || scheme == "tel" || scheme == "javascript" {
		return false
	}

	pathLower := strings.ToLower(parsed.Path)
	queryLower := strings.ToLower(parsed.RawQuery)
	hostLower := strings.ToLower(parsed.Hostname())

	// 1. Server admin prefixes
	for _, p := range serverAdminPrefixes {
		if strings.HasPrefix(pathLower, p) || strings.Contains(pathLower, p+"/") || strings.HasSuffix(pathLower, p) {
			return false
		}
	}

	// 2. CDN patterns
	for _, p := range cdnPatterns {
		if strings.Contains(pathLower, p) {
			return false
		}
	}

	// 3. Action / cart traps
	for _, trap := range actionTraps {
		if strings.Contains(queryLower, trap) {
			return false
		}
	}

	// 4. CDN subdomains
	for _, sub := range cdnSubdomains {
		if strings.HasPrefix(hostLower, sub) {
			return false
		}
	}

	// 5. Ignored extensions
	ext := strings.TrimPrefix(strings.ToLower(path.Ext(pathLower)), ".")
	if _, ok := ignoredExtensions[ext]; ok {
		return false
	}

	// 6. Repeating path segment traps
	var segments []string
	for _, s := range strings.Split(parsed.Path, "/") {
		if s != "" {
			segments = append(segments, s)
		}
	}
	if len(segments) > 10 {
		return false
	}
	segSet := make(map[string]struct{}, len(segments))
	for _, s := range segments {
		segSet[s] = struct{}{}
	}
	if len(segSet) < len(segments)-3 {
		return false
	}

	// 7. Too many query parameters
	if len(parsed.Query()) > 5 {
		return false
	}

	return true
}
