"""
Modular SEO Spider Enrichment Pipeline & Tab Dataset Builders.
Supports 22 Primary Tabs, Dynamic Headings Expansion, Right Sidebar Aggregations, and Inspector Data.
"""

import re
import json
import logging
import urllib.parse
from typing import Dict, Any, List, Optional, Tuple
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

# -------------------------------------------------------------------------
# Column Schemas for All Tabs
# -------------------------------------------------------------------------

TAB_SCHEMAS: Dict[str, Dict[str, Any]] = {
    'all': {
        'label': 'All URLs',
        'columns': [
            {'key': 'row', 'label': '#', 'width': 'w-12', 'align': 'text-center'},
            {'key': 'url', 'label': 'Address', 'width': 'min-w-[360px]'},
            {'key': 'content_type', 'label': 'Content Type', 'width': 'w-28'},
            {'key': 'status_code', 'label': 'Status Code', 'width': 'w-24', 'align': 'text-center'},
            {'key': 'status', 'label': 'Status', 'width': 'w-24'},
            {'key': 'indexability', 'label': 'Indexability', 'width': 'w-28'},
            {'key': 'indexability_status', 'label': 'Indexability Status', 'width': 'w-32'},
            {'key': 'canonical_status', 'label': 'Canonical Status', 'width': 'w-32'},
            {'key': 'canonical_url', 'label': 'Canonical Link Element', 'width': 'min-w-[240px]'},
            {'key': 'internal_pagerank', 'label': 'Internal PageRank', 'width': 'w-28', 'align': 'text-right'},
            {'key': 'length', 'label': 'Length', 'width': 'w-20', 'align': 'text-right'}
        ]
    },

    'internal': {
        'label': 'Internal',
        'columns': [
            {'key': 'row', 'label': '#', 'width': 'w-12', 'align': 'text-center'},
            {'key': 'url', 'label': 'Address', 'width': 'min-w-[360px]'},
            {'key': 'content_type', 'label': 'Content Type', 'width': 'w-28'},
            {'key': 'status_code', 'label': 'Status Code', 'width': 'w-20', 'align': 'text-center'},
            {'key': 'status', 'label': 'Status', 'width': 'w-24'},
            {'key': 'indexability', 'label': 'Indexability', 'width': 'w-28'},
            {'key': 'indexability_status', 'label': 'Indexability Status', 'width': 'w-32'},
            {'key': 'canonical_status', 'label': 'Canonical Status', 'width': 'w-32'},
            {'key': 'title', 'label': 'Title 1', 'width': 'min-w-[200px]'},
            {'key': 'title_length', 'label': 'Title 1 Length', 'width': 'w-24', 'align': 'text-right'},
            {'key': 'meta_description', 'label': 'Meta Description 1', 'width': 'min-w-[200px]'},
            {'key': 'meta_description_length', 'label': 'Description 1 Length', 'width': 'w-28', 'align': 'text-right'},
            {'key': 'canonical_url', 'label': 'Canonical Link Element', 'width': 'min-w-[200px]'},
            {'key': 'internal_pagerank', 'label': 'Internal PageRank', 'width': 'w-24', 'align': 'text-right'},
            {'key': 'size_bytes', 'label': 'Size', 'width': 'w-20', 'align': 'text-right'},
            {'key': 'transferred_bytes', 'label': 'Transferred', 'width': 'w-24', 'align': 'text-right'},
            {'key': 'total_transferred_bytes', 'label': 'Total Transferred', 'width': 'w-28', 'align': 'text-right'},
            {'key': 'word_count', 'label': 'Word Count', 'width': 'w-24', 'align': 'text-right'},
            {'key': 'sentence_count', 'label': 'Sentence Count', 'width': 'w-24', 'align': 'text-right'},
            {'key': 'avg_words_per_sentence', 'label': 'Avg Words/Sentence', 'width': 'w-28', 'align': 'text-right'},
            {'key': 'text_ratio', 'label': 'Text Ratio', 'width': 'w-24', 'align': 'text-right'},
            {'key': 'crawl_depth', 'label': 'Crawl Depth', 'width': 'w-24', 'align': 'text-right'},
            {'key': 'folder_depth', 'label': 'Folder Depth', 'width': 'w-24', 'align': 'text-right'},
            {'key': 'inlinks_count', 'label': 'Inlinks', 'width': 'w-20', 'align': 'text-right'},
            {'key': 'unique_inlinks', 'label': 'Unique Inlinks', 'width': 'w-24', 'align': 'text-right'},
            {'key': 'outlinks_count', 'label': 'Outlinks', 'width': 'w-20', 'align': 'text-right'},
            {'key': 'unique_outlinks', 'label': 'Unique Outlinks', 'width': 'w-24', 'align': 'text-right'},
            {'key': 'response_time', 'label': 'Response Time', 'width': 'w-24', 'align': 'text-right'},
            {'key': 'redirect_url', 'label': 'Redirect URL', 'width': 'min-w-[200px]'},
            {'key': 'language', 'label': 'Language', 'width': 'w-20'},
            {'key': 'http_version', 'label': 'HTTP Version', 'width': 'w-24'},
            {'key': 'mobile_alt_link', 'label': 'Mobile Alt Link', 'width': 'min-w-[200px]'},
            {'key': 'crawl_timestamp', 'label': 'Crawl Timestamp', 'width': 'w-36'}
        ]
    },

    'external': {
        'label': 'External',
        'columns': [
            {'key': 'row', 'label': '#', 'width': 'w-12', 'align': 'text-center'},
            {'key': 'url', 'label': 'Address', 'width': 'min-w-[400px]'},
            {'key': 'content_type', 'label': 'Content Type', 'width': 'w-32'},
            {'key': 'status_code', 'label': 'Status Code', 'width': 'w-24', 'align': 'text-center'},
            {'key': 'status', 'label': 'Status', 'width': 'w-28'},
            {'key': 'crawl_depth', 'label': 'Crawl Depth', 'width': 'w-24', 'align': 'text-right'},
            {'key': 'inlinks_count', 'label': 'Inlinks', 'width': 'w-20', 'align': 'text-right'}
        ]
    },

    'response_codes': {
        'label': 'Response Codes',
        'columns': [
            {'key': 'row', 'label': '#', 'width': 'w-12', 'align': 'text-center'},
            {'key': 'url', 'label': 'Address', 'width': 'min-w-[360px]'},
            {'key': 'content_type', 'label': 'Content Type', 'width': 'w-32'},
            {'key': 'status_code', 'label': 'Status Code', 'width': 'w-24', 'align': 'text-center'},
            {'key': 'status', 'label': 'Status', 'width': 'w-28'},
            {'key': 'indexability', 'label': 'Indexability', 'width': 'w-28'},
            {'key': 'indexability_status', 'label': 'Indexability Status', 'width': 'w-32'},
            {'key': 'inlinks_count', 'label': 'Inlinks', 'width': 'w-20', 'align': 'text-right'},
            {'key': 'response_time', 'label': 'Response Time', 'width': 'w-24', 'align': 'text-right'},
            {'key': 'redirect_url', 'label': 'Redirect URL', 'width': 'min-w-[240px]'},
            {'key': 'redirect_type', 'label': 'Redirect Type', 'width': 'w-28'}
        ]
    },

    'page_titles': {
        'label': 'Page Titles',
        'columns': [
            {'key': 'row', 'label': '#', 'width': 'w-12', 'align': 'text-center'},
            {'key': 'url', 'label': 'Address', 'width': 'min-w-[300px]'},
            {'key': 'occurrences', 'label': 'Occurrences', 'width': 'w-24', 'align': 'text-right'},
            {'key': 'title', 'label': 'Title 1', 'width': 'min-w-[280px]'},
            {'key': 'title_pixel_width', 'label': 'Title 1 Pixel Width', 'width': 'w-32', 'align': 'text-right'},
            {'key': 'indexability', 'label': 'Indexability', 'width': 'w-28'},
            {'key': 'indexability_status', 'label': 'Indexability Status', 'width': 'w-32'}
        ]
    },

    'meta_description': {
        'label': 'Meta Description',
        'columns': [
            {'key': 'row', 'label': '#', 'width': 'w-12', 'align': 'text-center'},
            {'key': 'url', 'label': 'Address', 'width': 'min-w-[300px]'},
            {'key': 'occurrences', 'label': 'Occurrences', 'width': 'w-24', 'align': 'text-right'},
            {'key': 'meta_description', 'label': 'Meta Description 1', 'width': 'min-w-[300px]'},
            {'key': 'meta_description_length', 'label': 'Meta Desc 1 Length', 'width': 'w-28', 'align': 'text-right'},
            {'key': 'meta_desc_pixel_width', 'label': 'Meta Desc 1 Pixel Width', 'width': 'w-36', 'align': 'text-right'},
            {'key': 'indexability', 'label': 'Indexability', 'width': 'w-28'},
            {'key': 'indexability_status', 'label': 'Indexability Status', 'width': 'w-32'}
        ]
    },

    'meta_keywords': {
        'label': 'Meta Keywords',
        'columns': [
            {'key': 'row', 'label': '#', 'width': 'w-12', 'align': 'text-center'},
            {'key': 'url', 'label': 'Address', 'width': 'min-w-[300px]'},
            {'key': 'occurrences', 'label': 'Occurrences', 'width': 'w-24', 'align': 'text-right'},
            {'key': 'meta_keywords', 'label': 'Meta Keywords 1', 'width': 'min-w-[300px]'},
            {'key': 'meta_keywords_length', 'label': 'Meta Keywords 1 Length', 'width': 'w-32', 'align': 'text-right'},
            {'key': 'indexability', 'label': 'Indexability', 'width': 'w-28'},
            {'key': 'indexability_status', 'label': 'Indexability Status', 'width': 'w-32'}
        ]
    },

    'h1': {
        'label': 'H1',
        'columns': [
            {'key': 'row', 'label': '#', 'width': 'w-12', 'align': 'text-center'},
            {'key': 'url', 'label': 'Address', 'width': 'min-w-[300px]'},
            {'key': 'occurrences', 'label': 'Occurrences', 'width': 'w-24', 'align': 'text-right'},
            {'key': 'h1_1', 'label': 'H1-1', 'width': 'min-w-[240px]'},
            {'key': 'h1_1_length', 'label': 'H1-1 Length', 'width': 'w-24', 'align': 'text-right'},
            {'key': 'indexability', 'label': 'Indexability', 'width': 'w-28'},
            {'key': 'indexability_status', 'label': 'Indexability Status', 'width': 'w-32'}
        ]
    },

    'h2': {
        'label': 'H2',
        'columns': [
            {'key': 'row', 'label': '#', 'width': 'w-12', 'align': 'text-center'},
            {'key': 'url', 'label': 'Address', 'width': 'min-w-[300px]'},
            {'key': 'occurrences', 'label': 'Occurrences', 'width': 'w-24', 'align': 'text-right'},
            {'key': 'h2_1', 'label': 'H2-1', 'width': 'min-w-[240px]'},
            {'key': 'h2_1_length', 'label': 'H2-1 Length', 'width': 'w-24', 'align': 'text-right'},
            {'key': 'indexability', 'label': 'Indexability', 'width': 'w-28'},
            {'key': 'indexability_status', 'label': 'Indexability Status', 'width': 'w-32'}
        ]
    },

    'content': {
        'label': 'Content',
        'columns': [
            {'key': 'row', 'label': '#', 'width': 'w-12', 'align': 'text-center'},
            {'key': 'url', 'label': 'Address', 'width': 'min-w-[300px]'},
            {'key': 'word_count', 'label': 'Word Count', 'width': 'w-24', 'align': 'text-right'},
            {'key': 'sentence_count', 'label': 'Sentence Count', 'width': 'w-28', 'align': 'text-right'},
            {'key': 'avg_words_per_sentence', 'label': 'Avg Words/Sentence', 'width': 'w-32', 'align': 'text-right'},
            {'key': 'flesch_reading_ease', 'label': 'Flesch Reading Ease', 'width': 'w-32', 'align': 'text-right'},
            {'key': 'readability_label', 'label': 'Readability', 'width': 'w-28'},
            {'key': 'closest_duplicate_url', 'label': 'Near Duplicate Match', 'width': 'min-w-[240px]'},
            {'key': 'near_duplicate_count', 'label': 'No. Near Duplicates', 'width': 'w-32', 'align': 'text-right'},
            {'key': 'closest_semantic_url', 'label': 'Closest Similar Address', 'width': 'min-w-[240px]'}
        ]
    },

    'images': {
        'label': 'Images',
        'columns': [
            {'key': 'row', 'label': '#', 'width': 'w-12', 'align': 'text-center'},
            {'key': 'url', 'label': 'Address', 'width': 'min-w-[360px]'},
            {'key': 'content_type', 'label': 'Content Type', 'width': 'w-28'},
            {'key': 'size_bytes', 'label': 'Size', 'width': 'w-20', 'align': 'text-right'},
            {'key': 'img_inlinks', 'label': 'Img Inlinks No.', 'width': 'w-28', 'align': 'text-right'},
            {'key': 'indexability', 'label': 'Indexability', 'width': 'w-28'},
            {'key': 'indexability_status', 'label': 'Indexability Status', 'width': 'w-32'},
            {'key': 'dimensions', 'label': 'Dimensions', 'width': 'w-28'}
        ]
    },

    'canonicals': {
        'label': 'Canonicals',
        'columns': [
            {'key': 'row', 'label': '#', 'width': 'w-12', 'align': 'text-center'},
            {'key': 'url', 'label': 'Address', 'width': 'min-w-[300px]'},
            {'key': 'occurrences', 'label': 'Occurrences', 'width': 'w-24', 'align': 'text-right'},
            {'key': 'canonical_status', 'label': 'Canonical Status', 'width': 'w-32'},
            {'key': 'indexability', 'label': 'Indexability', 'width': 'w-28'},
            {'key': 'indexability_status', 'label': 'Indexability Status', 'width': 'w-32'},
            {'key': 'canonical_url', 'label': 'Canonical Link Element 1', 'width': 'min-w-[260px]'},
            {'key': 'http_canonical', 'label': 'HTTP Canonical', 'width': 'min-w-[240px]'},
            {'key': 'robots_meta', 'label': 'Meta Robots 1', 'width': 'min-w-[180px]'}
        ]
    },

    'pagination': {
        'label': 'Pagination',
        'columns': [
            {'key': 'row', 'label': '#', 'width': 'w-12', 'align': 'text-center'},
            {'key': 'url', 'label': 'Address', 'width': 'min-w-[300px]'},
            {'key': 'indexability', 'label': 'Indexability', 'width': 'w-28'},
            {'key': 'indexability_status', 'label': 'Indexability Status', 'width': 'w-32'},
            {'key': 'canonical_url', 'label': 'Canonical Link Element 1', 'width': 'min-w-[240px]'},
            {'key': 'http_canonical', 'label': 'HTTP Canonical', 'width': 'min-w-[200px]'},
            {'key': 'robots_meta', 'label': 'Meta Robots 1', 'width': 'min-w-[160px]'},
            {'key': 'x_robots_tag', 'label': 'X-Robots-Tag 1', 'width': 'min-w-[160px]'}
        ]
    },

    'hreflang': {
        'label': 'Hreflang',
        'columns': [
            {'key': 'row', 'label': '#', 'width': 'w-12', 'align': 'text-center'},
            {'key': 'url', 'label': 'Address', 'width': 'min-w-[280px]'},
            {'key': 'title', 'label': 'Title 1', 'width': 'min-w-[200px]'},
            {'key': 'hreflang_occurrence', 'label': 'Occurrence', 'width': 'w-24', 'align': 'text-right'},
            {'key': 'html_hreflang_1', 'label': 'HTML Hreflang 1', 'width': 'w-28', 'dynamic': True},
            {'key': 'html_hreflang_1_url', 'label': 'HTML Hreflang 1 URL', 'width': 'min-w-[200px]', 'dynamic': True},
            {'key': 'indexability', 'label': 'Indexability', 'width': 'w-28'},
            {'key': 'indexability_status', 'label': 'Indexability Status', 'width': 'w-32'},
            {'key': 'sitemap_hreflang_1', 'label': 'Sitemap Hreflang 1', 'width': 'w-28', 'dynamic': True},
            {'key': 'sitemap_hreflang_1_url', 'label': 'Sitemap Hreflang 1 URL', 'width': 'min-w-[200px]', 'dynamic': True}
        ]
    },

    'javascript': {
        'label': 'JavaScript',
        'columns': [
            {'key': 'row', 'label': '#', 'width': 'w-12', 'align': 'text-center'},
            {'key': 'url', 'label': 'Address', 'width': 'min-w-[280px]'},
            {'key': 'status_code', 'label': 'Status Code', 'width': 'w-20', 'align': 'text-center'},
            {'key': 'status', 'label': 'Status', 'width': 'w-24'},
            {'key': 'html_word_count', 'label': 'HTML Word Count', 'width': 'w-28', 'align': 'text-right'},
            {'key': 'rendered_word_count', 'label': 'Rendered Word Count', 'width': 'w-32', 'align': 'text-right'},
            {'key': 'word_count_change', 'label': 'Word Count Change', 'width': 'w-28', 'align': 'text-right'},
            {'key': 'js_word_count_pct', 'label': 'JS Word Count %', 'width': 'w-28', 'align': 'text-right'},
            {'key': 'html_title', 'label': 'HTML Title', 'width': 'min-w-[180px]'},
            {'key': 'rendered_title', 'label': 'Rendered Title', 'width': 'min-w-[180px]'},
            {'key': 'html_h1', 'label': 'HTML H1', 'width': 'min-w-[160px]'},
            {'key': 'rendered_h1', 'label': 'Rendered H1', 'width': 'min-w-[160px]'},
            {'key': 'html_meta_description', 'label': 'HTML Meta Desc', 'width': 'min-w-[180px]'},
            {'key': 'rendered_meta_description', 'label': 'Rendered Meta Desc', 'width': 'min-w-[180px]'},
            {'key': 'html_canonical', 'label': 'HTML Canonical', 'width': 'min-w-[180px]'},
            {'key': 'rendered_canonical', 'label': 'Rendered Canonical', 'width': 'min-w-[180px]'},
            {'key': 'unique_inlinks', 'label': 'Unique Inlinks', 'width': 'w-24', 'align': 'text-right'},
            {'key': 'unique_js_inlinks', 'label': 'Unique JS Inlinks', 'width': 'w-28', 'align': 'text-right'},
            {'key': 'unique_outlinks', 'label': 'Unique Outlinks', 'width': 'w-24', 'align': 'text-right'},
            {'key': 'unique_js_outlinks', 'label': 'Unique JS Outlinks', 'width': 'w-28', 'align': 'text-right'},
            {'key': 'unique_external_outlinks', 'label': 'Ext Outlinks', 'width': 'w-24', 'align': 'text-right'},
            {'key': 'unique_external_js_outlinks', 'label': 'Ext JS Outlinks', 'width': 'w-28', 'align': 'text-right'},
            {'key': 'html_meta_robots', 'label': 'HTML Meta Robots', 'width': 'w-32'},
            {'key': 'rendered_meta_robots', 'label': 'Rendered Meta Robots', 'width': 'w-36'},
            {'key': 'pretty_url', 'label': 'Pretty URL', 'width': 'min-w-[200px]'},
            {'key': 'ugly_url', 'label': 'Ugly URL', 'width': 'min-w-[200px]'},
            {'key': 'js_errors', 'label': 'JS Error', 'width': 'w-20', 'align': 'text-right'},
            {'key': 'js_warnings', 'label': 'JS Warning', 'width': 'w-20', 'align': 'text-right'},
            {'key': 'js_info', 'label': 'JS Info', 'width': 'w-20', 'align': 'text-right'},
            {'key': 'js_debug', 'label': 'JS Debug', 'width': 'w-20', 'align': 'text-right'},
            {'key': 'js_issues', 'label': 'JS Issue', 'width': 'w-20', 'align': 'text-right'}
        ]
    },

    'links': {
        'label': 'Links',
        'columns': [
            {'key': 'row', 'label': '#', 'width': 'w-12', 'align': 'text-center'},
            {'key': 'url', 'label': 'Address', 'width': 'min-w-[300px]'},
            {'key': 'indexability', 'label': 'Indexability', 'width': 'w-28'},
            {'key': 'indexability_status', 'label': 'Indexability Status', 'width': 'w-32'},
            {'key': 'crawl_depth', 'label': 'Crawl Depth', 'width': 'w-24', 'align': 'text-right'},
            {'key': 'link_score', 'label': 'Link Score', 'width': 'w-24', 'align': 'text-right'},
            {'key': 'inlinks_count', 'label': 'Inlinks', 'width': 'w-20', 'align': 'text-right'},
            {'key': 'unique_inlinks', 'label': 'Unique Inlinks', 'width': 'w-24', 'align': 'text-right'},
            {'key': 'unique_js_inlinks', 'label': 'Unique JS Inlinks', 'width': 'w-28', 'align': 'text-right'},
            {'key': 'inlinks_pct', 'label': '% of Total', 'width': 'w-20', 'align': 'text-right'},
            {'key': 'outlinks_count', 'label': 'Outlinks', 'width': 'w-20', 'align': 'text-right'},
            {'key': 'unique_outlinks', 'label': 'Unique Outlinks', 'width': 'w-24', 'align': 'text-right'},
            {'key': 'unique_js_outlinks', 'label': 'Unique JS Outlinks', 'width': 'w-28', 'align': 'text-right'},
            {'key': 'external_outlinks', 'label': 'Ext Outlinks', 'width': 'w-24', 'align': 'text-right'},
            {'key': 'unique_external_outlinks', 'label': 'Unique Ext Outlinks', 'width': 'w-28', 'align': 'text-right'},
            {'key': 'unique_external_js_outlinks', 'label': 'Unique Ext JS Outlinks', 'width': 'w-32', 'align': 'text-right'}
        ]
    },

    'structured_data': {
        'label': 'Structured Data',
        'columns': [
            {'key': 'row', 'label': '#', 'width': 'w-12', 'align': 'text-center'},
            {'key': 'url', 'label': 'Address', 'width': 'min-w-[280px]'},
            {'key': 'sd_errors', 'label': 'Errors', 'width': 'w-20', 'align': 'text-right'},
            {'key': 'sd_warnings', 'label': 'Warnings', 'width': 'w-20', 'align': 'text-right'},
            {'key': 'rich_result_errors', 'label': 'Rich Result Errors', 'width': 'w-28', 'align': 'text-right'},
            {'key': 'rich_result_warnings', 'label': 'Rich Result Warnings', 'width': 'w-32', 'align': 'text-right'},
            {'key': 'rich_result_features', 'label': 'Rich Result Features', 'width': 'min-w-[160px]'},
            {'key': 'sd_feature_1', 'label': 'Feature-1', 'width': 'w-28'},
            {'key': 'sd_total_types', 'label': 'Total Types', 'width': 'w-24', 'align': 'text-right'},
            {'key': 'sd_unique_types', 'label': 'Unique Types', 'width': 'w-24', 'align': 'text-right'},
            {'key': 'sd_type_1', 'label': 'Type-1', 'width': 'w-28'},
            {'key': 'indexability', 'label': 'Indexability', 'width': 'w-28'},
            {'key': 'indexability_status', 'label': 'Indexability Status', 'width': 'w-32'}
        ]
    },

    'sitemaps': {
        'label': 'Sitemaps',
        'columns': [
            {'key': 'row', 'label': '#', 'width': 'w-12', 'align': 'text-center'},
            {'key': 'url', 'label': 'Address', 'width': 'min-w-[360px]'},
            {'key': 'content_type', 'label': 'Content Type', 'width': 'w-32'},
            {'key': 'status_code', 'label': 'Status Code', 'width': 'w-24', 'align': 'text-center'},
            {'key': 'status', 'label': 'Status', 'width': 'w-28'},
            {'key': 'indexability', 'label': 'Indexability', 'width': 'w-28'},
            {'key': 'indexability_status', 'label': 'Indexability Status', 'width': 'w-32'}
        ]
    },

    'pagespeed': {
        'label': 'PageSpeed',
        'columns': [
            {'key': 'row', 'label': '#', 'width': 'w-12', 'align': 'text-center'},
            {'key': 'url', 'label': 'Address', 'width': 'min-w-[360px]'},
            {'key': 'psi_status', 'label': 'PSI Request Status', 'width': 'w-32'}
        ]
    },

    'mobile': {
        'label': 'Mobile',
        'columns': [
            {'key': 'row', 'label': '#', 'width': 'w-12', 'align': 'text-center'},
            {'key': 'url', 'label': 'Address', 'width': 'min-w-[360px]'},
            {'key': 'psi_status', 'label': 'PSI Request', 'width': 'w-32'},
            {'key': 'mobile_alt_link', 'label': 'Mobile Alternate Link', 'width': 'min-w-[280px]'}
        ]
    },

    'accessibility': {
        'label': 'Accessibility',
        'columns': [
            {'key': 'row', 'label': '#', 'width': 'w-12', 'align': 'text-center'},
            {'key': 'url', 'label': 'Address', 'width': 'min-w-[280px]'},
            {'key': 'content_type', 'label': 'Content Type', 'width': 'w-28'},
            {'key': 'status_code', 'label': 'Status Code', 'width': 'w-20', 'align': 'text-center'},
            {'key': 'status', 'label': 'Status', 'width': 'w-24'},
            {'key': 'indexability', 'label': 'Indexability', 'width': 'w-28'},
            {'key': 'indexability_status', 'label': 'Indexability Status', 'width': 'w-32'},
            {'key': 'accessibility_violations_total', 'label': 'All Violations', 'width': 'w-24', 'align': 'text-right'},
            {'key': 'accessibility_best_practice', 'label': 'Best Practice', 'width': 'w-24', 'align': 'text-right'},
            {'key': 'accessibility_wcag_2_0_a', 'label': 'WCAG 2.0 A', 'width': 'w-24', 'align': 'text-right'},
            {'key': 'accessibility_wcag_2_0_aa', 'label': 'WCAG 2.0 AA', 'width': 'w-24', 'align': 'text-right'},
            {'key': 'accessibility_wcag_2_0_aaa', 'label': 'WCAG 2.0 AAA', 'width': 'w-24', 'align': 'text-right'},
            {'key': 'accessibility_wcag_2_1_aa', 'label': 'WCAG 2.1 AA', 'width': 'w-28', 'align': 'text-right'},
            {'key': 'accessibility_wcag_2_2_aa', 'label': 'WCAG 2.2 AA', 'width': 'w-28', 'align': 'text-right'},
            {'key': 'psi_status', 'label': 'PSI Request Status', 'width': 'w-32'}
        ]
    },

    'amp': {
        'label': 'AMP',
        'columns': [
            {'key': 'row', 'label': '#', 'width': 'w-12', 'align': 'text-center'},
            {'key': 'url', 'label': 'Address', 'width': 'min-w-[360px]'},
            {'key': 'content_type', 'label': 'Content Type', 'width': 'w-28'},
            {'key': 'status_code', 'label': 'Status Code', 'width': 'w-24', 'align': 'text-center'},
            {'key': 'status', 'label': 'Status', 'width': 'w-28'},
            {'key': 'amp_html_link', 'label': 'AMP HTML Link', 'width': 'min-w-[280px]'},
            {'key': 'indexability', 'label': 'Indexability', 'width': 'w-28'},
            {'key': 'indexability_status', 'label': 'Indexability Status', 'width': 'w-32'}
        ]
    }
}

