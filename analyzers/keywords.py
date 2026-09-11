import logging
import urllib.parse
from collections import Counter
import re
from typing import Optional, Any, List
from database.db import Database

logger = logging.getLogger(__name__)

STOP_WORDS = set([
    "a", "about", "above", "after", "again", "against", "all", "am", "an", "and", "any", "are", "aren't", "as", "at", 
    "be", "because", "been", "before", "being", "below", "between", "both", "but", "by", "can't", "cannot", "could", 
    "couldn't", "did", "didn't", "do", "does", "doesn't", "doing", "don't", "down", "during", "each", "few", "for", 
    "from", "further", "had", "hadn't", "has", "hasn't", "have", "haven't", "having", "he", "he'd", "he'll", "he's", 
    "her", "here", "here's", "hers", "herself", "him", "himself", "his", "how", "how's", "i", "i'd", "i'll", "i'm", 
    "i've", "if", "in", "into", "is", "isn't", "it", "it's", "its", "itself", "let's", "me", "more", "most", "mustn't", 
    "my", "myself", "no", "nor", "not", "of", "off", "on", "once", "only", "or", "other", "ought", "our", "ours", 
    "ourselves", "out", "over", "own", "same", "shan't", "she", "she'd", "she'll", "she's", "should", "shouldn't", 
    "so", "some", "such", "than", "that", "that's", "the", "their", "theirs", "them", "themselves", "then", "there", 
    "there's", "these", "they", "they'd", "they'll", "they're", "they've", "this", "those", "through", "to", "too", 
    "under", "until", "up", "very", "was", "wasn't", "we", "we'd", "we'll", "we're", "we've", "were", "weren't", 
    "what", "what's", "when", "when's", "where", "where's", "which", "while", "who", "who's", "whom", "why", "why's", 
    "with", "won't", "would", "wouldn't", "you", "you'd", "you'll", "you're", "you've", "your", "yours", "yourself", 
    "yourselves"
])

class KeywordAnalyzer:
    def __init__(self, db: Database, audit_id: str):
        self.db = db
        self.audit_id = audit_id

    def tokenize(self, text: str) -> List[str]:
        if not text:
            return []
        text = text.lower()
        words = re.findall(r'\b[a-z]{2,}\b', text)
        return [w for w in words if w not in STOP_WORDS]

    def get_ngrams(self, words: List[str], n: int) -> List[str]:
        return [' '.join(words[i:i+n]) for i in range(len(words)-n+1)]

    async def analyze(self):
        logger.info(f"Starting keyword analysis for audit {self.audit_id}")
        
        pages = await self.db.get_pages(self.audit_id)
        if not pages:
            return

        top_keywords_by_page = {}
        no_keywords_count = 0

        for page in pages:
            page_id = page.get('id')
            url = page.get('url', '')
            title = page.get('title', '') or ''
            meta_desc = page.get('meta_description', '') or ''
            h1 = page.get('h1', '') or ''
            word_count = page.get('word_count', 0)

            text_content = f"{title} {meta_desc} {h1}"
            words = self.tokenize(text_content)
            
            if not words:
                no_keywords_count += 1
                await self._add_issue(page_id, url, 'info', 'no_keywords', "Pages with no extractable keywords", "Add substantial text content to the page.", None)
                continue

            single_counts = Counter(words)
            bigram_counts = Counter(self.get_ngrams(words, 2))
            trigram_counts = Counter(self.get_ngrams(words, 3))

            top_singles = single_counts.most_common(10)
            top_bigrams = bigram_counts.most_common(10)
            top_trigrams = trigram_counts.most_common(5)

            all_top = top_singles + top_bigrams + top_trigrams

            # Identify target keyword (most frequent single word or bigram if tied)
            target_keyword = None
            if all_top:
                target_keyword = all_top[0][0]
                top_keywords_by_page[target_keyword] = top_keywords_by_page.get(target_keyword, []) + [url]

            # Save keywords and check rules
            for kw, freq in all_top:
                ngram_size = len(kw.split())
                
                # Use total text word count if available, else fallback to extracted words count
                total_words = word_count if word_count > 0 else len(words)
                if total_words == 0:
                    total_words = 1
                
                density = (freq / total_words) * 100

                in_title = kw in title.lower()
                in_h1 = kw in h1.lower()
                in_meta_description = kw in meta_desc.lower()
                
                parsed_url = urllib.parse.urlparse(url)
                path_lower = parsed_url.path.lower()
                # for multi-word, check if hyphenated version is in url
                kw_url_form = kw.replace(' ', '-')
                in_url = kw_url_form in path_lower or kw.replace(' ', '') in path_lower

                await self.db.add_keyword(
                    self.audit_id, page_id,
                    page_url=url,
                    keyword=kw,
                    frequency=freq,
                    density=density,
                    in_title=in_title,
                    in_h1=in_h1,
                    in_meta_description=in_meta_description,
                    in_url=in_url,
                    ngram_size=ngram_size
                )

                if density > 3.0 and ngram_size == 1:
                    await self._add_issue(page_id, url, 'warning', 'keyword_stuffing', f"Keyword density > 3% for '{kw}'", "Reduce frequency of this keyword to avoid stuffing.", density)

            # Checks for target keyword
            if target_keyword:
                if not (target_keyword in title.lower()):
                    await self._add_issue(page_id, url, 'warning', 'target_keyword_not_in_title', f"Target keyword '{target_keyword}' not in title", "Include primary keyword in the page title.", target_keyword)
                if not (target_keyword in h1.lower()):
                    await self._add_issue(page_id, url, 'warning', 'target_keyword_not_in_h1', f"Target keyword '{target_keyword}' not in H1", "Include primary keyword in the main H1 heading.", target_keyword)
                if not (target_keyword in meta_desc.lower()):
                    await self._add_issue(page_id, url, 'warning', 'target_keyword_not_in_meta', f"Target keyword '{target_keyword}' not in meta description", "Include primary keyword in the meta description.", target_keyword)
                
                kw_url_form = target_keyword.replace(' ', '-')
                parsed_url = urllib.parse.urlparse(url)
                path_lower = parsed_url.path.lower()
                if not (kw_url_form in path_lower or target_keyword.replace(' ', '') in path_lower):
                    await self._add_issue(page_id, url, 'info', 'target_keyword_not_in_url', f"Target keyword '{target_keyword}' not in URL", "Consider including the primary keyword in the URL slug.", target_keyword)

        # Site-wide checks
        # Keyword cannibalization
        for kw, urls in top_keywords_by_page.items():
            if len(urls) > 1:
                await self._add_issue(None, None, 'warning', 'keyword_cannibalization', f"Keyword cannibalization: '{kw}' is the top keyword for multiple pages", "Differentiate content targeting this keyword.", urls)

        if no_keywords_count > 0:
            await self._add_issue(None, None, 'info', 'site_wide_thin_content', f"{no_keywords_count} pages with no extractable keywords", "Add substantial text content.", no_keywords_count)

    async def _add_issue(self, page_id: Optional[int], url: Optional[str], severity: str, issue_type: str, message: str, recommendation: str, element: Any = None):
        await self.db.add_issue(
            audit_id=self.audit_id,
            page_id=page_id,
            url=url,
            category='keywords',
            severity=severity,
            issue_type=issue_type,
            message=message,
            recommendation=recommendation,
            element=element
        )
