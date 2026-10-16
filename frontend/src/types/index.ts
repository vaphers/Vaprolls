export interface PageRow {
  id: number;
  row?: number;
  url: string;
  final_url?: string;
  status_code: number;
  status?: string;
  content_type?: string;
  mime_type?: string;
  response_time?: number;
  response_time_ms?: number;
  size_bytes?: number;
  crawl_depth?: number;
  title?: string;
  title_length?: number;
  meta_description?: string;
  meta_description_length?: number;
  h1?: string;
  h1_length?: number;
  canonical_url?: string;
  canonical_status?: string;
  word_count?: number;
  indexability?: string;
  indexability_status?: string;
  internal_pagerank?: number | string;
  inlinks_count?: number;
  outlinks_count?: number;
  external_links_count?: number;
  images_count?: number;
  schema_count?: number;
  issues_count?: number;
  redirect_url?: string;
  redirect_type?: string;
  redirect_chain_length?: number;
  final_destination?: string;
  robots_directive?: string;
  language?: string;
  [key: string]: any;
}

export type CrawlStatus = 'idle' | 'crawling' | 'analyzing' | 'analyzing_deep' | 'complete' | 'stopped' | 'error';

export interface CrawlProgress {
  crawled: number;
  total: number;
  max_pages: number;
  pages_per_sec: number;
  avg_response_ms: number;
  memory_mb: number;
  errors: number;
  status: CrawlStatus;
  current_url?: string;
}

export interface ColumnDef {
  key: string;
  label: string;
  defaultWidth: number;
  align?: 'text-left' | 'text-center' | 'text-right';
}

export interface TabSchema {
  label: string;
  columns: ColumnDef[];
}

export interface InspectorLink {
  source_url?: string;
  target_url?: string;
  anchor_text?: string;
  status_code?: number;
  nofollow?: boolean;
  is_internal?: boolean;
}

export interface InspectorImage {
  src: string;
  alt_text: string;
  file_size?: number;
  width?: number;
  height?: number;
  is_lazy_loaded?: boolean;
}

export interface InspectorResource {
  url: string;
  resource_type: string;
  size?: number;
  is_render_blocking?: boolean;
  is_minified?: boolean;
  cache_control?: string;
}

export interface InspectorIssue {
  code: string;
  title: string;
  severity: 'critical' | 'warning' | 'notice' | 'info';
  category?: string;
  description?: string;
  recommendation?: string;
}

export interface InspectorStructuredData {
  schema_type: string;
  is_valid: boolean;
  data_json: string;
}

export interface InspectorData {
  page?: PageRow;
  inlinks?: InspectorLink[];
  outlinks?: InspectorLink[];
  images?: InspectorImage[];
  resources?: InspectorResource[];
  headers?: Record<string, string>;
  tech_stack?: Array<{ name: string; category: string; version?: string }>;
  issues?: InspectorIssue[];
  redirect_chain?: any[];
  duplicate_details?: {
    near_duplicate_count?: number;
    content_hash?: string;
    closest_duplicate_url?: string;
    similarity?: number;
    matches?: Array<{ url: string; similarity: number; content_hash: string }>;
  };
  structured_data?: InspectorStructuredData[];
}

export interface SegmentStat {
  segment: string;
  count: number;
  pct: number;
}

export interface DistributionStat {
  range?: string;
  depth?: string | number;
  count: number;
  pct: number;
}

export interface RightPanelData {
  issues?: any[];
  site_structure?: any;
  segments?: SegmentStat[];
  response_times?: DistributionStat[];
  depth?: DistributionStat[];
}

export interface CustomExtractorRule {
  name: string;
  type: 'xpath' | 'css' | 'regex';
  expression: string;
  extract_attribute?: string;
}

export interface CustomSearchRule {
  name: string;
  type: 'contains' | 'does_not_contain' | 'regex';
  query: string;
}

export interface AuditListItem {
  id: string;
  domain: string;
  url: string;
  created_at: string;
  status: string;
  total_pages: number;
}

export interface ComparisonDiff {
  base_audit: { id: string; domain: string; url: string; total_pages: number };
  compare_audit: { id: string; domain: string; url: string; total_pages: number };
  summary: {
    base_total: number;
    compare_total: number;
    added_urls_count: number;
    removed_urls_count: number;
    status_changed_count: number;
    title_changed_count: number;
    canonical_changed_count: number;
  };
  added_urls: string[];
  removed_urls: string[];
  status_changes: Array<{
    url: string;
    base_status: number;
    compare_status: number;
  }>;
  title_changes: Array<{
    url: string;
    base_title: string;
    compare_title: string;
  }>;
  canonical_changes: Array<{
    url: string;
    base_canonical: string;
    compare_canonical: string;
  }>;
}


