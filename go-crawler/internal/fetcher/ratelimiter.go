package fetcher

import (
	"context"
	"sync"
	"time"

	"golang.org/x/time/rate"
)

// DomainLimiter manages rate limiting and concurrency for an individual domain
type DomainLimiter struct {
	limiter   *rate.Limiter
	semaphore chan struct{}
	lastSeen  time.Time
}

// PerDomainLimiter manages per-host rate limits and concurrency locks across all hosts
type PerDomainLimiter struct {
	mu           sync.RWMutex
	domains      map[string]*DomainLimiter
	maxPerHost   int
	delayPerHost time.Duration
}

// NewPerDomainLimiter creates a new rate limiter
func NewPerDomainLimiter(maxPerHost int, delay time.Duration) *PerDomainLimiter {
	if maxPerHost <= 0 {
		maxPerHost = 30
	}
	if delay < 0 {
		delay = 0
	}

	p := &PerDomainLimiter{
		domains:      make(map[string]*DomainLimiter),
		maxPerHost:   maxPerHost,
		delayPerHost: delay,
	}

	// Periodically evict idle domains older than 10 minutes
	go p.cleanupLoop(10 * time.Minute)

	return p
}

// Acquire reserves a rate-limit slot and concurrency slot for the given host.
// The returned function MUST be called when the request finishes to release the slot.
func (p *PerDomainLimiter) Acquire(ctx context.Context, host string) (func(), error) {
	p.mu.Lock()
	dl, exists := p.domains[host]
	if !exists {
		var lim *rate.Limiter
		if p.delayPerHost > 0 {
			lim = rate.NewLimiter(rate.Every(p.delayPerHost), 1)
		}
		dl = &DomainLimiter{
			limiter:   lim,
			semaphore: make(chan struct{}, p.maxPerHost),
		}
		p.domains[host] = dl
	}
	dl.lastSeen = time.Now()
	p.mu.Unlock()

	// 1. Wait for delay token only if delay > 0
	if dl.limiter != nil {
		if err := dl.limiter.Wait(ctx); err != nil {
			return nil, err
		}
	}

	// 2. Acquire concurrency semaphore
	select {
	case dl.semaphore <- struct{}{}:
	case <-ctx.Done():
		return nil, ctx.Err()
	}

	return func() {
		<-dl.semaphore
	}, nil
}

// SetHostDelay updates the delay for a specific host (e.g., from robots.txt Crawl-delay)
func (p *PerDomainLimiter) SetHostDelay(host string, delay time.Duration) {
	p.mu.Lock()
	defer p.mu.Unlock()

	dl, exists := p.domains[host]
	if !exists {
		dl = &DomainLimiter{
			semaphore: make(chan struct{}, p.maxPerHost),
		}
		p.domains[host] = dl
	}
	dl.limiter = rate.NewLimiter(rate.Every(delay), 1)
	dl.lastSeen = time.Now()
}

func (p *PerDomainLimiter) cleanupLoop(interval time.Duration) {
	ticker := time.NewTicker(interval)
	for range ticker.C {
		p.mu.Lock()
		cutoff := time.Now().Add(-interval)
		for host, dl := range p.domains {
			if dl.lastSeen.Before(cutoff) && len(dl.semaphore) == 0 {
				delete(p.domains, host)
			}
		}
		p.mu.Unlock()
	}
}
