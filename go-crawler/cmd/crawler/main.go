package main

import (
	"context"
	"encoding/json"
	"flag"
	"fmt"
	"log"
	"net"
	"net/http"
	"net/url"
	"os"
	"os/signal"
	"path/filepath"
	"strings"
	"sync"
	"syscall"
	"time"

	"go-crawler/internal/config"
	"go-crawler/internal/fetcher"
	"go-crawler/internal/frontier"
	"go-crawler/internal/parser"
	"go-crawler/internal/worker"
	"go-crawler/internal/writer"
	pb "go-crawler/proto"

	"google.golang.org/grpc"
)

type server struct {
	pb.UnimplementedCrawlerServiceServer
	mu          sync.RWMutex
	activePools map[string]*worker.WorkerPool
	dataDir     string
}

func saveCrawlConfig(dataDir, auditID string, cfg config.CrawlConfig) error {
	dir := filepath.Join(dataDir, auditID)
	_ = os.MkdirAll(dir, 0755)
	data, err := json.MarshalIndent(cfg, "", "  ")
	if err != nil {
		return err
	}
	return os.WriteFile(filepath.Join(dir, "config.json"), data, 0644)
}

func loadCrawlConfig(dataDir, auditID string) (config.CrawlConfig, error) {
	var cfg config.CrawlConfig
	path := filepath.Join(dataDir, auditID, "config.json")
	data, err := os.ReadFile(path)
	if err != nil {
		return cfg, err
	}
	err = json.Unmarshal(data, &cfg)
	return cfg, err
}

func main() {
	port := flag.Int("port", 50051, "gRPC server listening port")
	dataDir := flag.String("data-dir", "./data/crawler", "Directory for BadgerDB and Bloom filters")
	flag.Parse()

	lis, err := net.Listen("tcp", fmt.Sprintf("0.0.0.0:%d", *port))
	if err != nil {
		log.Fatalf("Failed to listen on port %d: %v", *port, err)
	}

	grpcServer := grpc.NewServer(
		grpc.MaxRecvMsgSize(100*1024*1024),
		grpc.MaxSendMsgSize(100*1024*1024),
	)

	srv := &server{
		activePools: make(map[string]*worker.WorkerPool),
		dataDir:     *dataDir,
	}

	pb.RegisterCrawlerServiceServer(grpcServer, srv)

	// Graceful shutdown
	sigChan := make(chan os.Signal, 1)
	signal.Notify(sigChan, os.Interrupt, syscall.SIGTERM)
	go func() {
		<-sigChan
		log.Println("Shutting down Go Crawler Engine...")
		grpcServer.GracefulStop()
	}()

	log.Printf("🚀 Go High-Throughput Crawl Engine running on :%d", *port)
	if err := grpcServer.Serve(lis); err != nil {
		log.Fatalf("gRPC server error: %v", err)
	}
}

