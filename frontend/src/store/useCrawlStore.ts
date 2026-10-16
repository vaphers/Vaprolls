import { create } from 'zustand';
import type { PageRow, CrawlProgress, InspectorData, RightPanelData, CrawlStatus } from '../types';
import { api } from '../services/api';

interface CrawlState {
  auditId: string | null;
  startUrl: string;
  mode: 'spider' | 'sitemaps';
  sitemapsText: string;
  concurrency: number;
  maxPages: number;
  crawlDelay: number;
  userAgentPreset: string;
  elapsedSeconds: number;
  renderingMode: 'text' | 'javascript';
  customExtractors: any[];
  customSearchRules: any[];
  
  isCompareOpen: boolean;
  isVisualizerOpen: boolean;
  isCustomRulesOpen: boolean;
  
  progress: CrawlProgress;
  
  currentTab: string;
  columnPreset: string;
  columnWidths: Record<string, number>;
  sortBy: string;
  sortDir: 'asc' | 'desc';
  
  searchTerm: string;
  includeRegex: string;
  excludeRegex: string;
  contentTypeFilter: string;
  
  rows: PageRow[];
  filteredRows: PageRow[];
  tabCounts: Record<string, number>;
  
  selectedPageId: number | null;
  inspectorData: InspectorData | null;
  inspectorLoading: boolean;
  activeInspectorTab: string;
  
  rightPanelTab: string;
  rightPanelData: RightPanelData;
  isRightPanelOpen: boolean;
  isInspectorOpen: boolean;

  setStartUrl: (url: string) => void;
  setMode: (mode: 'spider' | 'sitemaps') => void;
  setSitemapsText: (text: string) => void;
  setConcurrency: (threads: number) => void;
  setMaxPages: (max: number) => void;
  setRenderingMode: (mode: 'text' | 'javascript') => void;
  setCustomExtractors: (rules: any[]) => void;
  setCustomSearchRules: (rules: any[]) => void;
  setIsCompareOpen: (open: boolean) => void;
  setIsVisualizerOpen: (open: boolean) => void;
  setIsCustomRulesOpen: (open: boolean) => void;
  
  startCrawl: () => Promise<void>;
  stopCrawl: () => Promise<void>;
  clearAll: () => Promise<void>;
  
  switchTab: (tabKey: string) => Promise<void>;
  setColumnPreset: (preset: string) => void;
  setColumnWidth: (colKey: string, width: number) => void;
  setSort: (colKey: string) => void;
  
  setSearchTerm: (term: string) => void;
  setIncludeRegex: (regex: string) => void;
  setExcludeRegex: (regex: string) => void;
  setContentTypeFilter: (type: string) => void;
  
  selectPage: (pageId: number) => Promise<void>;
  setActiveInspectorTab: (tab: string) => void;
  setRightPanelTab: (tab: string) => void;
  toggleRightPanel: () => void;
  toggleInspector: () => void;
  
  connectWebSocket: (auditId: string) => void;
  disconnectWebSocket: () => void;
  ingestStreamRows: (newRows: PageRow[]) => void;
}

let wsConnection: WebSocket | null = null;
let timerInterval: any = null;
let pendingRowsBuffer: PageRow[] = [];
let bufferRaf: number | null = null;

