package parser

import (
	"strings"
	"testing"
)

func TestStreamParser(t *testing.T) {
	htmlContent := `
<!DOCTYPE html>
<html lang="en">
<head>
    <title>Awesome Product Page - MyBrand</title>
    <meta name="description" content="Discover our awesome high performance products.">
    <meta name="keywords" content="seo, audit, crawler, fast">
    <meta name="robots" content="index, follow">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta property="og:title" content="Awesome Product">
    <meta property="og:image" content="https://example.com/cover.jpg">
    <link rel="canonical" href="https://example.com/product">
    <link rel="alternate" hreflang="es" href="https://example.com/es/product">
    <script type="application/ld+json">
    {"@context": "https://schema.org", "@type": "Product", "name": "Awesome"}
    </script>
</head>
<body>
    <h1>Main Heading for Awesome Product</h1>
    <h2>Features and Specs</h2>
    <h2>Customer Reviews</h2>
    <p>This is a paragraph explaining our incredible performance. Buy now!</p>
    <a href="/pricing" rel="nofollow">Pricing Plan</a>
    <a href="https://other.com/partner">External Partner</a>
    <img src="/images/hero.webp" alt="Hero banner" width="800" height="600" loading="lazy">
    <form action="/search" method="POST">
        <input type="search" name="q">
    </form>
</body>
</html>`

	parser := NewStreamParser()
	res, err := parser.Parse(strings.NewReader(htmlContent), "https://example.com/product")
	if err != nil {
		t.Fatalf("Parse failed: %v", err)
	}

	if res.Title != "Awesome Product Page - MyBrand" {
		t.Errorf("Unexpected title: %q", res.Title)
	}
	if res.MetaDescription != "Discover our awesome high performance products." {
		t.Errorf("Unexpected meta_description: %q", res.MetaDescription)
	}
	if res.CanonicalURL != "https://example.com/product" {
		t.Errorf("Unexpected canonical: %q", res.CanonicalURL)
	}
	if res.H1 != "Main Heading for Awesome Product" {
		t.Errorf("Unexpected H1: %q", res.H1)
	}
	if res.H2Count != 2 {
		t.Errorf("Expected 2 H2s, got %d", res.H2Count)
	}
	if len(res.Links) != 2 {
		t.Errorf("Expected 2 links, got %d", len(res.Links))
	}
	if len(res.Images) != 1 {
		t.Errorf("Expected 1 image, got %d", len(res.Images))
	}
	if res.WordCount == 0 {
		t.Errorf("Expected positive word count, got %d", res.WordCount)
	}
	if res.SimHash == "" || res.SimHash == "0000000000000000" {
		t.Errorf("SimHash was empty or 0: %s", res.SimHash)
	}
	if len(res.StructuredData) != 1 {
		t.Errorf("Expected 1 structured data JSON-LD, got %d", len(res.StructuredData))
	}
}
