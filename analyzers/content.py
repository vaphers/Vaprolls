import logging
import re
import math
import hashlib
from typing import List, Dict, Any, Optional
from database.db import Database

logger = logging.getLogger(__name__)

# Arial character width approximations at standard SERP display sizes
# Arial 20px (Google SERP Title ~20px regular)
ARIAL_20PX_WIDTHS = {
    ' ': 6, '!': 7, '"': 9, '#': 12, '$': 12, '%': 19, '&': 15, "'": 5, '(': 7, ')': 7,
    '*': 9, '+': 13, ',': 6, '-': 7, '.': 6, '/': 6, '0': 12, '1': 12, '2': 12, '3': 12,
    '4': 12, '5': 12, '6': 12, '7': 12, '8': 12, '9': 12, ':': 6, ';': 6, '<': 13, '=': 13,
    '>': 13, '?': 12, '@': 22, 'A': 15, 'B': 15, 'C': 16, 'D': 16, 'E': 15, 'F': 13, 'G': 17,
    'H': 16, 'I': 6, 'J': 11, 'K': 15, 'L': 12, 'M': 19, 'N': 16, 'O': 17, 'P': 15, 'Q': 17,
    'R': 16, 'S': 15, 'T': 13, 'U': 16, 'V': 15, 'W': 21, 'X': 15, 'Y': 15, 'Z': 13, '[': 6,
    '\\': 6, ']': 6, '^': 10, '_': 12, '`': 7, 'a': 12, 'b': 12, 'c': 11, 'd': 12, 'e': 12,
    'f': 6, 'g': 12, 'h': 12, 'i': 5, 'j': 5, 'k': 11, 'l': 5, 'm': 18, 'n': 12, 'o': 12,
    'p': 12, 'q': 12, 'r': 7, 's': 11, 't': 6, 'u': 12, 'v': 11, 'w': 16, 'x': 11, 'y': 11,
    'z': 11, '{': 7, '|': 6, '}': 7, '~': 13
}
ARIAL_20PX_DEFAULT = 12

# Arial 14px (Google SERP Snippet / Description ~14px regular)
ARIAL_14PX_WIDTHS = {
    ' ': 4, '!': 5, '"': 6, '#': 8, '$': 8, '%': 13, '&': 11, "'": 3, '(': 5, ')': 5,
    '*': 6, '+': 9, ',': 4, '-': 5, '.': 4, '/': 4, '0': 8, '1': 8, '2': 8, '3': 8,
    '4': 8, '5': 8, '6': 8, '7': 8, '8': 8, '9': 8, ':': 4, ';': 4, '<': 9, '=': 9,
    '>': 9, '?': 8, '@': 15, 'A': 10, 'B': 10, 'C': 11, 'D': 11, 'E': 10, 'F': 9, 'G': 12,
    'H': 11, 'I': 4, 'J': 8, 'K': 10, 'L': 8, 'M': 13, 'N': 11, 'O': 12, 'P': 10, 'Q': 12,
    'R': 11, 'S': 10, 'T': 9, 'U': 11, 'V': 10, 'W': 15, 'X': 10, 'Y': 10, 'Z': 9, '[': 4,
    '\\': 4, ']': 4, '^': 7, '_': 8, '`': 5, 'a': 8, 'b': 8, 'c': 8, 'd': 8, 'e': 8,
    'f': 4, 'g': 8, 'h': 8, 'i': 3, 'j': 3, 'k': 8, 'l': 3, 'm': 13, 'n': 8, 'o': 8,
    'p': 8, 'q': 8, 'r': 5, 's': 8, 't': 4, 'u': 8, 'v': 8, 'w': 11, 'x': 8, 'y': 8,
    'z': 8, '{': 5, '|': 4, '}': 5, '~': 9
}
ARIAL_14PX_DEFAULT = 8


