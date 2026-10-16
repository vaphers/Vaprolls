package frontier

import (
	"bytes"
	"encoding/binary"
	"encoding/json"
	"errors"
	"fmt"
	"os"
	"path/filepath"
	"sync"
	"sync/atomic"
	"time"

	"github.com/dgraph-io/badger/v4"
)

type statusUpdate struct {
	key []byte
	val byte
}

// BadgerFrontier implements Frontier backed by BadgerDB LSM store & Bloom filter
type BadgerFrontier struct {
	db         *badger.DB
	bloom      *BloomFilter
	bloomPath  string
	mu         sync.Mutex
	memQueue   chan QueueItem
	size       int64
	closed     bool
	stopGC     chan struct{}
	statusChan chan statusUpdate
	stopStatus chan struct{}
}

// NewBadgerFrontier opens or creates a Badger-backed frontier
func NewBadgerFrontier(dataDir string, auditID string, expectedURLs uint) (*BadgerFrontier, error) {
	badgerDir := filepath.Join(dataDir, auditID, "badger")
	bloomPath := filepath.Join(dataDir, auditID, "bloom.filter")

	if err := os.MkdirAll(badgerDir, 0755); err != nil {
		return nil, fmt.Errorf("failed to create badger directory: %w", err)
	}

	opts := badger.DefaultOptions(badgerDir).
		WithLoggingLevel(badger.ERROR).
		WithSyncWrites(false) // Batch write for high throughput

	db, err := badger.Open(opts)
	if err != nil {
		return nil, fmt.Errorf("failed to open badger db: %w", err)
	}

	bf := NewBloomFilter(expectedURLs, 0.001)
	if _, err := os.Stat(bloomPath); err == nil {
		_ = bf.LoadFromFile(bloomPath)
	}

	frontier := &BadgerFrontier{
		db:         db,
		bloom:      bf,
		bloomPath:  bloomPath,
		memQueue:   make(chan QueueItem, 100000), // 100K buffer for massive 100k+ crawls
		stopGC:     make(chan struct{}),
		statusChan: make(chan statusUpdate, 50000),
		stopStatus: make(chan struct{}),
	}

	// Calculate current pending size
	frontier.calculateInitialSize()

	// Start background value log GC & status flush loop
	go frontier.startGC()
	go frontier.statusFlushLoop()

	return frontier, nil
}

func (b *BadgerFrontier) statusFlushLoop() {
	ticker := time.NewTicker(200 * time.Millisecond)
	defer ticker.Stop()
	var buffer []statusUpdate

	flush := func() {
		if len(buffer) == 0 {
			return
		}
		wb := b.db.NewWriteBatch()
		defer wb.Cancel()
		for _, su := range buffer {
			_ = wb.Set(su.key, []byte{su.val})
		}
		_ = wb.Flush()
		buffer = buffer[:0]
	}

	for {
		select {
		case su := <-b.statusChan:
			buffer = append(buffer, su)
			if len(buffer) >= 1000 {
				flush()
			}
		case <-ticker.C:
			flush()
		case <-b.stopStatus:
			// Drain remaining
			for {
				select {
				case su := <-b.statusChan:
					buffer = append(buffer, su)
				default:
					flush()
					return
				}
			}
		}
	}
}

func (b *BadgerFrontier) startGC() {
	ticker := time.NewTicker(5 * time.Minute)
	defer ticker.Stop()
	for {
		select {
		case <-ticker.C:
			for {
				if err := b.db.RunValueLogGC(0.5); err != nil {
					break
				}
			}
		case <-b.stopGC:
			return
		}
	}
}

func (b *BadgerFrontier) calculateInitialSize() {
	var count int64
	_ = b.db.View(func(txn *badger.Txn) error {
		opts := badger.DefaultIteratorOptions
		opts.Prefix = []byte("q:")
		it := txn.NewIterator(opts)
		defer it.Close()
		for it.Rewind(); it.Valid(); it.Next() {
			count++
		}
		return nil
	})
	atomic.StoreInt64(&b.size, count)
}

func makeQueueKey(depth int, u string) []byte {
	// "q:" + 4-byte depth + 8-byte URL hash
	key := make([]byte, 2+4+8)
	copy(key[0:2], "q:")
	binary.BigEndian.PutUint32(key[2:6], uint32(depth))
	binary.BigEndian.PutUint64(key[6:14], URLHash(u))
	return key
}

func makeStatusKey(u string) []byte {
	key := make([]byte, 2+8)
	copy(key[0:2], "s:")
	binary.BigEndian.PutUint64(key[2:10], URLHash(u))
	return key
}

// Push queues a single URL if it hasn't been queued before
func (b *BadgerFrontier) Push(item QueueItem) (bool, error) {
	if !b.bloom.Add(item.URL) {
		return false, nil // Already seen in Bloom filter
	}

	sKey := makeStatusKey(item.URL)
	select {
	case b.memQueue <- item:
		// Fits in memory queue directly; persist status marker asynchronously or in small txn
		_ = b.db.Update(func(txn *badger.Txn) error {
			return txn.Set(sKey, []byte("p"))
		})
	default:
		payload, err := json.Marshal(item)
		if err != nil {
			return false, err
		}
		qKey := makeQueueKey(item.Depth, item.URL)
		err = b.db.Update(func(txn *badger.Txn) error {
			if err := txn.Set(qKey, payload); err != nil {
				return err
			}
			return txn.Set(sKey, []byte("p"))
		})
		if err != nil {
			return false, err
		}
	}

	atomic.AddInt64(&b.size, 1)
	return true, nil
}

