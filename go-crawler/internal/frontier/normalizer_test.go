package frontier

import (
	"testing"
)

func TestNormalizeURL(t *testing.T) {
	tests := []struct {
		raw      string
		base     string
		expected string
	}{
		{
			raw:      "/about/",
			base:     "https://EXAMPLE.com/page",
			expected: "https://example.com/about",
		},
		{
			raw:      "contact/?utm_source=google&utm_medium=cpc&ref=xyz#section",
			base:     "https://example.com/",
			expected: "https://example.com/contact?ref=xyz",
		},
		{
			raw:      "https://example.com/products/shoes/?fbclid=12345",
			base:     "https://example.com/",
			expected: "https://example.com/products/shoes",
		},
		{
			raw:      "https://example.com/",
			base:     "https://example.com/",
			expected: "https://example.com/",
		},
		{
			raw:      "/blog/post-1/",
			base:     "https://example.com",
			expected: "https://example.com/blog/post-1",
		},
		{
			raw:      "page.html?utm_source=google&id=42#reviews",
			base:     "https://example.com/section/",
			expected: "https://example.com/section/page.html?id=42",
		},
		{
			raw:      "https://EXAMPLE.COM/about/?fbclid=XYZ&ref=abc",
			base:     "https://example.com",
			expected: "https://example.com/about?ref=abc",
		},
		{
			raw:      "/products/item?gclid=123",
			base:     "https://example.com/catalog/",
			expected: "https://example.com/products/item",
		},
	}

	for _, tt := range tests {
		got := NormalizeURL(tt.raw, tt.base)
		if got != tt.expected {
			t.Errorf("NormalizeURL(%q, %q) = %q, want %q", tt.raw, tt.base, got, tt.expected)
		}
	}
}

func TestURLHash(t *testing.T) {
	u := "https://example.com/about"
	h := URLHash(u)
	if h == 0 {
		t.Errorf("URLHash(%q) returned 0", u)
	}
}
