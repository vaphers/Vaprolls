package frontier

import (
	"time"
)

// QueueItem represents a URL queued to be crawled
type QueueItem struct {
	URL        string    `json:"url"`
	Depth      int       `json:"depth"`
	ParentURL  string    `json:"parent_url"`
	RetryCount int       `json:"retry_count"`
	AddedAt    time.Time `json:"added_at"`
}

// Frontier defines the interface for URL queueing, deduplication, and persistence
type Frontier interface {
	// Push queues a URL if it hasn't been visited before. Returns true if queued.
	Push(item QueueItem) (bool, error)

	// PushBatch queues multiple URLs. Returns count of newly queued URLs.
	PushBatch(items []QueueItem) (int, error)

	// Pop dequeues the next URL to crawl. Returns nil if queue is empty.
	Pop() (*QueueItem, error)

	// MarkCompleted records that a URL was successfully fetched and processed
	MarkCompleted(url string) error

	// MarkFailed records that a URL fetch failed
	MarkFailed(url string, reason string) error

	// Size returns current number of items waiting in queue
	Size() int64

	// VisitedCount returns number of unique URLs checked
	VisitedCount() uint64

	// Checkpoint flushes state (LSM memtables and Bloom filter) to disk
	Checkpoint() error

	// Close shuts down storage engine cleanly
	Close() error
}