export const useCrawlStore = create<CrawlState>((set, get) => ({
  auditId: null,
  startUrl: '',
  mode: 'spider',
  sitemapsText: '',
  concurrency: 15,
  maxPages: 0,
  crawlDelay: 0,
  userAgentPreset: 'screaming-frog',
  elapsedSeconds: 0,
  renderingMode: 'text',
  customExtractors: [],
  customSearchRules: [],
  
  isCompareOpen: false,
  isVisualizerOpen: false,
  isCustomRulesOpen: false,

  progress: {
    crawled: 0,
    total: 0,
    max_pages: 0,
    pages_per_sec: 0,
    avg_response_ms: 0,
    memory_mb: 0,
    errors: 0,
    status: 'idle',
  },

  currentTab: 'all',
  columnPreset: 'all',
  columnWidths: {},
  sortBy: 'status',
  sortDir: 'asc',

  searchTerm: '',
  includeRegex: '',
  excludeRegex: '',
  contentTypeFilter: 'all',

  rows: [],
  filteredRows: [],
  tabCounts: {},

  selectedPageId: null,
  inspectorData: null,
  inspectorLoading: false,
  activeInspectorTab: 'overview',

  rightPanelTab: 'site-issues',
  rightPanelData: {},
  isRightPanelOpen: true,
  isInspectorOpen: true,

  setStartUrl: (url) => set({ startUrl: url }),
  setMode: (mode) => set({ mode }),
  setSitemapsText: (sitemapsText) => set({ sitemapsText }),
  setConcurrency: (concurrency) => set({ concurrency }),
  setMaxPages: (maxPages) => set({ maxPages }),
  setRenderingMode: (renderingMode) => set({ renderingMode }),
  setCustomExtractors: (customExtractors) => set({ customExtractors }),
  setCustomSearchRules: (customSearchRules) => set({ customSearchRules }),
  setIsCompareOpen: (isCompareOpen) => set({ isCompareOpen }),
  setIsVisualizerOpen: (isVisualizerOpen) => set({ isVisualizerOpen }),
  setIsCustomRulesOpen: (isCustomRulesOpen) => set({ isCustomRulesOpen }),

  startCrawl: async () => {
    const { startUrl, maxPages, concurrency, crawlDelay, userAgentPreset, mode, sitemapsText, renderingMode, customExtractors, customSearchRules } = get();
    if (!startUrl.trim()) return;

    // Clean duplicate protocols
    let cleanUrl = startUrl.trim().replace(/^(https?:\/\/)+/i, '');
    cleanUrl = startUrl.toLowerCase().startsWith('http://') ? 'http://' + cleanUrl : 'https://' + cleanUrl;
    set({ startUrl: cleanUrl });

    // Reset workspace rows & progress
    pendingRowsBuffer = [];
    if (bufferRaf) {
      cancelAnimationFrame(bufferRaf);
      bufferRaf = null;
    }
    set({
      rows: [],
      filteredRows: [],
      selectedPageId: null,
      inspectorData: null,
      elapsedSeconds: 0,
      progress: {
        crawled: 0,
        total: 0,
        max_pages: maxPages,
        pages_per_sec: 0,
        avg_response_ms: 0,
        memory_mb: 0,
        errors: 0,
        status: 'crawling',
      }
    });

    if (timerInterval) clearInterval(timerInterval);
    const startTime = Date.now();
    timerInterval = setInterval(() => {
      set({ elapsedSeconds: Math.floor((Date.now() - startTime) / 1000) });
    }, 1000);

    try {
      const data = await api.startAudit({
        url: cleanUrl,
        max_pages: maxPages,
        concurrency,
        crawl_delay: crawlDelay,
        user_agent_preset: userAgentPreset,
        mode,
        sitemaps_text: sitemapsText,
        rendering_mode: renderingMode,
        custom_extractors: customExtractors,
        custom_search: customSearchRules,
      });

      if (data.audit_id) {
        set({ auditId: data.audit_id });
        if (window.history && window.history.pushState) {
          window.history.pushState({ auditId: data.audit_id }, '', `/?audit_id=${data.audit_id}`);
        }
        get().connectWebSocket(data.audit_id);
      }
    } catch (err) {
      console.error("Crawl start failed:", err);
      if (timerInterval) clearInterval(timerInterval);
      set((state) => ({ progress: { ...state.progress, status: 'error' } }));
    }
  },

  stopCrawl: async () => {
    const { auditId } = get();
    if (!auditId) return;
    if (timerInterval) clearInterval(timerInterval);
    get().disconnectWebSocket();
    try {
      await api.stopAudit(auditId);
      set((state) => ({ progress: { ...state.progress, status: 'stopped' } }));
      get().switchTab(get().currentTab);
    } catch (e) {
      console.error(e);
    }
  },

  clearAll: async () => {
    if (!confirm("Are you sure you want to clear all crawl data and caches?")) return;
    if (timerInterval) clearInterval(timerInterval);
    get().disconnectWebSocket();
    pendingRowsBuffer = [];
    if (bufferRaf) {
      cancelAnimationFrame(bufferRaf);
      bufferRaf = null;
    }
    try {
      await api.clearAuditData();
      set({
        auditId: null,
        rows: [],
        filteredRows: [],
        selectedPageId: null,
        inspectorData: null,
        rightPanelData: {},
        progress: {
          crawled: 0,
          total: 0,
          max_pages: 0,
          pages_per_sec: 0,
          avg_response_ms: 0,
          memory_mb: 0,
          errors: 0,
          status: 'idle',
        }
      });
      if (window.history && window.history.replaceState) {
        window.history.replaceState({}, '', '/');
      }
    } catch (e) {
      console.error(e);
    }
  },

  switchTab: async (tabKey: string) => {
    set({ currentTab: tabKey });
    const { auditId, sortBy, sortDir } = get();
    if (!auditId) return;

    try {
      const data = await api.getTabRows(auditId, tabKey, sortBy, sortDir);
      const rows = data.rows || [];
      set({ rows });
      filterAndSortRows(set, get);
    } catch (err) {
      console.error("Tab switch fetch error:", err);
    }
  },

  setColumnPreset: (preset: string) => {
    set({ columnPreset: preset });
  },

  setColumnWidth: (colKey: string, width: number) => {
    set((state) => ({
      columnWidths: { ...state.columnWidths, [colKey]: width }
    }));
  },

  setSort: (colKey: string) => {
    const { sortBy, sortDir } = get();
    let newDir: 'asc' | 'desc' = 'asc';
    if (sortBy === colKey) {
      newDir = sortDir === 'asc' ? 'desc' : 'asc';
    }
    set({ sortBy: colKey, sortDir: newDir });
    get().switchTab(get().currentTab);
  },

  setSearchTerm: (searchTerm: string) => {
    set({ searchTerm });
    filterAndSortRows(set, get);
  },

  setIncludeRegex: (includeRegex: string) => {
    set({ includeRegex });
    filterAndSortRows(set, get);
  },

  setExcludeRegex: (excludeRegex: string) => {
    set({ excludeRegex });
    filterAndSortRows(set, get);
  },

  setContentTypeFilter: (contentTypeFilter: string) => {
    set({ contentTypeFilter });
    filterAndSortRows(set, get);
  },

  selectPage: async (pageId: number) => {
    set({ selectedPageId: pageId, inspectorLoading: true });
    const { auditId } = get();
    if (!auditId) return;

    try {
      const data = await api.getInspectorData(auditId, pageId);
      set({ inspectorData: data, inspectorLoading: false });
    } catch (err) {
      console.error("Failed to load page inspector:", err);
      set({ inspectorLoading: false });
    }
  },

  setActiveInspectorTab: (activeInspectorTab) => set({ activeInspectorTab }),
  setRightPanelTab: async (rightPanelTab) => {
    set({ rightPanelTab });
    const { auditId } = get();
    if (!auditId) return;
    try {
      const data = await api.getRightPanelData(auditId, rightPanelTab);
      if (data) {
        set((state) => ({
          rightPanelData: { ...state.rightPanelData, [rightPanelTab]: data }
        }));
      }
    } catch (e) {}
  },
  toggleRightPanel: () => set((state) => ({ isRightPanelOpen: !state.isRightPanelOpen })),
  toggleInspector: () => set((state) => ({ isInspectorOpen: !state.isInspectorOpen })),

  connectWebSocket: (auditId: string) => {
    get().disconnectWebSocket();
    const proto = location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${proto}//${location.host}/ws/audit/${auditId}`;
    wsConnection = new WebSocket(wsUrl);

    wsConnection.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data);
        if (msg.type === 'progress') {
          const crawled = msg.crawled || 0;
          set((state) => ({
            progress: {
              ...state.progress,
              crawled,
              total: msg.total || crawled,
              max_pages: msg.max_pages ?? state.progress.max_pages,
              pages_per_sec: msg.pages_per_sec || 0,
              avg_response_ms: msg.avg_response_ms || 0,
              memory_mb: msg.memory_mb || 0,
              errors: msg.errors || 0,
              status: 'crawling',
              current_url: msg.url || '',
            }
          }));

          // Ingest live streamed page rows
          if (msg.page_rows && Array.isArray(msg.page_rows) && msg.page_rows.length > 0) {
            get().ingestStreamRows(msg.page_rows);
          } else if (msg.page_row) {
            get().ingestStreamRows([msg.page_row]);
          }
        } else if (msg.type === 'initial_state') {
          const crawled = msg.crawled || 0;
          set((state) => ({
            progress: {
              ...state.progress,
              crawled,
              total: crawled,
              max_pages: msg.max_pages ?? state.progress.max_pages,
              status: (msg.status as CrawlStatus) || 'crawling',
            }
          }));
          if (msg.page_rows && Array.isArray(msg.page_rows) && msg.page_rows.length > 0) {
            get().ingestStreamRows(msg.page_rows);
          } else if (crawled > 0) {
            get().switchTab(get().currentTab);
          }
          if (msg.status === 'complete' || msg.status === 'stopped') {
            if (timerInterval) clearInterval(timerInterval);
            get().switchTab(get().currentTab);
            get().setRightPanelTab(get().rightPanelTab);
          }
        } else if (msg.type === 'status' && msg.status === 'analyzing') {
          set((state) => ({
            progress: { ...state.progress, status: 'analyzing' }
          }));
        } else if (msg.type === 'analyzers_tier2_complete') {
          set((state) => ({
            progress: { ...state.progress, status: 'analyzing_deep' }
          }));
          get().switchTab(get().currentTab);
        } else if (msg.type === 'complete') {
          if (timerInterval) clearInterval(timerInterval);
          set((state) => ({
            progress: { ...state.progress, status: 'complete' }
          }));
          get().switchTab(get().currentTab);
          // Refresh right panel data
          get().setRightPanelTab(get().rightPanelTab);
        }
      } catch (e) {
        console.error("WS Parse error", e);
      }
    };

    wsConnection.onclose = () => {
      // Check final status on disconnect
      setTimeout(async () => {
        try {
          const st = await api.getAuditStatus(auditId);
          if (st.status === 'complete' || st.status === 'stopped') {
            if (timerInterval) clearInterval(timerInterval);
            set((state) => ({
              progress: { ...state.progress, status: st.status as CrawlStatus }
            }));
            get().switchTab(get().currentTab);
          }
        } catch (e) {}
      }, 500);
    };
  },

  disconnectWebSocket: () => {
    if (wsConnection) {
      wsConnection.close();
      wsConnection = null;
    }
  },

  ingestStreamRows: (newRows: PageRow[]) => {
    if (!newRows || newRows.length === 0) return;

    const stateRows = get().rows;
    const existingUrls = new Set(stateRows.map((r: PageRow) => r.url));
    for (let i = 0; i < pendingRowsBuffer.length; i++) {
      existingUrls.add(pendingRowsBuffer[i].url);
    }

    const toAdd: PageRow[] = [];
    const baseIndex = stateRows.length + pendingRowsBuffer.length;

    for (let i = 0; i < newRows.length; i++) {
      const r = newRows[i];
      if (!r || !r.url) continue;
      if (existingUrls.has(r.url)) continue;
      existingUrls.add(r.url);

      toAdd.push({
        ...r,
        id: r.id || (baseIndex + toAdd.length + 1),
        row: baseIndex + toAdd.length + 1,
        url: r.url || '',
        status_code: r.status_code || 0,
        content_type: r.content_type || '',
        status: r.status || (r.status_code === 200 ? 'OK' : (r.status_code ? String(r.status_code) : '')),
        response_time: r.response_time || r.response_time_ms || 0,
        size_bytes: r.size_bytes || (r as any).length || 0,
        crawl_depth: r.crawl_depth || 0,
        click_depth: r.click_depth !== undefined ? r.click_depth : r.crawl_depth || 0,
        is_orphan: r.is_orphan || false,
        title: r.title || '',
        meta_description: r.meta_description || '',
        h1: r.h1 || '',
        word_count: r.word_count || 0,
        canonical_url: r.canonical_url || '',
        canonical_status: r.canonical_url && r.canonical_url === r.url ? 'Self-Referential' : (r.canonical_url ? 'Canonicalised' : ''),
        indexability: r.indexability || (r.status_code === 200 ? 'Indexable' : (r.status_code ? 'Non-Indexable' : '')),
        indexability_status: r.indexability_status || '',
      });
    }

    if (toAdd.length === 0) return;
    pendingRowsBuffer.push(...toAdd);

    if (!bufferRaf) {
      bufferRaf = requestAnimationFrame(() => {
        bufferRaf = null;
        const chunk = pendingRowsBuffer;
        pendingRowsBuffer = [];
        set((state) => {
          const updatedRows = [...state.rows, ...chunk];
          return { rows: updatedRows };
        });
        filterAndSortRows(set, get);
      });
    }
  }
}));