# -------------------------------------------------------------------------
# Helpers
# -------------------------------------------------------------------------

def classify_page_type(url: str, depth: int) -> str:
    if depth == 0:
        return 'Home Page'
    u = url.lower()
    if any(p in u for p in ['/product', '/item', '/p/', '/dp/']):
        return 'Product Page'
    if any(c in u for c in ['/category', '/collections', '/c/', '/catalog']):
        return 'Category Page'
    if any(b in u for b in ['/blog', '/post', '/article', '/news']):
        return 'Blog / Article'
    if any(s in u for s in ['/search', '?q=', '?s=']):
        return 'Search Page'
    if any(x in u for x in ['/cart', '/checkout', '/basket', '/order']):
        return 'Cart / Checkout'
    if any(a in u for a in ['/account', '/login', '/register', '/profile']):
        return 'Account / Auth'
    if any(i in u for i in ['/about', '/contact', '/privacy', '/terms', '/help', '/faq', '/policy']):
        return 'Informational / Utility'
    return 'Content Page'

def determine_asset_mime(url: str) -> str:
    u = url.lower().split('?')[0]
    if any(u.endswith(ext) for ext in ['.jpg', '.jpeg']): return 'image/jpeg'
    if u.endswith('.png'): return 'image/png'
    if u.endswith('.webp'): return 'image/webp'
    if u.endswith('.svg'): return 'image/svg+xml'
    if u.endswith('.gif'): return 'image/gif'
    if u.endswith('.css'): return 'text/css'
    if u.endswith('.js'): return 'application/javascript'
    if u.endswith('.pdf'): return 'application/pdf'
    if u.endswith('.xml'): return 'application/xml'
    if u.endswith('.json'): return 'application/json'
    if any(u.endswith(ext) for ext in ['.woff', '.woff2', '.ttf']): return 'font/woff2'
    return 'text/html; charset=utf-8'

