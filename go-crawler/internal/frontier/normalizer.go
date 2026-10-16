package frontier

import (
	"crypto/md5"
	"encoding/binary"
	"encoding/hex"
	"net/url"
	"sort"
	"strconv"
	"strings"
)

var trackingParams = map[string]struct{}{
	"utm_source":   {},
	"utm_medium":   {},
	"utm_campaign": {},
	"utm_term":     {},
	"utm_content":  {},
	"fbclid":       {},
	"gclid":        {},
}

// NormalizeURL resolves a raw URL against a base URL, removes tracking parameters & fragments,
// normalizes trailing slashes and lowercases scheme & host, matching Python's _normalize_url.
func NormalizeURL(rawURL string, baseURL string) string {
	rawURL = strings.TrimSpace(rawURL)
	if rawURL == "" {
		return ""
	}

	base, err := url.Parse(strings.TrimSpace(baseURL))
	if err != nil {
		return ""
	}

	rel, err := url.Parse(rawURL)
	if err != nil {
		return ""
	}

	resolved := base.ResolveReference(rel)
	resolved.Fragment = ""

	scheme := strings.ToLower(resolved.Scheme)
	host := strings.ToLower(resolved.Host)
	if scheme == "" || host == "" {
		return ""
	}

	// Clean tracking query params
	origQuery := resolved.Query()
	cleanValues := url.Values{}
	for k, vs := range origQuery {
		if _, isTrack := trackingParams[strings.ToLower(k)]; !isTrack {
			cleanValues[k] = vs
		}
	}

	path := resolved.Path
	if path == "" {
		path = "/"
	} else if path != "/" && strings.HasSuffix(path, "/") {
		path = strings.TrimRight(path, "/")
	}

	var cleanQueryStr string
	if len(cleanValues) > 0 {
		// Sort keys for deterministic URL encoding
		keys := make([]string, 0, len(cleanValues))
		for k := range cleanValues {
			keys = append(keys, k)
		}
		sort.Strings(keys)

		var pairs []string
		for _, k := range keys {
			for _, v := range cleanValues[k] {
				pairs = append(pairs, url.QueryEscape(k)+"="+url.QueryEscape(v))
			}
		}
		cleanQueryStr = strings.Join(pairs, "&")
	}

	norm := scheme + "://" + host + path
	if cleanQueryStr != "" {
		norm += "?" + cleanQueryStr
	}

	return norm
}

// URLHash computes the 64-bit integer hash identical to Python's:
// int(hashlib.md5(url.encode('utf-8')).hexdigest()[:16], 16)
func URLHash(u string) uint64 {
	hasher := md5.New()
	hasher.Write([]byte(u))
	sum := hasher.Sum(nil)
	hexStr := hex.EncodeToString(sum)
	first16 := hexStr[:16]
	val, err := strconv.ParseUint(first16, 16, 64)
	if err != nil {
		return binary.BigEndian.Uint64(sum[:8])
	}
	return val
}

// URLHashBytes returns the 8-byte big-endian slice of the URLHash
func URLHashBytes(u string) []byte {
	h := URLHash(u)
	buf := make([]byte, 8)
	binary.BigEndian.PutUint64(buf, h)
	return buf
}