def calculate_pixel_width(text: Optional[str], font_size: int = 20) -> int:
    """Simulate rendered pixel width for Arial font."""
    if not text:
        return 0
    if font_size >= 18:
        widths = ARIAL_20PX_WIDTHS
        default_w = ARIAL_20PX_DEFAULT
    else:
        widths = ARIAL_14PX_WIDTHS
        default_w = ARIAL_14PX_DEFAULT
    return sum(widths.get(ch, default_w) for ch in text)


def count_syllables(word: str) -> int:
    """Vowel-group heuristic for syllable counting in English words."""
    word = word.lower().strip()
    if not word:
        return 1
    if len(word) <= 3:
        return 1
    # Remove non-alpha
    word = re.sub(r'[^a-z]', '', word)
    if not word:
        return 1

    # Count vowel groups
    vowel_groups = re.findall(r'[aeiouy]+', word)
    count = len(vowel_groups)

    # Adjust for silent ending 'e'
    if word.endswith('e') and not word.endswith('le') and count > 1:
        count -= 1
    # Adjust for 'ed' endings
    if word.endswith('ed') and not word.endswith('ted') and not word.endswith('ded') and count > 1:
        count -= 1

    return max(1, count)


def calculate_flesch_reading_ease(word_count: int, sentence_count: int, total_syllables: int) -> float:
    """
    Flesch Reading Ease formula:
    206.835 - 1.015 * (total_words / total_sentences) - 84.6 * (total_syllables / total_words)
    Clamped to 0.0 - 100.0.
    """
    if word_count <= 0 or sentence_count <= 0:
        return 0.0
    words_per_sent = word_count / max(1, sentence_count)
    syllables_per_word = total_syllables / max(1, word_count)
    score = 206.835 - (1.015 * words_per_sent) - (84.6 * syllables_per_word)
    return round(max(0.0, min(100.0, score)), 1)


def get_readability_label(score: float) -> str:
    """Map Flesch score to descriptive readability category."""
    if score >= 90.0:
        return "Very Easy"
    elif score >= 80.0:
        return "Easy"
    elif score >= 60.0:
        return "Standard"
    elif score >= 30.0:
        return "Difficult"
    else:
        return "Very Difficult"


def compute_simhash(text: str) -> int:
    """Compute a 64-bit SimHash integer fingerprint from text."""
    if not text:
        return 0
    words = re.findall(r'\b[a-zA-Z]{3,}\b', text.lower())
    if not words:
        return 0

    v = [0] * 64
    for word in words:
        h = int(hashlib.md5(word.encode('utf-8')).hexdigest()[:16], 16)
        for i in range(64):
            bit = (h >> i) & 1
            if bit:
                v[i] += 1
            else:
                v[i] -= 1

    fingerprint = 0
    for i in range(64):
        if v[i] > 0:
            fingerprint |= (1 << i)
    return fingerprint


def hamming_distance(hash1: int, hash2: int) -> int:
    """Calculate bitwise Hamming distance between two 64-bit integers."""
    x = hash1 ^ hash2
    dist = 0
    while x > 0:
        dist += x & 1
        x >>= 1
    return dist


