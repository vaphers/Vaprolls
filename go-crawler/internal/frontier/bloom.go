package frontier

import (
	"fmt"
	"os"
	"path/filepath"
	"sync"
	"sync/atomic"

	"github.com/bits-and-blooms/bloom/v3"
)

// BloomFilter wraps a thread-safe bloom.BloomFilter with disk persistence
type BloomFilter struct {
	mu     sync.RWMutex
	filter *bloom.BloomFilter
	count  atomic.Uint64
}

// NewBloomFilter creates a filter with expected capacity and target false positive rate
func NewBloomFilter(expectedElements uint, fpRate float64) *BloomFilter {
	if expectedElements == 0 {
		expectedElements = 10_000_000 // 10 million default
	}
	if fpRate <= 0 || fpRate >= 1 {
		fpRate = 0.001 // 0.1% false positive rate
	}
	return &BloomFilter{
		filter: bloom.NewWithEstimates(expectedElements, fpRate),
	}
}

// Add adds a URL to the bloom filter and returns true if it was newly added,
// or false if it was already present.
func (b *BloomFilter) Add(u string) bool {
	b.mu.Lock()
	defer b.mu.Unlock()

	data := URLHashBytes(u)
	if b.filter.Test(data) {
		return false
	}
	b.filter.Add(data)
	b.count.Add(1)
	return true
}

// Test checks if URL might be in the bloom filter
func (b *BloomFilter) Test(u string) bool {
	b.mu.RLock()
	defer b.mu.RUnlock()
	return b.filter.Test(URLHashBytes(u))
}

// Count returns the number of unique items added in this session (lock-free)
func (b *BloomFilter) Count() uint64 {
	return b.count.Load()
}

// SaveToFile serializes the Bloom filter to disk
func (b *BloomFilter) SaveToFile(filePath string) error {
	b.mu.RLock()
	defer b.mu.RUnlock()

	if err := os.MkdirAll(filepath.Dir(filePath), 0755); err != nil {
		return fmt.Errorf("failed to create bloom parent directory: %w", err)
	}

	tmpPath := filePath + ".tmp"
	f, err := os.Create(tmpPath)
	if err != nil {
		return fmt.Errorf("failed to create bloom temp file: %w", err)
	}

	if _, err := b.filter.WriteTo(f); err != nil {
		f.Close()
		os.Remove(tmpPath)
		return fmt.Errorf("failed to write bloom filter: %w", err)
	}

	if err := f.Sync(); err != nil {
		f.Close()
		os.Remove(tmpPath)
		return fmt.Errorf("failed to sync bloom filter: %w", err)
	}

	if err := f.Close(); err != nil {
		os.Remove(tmpPath)
		return fmt.Errorf("failed to close bloom temp file: %w", err)
	}

	return os.Rename(tmpPath, filePath)
}

// LoadFromFile restores a Bloom filter from disk
func (b *BloomFilter) LoadFromFile(filePath string) error {
	b.mu.Lock()
	defer b.mu.Unlock()

	f, err := os.Open(filePath)
	if err != nil {
		return fmt.Errorf("failed to open bloom file: %w", err)
	}
	defer f.Close()

	newFilter := bloom.New(100, 1)
	if _, err := newFilter.ReadFrom(f); err != nil {
		return fmt.Errorf("failed to read bloom filter: %w", err)
	}

	b.filter = newFilter
	return nil
}
