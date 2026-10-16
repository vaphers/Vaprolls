package worker

import (
	"context"
	"go-crawler/internal/config"
	"go-crawler/internal/fetcher"
	"go-crawler/internal/frontier"
	"go-crawler/internal/writer"
	"log"
	"net/url"
	"runtime"
	"sync"
	"sync/atomic"
	"time"
)

// WorkerPool coordinates goroutine workers, rate limiting, and crawl progress
type WorkerPool struct {
	cfg          config.CrawlConfig
	frontier     frontier.Frontier
	pipeline     *Pipeline
	limiter      *fetcher.PerDomainLimiter
	robots       *fetcher.RobotsManager
	streamer     *writer.GRPCStreamer
	checkpointer *writer.Checkpointer

	pagesCrawled   int64
	crawlErrors    int64
	totalElapsedMs int64
	activeWorkers  int32
	pageIDCounter  int64
	memoryPressure atomic.Bool

	stopChan chan struct{}
	stopOnce sync.Once
}

// NewWorkerPool creates a new crawler pool
func NewWorkerPool(
	cfg config.CrawlConfig,
	front frontier.Frontier,
	pipe *Pipeline,
	limiter *fetcher.PerDomainLimiter,
	robots *fetcher.RobotsManager,
	streamer *writer.GRPCStreamer,
	checkpointer *writer.Checkpointer,
) *WorkerPool {
	return &WorkerPool{
		cfg:          cfg,
		frontier:     front,
		pipeline:     pipe,
		limiter:      limiter,
		robots:       robots,
		streamer:     streamer,
		checkpointer: checkpointer,
		stopChan:     make(chan struct{}),
	}
}

// Start launches the crawl loop across configured goroutines
func (p *WorkerPool) Start(ctx context.Context) error {
	concurrency := p.cfg.Concurrency
	if concurrency <= 0 {
		concurrency = 15
	}

	var wg sync.WaitGroup
	ctx, cancel := context.WithCancel(ctx)
	defer cancel()

	// Progress ticker
	go p.progressHeartbeat(ctx)

	// Periodic checkpoint ticker
	go p.checkpointLoop(ctx)

	// Memory watchdog & backpressure
	go p.memoryWatchdog(ctx)

	// Launch worker goroutines
	for i := 0; i < concurrency; i++ {
		wg.Add(1)
		go func(workerID int) {
			defer wg.Done()
			p.runWorker(ctx, cancel)
		}(i)
	}

	wg.Wait()

	// Final progress update
	p.sendFinalProgress()

	return nil
}

func (p *WorkerPool) runWorker(ctx context.Context, cancel context.CancelFunc) {
	idleCycles := 0

	for {
		select {
		case <-ctx.Done():
			return
		case <-p.stopChan:
			return
		default:
		}

		// Pause briefly if memory backpressure is triggered
		if p.memoryPressure.Load() {
			time.Sleep(100 * time.Millisecond)
			continue
		}

		// Check max page limit
		if p.cfg.MaxPages > 0 && atomic.LoadInt64(&p.pagesCrawled) >= p.cfg.MaxPages {
			cancel()
			return
		}

		// Dequeue next URL
		item, err := p.frontier.Pop()
		if err != nil {
			time.Sleep(100 * time.Millisecond)
			continue
		}

		if item == nil {
			// Queue is currently empty, wait briefly
			idleCycles++
			if idleCycles > 40 && atomic.LoadInt32(&p.activeWorkers) == 0 {
				// Frontier is drained and no other worker is processing
				cancel()
				return
			}
			time.Sleep(50 * time.Millisecond)
			continue
		}

		idleCycles = 0
		atomic.AddInt32(&p.activeWorkers, 1)

		p.processItem(ctx, item)

		atomic.AddInt32(&p.activeWorkers, -1)
	}
}

