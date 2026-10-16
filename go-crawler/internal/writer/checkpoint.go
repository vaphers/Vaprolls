package writer

import (
	"context"
	"fmt"
	"log"
	"time"

	"github.com/jackc/pgx/v5/pgxpool"
)

// Checkpointer periodically commits BadgerDB state and Bloom filter to disk and PostgreSQL
type Checkpointer struct {
	pool      *pgxpool.Pool
	auditID   string
	bloomPath string
	badgerDir string
	interval  time.Duration
	stopChan  chan struct{}
}

// NewCheckpointer creates a checkpoint manager
func NewCheckpointer(pool *pgxpool.Pool, auditID, bloomPath, badgerDir string, interval time.Duration) *Checkpointer {
	if interval <= 0 {
		interval = 60 * time.Second
	}
	return &Checkpointer{
		pool:      pool,
		auditID:   auditID,
		bloomPath: bloomPath,
		badgerDir: badgerDir,
		interval:  interval,
		stopChan:  make(chan struct{}),
	}
}

// SaveCheckpoint updates crawl_checkpoints table in PostgreSQL
func (c *Checkpointer) SaveCheckpoint(ctx context.Context, crawled, queueSize, errors int64) error {
	if c.pool == nil {
		return nil
	}

	query := `
		INSERT INTO crawl_checkpoints (audit_id, pages_crawled, queue_size, errors_count, bloom_file_path, badger_dir_path, updated_at)
		VALUES ($1, $2, $3, $4, $5, $6, NOW())
		ON CONFLICT (audit_id) DO UPDATE SET
			pages_crawled = EXCLUDED.pages_crawled,
			queue_size = EXCLUDED.queue_size,
			errors_count = EXCLUDED.errors_count,
			updated_at = NOW()
	`

	_, err := c.pool.Exec(ctx, query, c.auditID, crawled, queueSize, errors, c.bloomPath, c.badgerDir)
	if err != nil {
		return fmt.Errorf("failed to save checkpoint to postgres: %w", err)
	}

	log.Printf("[Checkpointer] Checkpoint recorded for audit %s: %d crawled, %d queued", c.auditID, crawled, queueSize)
	return nil
}