// PushBatch queues multiple items efficiently using Badger's WriteBatch
func (b *BadgerFrontier) PushBatch(items []QueueItem) (int, error) {
	var toAdd []QueueItem
	for _, item := range items {
		if b.bloom.Add(item.URL) {
			toAdd = append(toAdd, item)
		}
	}

	if len(toAdd) == 0 {
		return 0, nil
	}

	wb := b.db.NewWriteBatch()
	defer wb.Cancel()

	for _, item := range toAdd {
		sKey := makeStatusKey(item.URL)
		_ = wb.Set(sKey, []byte("p"))

		select {
		case b.memQueue <- item:
			// Directly in memory queue, no need to write qKey or delete later!
		default:
			// Memory queue full; spill to Badger disk queue
			payload, err := json.Marshal(item)
			if err == nil {
				qKey := makeQueueKey(item.Depth, item.URL)
				_ = wb.Set(qKey, payload)
			}
		}
	}

	if err := wb.Flush(); err != nil {
		return 0, err
	}

	atomic.AddInt64(&b.size, int64(len(toAdd)))
	return len(toAdd), nil
}

// Pop retrieves the next URL to crawl with high-throughput batch refills
func (b *BadgerFrontier) Pop() (*QueueItem, error) {
	// Fast path: pop from in-memory queue without any Badger transaction
	select {
	case item := <-b.memQueue:
		atomic.AddInt64(&b.size, -1)
		return &item, nil
	default:
	}

	// Slow path: refill memory queue from BadgerDB in a single batch transaction
	b.mu.Lock()
	defer b.mu.Unlock()

	// Double-check memory channel under lock
	select {
	case item := <-b.memQueue:
		atomic.AddInt64(&b.size, -1)
		return &item, nil
	default:
	}

	var fetched []QueueItem
	err := b.db.Update(func(txn *badger.Txn) error {
		opts := badger.DefaultIteratorOptions
		opts.Prefix = []byte("q:")
		opts.PrefetchValues = true
		it := txn.NewIterator(opts)
		defer it.Close()

		var keysToDelete [][]byte
		for it.Rewind(); it.Valid() && len(fetched) < 5000; it.Next() {
			item := it.Item()
			keysToDelete = append(keysToDelete, bytes.Clone(item.Key()))

			err := item.Value(func(val []byte) error {
				var qi QueueItem
				if err := json.Unmarshal(val, &qi); err != nil {
					return err
				}
				fetched = append(fetched, qi)
				return nil
			})
			if err != nil {
				return err
			}
		}

		for _, k := range keysToDelete {
			if err := txn.Delete(k); err != nil {
				return err
			}
		}
		return nil
	})

	if err != nil {
		return nil, err
	}

	if len(fetched) == 0 {
		return nil, nil // Queue is drained
	}

	res := fetched[0]
	atomic.AddInt64(&b.size, -1)

	var overflow []QueueItem
	for i := 1; i < len(fetched); i++ {
		select {
		case b.memQueue <- fetched[i]:
		default:
			overflow = append(overflow, fetched[i])
		}
	}

	if len(overflow) > 0 {
		wb := b.db.NewWriteBatch()
		defer wb.Cancel()
		for _, item := range overflow {
			if payload, err := json.Marshal(item); err == nil {
				_ = wb.Set(makeQueueKey(item.Depth, item.URL), payload)
			}
		}
		_ = wb.Flush()
	}

	return &res, nil
}

// MarkCompleted marks a URL as successfully crawled via non-blocking batch channel
func (b *BadgerFrontier) MarkCompleted(u string) error {
	sKey := makeStatusKey(u)
	select {
	case b.statusChan <- statusUpdate{key: sKey, val: 'c'}:
		return nil
	default:
		return b.db.Update(func(txn *badger.Txn) error {
			return txn.Set(sKey, []byte("c"))
		})
	}
}

// MarkFailed marks a URL as failed via non-blocking batch channel
func (b *BadgerFrontier) MarkFailed(u string, reason string) error {
	sKey := makeStatusKey(u)
	select {
	case b.statusChan <- statusUpdate{key: sKey, val: 'f'}:
		return nil
	default:
		return b.db.Update(func(txn *badger.Txn) error {
			return txn.Set(sKey, []byte("f"))
		})
	}
}

// Size returns total pending URLs
func (b *BadgerFrontier) Size() int64 {
	s := atomic.LoadInt64(&b.size)
	if s < 0 {
		return 0
	}
	return s
}

// VisitedCount returns number of seen URLs
func (b *BadgerFrontier) VisitedCount() uint64 {
	return b.bloom.Count()
}

// Checkpoint persists LSM memtables and Bloom filter to disk
func (b *BadgerFrontier) Checkpoint() error {
	b.mu.Lock()
	defer b.mu.Unlock()

	if b.closed {
		return errors.New("frontier is closed")
	}

	if err := b.db.Sync(); err != nil {
		return fmt.Errorf("failed to sync badger: %w", err)
	}

	if err := b.bloom.SaveToFile(b.bloomPath); err != nil {
		return fmt.Errorf("failed to save bloom filter: %w", err)
	}

	return nil
}

// Close flushes data and closes the database
func (b *BadgerFrontier) Close() error {
	b.mu.Lock()
	defer b.mu.Unlock()

	if b.closed {
		return nil
	}
	b.closed = true

	close(b.stopGC)
	close(b.stopStatus)
	_ = b.bloom.SaveToFile(b.bloomPath)
	return b.db.Close()
}
