package writer

import (
	"context"
	pb "go-crawler/proto"
	"runtime"
	"sync"
	"time"
)

// GRPCStreamer manages streaming events to a connected gRPC client
type GRPCStreamer struct {
	stream    pb.CrawlerService_StartCrawlServer
	resStream pb.CrawlerService_ResumeCrawlServer
	mu        sync.Mutex
	startTime time.Time
}

// NewGRPCStreamer wraps a gRPC stream server
func NewGRPCStreamer(stream pb.CrawlerService_StartCrawlServer) *GRPCStreamer {
	return &GRPCStreamer{
		stream:    stream,
		startTime: time.Now(),
	}
}

// NewResumeGRPCStreamer wraps a ResumeCrawl gRPC stream server
func NewResumeGRPCStreamer(stream pb.CrawlerService_ResumeCrawlServer) *GRPCStreamer {
	return &GRPCStreamer{
		resStream: stream,
		startTime: time.Now(),
	}
}

// SendPageResult emits a page_result event with PageSummary
func (s *GRPCStreamer) SendPageResult(rec *CrawlRecord) error {
	s.mu.Lock()
	defer s.mu.Unlock()

	summary := &pb.PageSummary{
		Url:            rec.URL,
		FinalUrl:       rec.FinalURL,
		StatusCode:     int32(rec.StatusCode),
		ContentType:    rec.ContentType,
		ResponseTimeMs: rec.ResponseTimeMs,
		SizeBytes:      rec.SizeBytes,
		CrawlDepth:     int32(rec.CrawlDepth),
		Indexability:   "indexable",
	}

	if rec.StatusCode >= 400 || rec.StatusCode == 0 {
		summary.Indexability = "error"
	}

	if p := rec.Parsed; p != nil {
		summary.Title = p.Title
		summary.MetaDescription = p.MetaDescription
		summary.H1 = p.H1
		summary.CanonicalUrl = p.CanonicalURL
		summary.WordCount = int32(p.WordCount)
		summary.ImagesCount = int32(len(p.Images))

		var intLinks, extLinks int
		for _, l := range p.Links {
			if l.IsInternal {
				intLinks++
			} else {
				extLinks++
			}
		}
		summary.InternalLinksCount = int32(intLinks)
		summary.ExternalLinksCount = int32(extLinks)
	}

	event := &pb.CrawlEvent{
		Type: "page_result",
		Page: summary,
	}

	if s.stream != nil {
		return s.stream.Send(event)
	} else if s.resStream != nil {
		return s.resStream.Send(event)
	}
	return nil
}

// SendProgress emits a progress heartbeat
func (s *GRPCStreamer) SendProgress(crawled, queueSize, maxPages, errors int64, currentURL string, avgResponseMs float64, visitedCount uint64) error {
	s.mu.Lock()
	defer s.mu.Unlock()

	elapsedSec := time.Since(s.startTime).Seconds()
	var pagesPerSec float64
	if elapsedSec > 0 {
		pagesPerSec = float64(crawled) / elapsedSec
	}

	var m runtime.MemStats
	runtime.ReadMemStats(&m)
	memMB := int64(m.Alloc / 1024 / 1024)

	prog := &pb.CrawlProgress{
		PagesCrawled:  crawled,
		QueueSize:     queueSize,
		MaxPages:      maxPages,
		PagesPerSec:   pagesPerSec,
		CurrentUrl:    currentURL,
		Errors:        errors,
		AvgResponseMs: avgResponseMs,
		MemoryMb:      memMB,
		VisitedCount:  int64(visitedCount),
	}

	event := &pb.CrawlEvent{
		Type:     "progress",
		Progress: prog,
	}

	if s.stream != nil {
		return s.stream.Send(event)
	} else if s.resStream != nil {
		return s.resStream.Send(event)
	}
	return nil
}

// SendCompleted emits a completed event
func (s *GRPCStreamer) SendCompleted(message string) error {
	s.mu.Lock()
	defer s.mu.Unlock()

	event := &pb.CrawlEvent{
		Type:    "completed",
		Message: message,
	}

	if s.stream != nil {
		return s.stream.Send(event)
	} else if s.resStream != nil {
		return s.resStream.Send(event)
	}
	return nil
}

// SendError emits an error event
func (s *GRPCStreamer) SendError(message string) error {
	s.mu.Lock()
	defer s.mu.Unlock()

	event := &pb.CrawlEvent{
		Type:    "error",
		Message: message,
	}

	if s.stream != nil {
		return s.stream.Send(event)
	} else if s.resStream != nil {
		return s.resStream.Send(event)
	}
	return nil
}

// SendCheckpoint emits a checkpoint notification
func (s *GRPCStreamer) SendCheckpoint(message string) error {
	s.mu.Lock()
	defer s.mu.Unlock()

	event := &pb.CrawlEvent{
		Type:    "checkpoint",
		Message: message,
	}

	if s.stream != nil {
		return s.stream.Send(event)
	} else if s.resStream != nil {
		return s.resStream.Send(event)
	}
	return nil
}

// Context returns the underlying stream context
func (s *GRPCStreamer) Context() context.Context {
	if s.stream != nil {
		return s.stream.Context()
	} else if s.resStream != nil {
		return s.resStream.Context()
	}
	return context.Background()
}
