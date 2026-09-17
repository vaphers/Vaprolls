"""
Database Migration System for Vaprolls SEO Spider.
Safely migrates SQLite schemas across upgrades without data loss.
"""
import logging
from typing import Any

logger = logging.getLogger(__name__)

NEW_PAGE_COLUMNS = [
    # Social Meta Tags (Open Graph & Twitter Cards)
    ("og_title", "TEXT"),
    ("og_description", "TEXT"),
    ("og_image", "TEXT"),
    ("og_type", "TEXT"),
    ("twitter_card", "TEXT"),
    ("twitter_title", "TEXT"),
    ("twitter_description", "TEXT"),
    ("twitter_image", "TEXT"),

    # Security Headers & Network Details
    ("hsts_header", "TEXT"),
    ("csp_header", "TEXT"),
    ("x_content_type_options", "TEXT"),
    ("x_frame_options", "TEXT"),
    ("referrer_policy", "TEXT"),
    ("permissions_policy", "TEXT"),
    ("tls_protocol", "TEXT"),
    ("server_header", "TEXT"),

    # Redirect Chains
    ("redirect_chain_details", "TEXT"),

    # Element Counts & Metadata
    ("form_count", "INTEGER DEFAULT 0"),
    ("iframe_count", "INTEGER DEFAULT 0"),
    ("has_mixed_content", "BOOLEAN DEFAULT 0"),
    ("microdata_json", "TEXT"),
    ("rdfa_json", "TEXT"),
    ("plaintext_emails_json", "TEXT"),
]

NEW_TABLES_SQL = """
CREATE TABLE IF NOT EXISTS forms (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    audit_id TEXT,
    page_id INTEGER,
    page_url TEXT,
    action_url TEXT,
    method TEXT,
    form_id TEXT,
    has_password BOOLEAN DEFAULT 0,
    is_search BOOLEAN DEFAULT 0,
    is_insecure BOOLEAN DEFAULT 0,
    created_at TIMESTAMP,
    FOREIGN KEY(audit_id) REFERENCES audits(id),
    FOREIGN KEY(page_id) REFERENCES pages(id)
);
CREATE INDEX IF NOT EXISTS idx_forms_audit_id ON forms(audit_id);
CREATE INDEX IF NOT EXISTS idx_forms_page_id ON forms(page_id);

CREATE TABLE IF NOT EXISTS external_links (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    audit_id TEXT,
    source_page_id INTEGER,
    source_url TEXT,
    target_url TEXT,
    anchor_text TEXT,
    rel_attributes TEXT,
    status_code INTEGER,
    is_broken BOOLEAN DEFAULT 0,
    created_at TIMESTAMP,
    FOREIGN KEY(audit_id) REFERENCES audits(id),
    FOREIGN KEY(source_page_id) REFERENCES pages(id)
);
CREATE INDEX IF NOT EXISTS idx_external_links_audit_id ON external_links(audit_id);
"""

async def run_migrations(conn: Any) -> None:
    """Run all pending schema migrations on the provided aiosqlite connection."""
    # 1. Create any missing tables
    await conn.executescript(NEW_TABLES_SQL)

    # 2. Add any missing columns to pages table
    for col, col_type in NEW_PAGE_COLUMNS:
        try:
            await conn.execute(f"ALTER TABLE pages ADD COLUMN {col} {col_type};")
        except Exception:
            # Column already exists in SQLite table
            pass

    await conn.commit()
