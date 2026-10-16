package frontier

import (
	"fmt"
	"os"
	"testing"
	"time"
)

func TestBadgerFrontierBatchOperations(t *testing.T) {
	dataDir := t.TempDir()
	auditID := "test-audit-batch"

	front, err := NewBadgerFrontier(dataDir, auditID, 10000)
	if err != nil {
		t.Fatalf("Failed to create frontier: %v", err)
	}

	// 1. Test PushBatch
	var items []QueueItem
	for i := 0; i < 300; i++ {
		items = append(items, QueueItem{
			URL:     fmt.Sprintf("https://example.com/page/%d", i),
			Depth:   1,
			AddedAt: time.Now(),
		})
	}

	added, err := front.PushBatch(items)
	if err != nil {
		t.Fatalf("PushBatch failed: %v", err)
	}
	if added != 300 {
		t.Errorf("Expected 300 items added, got %d", added)
	}

	// 2. Test Bloom Filter Deduplication
	addedDup, err := front.PushBatch(items[:50])
	if err != nil {
		t.Fatalf("PushBatch dup failed: %v", err)
	}
	if addedDup != 0 {
		t.Errorf("Expected 0 duplicates added, got %d", addedDup)
	}

	// 3. Test Batch Pop
	var poppedCount int
	for {
		item, err := front.Pop()
		if err != nil {
			t.Fatalf("Pop error: %v", err)
		}
		if item == nil {
			break
		}
		poppedCount++
	}

	if poppedCount != 300 {
		t.Errorf("Expected 300 items popped, got %d", poppedCount)
	}

	// 4. Test Checkpoint and Close
	if err := front.Checkpoint(); err != nil {
		t.Fatalf("Checkpoint failed: %v", err)
	}
	if err := front.Close(); err != nil {
		t.Fatalf("Close failed: %v", err)
	}

	// 5. Test Reload from disk
	front2, err := NewBadgerFrontier(dataDir, auditID, 10000)
	if err != nil {
		t.Fatalf("Failed to reload frontier: %v", err)
	}
	defer front2.Close()

	// Should still remember all 300 URLs in Bloom filter
	ok, _ := front2.Push(QueueItem{URL: "https://example.com/page/0", Depth: 0, AddedAt: time.Now()})
	if ok {
		t.Errorf("Expected page/0 to be rejected as duplicate on reload")
	}

	_ = os.RemoveAll(dataDir)
}
