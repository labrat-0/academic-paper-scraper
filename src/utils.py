"""
Utilities for Academic Paper Scraper.

Rate limiting and paper ID detection helpers.
"""

from __future__ import annotations

import asyncio
import logging
import re

logger = logging.getLogger("src")


class RateLimiter:
    """Async rate limiter ensuring minimum interval between requests."""

    def __init__(self, interval_secs: float = 1.5) -> None:
        self._interval = interval_secs
        self._lock = asyncio.Lock()
        self._last_request: float = 0.0

    async def wait(self) -> None:
        async with self._lock:
            now = asyncio.get_running_loop().time()
            elapsed = now - self._last_request
            if elapsed < self._interval:
                await asyncio.sleep(self._interval - elapsed)
            self._last_request = asyncio.get_running_loop().time()


# ---------------------------------------------------------------------------
# Paper ID detection
# ---------------------------------------------------------------------------

# DOI pattern: 10.XXXX/anything
_DOI_RE = re.compile(r"^10\.\d{4,9}/\S+$")

# arXiv ID: YYMM.NNNNN (with optional vN version)
_ARXIV_RE = re.compile(r"^(\d{4}\.\d{4,5})(v\d+)?$")

# PubMed ID: PMID:12345678 or just digits (8+ digits)
_PMID_RE = re.compile(r"^(?:PMID:\s*)?(\d{7,9})$", re.IGNORECASE)

# Semantic Scholar Corpus ID: CorpusId:12345678
_CORPUS_ID_RE = re.compile(r"^CorpusId:\s*(\d+)$", re.IGNORECASE)

# Semantic Scholar paper ID: 40-char hex
_S2_ID_RE = re.compile(r"^[0-9a-f]{40}$", re.IGNORECASE)


def detect_paper_id_type(query: str) -> tuple[str, str]:
    """Detect the type of paper identifier from a query string.

    Returns:
        (id_type, normalized_id) where id_type is one of:
        'doi', 'arxiv', 'pmid', 'corpus_id', 's2_id', or 'unknown'.
    """
    query = query.strip()

    # Check DOI (with or without prefix)
    if query.startswith("DOI:"):
        return "doi", query[4:].strip()
    if _DOI_RE.match(query):
        return "doi", query

    # Check arXiv (with or without prefix)
    if query.lower().startswith("arxiv:"):
        arxiv_id = query[6:].strip()
        return "arxiv", arxiv_id
    m = _ARXIV_RE.match(query)
    if m:
        return "arxiv", query

    # Check PubMed ID
    if query.upper().startswith("PMID:"):
        m = _PMID_RE.match(query)
        if m:
            return "pmid", m.group(1)
    # Bare numeric (8-9 digits could be PMID)
    if query.isdigit() and 7 <= len(query) <= 9:
        return "pmid", query

    # Corpus ID
    m = _CORPUS_ID_RE.match(query)
    if m:
        return "corpus_id", m.group(1)

    # S2 paper ID (40 hex chars)
    if _S2_ID_RE.match(query):
        return "s2_id", query

    return "unknown", query


def s2_paper_id(id_type: str, normalized_id: str) -> str:
    """Convert a detected paper ID to Semantic Scholar's lookup format.

    Semantic Scholar accepts:
        - DOI:10.xxxx/...
        - ArXiv:YYMM.NNNNN
        - PMID:12345678
        - CorpusId:12345678
        - Raw S2 paper ID (40 hex chars)
    """
    if id_type == "doi":
        return f"DOI:{normalized_id}"
    if id_type == "arxiv":
        return f"ArXiv:{normalized_id}"
    if id_type == "pmid":
        return f"PMID:{normalized_id}"
    if id_type == "corpus_id":
        return f"CorpusId:{normalized_id}"
    if id_type == "s2_id":
        return normalized_id
    # Unknown -- try raw (S2 will 404 if invalid)
    return normalized_id