func (s *server) StartCrawl(req *pb.CrawlRequest, stream pb.CrawlerService_StartCrawlServer) error {
	auditID := req.AuditId
	if auditID == "" {
		return fmt.Errorf("audit_id is required")
	}

	s.mu.RLock()
	_, running := s.activePools[auditID]
	s.mu.RUnlock()
	if running {
		return fmt.Errorf("audit %s is already running", auditID)
	}

	log.Printf("Starting crawl for audit: %s, target: %s", auditID, req.StartUrl)

	cfg := config.DefaultConfig()
	cfg.AuditID = auditID
	cfg.StartURL = req.StartUrl
	if req.MaxPages > 0 {
		cfg.MaxPages = req.MaxPages
	}
	if req.Concurrency > 0 {
		cfg.Concurrency = int(req.Concurrency)
	}
	if req.MaxPerHost > 0 {
		cfg.MaxPerHost = int(req.MaxPerHost)
	}
	if req.HostDelayMs > 0 {
		cfg.HostDelay = time.Duration(req.HostDelayMs) * time.Millisecond
	}
	if req.UserAgent != "" {
		cfg.UserAgent = req.UserAgent
	}
	if req.CrawlMode != "" {
		cfg.CrawlMode = req.CrawlMode
	}
	cfg.URLsList = req.UrlsList
	cfg.IncludeRegex = req.IncludeRegex
	cfg.ExcludeRegex = req.ExcludeRegex
	if req.MaxCrawlDepth > 0 {
		cfg.MaxCrawlDepth = int(req.MaxCrawlDepth)
	} else if req.MaxCrawlDepth < 0 {
		cfg.MaxCrawlDepth = -1
	}
	cfg.CrawlSubdomains = req.CrawlSubdomains
	cfg.AllowedDomains = req.AllowedDomains
	cfg.BlockURLs = req.BlockUrls
	cfg.PostgresDSN = req.PostgresDsn
	if req.SqlitePath != "" {
		cfg.SQLitePath = req.SqlitePath
	}
	cfg.RespectRobotsCrawlDelay = req.RespectRobotsCrawlDelay
	cfg.DataDir = s.dataDir

	// Persist configuration for crash recovery and resume
	_ = saveCrawlConfig(cfg.DataDir, auditID, cfg)

	// Dynamic Bloom filter capacity: scale based on max_pages (minimum 10M)
	expectedURLs := uint(10_000_000)
	if cfg.MaxPages > 3_000_000 {
		expectedURLs = uint(cfg.MaxPages * 3)
	}

	// 1. Initialize Frontier
	front, err := frontier.NewBadgerFrontier(cfg.DataDir, auditID, expectedURLs)
	if err != nil {
		return fmt.Errorf("failed to init badger frontier: %w", err)
	}
	defer front.Close()

	// 2. Queue Seed URLs
	parsedStart, err := url.Parse(cfg.StartURL)
	if err != nil {
		return fmt.Errorf("invalid start url: %w", err)
	}
	baseDomain := stringsTrimPrefix(parsedStart.Hostname(), "www.")

	if cfg.CrawlMode == "list" && len(cfg.URLsList) > 0 {
		for _, u := range cfg.URLsList {
			norm := frontier.NormalizeURL(u, cfg.StartURL)
			if norm != "" {
				_, _ = front.Push(frontier.QueueItem{URL: norm, Depth: 0, AddedAt: time.Now()})
			}
		}
	} else if cfg.CrawlMode == "sitemap" {
		// In sitemap mode, seed URLs are populated strictly from discoverAndIngestSitemaps
	} else {
		normStart := frontier.NormalizeURL(cfg.StartURL, cfg.StartURL)
		if normStart != "" {
			_, _ = front.Push(frontier.QueueItem{URL: normStart, Depth: 0, AddedAt: time.Now()})
		}
	}

	// 3. Initialize Fetcher, Parser, Filter, RateLimiter, Robots (with uTLS)
	httpFetcher := fetcher.NewUTLSHTTPFetcher(cfg.UserAgent, 25*time.Second)
	streamParser := parser.NewStreamParser()
	urlFilter := fetcher.NewURLFilter(
		baseDomain,
		cfg.AllowedDomains,
		cfg.CrawlSubdomains,
		cfg.MaxCrawlDepth,
		cfg.IncludeRegex,
		cfg.ExcludeRegex,
		cfg.BlockURLs,
		nil,
	)
	limiter := fetcher.NewPerDomainLimiter(cfg.MaxPerHost, cfg.HostDelay)
	robotsMgr := fetcher.NewRobotsManager(httpFetcher.Client())
	robotsMgr.UserAgent = cfg.UserAgent
	streamer := writer.NewGRPCStreamer(stream)

	// 4. Initialize Database Writer: Postgres if configured, otherwise SQLite
	var dbWriter writer.Writer
	var checkpointer *writer.Checkpointer
	if cfg.PostgresDSN != "" {
		batchWriter, err := writer.NewPostgresBatchWriter(stream.Context(), cfg.PostgresDSN, 2000, 2*time.Second)
		if err != nil {
			log.Printf("Warning: Failed to connect to PostgreSQL: %v (continuing without pgx batching)", err)
		} else if batchWriter != nil {
			dbWriter = batchWriter
			defer batchWriter.Close()
			checkpointer = writer.NewCheckpointer(
				batchWriter.Pool(),
				auditID,
				filepath.Join(cfg.DataDir, auditID, "bloom.filter"),
				filepath.Join(cfg.DataDir, auditID, "badger"),
				60*time.Second,
			)
		}
	} else if cfg.SQLitePath != "" {
		sqliteWriter, err := writer.NewSQLiteBatchWriter(cfg.SQLitePath, auditID, 100, 1*time.Second)
		if err != nil {
			log.Printf("Warning: Failed to open SQLite writer (%s): %v", cfg.SQLitePath, err)
		} else if sqliteWriter != nil {
			dbWriter = sqliteWriter
			defer sqliteWriter.Close()
		}
	}

	// 5. Build Pipeline & WorkerPool
	pipe := worker.NewPipeline(httpFetcher, streamParser, urlFilter, front, dbWriter, streamer, auditID)
	pipe.CrawlMode = cfg.CrawlMode
	pool := worker.NewWorkerPool(cfg, front, pipe, limiter, robotsMgr, streamer, checkpointer)

	s.mu.Lock()
	s.activePools[auditID] = pool
	s.mu.Unlock()

	defer func() {
		s.mu.Lock()
		delete(s.activePools, auditID)
		s.mu.Unlock()
	}()

	// 6. Discover and Ingest XML Sitemaps into DB and Frontier
	discoverAndIngestSitemaps(stream.Context(), cfg, httpFetcher.Client(), robotsMgr, front, dbWriter)

	// 7. Run Crawl
	err = pool.Start(stream.Context())
	if err != nil {
		_ = streamer.SendError(err.Error())
		return err
	}

	// Final sync
	_ = front.Checkpoint()
	if dbWriter != nil {
		_ = dbWriter.Flush()
	}

	log.Printf("Crawl completed successfully for audit: %s", auditID)
	return nil
}

