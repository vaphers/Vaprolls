/**
 * AppState — Centralized Reactive Pub/Sub Store for SEO Auditer
 * Coordinates crawl state, table state, inspector, and WebSocket updates across templates.
 */

(function (window) {
    'use strict';

    const AppState = {
        // 1. Crawl Lifecycle State
        crawl: {
            auditId: null,
            status: 'idle', // 'idle' | 'crawling' | 'analyzing' | 'analyzing_deep' | 'complete' | 'stopped' | 'error'
            maxPages: 0,    // 0 = unlimited
            crawledCount: 0,
            totalEstimate: 0,
            errorsCount: 0,
            pagesPerSec: 0,
            avgResponseMs: 0,
            memoryMb: 0,
            currentUrl: '',
            queued: 0,
            startTime: null
        },

        // 2. Active Audit Metadata
        audit: {
            id: null,
            domain: '',
            url: '',
            status: '',
            healthScore: 0,
            totalPages: 0,
            totalIssues: 0
        },

        // 3. Table State & Filters
        table: {
            activeTab: 'all',
            activeGroup: 'all',
            rows: [],          // Currently rendered rows (virtual table dataset)
            bufferedRows: [],  // Live buffer queue for rAF batching
            filters: {
                status: 'all',
                indexable: 'all',
                pageType: 'all',
                contentType: 'all',
                depth: 'all',
                wordCount: 'all',
                issues: 'all',
                include: '',
                exclude: '',
                q: ''
            },
            sort: { key: 'status_code', direction: 'asc' },
            selectedPageId: null,
            visibleCount: 0,
            totalCount: 0
        },

        // 4. Inspector State
        inspector: {
            activeTab: 'details', // 'details' | 'redirects' | 'inlinks' | 'outlinks' | 'images' | 'schema' | 'issues' | 'headers' | 'serp'
            pageData: null,
            redirectChain: [],
            isLoading: false
        },

        // 5. Right Sidebar State
        sidebar: {
            activeTab: 'overview', // 'overview' | 'issues' | 'structure' | 'segments'
            subMode: 'url'
        },

        // Pub/Sub listeners dictionary
        _listeners: {},

        /**
         * Subscribe to a state path or event.
         * Examples:
         *   AppState.subscribe('crawl.status', (status) => { ... });
         *   AppState.subscribe('crawl.*', (val) => { ... });
         *   AppState.subscribe('page_row_received', (row) => { ... });
         */
        subscribe(path, callback) {
            if (!this._listeners[path]) {
                this._listeners[path] = [];
            }
            this._listeners[path].push(callback);
            return () => this.unsubscribe(path, callback);
        },

        unsubscribe(path, callback) {
            if (!this._listeners[path]) return;
            this._listeners[path] = this._listeners[path].filter(cb => cb !== callback);
        },

        /**
         * Safely notify all subscribers registered for a key/path.
         */
        emit(path, data) {
            const notify = (key, val) => {
                if (this._listeners[key]) {
                    const callbacks = [...this._listeners[key]];
                    for (const cb of callbacks) {
                        try {
                            cb(val, this);
                        } catch (err) {
                            console.error(`[AppState] Error in subscriber callback for '${key}':`, err);
                        }
                    }
                }
            };

            notify(path, data);

            // Notify wildcard parent path, e.g., 'crawl.*' for 'crawl.status'
            if (path.includes('.')) {
                const prefix = path.split('.')[0];
                notify(`${prefix}.*`, data);
            }
            notify('*', { path, data });
        },

        /**
         * Get a nested state property using dotted notation.
         */
        get(path) {
            const parts = path.split('.');
            let curr = this;
            for (const p of parts) {
                if (curr == null) return undefined;
                curr = curr[p];
            }
            return curr;
        },

        /**
         * Set a nested property and emit change notification.
         */
        set(path, value) {
            const parts = path.split('.');
            let curr = this;
            for (let i = 0; i < parts.length - 1; i++) {
                const p = parts[i];
                if (curr[p] == null || typeof curr[p] !== 'object') {
                    curr[p] = {};
                }
                curr = curr[p];
            }
            const lastKey = parts[parts.length - 1];
            const oldVal = curr[lastKey];
            curr[lastKey] = value;
            if (oldVal !== value) {
                this.emit(path, value);
            }
        },

        /**
         * Shallow merge object into an existing state branch.
         */
        patch(path, patchObj) {
            const target = this.get(path);
            if (target && typeof target === 'object') {
                Object.assign(target, patchObj);
                this.emit(path, target);
            } else {
                this.set(path, patchObj);
            }
        },

        /**
         * Hydrate state from server rendered Jinja2 bootstrap JSON.
         */
        hydrate(seed) {
            if (!seed || typeof seed !== 'object') return;
            if (seed.crawl) Object.assign(this.crawl, seed.crawl);
            if (seed.audit) Object.assign(this.audit, seed.audit);
            if (seed.table) {
                if (seed.table.filters) Object.assign(this.table.filters, seed.table.filters);
                if (seed.table.activeTab) this.table.activeTab = seed.table.activeTab;
                if (seed.table.rows) this.table.rows = seed.table.rows;
                if (seed.table.totalCount !== undefined) this.table.totalCount = seed.table.totalCount;
                if (seed.table.visibleCount !== undefined) this.table.visibleCount = seed.table.visibleCount;
            }
            this.emit('hydrated', this);
        },

        /**
         * Handle incoming WebSocket progress / crawl events.
         */
        handleWsMessage(data) {
            if (!data) return;

            if (data.type === 'initial_state') {
                this.patch('crawl', {
                    status: data.status || 'crawling',
                    crawledCount: data.crawled || 0,
                    maxPages: data.max_pages !== undefined ? data.max_pages : this.crawl.maxPages
                });
                return;
            }

            if (data.type === 'progress') {
                this.patch('crawl', {
                    status: data.status || 'crawling',
                    crawledCount: data.crawled || 0,
                    totalEstimate: data.total || 0,
                    maxPages: data.max_pages !== undefined ? data.max_pages : this.crawl.maxPages,
                    pagesPerSec: data.pages_per_sec || 0,
                    avgResponseMs: data.avg_response_ms || 0,
                    memoryMb: data.memory_mb || 0,
                    errorsCount: data.errors || 0,
                    currentUrl: data.url || '',
                    queued: data.queued || 0
                });

                if (data.page_row) {
                    this.emit('page_row_received', data.page_row);
                }
            } else if (data.type === 'status') {
                this.set('crawl.status', data.status || 'analyzing');
            } else if (data.type === 'analyzers_tier2_complete') {
                this.set('crawl.status', 'analyzing_deep');
                this.emit('analyzers_tier2_complete', data);
            } else if (data.type === 'complete') {
                this.set('crawl.status', 'complete');
                this.emit('crawl_complete', data);
            } else if (data.type === 'warning') {
                this.emit('crawl_warning', data);
            }
        }
    };

    window.AppState = AppState;
})(window);