def parse_cookies_json(raw_cookies: Any) -> List[Dict[str, Any]]:
    if not raw_cookies:
        return []
    parsed = []
    data = raw_cookies
    if isinstance(raw_cookies, str):
        try:
            data = json.loads(raw_cookies)
        except Exception:
            data = [raw_cookies]
    if isinstance(data, dict):
        data = [data]
    if isinstance(data, list):
        for item in data:
            if isinstance(item, dict):
                parsed.append({
                    'name': item.get('name') or item.get('key') or '',
                    'value': item.get('value') or '',
                    'domain': item.get('domain') or '',
                    'path': item.get('path') or '/',
                    'expires': item.get('expires') or item.get('max_age') or '',
                    'secure': bool(item.get('secure', False)),
                    'httponly': bool(item.get('httponly', item.get('http_only', False))),
                    'samesite': item.get('samesite') or item.get('same_site') or ''
                })
            elif isinstance(item, str) and '=' in item:
                parts = [p.strip() for p in item.split(';')]
                first = parts[0].split('=', 1)
                c_dict = {
                    'name': first[0],
                    'value': first[1] if len(first) > 1 else '',
                    'domain': '', 'path': '/', 'expires': '',
                    'secure': False, 'httponly': False, 'samesite': ''
                }
                for p in parts[1:]:
                    pl = p.lower()
                    if pl.startswith('domain='): c_dict['domain'] = p.split('=', 1)[1]
                    elif pl.startswith('path='): c_dict['path'] = p.split('=', 1)[1]
                    elif pl.startswith('expires='): c_dict['expires'] = p.split('=', 1)[1]
                    elif pl == 'secure': c_dict['secure'] = True
                    elif pl == 'httponly': c_dict['httponly'] = True
                    elif pl.startswith('samesite='): c_dict['samesite'] = p.split('=', 1)[1]
                parsed.append(c_dict)
    return parsed