class ContentAnalyzer:
    """
    Analyzes content metrics across pages in an audit:
    - Flesch Reading Ease score & readability label
    - Pixel width simulation for Titles (Arial 20px) and Meta Descriptions (Arial 14px)
    - SimHash 64-bit fingerprinting and pairwise near-duplicate detection
    """
    def __init__(self, db: Database, audit_id: str):
        self.db = db
        self.audit_id = audit_id

    async def analyze(self):
        logger.info(f"Starting content analysis for audit {self.audit_id}")
        pages = await self.db.get_pages(self.audit_id)
        if not pages:
            return

        page_simhashes: Dict[int, Dict[str, Any]] = {}

        for page in pages:
            page_id = page['id']
            url = page.get('url', '')
            title = page.get('title') or ''
            meta_desc = page.get('meta_description') or ''
            h1 = page.get('h1') or ''
            word_count = page.get('word_count', 0) or 0
            sentence_count = page.get('sentence_count', 0) or 0

            # Pixel width calculations
            title_pw = calculate_pixel_width(title, font_size=20)
            desc_pw = calculate_pixel_width(meta_desc, font_size=14)

            # Readability calculation
            sample_text = f"{title} {meta_desc} {h1}"
            words = sample_text.split()
            if words:
                syllables = sum(count_syllables(w) for w in words)
                syl_ratio = syllables / max(1, len(words))
                total_syllables = int(word_count * syl_ratio)
            else:
                total_syllables = int(word_count * 1.5)

            if word_count > 0 and sentence_count > 0:
                flesch = calculate_flesch_reading_ease(word_count, sentence_count, total_syllables)
                read_label = get_readability_label(flesch)
            else:
                flesch = 0.0
                read_label = "N/A"

            # SimHash fingerprint: prefer precomputed full-body hash from crawl, fallback to metadata
            stored_hash = page.get('content_near_duplicate_hash')
            if stored_hash and len(str(stored_hash)) == 16:
                try:
                    sh_val = int(stored_hash, 16)
                    sh_hex = str(stored_hash)
                except ValueError:
                    sh_val = compute_simhash(f"{title} {meta_desc} {h1}")
                    sh_hex = f"{sh_val:016x}"
            else:
                sh_val = compute_simhash(f"{title} {meta_desc} {h1}")
                sh_hex = f"{sh_val:016x}"

            page_simhashes[page_id] = {
                'url': url,
                'simhash': sh_val,
                'simhash_hex': sh_hex,
                'title_pw': title_pw,
                'desc_pw': desc_pw,
                'flesch': flesch,
                'read_label': read_label
            }

        # Pairwise near-duplicate comparison
        page_ids = list(page_simhashes.keys())
        near_dups: Dict[int, Dict[str, Any]] = {
            pid: {'count': 0, 'closest_url': None, 'closest_sim': 0.0}
            for pid in page_ids
        }

        for i in range(len(page_ids)):
            pid1 = page_ids[i]
            info1 = page_simhashes[pid1]
            sh1 = info1['simhash']
            if sh1 == 0:
                continue

            for j in range(i + 1, len(page_ids)):
                pid2 = page_ids[j]
                info2 = page_simhashes[pid2]
                sh2 = info2['simhash']
                if sh2 == 0:
                    continue

                dist = hamming_distance(sh1, sh2)
                sim = round(1.0 - (dist / 64.0), 3)

                # Near-duplicate threshold: distance <= 6 (similarity >= ~90.6%)
                if dist <= 6:
                    near_dups[pid1]['count'] += 1
                    if sim > near_dups[pid1]['closest_sim']:
                        near_dups[pid1]['closest_sim'] = sim
                        near_dups[pid1]['closest_url'] = info2['url']

                    near_dups[pid2]['count'] += 1
                    if sim > near_dups[pid2]['closest_sim']:
                        near_dups[pid2]['closest_sim'] = sim
                        near_dups[pid2]['closest_url'] = info1['url']

        # Update all pages in database
        for pid, info in page_simhashes.items():
            dup_info = near_dups.get(pid, {'count': 0, 'closest_url': None, 'closest_sim': 0.0})
            await self.db.update_page_columns(
                pid,
                title_pixel_width=info['title_pw'],
                meta_desc_pixel_width=info['desc_pw'],
                flesch_reading_ease=info['flesch'],
                readability_label=info['read_label'],
                content_near_duplicate_hash=info['simhash_hex'],
                near_duplicate_count=dup_info['count'],
                closest_duplicate_url=dup_info['closest_url'],
                closest_duplicate_similarity=dup_info['closest_sim']
            )

        logger.info(f"Completed content analysis for audit {self.audit_id}")