func (s *server) ResumeCrawl(req *pb.ResumeRequest, stream pb.CrawlerService_ResumeCrawlServer) error {
	auditID := req.AuditId
	if auditID == "" {
		return fmt.Errorf("audit_id is required")
	}

	log.Printf("Resuming crawl for audit: %s", auditID)

	s.mu.RLock()
	_, running := s.activePools[auditID]
	s.mu.RUnlock()
	if running {
		return fmt.Errorf("audit %s is already running", auditID)
	}

	cfg, err := loadCrawlConfig(s.dataDir, auditID)
	if err != nil {
		return fmt.Errorf("failed to load crawl configuration for %s: %w", auditID, err)
	}

	if req.PostgresDsn != "" {
		cfg.PostgresDSN = req.PostgresDsn
	}
	if req.SqlitePath != "" {
		cfg.SQLitePath = req.SqlitePath
	}

	expectedURLs := uint(10_000_000)
	if cfg.MaxPages > 3_000_000 {
		expectedURLs = uint(cfg.MaxPages * 3)
	}

	// 1. Re-open Badger Frontier (reloads Bloom filter and counts pending keys)
	front, err := frontier.NewBadgerFrontier(cfg.DataDir, auditID, expectedURLs)
	if err != nil {
		return fmt.Errorf("failed to open badger frontier for resume: %w", err)
	}
	defer front.Close()

	parsedStart, err := url.Parse(cfg.StartURL)
	if err != nil {
		return fmt.Errorf("invalid start url: %w", err)
	}
	baseDomain := stringsTrimPrefix(parsedStart.Hostname(), "www.")

	// 2. Initialize Fetcher, Parser, Filter, Limiter, Robots (with uTLS)
	httpFetcher := fetcher.NewUTLSHTTPFetcher(cfg.UserAgent, 25*time.Second)
	streamParser := parser.NewStreamParser()
	urlFilter := fetcher.NewURLFilter(
		baseDomain,
		cfg.AllowedDomains,
		cfg.CrawlSubdomains,
		cfg.MaxCrawlDepth,
		cfg.IncludeRegex,
		cfg.ExcludeRegex,
		cfg.BlockURLs,
		nil,
	)
	limiter := fetcher.NewPerDomainLimiter(cfg.MaxPerHost, cfg.HostDelay)
	robotsMgr := fetcher.NewRobotsManager(httpFetcher.Client())
	robotsMgr.UserAgent = cfg.UserAgent
	streamer := writer.NewResumeGRPCStreamer(stream)

	// 3. Database Writer: PostgreSQL or SQLite
	var dbWriter writer.Writer
	var checkpointer *writer.Checkpointer
	if cfg.PostgresDSN != "" {
		batchWriter, err := writer.NewPostgresBatchWriter(stream.Context(), cfg.PostgresDSN, 2000, 2*time.Second)
		if err != nil {
			log.Printf("Warning: Failed to connect to PostgreSQL on resume: %v", err)
		} else if batchWriter != nil {
			dbWriter = batchWriter
			defer batchWriter.Close()
			checkpointer = writer.NewCheckpointer(
				batchWriter.Pool(),
				auditID,
				filepath.Join(cfg.DataDir, auditID, "bloom.filter"),
				filepath.Join(cfg.DataDir, auditID, "badger"),
				60*time.Second,
			)
		}
	} else if cfg.SQLitePath != "" {
		sqliteWriter, err := writer.NewSQLiteBatchWriter(cfg.SQLitePath, auditID, 100, 1*time.Second)
		if err != nil {
			log.Printf("Warning: Failed to open SQLite writer on resume (%s): %v", cfg.SQLitePath, err)
		} else if sqliteWriter != nil {
			dbWriter = sqliteWriter
			defer sqliteWriter.Close()
		}
	}

	// 4. Build Pipeline & WorkerPool
	pipe := worker.NewPipeline(httpFetcher, streamParser, urlFilter, front, dbWriter, streamer, auditID)
	pool := worker.NewWorkerPool(cfg, front, pipe, limiter, robotsMgr, streamer, checkpointer)

	s.mu.Lock()
	s.activePools[auditID] = pool
	s.mu.Unlock()

	defer func() {
		s.mu.Lock()
		delete(s.activePools, auditID)
		s.mu.Unlock()
	}()

	log.Printf("Resuming execution with %d pending items in frontier for audit: %s", front.Size(), auditID)
	err = pool.Start(stream.Context())
	if err != nil {
		_ = streamer.SendError(err.Error())
		return err
	}

	_ = front.Checkpoint()
	if dbWriter != nil {
		_ = dbWriter.Flush()
	}

	log.Printf("Resumed crawl completed successfully for audit: %s", auditID)
	return nil
}