# -------------------------------------------------------------------------
# Core Enrichment: enrich_base_page_data
# -------------------------------------------------------------------------

def enrich_base_page_data(raw_pages: List[Dict[str, Any]], audit: Optional[Dict[str, Any]],
                          raw_issues: List[Dict[str, Any]], all_links: List[Dict[str, Any]],
                          all_images: List[Dict[str, Any]], all_sd: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Enriches raw database page records with link metrics, counts, and classification.
    Produces comprehensive page rows covering all 48 database columns and virtual asset rows.
    """
    inlinks_map: Dict[str, int] = {}
    outlinks_map: Dict[int, int] = {}
    extlinks_map: Dict[int, int] = {}
    parent_map: Dict[str, str] = {}

    for l in (all_links or []):
        target = (l.get('target_url') or '').rstrip('/')
        src = l.get('source_url') or ''
        pid = l.get('source_page_id')
        if l.get('is_internal', True):
            inlinks_map[target] = inlinks_map.get(target, 0) + 1
            if target and target not in parent_map and src:
                parent_map[target] = src
            if pid:
                outlinks_map[pid] = outlinks_map.get(pid, 0) + 1
        else:
            if pid:
                extlinks_map[pid] = extlinks_map.get(pid, 0) + 1

    img_map: Dict[int, int] = {}
    for img in (all_images or []):
        pid = img.get('page_id')
        if pid:
            img_map[pid] = img_map.get(pid, 0) + 1

    sd_map: Dict[int, int] = {}
    for s in (all_sd or []):
        pid = s.get('page_id')
        if pid:
            sd_map[pid] = sd_map.get(pid, 0) + 1

    issues_map: Dict[int, List[Dict[str, Any]]] = {}
    for i in (raw_issues or []):
        pid = i.get('page_id')
        if pid:
            issues_map.setdefault(pid, []).append(i)

    audit_domain = urlparse(audit.get('url', '') if audit else '').netloc

    seen_urls = set()
    enriched: List[Dict[str, Any]] = []

    # 1. Crawled Pages
    for p in (raw_pages or []):
        pid = p['id']
        url = p.get('url') or ''
        seen_urls.add(url)
        norm_url = url.rstrip('/')
        depth = p.get('crawl_depth') if p.get('crawl_depth') is not None else 0
        sc = p.get('status_code') or 200
        ct = p.get('content_type') or 'text/html; charset=utf-8'
        mime = p.get('mime_type') or ct.split(';')[0].strip()
        url_domain = urlparse(url).netloc
        url_type = 'Internal' if (not url_domain or url_domain == audit_domain) else 'External'

        canonical = (p.get('canonical_url') or '').strip()
        http_canonical = (p.get('http_canonical') or '').strip()
        h = p.get('content_hash') or ''
        length = p.get('html_size') or p.get('size_bytes') or 0

        # Indexability determination
        if 400 <= sc < 500:
            idx = "Non-Indexable"
            idx_status = f"Client Error ({sc})"
        elif sc >= 500:
            idx = "Non-Indexable"
            idx_status = f"Server Error ({sc})"
        elif 300 <= sc < 400:
            idx = "Non-Indexable"
            idx_status = f"Redirect ({sc})"
        elif canonical and canonical.rstrip('/') != norm_url:
            idx = "Non-Indexable"
            idx_status = "Canonicalised"
        elif 'noindex' in (p.get('robots_meta') or '').lower() or 'noindex' in (p.get('x_robots_tag') or '').lower():
            idx = "Non-Indexable"
            idx_status = "Noindex"
        else:
            idx = "Indexable" if p.get('is_indexable', True) else "Non-Indexable"
            idx_status = "OK" if idx == "Indexable" else "Blocked"

        # Canonical health determination
        effective_canonical = canonical or http_canonical
        if not effective_canonical or effective_canonical == '—':
            canonical_status = "Missing"
        elif effective_canonical.rstrip('/') == norm_url:
            canonical_status = "Self-Referential"
        else:
            canon_domain = urlparse(effective_canonical).netloc
            if canon_domain and canon_domain != url_domain and canon_domain != audit_domain:
                canonical_status = "Cross-Domain"
            else:
                canonical_status = "Canonicalised"

        parent = p.get('parent_url') or parent_map.get(norm_url) or (audit.get('url') if audit and depth == 0 else '')
        if depth == 0 and not parent and audit:
            parent = audit.get('url') or 'Direct Seed'

        page_issues = issues_map.get(pid, [])
        pg_type = p.get('page_type') or classify_page_type(url, depth)

        # Calculate folder depth
        path_segments = [s for s in urlparse(url).path.split('/') if s]
        f_depth = p.get('folder_depth') if p.get('folder_depth') is not None else len(path_segments)

        resp_ms = p.get('response_time_ms') or 0.0
        resp_sec_str = f"{round(resp_ms / 1000.0, 2):.2f}s" if resp_ms > 0 else "0.00s"

        title_val = p.get('title') or ''
        meta_desc_val = p.get('meta_description') or ''
        meta_kw_val = p.get('meta_keywords') or ''
        h1_val = p.get('h1') or ''

        enriched.append({
            'id': pid,
            'url': url,
            'url_type': url_type,
            'status_code': sc,
            'status': "OK" if sc == 200 else f"HTTP {sc}",
            'content_type': ct,
            'mime_type': mime,
            'title': title_val,
            'title_length': p.get('title_length') if p.get('title_length') is not None else len(title_val),
            'title_pixel_width': p.get('title_pixel_width') or 0,
            'meta_description': meta_desc_val,
            'meta_description_length': p.get('meta_description_length') if p.get('meta_description_length') is not None else len(meta_desc_val),
            'meta_desc_pixel_width': p.get('meta_desc_pixel_width') or 0,
            'meta_keywords': meta_kw_val,
            'meta_keywords_length': p.get('meta_keywords_length') if p.get('meta_keywords_length') is not None else len(meta_kw_val),
            'h1': h1_val,
            'h1_1': h1_val,
            'h1_1_length': len(h1_val),
            'h1_count': p.get('h1_count') or (1 if h1_val else 0),
            'h1_length': p.get('h1_length') or len(h1_val),
            'h2_count': p.get('h2_count') or 0,
            'h2_length': p.get('h2_length') or 0,
            'canonical_url': canonical or '—',
            'http_canonical': http_canonical or '—',
            'canonical_status': canonical_status,
            'internal_pagerank': round(float(p.get('internal_pagerank') or 0.0), 6),
            'robots_directive': p.get('robots_meta') or ('index, follow' if idx == 'Indexable' else 'noindex, follow'),
            'robots_meta': p.get('robots_meta') or '',
            'x_robots_tag': p.get('x_robots_tag') or '',
            'indexability': idx,
            'indexability_status': idx_status,
            'content_hash': h,
            'length': length,
            'size_bytes': p.get('size_bytes') or length,
            'transferred_bytes': p.get('transferred_bytes') or length,

            'total_transferred_bytes': p.get('total_transferred_bytes') or length,
            'url_encoded_address': urllib.parse.quote(url, safe=''),
            'crawl_depth': depth,
            'folder_depth': f_depth,
            'parent_url': parent,
            'inlinks_count': inlinks_map.get(norm_url, 0) or p.get('unique_inlinks') or 0,
            'unique_inlinks': p.get('unique_inlinks') or inlinks_map.get(norm_url, 0),
            'unique_js_inlinks': 0,
            'outlinks_count': outlinks_map.get(pid, 0) or p.get('unique_outlinks') or 0,
            'unique_outlinks': p.get('unique_outlinks') or outlinks_map.get(pid, 0),
            'unique_js_outlinks': 0,
            'external_links_count': extlinks_map.get(pid, 0) or p.get('unique_external_outlinks') or 0,
            'external_outlinks': extlinks_map.get(pid, 0) or p.get('unique_external_outlinks') or 0,
            'unique_external_outlinks': p.get('unique_external_outlinks') or extlinks_map.get(pid, 0),
            'unique_external_js_outlinks': 0,
            'link_score': p.get('link_score') or 0.0,
            'images_count': img_map.get(pid, 0),
            'schema_count': sd_map.get(pid, 0),
            'response_time_ms': resp_ms,
            'response_time': resp_sec_str,
            'html_size': length,
            'redirect_url': p.get('redirect_url') or '',
            'redirect_type': p.get('redirect_type') or (f"HTTP {sc}" if 300 <= sc < 400 else ''),
            'final_url': p.get('redirect_url') or url,
            'language': p.get('language') or 'en',
            'http_version': p.get('http_version') or 'HTTP/1.1',
            'mobile_alt_link': p.get('mobile_alt_link') or '',
            'amp_html_link': p.get('amp_html_link') or '',
            'page_type': pg_type,
            'issues': page_issues,
            'issues_count': len(page_issues),
            'word_count': p.get('word_count') or 0,
            'sentence_count': p.get('sentence_count') or 0,
            'avg_words_per_sentence': p.get('avg_words_per_sentence') or 0.0,
            'text_ratio': p.get('text_ratio') or 0.0,
            'flesch_reading_ease': p.get('flesch_reading_ease') or 0.0,
            'readability_label': p.get('readability_label') or 'Standard',
            'crawl_timestamp': p.get('crawl_timestamp') or p.get('created_at') or '',
            'closest_duplicate_url': p.get('closest_duplicate_url') or '',
            'near_duplicate_count': p.get('near_duplicate_count') or 0,
            'closest_semantic_url': p.get('closest_duplicate_url') or '',
            'psi_status': p.get('psi_status') or 'Not Requested',
            'accessibility_violations_total': p.get('accessibility_violations_total') or 0,
            'accessibility_best_practice': p.get('accessibility_best_practice') or 0,
            'accessibility_wcag_2_0_a': p.get('accessibility_wcag_2_0_a') or 0,
            'accessibility_wcag_2_0_aa': p.get('accessibility_wcag_2_0_aa') or 0,
            'accessibility_wcag_2_0_aaa': p.get('accessibility_wcag_2_0_aaa') or 0,
            'accessibility_wcag_2_1_aa': p.get('accessibility_wcag_2_1_aa') or 0,
            'accessibility_wcag_2_2_aa': p.get('accessibility_wcag_2_2_aa') or 0,
            'html_word_count': p.get('html_word_count') or p.get('word_count') or 0,
            'rendered_word_count': p.get('rendered_word_count') or p.get('word_count') or 0,
            'word_count_change': p.get('word_count_change') or 0,
            'js_word_count_pct': p.get('js_word_count_pct') or 0.0,
            'html_title': p.get('html_title') or title_val,
            'rendered_title': p.get('rendered_title') or title_val,
            'html_h1': p.get('html_h1') or h1_val,
            'rendered_h1': p.get('rendered_h1') or h1_val,
            'html_meta_description': p.get('html_meta_description') or meta_desc_val,
            'rendered_meta_description': p.get('rendered_meta_description') or meta_desc_val,
            'html_canonical': p.get('html_canonical') or canonical or '',
            'rendered_canonical': p.get('rendered_canonical') or canonical or '',
            'html_meta_robots': p.get('html_meta_robots') or p.get('robots_meta') or '',
            'rendered_meta_robots': p.get('rendered_meta_robots') or p.get('robots_meta') or '',
            'pretty_url': p.get('pretty_url') or (url.split('?')[0] if '?' in url else url),
            'ugly_url': p.get('ugly_url') or (url if '?' in url else ''),
            'js_errors': p.get('js_errors') or 0,
            'js_warnings': p.get('js_warnings') or 0,
            'js_info': p.get('js_info') or 0,
            'js_debug': p.get('js_debug') or 0,
            'js_issues': p.get('js_issues') or ''
        })

    # 2. Map Discovered Images
    virtual_id = 100000
    for img in (all_images or []):
        src = img.get('src')
        if not src or src.startswith('data:') or src in seen_urls:
            continue
        seen_urls.add(src)
        virtual_id += 1
        img_domain = urlparse(src).netloc
        url_type = 'Internal' if (not img_domain or img_domain == audit_domain) else 'External'
        ct = determine_asset_mime(src)
        sz = img.get('file_size') or 0
        w, h_dim = img.get('width'), img.get('height')
        dim_str = f"{w}x{h_dim}" if (w and h_dim) else '—'

        enriched.append({
            'id': virtual_id,
            'url': src,
            'url_type': url_type,
            'status_code': 200,
            'status': "OK",
            'content_type': ct,
            'mime_type': ct.split(';')[0].strip(),
            'title': img.get('alt_text') or '',
            'meta_description': '',
            'h1': '',
            'canonical_url': '—',
            'http_canonical': '—',
            'robots_directive': '—',
            'indexability': "Non-Indexable",
            'indexability_status': "Resource / Image",
            'content_hash': '',
            'length': sz,
            'size_bytes': sz,
            'transferred_bytes': sz,
            'total_transferred_bytes': sz,
            'url_encoded_address': urllib.parse.quote(src, safe=''),
            'crawl_depth': 1,
            'folder_depth': len([s for s in urlparse(src).path.split('/') if s]),
            'parent_url': audit.get('url', '') if audit else '',
            'inlinks_count': 1,
            'unique_inlinks': 1,
            'outlinks_count': 0,
            'unique_outlinks': 0,
            'external_links_count': 0,
            'external_outlinks': 0,
            'unique_external_outlinks': 0,
            'link_score': 0.0,
            'images_count': 0,
            'schema_count': 0,
            'response_time_ms': 0,
            'response_time': "0.00s",
            'html_size': sz,
            'redirect_url': '',
            'redirect_type': '',
            'final_url': src,
            'language': '—',
            'http_version': 'HTTP/1.1',
            'mobile_alt_link': '',
            'amp_html_link': '',
            'page_type': 'Image Asset',
            'issues': [],
            'issues_count': 0,
            'img_inlinks': 1,
            'dimensions': dim_str,
            'word_count': 0,
            'sentence_count': 0,
            'avg_words_per_sentence': 0.0,
            'text_ratio': 0.0,
            'flesch_reading_ease': 0.0,
            'readability_label': '—',
            'crawl_timestamp': '',
            'closest_duplicate_url': '',
            'near_duplicate_count': 0,
            'closest_semantic_url': '',
            'psi_status': 'Not Applicable',
            'accessibility_violations_total': 0
        })

    # 3. Map Discovered Links
    for l in (all_links or []):
        tgt = l.get('target_url')
        if not tgt or tgt.startswith(('data:', 'javascript:', 'mailto:', 'tel:')) or tgt in seen_urls:
            continue
        seen_urls.add(tgt)
        virtual_id += 1
        tgt_domain = urlparse(tgt).netloc
        url_type = 'Internal' if (not tgt_domain or tgt_domain == audit_domain) else 'External'
        ct = determine_asset_mime(tgt)
        sc = l.get('status_code') or 200

        if 'image' in ct: idx_status = "Resource / Image"
        elif 'css' in ct: idx_status = "Resource / CSS"
        elif 'javascript' in ct: idx_status = "Resource / JS"
        elif url_type == 'External': idx_status = "External Link"
        else: idx_status = "Discovered Link"

        enriched.append({
            'id': virtual_id,
            'url': tgt,
            'url_type': url_type,
            'status_code': sc,
            'status': "OK" if sc == 200 else f"HTTP {sc}",
            'content_type': ct,
            'mime_type': ct.split(';')[0].strip(),
            'title': l.get('anchor_text') or '',
            'meta_description': '',
            'h1': '',
            'canonical_url': '—',
            'canonical_status': 'Missing',
            'internal_pagerank': 0.0,
            'http_canonical': '—',
            'robots_directive': '—',
            'indexability': "Non-Indexable" if url_type == 'External' or 'text/html' not in ct else "Indexable",
            'indexability_status': idx_status,
            'content_hash': '',
            'length': 0,
            'size_bytes': 0,
            'transferred_bytes': 0,
            'total_transferred_bytes': 0,
            'url_encoded_address': urllib.parse.quote(tgt, safe=''),
            'crawl_depth': 1,
            'folder_depth': len([s for s in urlparse(tgt).path.split('/') if s]),
            'parent_url': l.get('source_url', ''),
            'inlinks_count': 1,
            'unique_inlinks': 1,
            'outlinks_count': 0,
            'unique_outlinks': 0,
            'external_links_count': 0,
            'external_outlinks': 0,
            'unique_external_outlinks': 0,
            'link_score': 0.0,
            'images_count': 0,
            'schema_count': 0,
            'response_time_ms': 0,
            'response_time': "0.00s",
            'html_size': 0,
            'redirect_url': '',
            'redirect_type': '',
            'final_url': tgt,
            'language': '—',
            'http_version': 'HTTP/1.1',
            'mobile_alt_link': '',
            'amp_html_link': '',
            'page_type': 'External Link' if url_type == 'External' else 'Resource',
            'issues': [],
            'issues_count': 0,
            'word_count': 0,
            'sentence_count': 0,
            'avg_words_per_sentence': 0.0,
            'text_ratio': 0.0,
            'flesch_reading_ease': 0.0,
            'readability_label': '—',
            'crawl_timestamp': '',
            'closest_duplicate_url': '',
            'near_duplicate_count': 0,
            'closest_semantic_url': '',
            'psi_status': 'Not Applicable',
            'accessibility_violations_total': 0
        })

    return enriched

# Alias for backwards compatibility
enrich_pages_master = enrich_base_page_data

# -------------------------------------------------------------------------
# Dynamic Headings Expansion for Internal Tab
# -------------------------------------------------------------------------

def expand_internal_headings(pages: List[Dict[str, Any]], headings: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Expands dynamic H1-1, H1-1 Length, H1-2, etc., and H2-1, H2-1 Length, etc.
    Returns: (updated_pages, dynamic_columns)
    """
    # Group headings by page_id and tag
    page_h1s: Dict[int, List[str]] = {}
    page_h2s: Dict[int, List[str]] = {}

    for h in (headings or []):
        pid = h.get('page_id')
        if not pid:
            continue
        tag = (h.get('tag') or '').lower().strip()
        text = (h.get('text') or '').strip()
        if tag == 'h1':
            page_h1s.setdefault(pid, []).append(text)
        elif tag == 'h2':
            page_h2s.setdefault(pid, []).append(text)

    # Determine max counts across internal pages (minimum 1)
    max_h1 = 1
    max_h2 = 1

    for p in pages:
        pid = p.get('id')
        # If DB headings has entries, use them; else fallback to page.h1
        h1_list = page_h1s.get(pid, [])
        if not h1_list and p.get('h1'):
            h1_list = [p['h1']]
        h2_list = page_h2s.get(pid, [])
        if len(h1_list) > max_h1:
            max_h1 = len(h1_list)
        if len(h2_list) > max_h2:
            max_h2 = len(h2_list)

    # Cap dynamic columns at reasonable max to avoid UI explosion (e.g. max 10)
    max_h1 = min(max_h1, 10)
    max_h2 = min(max_h2, 10)

    dynamic_columns: List[Dict[str, Any]] = []
    for i in range(1, max_h1 + 1):
        dynamic_columns.append({'key': f'h1_{i}', 'label': f'H1-{i}', 'width': 'min-w-[180px]', 'dynamic': True})
        dynamic_columns.append({'key': f'h1_{i}_length', 'label': f'H1-{i} Length', 'width': 'w-24', 'align': 'text-right', 'dynamic': True})

    for i in range(1, max_h2 + 1):
        dynamic_columns.append({'key': f'h2_{i}', 'label': f'H2-{i}', 'width': 'min-w-[180px]', 'dynamic': True})
        dynamic_columns.append({'key': f'h2_{i}_length', 'label': f'H2-{i} Length', 'width': 'w-24', 'align': 'text-right', 'dynamic': True})

    # Populate pages with dynamic columns
    updated_pages = []
    for p in pages:
        row = dict(p)
        pid = row.get('id')
        h1_list = page_h1s.get(pid, [])
        if not h1_list and row.get('h1'):
            h1_list = [row['h1']]
        h2_list = page_h2s.get(pid, [])

        for i in range(1, max_h1 + 1):
            val = h1_list[i - 1] if (i - 1) < len(h1_list) else ''
            row[f'h1_{i}'] = val
            row[f'h1_{i}_length'] = len(val)

        for i in range(1, max_h2 + 1):
            val = h2_list[i - 1] if (i - 1) < len(h2_list) else ''
            row[f'h2_{i}'] = val
            row[f'h2_{i}_length'] = len(val)

        updated_pages.append(row)

    return updated_pages, dynamic_columns

# -------------------------------------------------------------------------
# Dynamic Hreflang Expansion
# -------------------------------------------------------------------------

def expand_hreflang_columns(pages: List[Dict[str, Any]], hreflangs: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Expands dynamic html_hreflang_1, html_hreflang_1_url, etc.
    """
    page_hrefs: Dict[str, List[Dict[str, Any]]] = {}
    for h in (hreflangs or []):
        src = (h.get('source_url') or '').rstrip('/')
        if src:
            page_hrefs.setdefault(src, []).append(h)

    max_href = 1
    for p in pages:
        u = (p.get('url') or '').rstrip('/')
        cnt = len(page_hrefs.get(u, []))
        if cnt > max_href:
            max_href = cnt

    max_href = min(max_href, 10)

    dynamic_columns: List[Dict[str, Any]] = []
    for i in range(1, max_href + 1):
        dynamic_columns.append({'key': f'html_hreflang_{i}', 'label': f'HTML Hreflang {i}', 'width': 'w-28', 'dynamic': True})
        dynamic_columns.append({'key': f'html_hreflang_{i}_url', 'label': f'HTML Hreflang {i} URL', 'width': 'min-w-[200px]', 'dynamic': True})

    updated_pages = []
    for p in pages:
        row = dict(p)
        u = (row.get('url') or '').rstrip('/')
        h_list = page_hrefs.get(u, [])
        row['hreflang_occurrence'] = len(h_list)
        for i in range(1, max_href + 1):
            if (i - 1) < len(h_list):
                entry = h_list[i - 1]
                row[f'html_hreflang_{i}'] = entry.get('lang_code') or ''
                row[f'html_hreflang_{i}_url'] = entry.get('target_url') or ''
            else:
                row[f'html_hreflang_{i}'] = ''
                row[f'html_hreflang_{i}_url'] = ''
        row['sitemap_hreflang_1'] = ''
        row['sitemap_hreflang_1_url'] = ''
        updated_pages.append(row)

    return updated_pages, dynamic_columns

# -------------------------------------------------------------------------
# Tab Dataset Builder: build_tab_dataset
# -------------------------------------------------------------------------

def build_tab_dataset(enriched_pages: List[Dict[str, Any]], tab_key: str,
                      headings: Optional[List[Dict[str, Any]]] = None,
                      pagination_tags: Optional[List[Dict[str, Any]]] = None,
                      hreflang_tags: Optional[List[Dict[str, Any]]] = None,
                      structured_data: Optional[List[Dict[str, Any]]] = None,
                      sitemap_entries: Optional[List[Dict[str, Any]]] = None,
                      accessibility_violations: Optional[List[Dict[str, Any]]] = None,
                      images_records: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
    """
    Transforms enriched pages into a tab-specific dataset.
    Returns:
    {
        'tab': tab_key,
        'columns': list of column definitions,
        'dynamic_columns': list of dynamically added columns,
        'rows': list of transformed rows,
        'total': total count before pagination
    }
    """
    clean_tab = tab_key.lower().replace('-', '_').strip()
    schema_info = TAB_SCHEMAS.get(clean_tab, TAB_SCHEMAS['all'])
    base_columns = list(schema_info['columns'])
    dynamic_columns: List[Dict[str, Any]] = []

    # Total inlinks across internal pages for % calculation
    total_inlinks_site = sum(p.get('inlinks_count', 0) for p in enriched_pages if p.get('url_type') == 'Internal')

    # Occurrence counters
    title_counts: Dict[str, int] = {}
    meta_desc_counts: Dict[str, int] = {}
    meta_kw_counts: Dict[str, int] = {}
    h1_counts: Dict[str, int] = {}
    h2_counts: Dict[str, int] = {}
    canonical_counts: Dict[str, int] = {}

    for p in enriched_pages:
        t = (p.get('title') or '').strip()
        if t: title_counts[t] = title_counts.get(t, 0) + 1
        d = (p.get('meta_description') or '').strip()
        if d: meta_desc_counts[d] = meta_desc_counts.get(d, 0) + 1
        k = (p.get('meta_keywords') or '').strip()
        if k: meta_kw_counts[k] = meta_kw_counts.get(k, 0) + 1
        h1 = (p.get('h1') or '').strip()
        if h1: h1_counts[h1] = h1_counts.get(h1, 0) + 1
        c = (p.get('canonical_url') or '').strip()
        if c and c != '—': canonical_counts[c] = canonical_counts.get(c, 0) + 1

    # Image inlinks count and dimensions mapping
    img_inlinks_map: Dict[str, int] = {}
    img_dim_map: Dict[str, str] = {}
    for img in (images_records or []):
        src = img.get('src') or ''
        if src:
            img_inlinks_map[src] = img_inlinks_map.get(src, 0) + 1
            w, h = img.get('width'), img.get('height')
            if w and h:
                img_dim_map[src] = f"{w}x{h}"

    # Structured data aggregation per page
    sd_agg_map: Dict[int, Dict[str, Any]] = {}
    for sd in (structured_data or []):
        pid = sd.get('page_id')
        if not pid:
            continue
        agg = sd_agg_map.setdefault(pid, {
            'errors': 0, 'warnings': 0, 'types': set(), 'first_type': '', 'first_feature': ''
        })
        stype = sd.get('schema_type') or 'Unknown'
        agg['types'].add(stype)
        if not agg['first_type'] and stype != 'Unknown':
            agg['first_type'] = stype
            agg['first_feature'] = stype
        if not sd.get('is_valid', True) or sd.get('errors'):
            agg['errors'] += 1

    # Sitemap URLs set
    sitemap_urls_set = set((s.get('page_url') or '').rstrip('/') for s in (sitemap_entries or []))

    # Filter rows based on tab
    filtered_rows: List[Dict[str, Any]] = []

    if clean_tab == 'all':
        filtered_rows = list(enriched_pages)

    elif clean_tab == 'internal':
        internal_pages = [p for p in enriched_pages if p.get('url_type') == 'Internal']
        # Apply dynamic headings expansion
        filtered_rows, dynamic_columns = expand_internal_headings(internal_pages, headings or [])
        # Insert dynamic columns into column schema
        insert_idx = next((i for i, col in enumerate(base_columns) if col['key'] == 'meta_description_length'), 10) + 1
        final_columns = base_columns[:insert_idx] + dynamic_columns + base_columns[insert_idx:]
        base_columns = final_columns

    elif clean_tab == 'external':
        filtered_rows = [p for p in enriched_pages if p.get('url_type') == 'External']

    elif clean_tab == 'response_codes':
        filtered_rows = sorted(list(enriched_pages), key=lambda p: (p.get('status_code', 200), p.get('url', '')))

    elif clean_tab == 'page_titles':
        filtered_rows = []
        for p in enriched_pages:
            if 'html' in (p.get('content_type') or '').lower() or p.get('title'):
                r = dict(p)
                t = (r.get('title') or '').strip()
                r['occurrences'] = title_counts.get(t, 1 if t else 0)
                filtered_rows.append(r)

    elif clean_tab == 'meta_description':
        filtered_rows = []
        for p in enriched_pages:
            if 'html' in (p.get('content_type') or '').lower() or p.get('meta_description'):
                r = dict(p)
                d = (r.get('meta_description') or '').strip()
                r['occurrences'] = meta_desc_counts.get(d, 1 if d else 0)
                filtered_rows.append(r)

    elif clean_tab == 'meta_keywords':
        filtered_rows = []
        for p in enriched_pages:
            if 'html' in (p.get('content_type') or '').lower() or p.get('meta_keywords'):
                r = dict(p)
                k = (r.get('meta_keywords') or '').strip()
                r['occurrences'] = meta_kw_counts.get(k, 1 if k else 0)
                filtered_rows.append(r)

    elif clean_tab == 'h1':
        filtered_rows = []
        for p in enriched_pages:
            if 'html' in (p.get('content_type') or '').lower() or p.get('h1'):
                r = dict(p)
                h1 = (r.get('h1') or '').strip()
                r['occurrences'] = h1_counts.get(h1, 1 if h1 else 0)
                r['h1_1'] = h1
                r['h1_1_length'] = len(h1)
                filtered_rows.append(r)

    elif clean_tab == 'h2':
        # Look for H2 in headings
        h2_map: Dict[int, str] = {}
        for h in (headings or []):
            if (h.get('tag') or '').lower() == 'h2' and h.get('page_id') not in h2_map:
                h2_map[h['page_id']] = (h.get('text') or '').strip()

        filtered_rows = []
        for p in enriched_pages:
            if 'html' in (p.get('content_type') or '').lower() or p.get('id') in h2_map:
                r = dict(p)
                h2_text = h2_map.get(r.get('id'), '')
                r['h2_1'] = h2_text
                r['h2_1_length'] = len(h2_text)
                r['occurrences'] = 1 if h2_text else 0
                filtered_rows.append(r)

    elif clean_tab == 'content':
        filtered_rows = [p for p in enriched_pages if 'html' in (p.get('content_type') or '').lower()]

    elif clean_tab == 'images':
        filtered_rows = []
        for p in enriched_pages:
            if 'image' in (p.get('content_type') or '').lower() or 'image' in (p.get('mime_type') or '').lower():
                r = dict(p)
                u = r.get('url', '')
                r['img_inlinks'] = img_inlinks_map.get(u, r.get('inlinks_count', 1))
                r['dimensions'] = img_dim_map.get(u, r.get('dimensions', '—'))
                filtered_rows.append(r)

    elif clean_tab == 'canonicals':
        filtered_rows = []
        for p in enriched_pages:
            c = (p.get('canonical_url') or '').strip()
            hc = (p.get('http_canonical') or '').strip()
            if (c and c != '—') or (hc and hc != '—') or 'html' in (p.get('content_type') or '').lower():
                r = dict(p)
                r['occurrences'] = canonical_counts.get(c, 1 if (c and c != '—') else 0)
                filtered_rows.append(r)

    elif clean_tab == 'pagination':
        pag_pids = set(t.get('page_id') for t in (pagination_tags or []) if t.get('page_id'))
        filtered_rows = [p for p in enriched_pages if p.get('id') in pag_pids or 'html' in (p.get('content_type') or '').lower()]

    elif clean_tab == 'hreflang':
        html_pages = [p for p in enriched_pages if 'html' in (p.get('content_type') or '').lower()]
        filtered_rows, dynamic_columns = expand_hreflang_columns(html_pages, hreflang_tags or [])

    elif clean_tab == 'javascript':
        filtered_rows = [p for p in enriched_pages if 'html' in (p.get('content_type') or '').lower()]

    elif clean_tab == 'links':
        filtered_rows = []
        for p in enriched_pages:
            if 'html' in (p.get('content_type') or '').lower():
                r = dict(p)
                in_cnt = r.get('inlinks_count', 0)
                r['inlinks_pct'] = round((in_cnt / max(1, total_inlinks_site)) * 100, 1) if total_inlinks_site > 0 else 0.0
                filtered_rows.append(r)

    elif clean_tab == 'structured_data':
        filtered_rows = []
        for p in enriched_pages:
            pid = p.get('id')
            agg = sd_agg_map.get(pid, {})
            if agg or p.get('schema_count', 0) > 0 or 'html' in (p.get('content_type') or '').lower():
                r = dict(p)
                types_set = agg.get('types', set())
                r['sd_errors'] = agg.get('errors', 0)
                r['sd_warnings'] = agg.get('warnings', 0)
                r['rich_result_errors'] = agg.get('errors', 0)
                r['rich_result_warnings'] = agg.get('warnings', 0)
                r['rich_result_features'] = ', '.join(sorted(types_set)) if types_set else '—'
                r['sd_feature_1'] = agg.get('first_feature') or '—'
                r['sd_total_types'] = len(types_set)
                r['sd_unique_types'] = len(types_set)
                r['sd_type_1'] = agg.get('first_type') or '—'
                filtered_rows.append(r)

    elif clean_tab == 'sitemaps':
        filtered_rows = []
        for p in enriched_pages:
            u = (p.get('url') or '').rstrip('/')
            if u in sitemap_urls_set or not sitemap_urls_set:
                filtered_rows.append(dict(p))

    elif clean_tab == 'pagespeed':
        filtered_rows = [p for p in enriched_pages if 'html' in (p.get('content_type') or '').lower()]

    elif clean_tab == 'mobile':
        filtered_rows = [p for p in enriched_pages if 'html' in (p.get('content_type') or '').lower()]

    elif clean_tab == 'accessibility':
        filtered_rows = [p for p in enriched_pages if 'html' in (p.get('content_type') or '').lower() or p.get('accessibility_violations_total', 0) > 0]

    elif clean_tab == 'amp':
        filtered_rows = [p for p in enriched_pages if p.get('amp_html_link') or 'html' in (p.get('content_type') or '').lower()]

    else:
        filtered_rows = list(enriched_pages)

    return {
        'tab': clean_tab,
        'columns': base_columns,
        'dynamic_columns': dynamic_columns,
        'rows': filtered_rows,
        'total': len(filtered_rows)
    }

# -------------------------------------------------------------------------
# Sorting, Filtering & Pagination: filter_and_sort_tab_rows
# -------------------------------------------------------------------------

def filter_and_sort_tab_rows(rows: List[Dict[str, Any]], sort_by: Optional[str] = None,
                             sort_dir: Optional[str] = 'asc', include: Optional[str] = None,
                             exclude: Optional[str] = None, page: int = 1,
                             page_size: int = 500) -> Tuple[List[Dict[str, Any]], int]:
    """
    Applies regex include/exclude filtering, multi-type sorting, and pagination.
    Assigns sequential 1-based `row` index.
    Returns (paginated_rows, total_filtered_count).
    """
    filtered = rows

    # 1. Regex Include Filter
    if include and include.strip():
        inc_pattern = include.strip()
        try:
            inc_re = re.compile(inc_pattern, re.IGNORECASE)
            filtered = [r for r in filtered if inc_re.search(r.get('url', '')) or any(inc_re.search(str(v)) for v in r.values() if isinstance(v, (str, int, float)))]
        except re.error:
            inc_low = inc_pattern.lower()
            filtered = [r for r in filtered if inc_low in (r.get('url') or '').lower()]

    # 2. Regex Exclude Filter
    if exclude and exclude.strip():
        exc_pattern = exclude.strip()
        try:
            exc_re = re.compile(exc_pattern, re.IGNORECASE)
            filtered = [r for r in filtered if not exc_re.search(r.get('url', ''))]
        except re.error:
            exc_low = exc_pattern.lower()
            filtered = [r for r in filtered if exc_low not in (r.get('url') or '').lower()]

    # 3. Sorting
    if sort_by and sort_by != 'row':
        is_desc = (sort_dir or 'asc').lower() == 'desc'

        def sort_key(row):
            val = row.get(sort_by)
            if val is None or val == '—':
                return (1, 0, "")
            if isinstance(val, (int, float)):
                return (0, 0, val)
            return (0, 1, str(val).lower())

        filtered = sorted(filtered, key=sort_key, reverse=is_desc)

    total = len(filtered)

    # 4. Pagination
    p = max(1, page)
    ps = max(1, min(page_size, 5000))
    start_idx = (p - 1) * ps
    end_idx = start_idx + ps
    page_rows = filtered[start_idx:end_idx]

    # Assign sequential row index
    result = []
    for i, r in enumerate(page_rows):
        row_copy = dict(r)
        row_copy['row'] = start_idx + i + 1
        result.append(row_copy)

    return result, total

# -------------------------------------------------------------------------
# Right Panel Aggregators
# -------------------------------------------------------------------------

def build_issues_summary(raw_issues: List[Dict[str, Any]], total_pages: int, raw_pages: List[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    """
    Aggregates issues by (category, message) for right panel Issues tab.
    urls_list always contains full URLs (resolved from page_id if needed).
    """
    # Build page_id -> URL lookup from pages list
    page_id_to_url: Dict[int, str] = {}
    for p in (raw_pages or []):
        pid = p.get('id')
        u = p.get('url') or ''
        if pid and u:
            page_id_to_url[int(pid)] = u

    grouped: Dict[Tuple[str, str], Dict[str, Any]] = {}
    for iss in (raw_issues or []):
        cat = iss.get('category') or 'onpage'
        msg = iss.get('message') or 'Issue detected'
        sev = iss.get('severity') or 'medium'
        rec = iss.get('recommendation') or ''
        key = (cat, msg)

        if key not in grouped:
            # Format issue name
            name_parts = (iss.get('issue_type') or cat).replace('_', ' ').title()
            grouped[key] = {
                'issue_name': name_parts,
                'issue_type': cat,
                'issue_priority': sev,
                'urls_set': set(),
                'description': msg,
                'how_to_fix': rec,
                'help_url': 'https://developers.google.com/search/docs'
            }

        # Prefer issue.url; fall back to looking up page_id in pages
        issue_url = (iss.get('url') or '').strip()
        if not issue_url:
            pid = iss.get('page_id')
            if pid is not None:
                issue_url = page_id_to_url.get(int(pid), '')
        if issue_url:
            grouped[key]['urls_set'].add(issue_url)

    issues_list = []
    # Sort priority order: critical > high > medium > low > info
    prio_order = {'critical': 0, 'high': 1, 'medium': 2, 'low': 3, 'info': 4}
    for item in grouped.values():
        cnt = len(item['urls_set'])
        pct = round((cnt / max(1, total_pages)) * 100, 1)
        issues_list.append({
            'issue_name': item['issue_name'],
            'issue_type': item['issue_type'],
            'issue_priority': item['issue_priority'],
            'urls': cnt,
            'urls_list': sorted(list(item['urls_set'])),
            'pct_of_total': pct,
            'description': item['description'],
            'how_to_fix': item['how_to_fix'],
            'help_url': item['help_url']
        })

    issues_list.sort(key=lambda x: (prio_order.get(x['issue_priority'].lower(), 99), -x['urls']))
    return issues_list

def build_site_structure_tree(urls: List[str]) -> List[Dict[str, Any]]:
    """
    Constructs a path hierarchy tree from URLs for right panel Site Structure tab.
    """
    root_node: Dict[str, Any] = {'path': '/', 'count': 0, 'children': {}}

    for u in (urls or []):
        parsed = urlparse(u)
        path = parsed.path or '/'
        if not path.startswith('/'):
            path = '/' + path
        segments = [s for s in path.split('/') if s]

        # Traverse and count
        root_node['count'] += 1
        curr = root_node
        built_path = ''
        for seg in segments:
            built_path += f"/{seg}"
            seg_path = built_path + '/'
            if seg_path not in curr['children']:
                curr['children'][seg_path] = {'path': seg_path, 'count': 0, 'children': {}}
            curr = curr['children'][seg_path]
            curr['count'] += 1

    def node_to_dict(node: Dict[str, Any]) -> Dict[str, Any]:
        return {
            'path': node['path'],
            'count': node['count'],
            'children': [node_to_dict(child) for child in sorted(node['children'].values(), key=lambda c: c['path'])]
        }

    return [node_to_dict(root_node)]

def build_response_times_buckets(pages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Computes distribution buckets: 0-0.5s, 0.5-1s, 1-2s, 2-5s, 5s+
    """
    total = len(pages)
    b_0_05 = 0
    b_05_1 = 0
    b_1_2 = 0
    b_2_5 = 0
    b_5_plus = 0

    for p in pages:
        ms = p.get('response_time_ms') or 0.0
        sec = ms / 1000.0
        if sec < 0.5:
            b_0_05 += 1
        elif sec < 1.0:
            b_05_1 += 1
        elif sec < 2.0:
            b_1_2 += 1
        elif sec < 5.0:
            b_2_5 += 1
        else:
            b_5_plus += 1

    def calc_pct(c: int) -> float:
        return round((c / max(1, total)) * 100, 1)

    return [
        {'range': '0-0.5s', 'urls': b_0_05, 'pct_of_total': calc_pct(b_0_05)},
        {'range': '0.5-1s', 'urls': b_05_1, 'pct_of_total': calc_pct(b_05_1)},
        {'range': '1-2s', 'urls': b_1_2, 'pct_of_total': calc_pct(b_1_2)},
        {'range': '2-5s', 'urls': b_2_5, 'pct_of_total': calc_pct(b_2_5)},
        {'range': '5s+', 'urls': b_5_plus, 'pct_of_total': calc_pct(b_5_plus)}
    ]

def build_depth_distribution(pages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Computes crawl depth distribution buckets: level, urls, pct_of_total
    """
    total = len(pages)
    depth_counts: Dict[int, int] = {}

    for p in pages:
        d = p.get('crawl_depth') if p.get('crawl_depth') is not None else 0
        depth_counts[d] = depth_counts.get(d, 0) + 1

    depths_list = []
    for d in sorted(depth_counts.keys()):
        cnt = depth_counts[d]
        pct = round((cnt / max(1, total)) * 100, 1)
        depths_list.append({
            'depth': d,
            'urls': cnt,
            'pct_of_total': pct
        })

    return depths_list

def build_segments_summary(pages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Groups URLs by their top-level directory segment (e.g., '/', '/products/', '/blog/').
    """
    total = len(pages)
    seg_counts: Dict[str, List[str]] = {}

    for p in pages:
        u = p.get('url') or ''
        parsed = urlparse(u)
        path = parsed.path or '/'
        if not path.startswith('/'):
            path = '/' + path
        parts = [seg for seg in path.split('/') if seg]
        if not parts:
            seg_name = '/'
        else:
            seg_name = f"/{parts[0]}/"

        if seg_name not in seg_counts:
            seg_counts[seg_name] = []
        seg_counts[seg_name].append(u)

    results = []
    for seg, url_list in sorted(seg_counts.items(), key=lambda x: -len(x[1])):
        cnt = len(url_list)
        pct = round((cnt / max(1, total)) * 100, 1)
        results.append({
            'segment': seg,
            'urls': cnt,
            'urls_list': sorted(url_list),
            'pct_of_total': pct
        })
    return results