func (p *WorkerPool) processItem(ctx context.Context, item *frontier.QueueItem) {
	host := ExtractHost(item.URL)

	// 1. Check robots.txt
	if p.robots != nil {
		rData, err := p.robots.FetchAndParse(item.URL)
		if err == nil && rData != nil {
			pathToCheck := "/"
			if u, err := url.Parse(item.URL); err == nil && u.Path != "" {
				pathToCheck = u.Path
			}
			if !rData.IsAllowed(p.cfg.UserAgent, pathToCheck) {
				_ = p.frontier.MarkCompleted(item.URL)
				return
			}
			if p.cfg.RespectRobotsCrawlDelay && rData.CrawlDelay > 0 {
				p.limiter.SetHostDelay(host, rData.CrawlDelay)
			}
		}
	}

	// 2. Acquire domain limiter slot
	release, err := p.limiter.Acquire(ctx, host)
	if err != nil {
		return // context cancelled
	}
	defer release()

	// 3. Process URL through pipeline
	pageID := atomic.AddInt64(&p.pageIDCounter, 1)
	rec, _, err := p.pipeline.ProcessURL(ctx, item, pageID)
	if err != nil {
		atomic.AddInt64(&p.crawlErrors, 1)
		return
	}

	atomic.AddInt64(&p.pagesCrawled, 1)
	if rec != nil {
		atomic.AddInt64(&p.totalElapsedMs, int64(rec.ResponseTimeMs))
	}
}

func (p *WorkerPool) progressHeartbeat(ctx context.Context) {
	ticker := time.NewTicker(500 * time.Millisecond)
	defer ticker.Stop()

	for {
		select {
		case <-ticker.C:
			p.sendProgress()
		case <-ctx.Done():
			return
		case <-p.stopChan:
			return
		}
	}
}

func (p *WorkerPool) sendProgress() {
	if p.streamer == nil {
		return
	}
	crawled := atomic.LoadInt64(&p.pagesCrawled)
	errors := atomic.LoadInt64(&p.crawlErrors)
	queueSize := p.frontier.Size()
	visited := p.frontier.VisitedCount()

	var avgMs float64
	if crawled > 0 {
		avgMs = float64(atomic.LoadInt64(&p.totalElapsedMs)) / float64(crawled)
	}

	_ = p.streamer.SendProgress(crawled, queueSize, p.cfg.MaxPages, errors, "", avgMs, visited)
}

func (p *WorkerPool) sendFinalProgress() {
	if p.streamer == nil {
		return
	}
	crawled := atomic.LoadInt64(&p.pagesCrawled)
	errors := atomic.LoadInt64(&p.crawlErrors)
	queueSize := p.frontier.Size()
	visited := p.frontier.VisitedCount()

	var avgMs float64
	if crawled > 0 {
		avgMs = float64(atomic.LoadInt64(&p.totalElapsedMs)) / float64(crawled)
	}

	_ = p.streamer.SendProgress(crawled, queueSize, p.cfg.MaxPages, errors, "Crawl complete", avgMs, visited)
	_ = p.streamer.SendCompleted("Crawl finished successfully")
}

func (p *WorkerPool) checkpointLoop(ctx context.Context) {
	ticker := time.NewTicker(60 * time.Second)
	defer ticker.Stop()

	for {
		select {
		case <-ticker.C:
			_ = p.frontier.Checkpoint()
			if p.checkpointer != nil {
				crawled := atomic.LoadInt64(&p.pagesCrawled)
				errors := atomic.LoadInt64(&p.crawlErrors)
				queueSize := p.frontier.Size()
				_ = p.checkpointer.SaveCheckpoint(ctx, crawled, queueSize, errors)
			}
			if p.streamer != nil {
				_ = p.streamer.SendCheckpoint("State checkpointed")
			}
		case <-ctx.Done():
			return
		case <-p.stopChan:
			return
		}
	}
}

// Stop signals all workers to stop immediately
func (p *WorkerPool) Stop() {
	p.stopOnce.Do(func() {
		close(p.stopChan)
		log.Printf("[WorkerPool] Stop signal received for audit %s", p.cfg.AuditID)
	})
}

func (p *WorkerPool) memoryWatchdog(ctx context.Context) {
	ticker := time.NewTicker(5 * time.Second)
	defer ticker.Stop()

	var m runtime.MemStats
	for {
		select {
		case <-ticker.C:
			runtime.ReadMemStats(&m)
			// Trigger backpressure if heap allocation exceeds 2GB
			if m.Alloc > 2*1024*1024*1024 {
				if !p.memoryPressure.Load() {
					log.Printf("[WorkerPool] Memory pressure high (%d MB allocated), throttling workers and running GC", m.Alloc/(1024*1024))
					p.memoryPressure.Store(true)
					runtime.GC()
				}
			} else if p.memoryPressure.Load() {
				log.Printf("[WorkerPool] Memory pressure relieved (%d MB allocated), resuming workers", m.Alloc/(1024*1024))
				p.memoryPressure.Store(false)
			}
		case <-ctx.Done():
			return
		case <-p.stopChan:
			return
		}
	}
}