func (s *server) StopCrawl(ctx context.Context, req *pb.StopRequest) (*pb.StopResponse, error) {
	s.mu.RLock()
	pool, ok := s.activePools[req.AuditId]
	s.mu.RUnlock()

	if !ok {
		return &pb.StopResponse{
			Success: false,
			Message: "Audit not found or not active",
		}, nil
	}

	pool.Stop()
	return &pb.StopResponse{
		Success: true,
		Message: "Stop signal sent to crawl pool",
	}, nil
}

func (s *server) GetStatus(ctx context.Context, req *pb.StatusRequest) (*pb.CrawlStatus, error) {
	s.mu.RLock()
	_, ok := s.activePools[req.AuditId]
	s.mu.RUnlock()

	state := "completed"
	if ok {
		state = "running"
	}

	return &pb.CrawlStatus{
		AuditId: req.AuditId,
		State:   state,
	}, nil
}

func stringsTrimPrefix(s, prefix string) string {
	if len(s) >= len(prefix) && s[:len(prefix)] == prefix {
		return s[len(prefix):]
	}
	return s
}

func discoverAndIngestSitemaps(ctx context.Context, cfg config.CrawlConfig, client *http.Client, robotsMgr *fetcher.RobotsManager, front frontier.Frontier, dbWriter writer.Writer) {
	if cfg.CrawlMode == "list" {
		return
	}

	var sitemaps []string
	// If user provided 1 or more specific sitemaps of the site:
	if cfg.CrawlMode == "sitemap" && len(cfg.URLsList) > 0 {
		sitemaps = cfg.URLsList
	} else if strings.HasSuffix(strings.ToLower(cfg.StartURL), ".xml") {
		sitemaps = []string{cfg.StartURL}
	} else {
		// Auto-discover via robots.txt and /sitemap.xml
		rData, _ := robotsMgr.FetchAndParse(cfg.StartURL)
		if rData != nil && len(rData.Sitemaps) > 0 {
			sitemaps = rData.Sitemaps
		} else {
			parsed, err := url.Parse(cfg.StartURL)
			if err == nil {
				sitemaps = []string{fmt.Sprintf("%s://%s/sitemap.xml", parsed.Scheme, parsed.Host)}
			}
		}
	}

	parser := fetcher.NewSitemapParser(client, cfg.UserAgent)
	var allEntries []writer.SitemapEntry
	var queueItems []frontier.QueueItem

	for _, sm := range sitemaps {
		items, err := parser.FetchAndParse(ctx, sm, 1)
		if err != nil || len(items) == 0 {
			continue
		}
		for _, it := range items {
			norm := frontier.NormalizeURL(it.Loc, cfg.StartURL)
			if norm == "" {
				continue
			}
			allEntries = append(allEntries, writer.SitemapEntry{
				AuditID:    cfg.AuditID,
				PageURL:    norm,
				SitemapURL: it.SitemapURL,
				LastMod:    it.LastMod,
				ChangeFreq: it.ChangeFreq,
				Priority:   it.Priority,
			})
			queueItems = append(queueItems, frontier.QueueItem{
				URL:       norm,
				Depth:     1,
				ParentURL: it.SitemapURL,
				AddedAt:   time.Now(),
			})
		}
	}

	if len(allEntries) > 0 && dbWriter != nil {
		_ = dbWriter.WriteSitemapEntries(allEntries)
	}
	if len(queueItems) > 0 {
		_, _ = front.PushBatch(queueItems)
	} else if cfg.CrawlMode == "sitemap" {
		// Fallback: If sitemaps could not be found or fetched, push start URL so crawl runs
		normStart := frontier.NormalizeURL(cfg.StartURL, cfg.StartURL)
		if normStart != "" {
			_, _ = front.Push(frontier.QueueItem{URL: normStart, Depth: 0, AddedAt: time.Now()})
		}
	}
}
