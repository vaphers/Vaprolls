package config

import (
	"time"
)

// CrawlConfig contains all settings for a crawl job
type CrawlConfig struct {
	AuditID         string
	StartURL        string
	MaxPages        int64
	Concurrency     int
	MaxPerHost      int
	HostDelay       time.Duration
	UserAgent       string
	CrawlMode       string
	URLsList        []string
	IncludeRegex    []string
	ExcludeRegex    []string
	MaxCrawlDepth   int
	CrawlSubdomains bool
	AllowedDomains  []string
	BlockURLs       []string
	PostgresDSN              string
	SQLitePath               string
	DataDir                  string
	RespectRobotsCrawlDelay  bool
}

// DefaultConfig returns reasonable defaults for enterprise crawling
func DefaultConfig() CrawlConfig {
	return CrawlConfig{
		MaxPages:                10000,
		Concurrency:             30,
		MaxPerHost:              30,
		HostDelay:               0,
		UserAgent:               "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
		CrawlMode:               "spider",
		MaxCrawlDepth:           10,
		DataDir:                 "./data/crawler",
		SQLitePath:              "./data/audits.db",
		RespectRobotsCrawlDelay: false,
	}
}