function filterAndSortRows(set: any, get: any) {
  const { rows, searchTerm, includeRegex, excludeRegex, contentTypeFilter } = get();
  
  let incReg: RegExp | null = null;
  if (includeRegex.trim()) {
    try { incReg = new RegExp(includeRegex.trim(), 'i'); } catch (e) {}
  }

  let excReg: RegExp | null = null;
  if (excludeRegex.trim()) {
    try { excReg = new RegExp(excludeRegex.trim(), 'i'); } catch (e) {}
  }

  const sTerm = searchTerm.toLowerCase().trim();
  const cType = contentTypeFilter.toLowerCase();

  const filtered = rows.filter((r: PageRow) => {
    const url = r.url || '';
    const ct = (r.content_type || '').toLowerCase();

    if (cType !== 'all') {
      if (cType === 'text/html' && !ct.includes('html')) return false;
      if (cType === 'image' && !ct.includes('image')) return false;
      if (cType === 'javascript' && !ct.includes('javascript') && !ct.includes('js')) return false;
      if (cType === 'css' && !ct.includes('css')) return false;
      if (cType === 'pdf' && !ct.includes('pdf')) return false;
    }

    if (incReg && !incReg.test(url)) return false;
    if (excReg && excReg.test(url)) return false;

    if (sTerm) {
      const match = url.toLowerCase().includes(sTerm) ||
                    (r.title && r.title.toLowerCase().includes(sTerm)) ||
                    (r.h1 && r.h1.toLowerCase().includes(sTerm));
      if (!match) return false;
    }

    return true;
  });

  set({ filteredRows: filtered });
}
