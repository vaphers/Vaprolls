package parser

import (
	"testing"
)

func TestComputeSimHash(t *testing.T) {
	text1 := "The quick brown fox jumps over the lazy dog"
	text2 := "The fast brown fox jumps over the lazy dog"
	text3 := "Complete different content about finance and stock markets and investment options"

	hash1 := ComputeSimHash(text1)
	hash2 := ComputeSimHash(text2)
	hash3 := ComputeSimHash(text3)

	if hash1 == 0 || hash2 == 0 || hash3 == 0 {
		t.Fatalf("SimHash returned 0 for non-empty text")
	}

	// Hamming distance between text1 and text2 should be small
	diff12 := 0
	for i := 0; i < 64; i++ {
		if ((hash1 >> i) & 1) != ((hash2 >> i) & 1) {
			diff12++
		}
	}

	// Hamming distance between text1 and text3 should be large
	diff13 := 0
	for i := 0; i < 64; i++ {
		if ((hash1 >> i) & 1) != ((hash3 >> i) & 1) {
			diff13++
		}
	}

	if diff12 >= diff13 {
		t.Errorf("Expected text1 and text2 to be closer (diff=%d) than text1 and text3 (diff=%d)", diff12, diff13)
	}

	formatted := FormatSimHash(hash1)
	if len(formatted) != 16 {
		t.Errorf("Expected 16-character hex string, got %s (len=%d)", formatted, len(formatted))
	}

	// Cross-language parity check with Python
	parityText := "The quick brown fox jumps over the lazy dog and explores search engine optimization techniques."
	gotHash := FormatSimHash(ComputeSimHash(parityText))
	wantHash := "2fd478f4cd0967de"
	if gotHash != wantHash {
		t.Errorf("SimHash cross-language mismatch! Got %s, want %s", gotHash, wantHash)
	}
}
