import type { TabSchema } from '../../types';

export const TAB_SCHEMAS: Record<string, TabSchema> = {
  all: {
    label: 'All URLs',
    columns: [
      { key: 'row', label: '#', defaultWidth: 50, align: 'text-center' },
      { key: 'url', label: 'Address', defaultWidth: 650 },
      { key: 'content_type', label: 'Content Type', defaultWidth: 140 },
      { key: 'status_code', label: 'Status Code', defaultWidth: 100, align: 'text-center' },
      { key: 'status', label: 'Status', defaultWidth: 110 },
      { key: 'indexability', label: 'Indexability', defaultWidth: 130 },
      { key: 'indexability_status', label: 'Indexability Status', defaultWidth: 160 },
      { key: 'canonical_status', label: 'Canonical Status', defaultWidth: 140 },
      { key: 'canonical_url', label: 'Canonical Link Element', defaultWidth: 320 },
      { key: 'internal_pagerank', label: 'Internal PageRank', defaultWidth: 120, align: 'text-right' },
      { key: 'click_depth', label: 'Click Depth', defaultWidth: 95, align: 'text-center' },
      { key: 'is_orphan', label: 'Orphan', defaultWidth: 85, align: 'text-center' },
      { key: 'length', label: 'Length', defaultWidth: 95, align: 'text-right' },
    ]
  },
  internal: {
    label: 'Internal',
    columns: [
      { key: 'row', label: '#', defaultWidth: 50, align: 'text-center' },
      { key: 'url', label: 'Address', defaultWidth: 650 },
      { key: 'content_type', label: 'Content Type', defaultWidth: 130 },
      { key: 'status_code', label: 'Status Code', defaultWidth: 95, align: 'text-center' },
      { key: 'status', label: 'Status', defaultWidth: 100 },
      { key: 'indexability', label: 'Indexability', defaultWidth: 120 },
      { key: 'indexability_status', label: 'Indexability Status', defaultWidth: 150 },
      { key: 'canonical_status', label: 'Canonical Status', defaultWidth: 140 },
      { key: 'title', label: 'Title 1', defaultWidth: 240 },
      { key: 'title_length', label: 'Title 1 Length', defaultWidth: 95, align: 'text-right' },
      { key: 'meta_description', label: 'Meta Description 1', defaultWidth: 260 },
      { key: 'meta_description_length', label: 'Description 1 Length', defaultWidth: 110, align: 'text-right' },
      { key: 'canonical_url', label: 'Canonical Link Element', defaultWidth: 240 },
      { key: 'internal_pagerank', label: 'Internal PageRank', defaultWidth: 120, align: 'text-right' },
      { key: 'size_bytes', label: 'Size', defaultWidth: 85, align: 'text-right' },
      { key: 'word_count', label: 'Word Count', defaultWidth: 90, align: 'text-right' },
      { key: 'click_depth', label: 'Click Depth', defaultWidth: 95, align: 'text-center' },
      { key: 'is_orphan', label: 'Orphan', defaultWidth: 85, align: 'text-center' },
      { key: 'crawl_depth', label: 'Crawl Depth', defaultWidth: 95, align: 'text-right' },
      { key: 'inlinks_count', label: 'Inlinks', defaultWidth: 80, align: 'text-right' },
      { key: 'outlinks_count', label: 'Outlinks', defaultWidth: 80, align: 'text-right' },
      { key: 'response_time', label: 'Response Time', defaultWidth: 100, align: 'text-right' },
      { key: 'redirect_url', label: 'Redirect URL', defaultWidth: 240 },
      { key: 'language', label: 'Language', defaultWidth: 85 }
    ]
  },
  external: {
    label: 'External',
    columns: [
      { key: 'row', label: '#', defaultWidth: 55, align: 'text-center' },
      { key: 'url', label: 'Address', defaultWidth: 650 },
      { key: 'content_type', label: 'Content Type', defaultWidth: 150 },
      { key: 'status_code', label: 'Status Code', defaultWidth: 95, align: 'text-center' },
      { key: 'status', label: 'Status', defaultWidth: 110 },
      { key: 'crawl_depth', label: 'Crawl Depth', defaultWidth: 95, align: 'text-right' },
      { key: 'inlinks_count', label: 'Inlinks', defaultWidth: 85, align: 'text-right' }
    ]
  },
  response_codes: {
    label: 'Response Codes',
    columns: [
      { key: 'row', label: '#', defaultWidth: 55, align: 'text-center' },
      { key: 'url', label: 'Address', defaultWidth: 550 },
      { key: 'content_type', label: 'Content Type', defaultWidth: 140 },
      { key: 'status_code', label: 'Status Code', defaultWidth: 95, align: 'text-center' },
      { key: 'status', label: 'Status', defaultWidth: 110 },
      { key: 'redirect_chain_length', label: 'Hops', defaultWidth: 70, align: 'text-center' },
      { key: 'redirect_type', label: 'Redirect Type', defaultWidth: 120 },
      { key: 'redirect_url', label: 'Redirect Destination', defaultWidth: 320 },
      { key: 'final_destination', label: 'Final Destination', defaultWidth: 320 },
      { key: 'indexability', label: 'Indexability', defaultWidth: 120 },
      { key: 'indexability_status', label: 'Indexability Status', defaultWidth: 150 },
      { key: 'inlinks_count', label: 'Inlinks', defaultWidth: 85, align: 'text-right' },
      { key: 'response_time', label: 'Response Time', defaultWidth: 100, align: 'text-right' }
    ]
  },
  page_titles: {
    label: 'Page Titles',
    columns: [
      { key: 'row', label: '#', defaultWidth: 55, align: 'text-center' },
      { key: 'url', label: 'Address', defaultWidth: 650 },
      { key: 'title', label: 'Title 1', defaultWidth: 350 },
      { key: 'title_length', label: 'Title 1 Length', defaultWidth: 110, align: 'text-right' },
      { key: 'title_pixel_width', label: 'Title 1 Pixel Width', defaultWidth: 130, align: 'text-right' },
      { key: 'indexability', label: 'Indexability', defaultWidth: 120 },
      { key: 'indexability_status', label: 'Indexability Status', defaultWidth: 150 }
    ]
  },
  meta_description: {
    label: 'Meta Description',
    columns: [
      { key: 'row', label: '#', defaultWidth: 55, align: 'text-center' },
      { key: 'url', label: 'Address', defaultWidth: 650 },
      { key: 'meta_description', label: 'Meta Description 1', defaultWidth: 380 },
      { key: 'meta_description_length', label: 'Meta Desc 1 Length', defaultWidth: 125, align: 'text-right' },
      { key: 'indexability', label: 'Indexability', defaultWidth: 120 },
      { key: 'indexability_status', label: 'Indexability Status', defaultWidth: 150 }
    ]
  },
  h1: {
    label: 'H1',
    columns: [
      { key: 'row', label: '#', defaultWidth: 55, align: 'text-center' },
      { key: 'url', label: 'Address', defaultWidth: 650 },
      { key: 'h1', label: 'H1-1', defaultWidth: 340 },
      { key: 'h1_length', label: 'H1-1 Length', defaultWidth: 100, align: 'text-right' },
      { key: 'indexability', label: 'Indexability', defaultWidth: 120 },
      { key: 'indexability_status', label: 'Indexability Status', defaultWidth: 150 }
    ]
  },
  content: {
    label: 'Content',
    columns: [
      { key: 'row', label: '#', defaultWidth: 55, align: 'text-center' },
      { key: 'url', label: 'Address', defaultWidth: 650 },
      { key: 'word_count', label: 'Word Count', defaultWidth: 95, align: 'text-right' },
      { key: 'sentence_count', label: 'Sentence Count', defaultWidth: 110, align: 'text-right' },
      { key: 'avg_words_per_sentence', label: 'Avg Words/Sentence', defaultWidth: 130, align: 'text-right' },
      { key: 'flesch_reading_ease', label: 'Flesch Reading Ease', defaultWidth: 130, align: 'text-right' },
      { key: 'readability_label', label: 'Readability', defaultWidth: 110 },
      { key: 'closest_duplicate_url', label: 'Near Duplicate Match', defaultWidth: 260 },
      { key: 'near_duplicate_count', label: 'No. Near Duplicates', defaultWidth: 130, align: 'text-right' }
    ]
  },
  images: {
    label: 'Images',
    columns: [
      { key: 'row', label: '#', defaultWidth: 55, align: 'text-center' },
      { key: 'url', label: 'Address', defaultWidth: 650 },
      { key: 'content_type', label: 'Content Type', defaultWidth: 130 },
      { key: 'size_bytes', label: 'Size', defaultWidth: 90, align: 'text-right' },
      { key: 'img_inlinks', label: 'Img Inlinks No.', defaultWidth: 110, align: 'text-right' },
      { key: 'indexability', label: 'Indexability', defaultWidth: 120 },
      { key: 'indexability_status', label: 'Indexability Status', defaultWidth: 150 },
      { key: 'dimensions', label: 'Dimensions', defaultWidth: 110 }
    ]
  },
  canonicals: {
    label: 'Canonicals',
    columns: [
      { key: 'row', label: '#', defaultWidth: 50, align: 'text-center' },
      { key: 'url', label: 'Address', defaultWidth: 420 },
      { key: 'canonical_status', label: 'Canonical Status', defaultWidth: 140 },
      { key: 'indexability', label: 'Indexability', defaultWidth: 120 },
      { key: 'indexability_status', label: 'Indexability Status', defaultWidth: 150 },
      { key: 'canonical_url', label: 'Canonical Link Element 1', defaultWidth: 360 },
      { key: 'robots_meta', label: 'Meta Robots 1', defaultWidth: 200 }
    ]
  },
  links: {
    label: 'Links',
    columns: [
      { key: 'row', label: '#', defaultWidth: 55, align: 'text-center' },
      { key: 'url', label: 'Address', defaultWidth: 650 },
      { key: 'indexability', label: 'Indexability', defaultWidth: 120 },
      { key: 'indexability_status', label: 'Indexability Status', defaultWidth: 150 },
      { key: 'crawl_depth', label: 'Crawl Depth', defaultWidth: 95, align: 'text-right' },
      { key: 'inlinks_count', label: 'Inlinks', defaultWidth: 80, align: 'text-right' },
      { key: 'unique_inlinks', label: 'Unique Inlinks', defaultWidth: 95, align: 'text-right' },
      { key: 'outlinks_count', label: 'Outlinks', defaultWidth: 80, align: 'text-right' },
      { key: 'unique_outlinks', label: 'Unique Outlinks', defaultWidth: 95, align: 'text-right' }
    ]
  },
  hreflang: {
    label: 'Hreflang',
    columns: [
      { key: 'row', label: '#', defaultWidth: 55, align: 'text-center' },
      { key: 'url', label: 'Address', defaultWidth: 650 },
      { key: 'title', label: 'Title 1', defaultWidth: 220 },
      { key: 'html_hreflang_1', label: 'HTML Hreflang 1', defaultWidth: 110 },
      { key: 'html_hreflang_1_url', label: 'HTML Hreflang 1 URL', defaultWidth: 240 },
      { key: 'indexability', label: 'Indexability', defaultWidth: 120 }
    ]
  },
  structured_data: {
    label: 'Structured Data',
    columns: [
      { key: 'row', label: '#', defaultWidth: 55, align: 'text-center' },
      { key: 'url', label: 'Address', defaultWidth: 650 },
      { key: 'sd_errors', label: 'Errors', defaultWidth: 80, align: 'text-right' },
      { key: 'sd_warnings', label: 'Warnings', defaultWidth: 85, align: 'text-right' },
      { key: 'sd_total_types', label: 'Total Types', defaultWidth: 95, align: 'text-right' },
      { key: 'sd_type_1', label: 'Type-1', defaultWidth: 140 },
      { key: 'indexability', label: 'Indexability', defaultWidth: 120 }
    ]
  },
  accessibility: {
    label: 'Accessibility',
    columns: [
      { key: 'row', label: '#', defaultWidth: 55, align: 'text-center' },
      { key: 'url', label: 'Address', defaultWidth: 650 },
      { key: 'content_type', label: 'Content Type', defaultWidth: 120 },
      { key: 'status_code', label: 'Status Code', defaultWidth: 95, align: 'text-center' },
      { key: 'accessibility_violations_total', label: 'All Violations', defaultWidth: 100, align: 'text-right' },
      { key: 'accessibility_wcag_2_1_aa', label: 'WCAG 2.1 AA', defaultWidth: 100, align: 'text-right' }
    ]
  },
  custom_extraction: {
    label: 'Custom Extraction',
    columns: [
      { key: 'row', label: '#', defaultWidth: 55, align: 'text-center' },
      { key: 'url', label: 'Address', defaultWidth: 500 },
      { key: 'status_code', label: 'Status Code', defaultWidth: 95, align: 'text-center' },
      { key: 'indexability', label: 'Indexability', defaultWidth: 120 },
      { key: 'custom_extraction_summary', label: 'Extracted Values', defaultWidth: 450 }
    ]
  },
  custom_search: {
    label: 'Custom Search',
    columns: [
      { key: 'row', label: '#', defaultWidth: 55, align: 'text-center' },
      { key: 'url', label: 'Address', defaultWidth: 500 },
      { key: 'status_code', label: 'Status Code', defaultWidth: 95, align: 'text-center' },
      { key: 'matched_rules', label: 'Matched Rule(s)', defaultWidth: 200 },
      { key: 'search_snippet', label: 'Matched Snippet', defaultWidth: 400 }
    ]
  },
  orphans: {
    label: 'Orphan Pages',
    columns: [
      { key: 'row', label: '#', defaultWidth: 55, align: 'text-center' },
      { key: 'url', label: 'Address', defaultWidth: 550 },
      { key: 'status_code', label: 'Status Code', defaultWidth: 95, align: 'text-center' },
      { key: 'unique_inlinks', label: 'Inlinks', defaultWidth: 80, align: 'text-center' },
      { key: 'click_depth', label: 'Click Depth', defaultWidth: 95, align: 'text-center' },
      { key: 'indexability', label: 'Indexability', defaultWidth: 120 },
      { key: 'title', label: 'Title 1', defaultWidth: 260 }
    ]
  },
  redirect_chains: {
    label: 'Redirect Chains',
    columns: [
      { key: 'row', label: '#', defaultWidth: 55, align: 'text-center' },
      { key: 'url', label: 'Address', defaultWidth: 420 },
      { key: 'status_code', label: 'Initial Code', defaultWidth: 95, align: 'text-center' },
      { key: 'redirect_chain_length', label: 'Hops', defaultWidth: 70, align: 'text-center' },
      { key: 'redirect_type', label: 'Type', defaultWidth: 110 },
      { key: 'redirect_chain_summary', label: 'Redirection Path', defaultWidth: 450 },
      { key: 'final_destination', label: 'Destination URL', defaultWidth: 350 }
    ]
  }
};

export const COLUMN_PRESETS: Record<string, string[] | null> = {
  all: null,
  seo_basics: ['row', 'url', 'status_code', 'status', 'indexability', 'title', 'meta_description', 'h1', 'canonical_url'],
  technical: ['row', 'url', 'status_code', 'canonical_status', 'canonical_url', 'indexability_status', 'robots_directive', 'response_time', 'content_type'],
  link_equity: ['row', 'url', 'internal_pagerank', 'inlinks_count', 'unique_inlinks', 'outlinks_count', 'unique_outlinks', 'crawl_depth'],
  content: ['row', 'url', 'word_count', 'sentence_count', 'avg_words_per_sentence', 'title_length', 'meta_description_length']
};
