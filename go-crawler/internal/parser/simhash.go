package parser

import (
	"crypto/md5"
	"encoding/hex"
	"fmt"
	"regexp"
	"strconv"
	"strings"
)

var wordRegex = regexp.MustCompile(`\b[a-zA-Z]{3,}\b`)

// ComputeSimHash calculates a 64-bit SimHash fingerprint identical to Python's _compute_simhash
func ComputeSimHash(text string) uint64 {
	if strings.TrimSpace(text) == "" {
		return 0
	}

	words := wordRegex.FindAllString(strings.ToLower(text), -1)
	if len(words) == 0 {
		return 0
	}

	var v [64]int

	for _, word := range words {
		hasher := md5.New()
		hasher.Write([]byte(word))
		sum := hasher.Sum(nil)
		hexStr := hex.EncodeToString(sum)
		first16 := hexStr[:16]

		h, err := strconv.ParseUint(first16, 16, 64)
		if err != nil {
			continue
		}

		for i := 0; i < 64; i++ {
			bit := (h >> i) & 1
			if bit == 1 {
				v[i]++
			} else {
				v[i]--
			}
		}
	}

	var fingerprint uint64
	for i := 0; i < 64; i++ {
		if v[i] > 0 {
			fingerprint |= (uint64(1) << i)
		}
	}

	return fingerprint
}

// FormatSimHash formats the 64-bit hash as a 16-character lower-hex string
func FormatSimHash(hash uint64) string {
	return fmt.Sprintf("%016x", hash)
}
