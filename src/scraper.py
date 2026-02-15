"""
Core academic paper search engine.

API clients for Semantic Scholar Graph API and arXiv API,
with unified output as PaperRecord models.

Modes:
  - search:    keyword search across Semantic Scholar or arXiv
  - get_paper: lookup by DOI, arXiv ID, PubMed ID, or S2 ID
  - citations: get citing/cited papers for a given paper
"""

from __future__ import annotations

import asyncio
import logging
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from typing import AsyncGenerator
from urllib.parse import quote

import httpx

from .models import PaperRecord, ScraperInput
from .utils import RateLimiter, detect_paper_id_type, s2_paper_id

logger = logging.getLogger("src")

# ---------------------------------------------------------------------------
# Semantic Scholar API
# ---------------------------------------------------------------------------

_S2_BASE = "https://api.semanticscholar.org/graph/v1"

# Fields to request from S2 API -- covers all our output fields
_S2_PAPER_FIELDS = ",".join([
    "title",
    "authors",
    "abstract",
    "year",
    "venue",
    "publicationDate",
    "journal",
    "externalIds",
    "fieldsOfStudy",
    "publicationTypes",
    "citationCount",
    "referenceCount",
    "influentialCitationCount",
    "isOpenAccess",
    "openAccessPdf",
    "tldr",
])

# Max results per S2 API page
_S2_PAGE_SIZE = 100

# arXiv API
_ARXIV_BASE = "http://export.arxiv.org/api/query"
_ARXIV_PAGE_SIZE = 100  # arXiv allows up to 2000, but 100 is reasonable

# Atom namespace for arXiv XML parsing
_ATOM_NS = "http://www.w3.org/2005/Atom"
_ARXIV_NS = "http://arxiv.org/schemas/atom"


class AcademicPaperScraper:
    """Searches and retrieves academic papers from multiple sources.

    Supports Semantic Scholar and arXiv APIs with unified PaperRecord output.
    """

    # Retry settings for S2 429 rate-limit responses
    _S2_MAX_RETRIES = 3
    _S2_BACKOFF_SECS = (5.0, 10.0, 20.0)
    _S2_USER_AGENT = (
        "AcademicPaperScraper/1.0 (Apify Actor; "
        "https://apify.com/labrat011/academic-paper-scraper)"
    )

    def __init__(
        self,
        config: ScraperInput,
        http_client: httpx.AsyncClient,
    ) -> None:
        self._config = config
        self._client = http_client
        self._rate_limiter = RateLimiter(config.request_interval_secs)

    async def _s2_request(
        self,
        url: str,
        params: dict[str, str | int] | None = None,
    ) -> httpx.Response | None:
        """Make an S2 API request with retry + exponential backoff on 429.

        Returns the Response on success, or None if all retries are exhausted
        or a non-retryable error occurs.
        """
        for attempt in range(self._S2_MAX_RETRIES + 1):
            await self._rate_limiter.wait()
            try:
                resp = await self._client.get(
                    url,
                    params=params,
                    timeout=30,
                    headers={"User-Agent": self._S2_USER_AGENT},
                )
            except httpx.HTTPError as exc:
                logger.error("S2 request failed: %s", exc)
                return None

            if resp.status_code != 429:
                return resp

            # 429 -- rate limited, retry with backoff
            if attempt >= self._S2_MAX_RETRIES:
                logger.error(
                    "S2 rate limited after %d retries, giving up. "
                    "Response body: %s",
                    self._S2_MAX_RETRIES,
                    resp.text[:500],
                )
                return None

            # Respect Retry-After header if present, otherwise use backoff
            retry_after = resp.headers.get("Retry-After")
            if retry_after:
                try:
                    wait_secs = float(retry_after)
                except ValueError:
                    wait_secs = self._S2_BACKOFF_SECS[attempt]
            else:
                wait_secs = self._S2_BACKOFF_SECS[attempt]

            logger.warning(
                "S2 rate limited (429), retry %d/%d in %.1fs. "
                "Response body: %s",
                attempt + 1,
                self._S2_MAX_RETRIES,
                wait_secs,
                resp.text[:300],
            )
            await asyncio.sleep(wait_secs)

        return None  # should not reach here

    async def run(self) -> AsyncGenerator[dict, None]:
        """Execute the configured mode and yield paper records."""
        mode = self._config.mode

        if mode == "search":
            async for record in self._search():
                yield record
        elif mode == "get_paper":
            async for record in self._get_paper():
                yield record
        elif mode == "citations":
            async for record in self._get_citations():
                yield record
        else:
            logger.error("Unknown mode: %s", mode)

    # ------------------------------------------------------------------
    # Search mode
    # ------------------------------------------------------------------

    async def _search(self) -> AsyncGenerator[dict, None]:
        """Keyword search across the configured source."""
        source = self._config.resolve_source()
        logger.info("Search mode: source=%s, query='%s'", source, self._config.query)

        if source == "semantic_scholar":
            async for record in self._s2_search():
                yield record
        elif source == "arxiv":
            async for record in self._arxiv_search():
                yield record

    async def _s2_search(self) -> AsyncGenerator[dict, None]:
        """Search Semantic Scholar Graph API."""
        query = self._config.query.strip()
        max_results = self._config.max_results
        offset = 0
        total_yielded = 0

        while total_yielded < max_results:
            page_size = min(_S2_PAGE_SIZE, max_results - total_yielded)
            params: dict[str, str | int] = {
                "query": query,
                "offset": offset,
                "limit": page_size,
                "fields": _S2_PAPER_FIELDS,
            }

            # Year filter
            if self._config.year_from or self._config.year_to:
                year_range = f"{self._config.year_from or ''}-{self._config.year_to or ''}"
                params["year"] = year_range

            # Fields of study filter
            if self._config.fields_of_study:
                params["fieldsOfStudy"] = ",".join(self._config.fields_of_study)

            # Open access filter
            if self._config.open_access_only:
                params["openAccessPdf"] = ""  # S2 uses empty string to filter

            resp = await self._s2_request(
                f"{_S2_BASE}/paper/search",
                params=params,
            )
            if resp is None:
                return

            if resp.status_code != 200:
                logger.error("S2 search returned %d: %s", resp.status_code, resp.text[:500])
                return

            data = resp.json()
            total_available = data.get("total", 0)
            papers = data.get("data", [])

            if not papers:
                break

            logger.info(
                "S2 search page: offset=%d, got=%d, total_available=%d",
                offset, len(papers), total_available,
            )

            for paper in papers:
                if total_yielded >= max_results:
                    return
                record = _s2_paper_to_record(paper, self._config)
                if self._config.open_access_only and not record.is_open_access:
                    continue
                yield record.model_dump()
                total_yielded += 1

            offset += len(papers)
            if offset >= total_available:
                break

        logger.info("S2 search complete: %d papers yielded", total_yielded)

    async def _arxiv_search(self) -> AsyncGenerator[dict, None]:
        """Search arXiv API."""
        query = self._build_arxiv_query()
        max_results = self._config.max_results
        start = 0
        total_yielded = 0

        while total_yielded < max_results:
            page_size = min(_ARXIV_PAGE_SIZE, max_results - total_yielded)
            params: dict[str, str | int] = {
                "search_query": query,
                "start": start,
                "max_results": page_size,
            }

            # Sort
            if self._config.sort_by == "date":
                params["sortBy"] = "submittedDate"
                params["sortOrder"] = "descending"
            else:
                params["sortBy"] = "relevance"
                params["sortOrder"] = "descending"

            await self._rate_limiter.wait()
            try:
                resp = await self._client.get(
                    _ARXIV_BASE,
                    params=params,
                    timeout=30,
                )
            except httpx.HTTPError as exc:
                logger.error("arXiv search request failed: %s", exc)
                return

            if resp.status_code != 200:
                logger.error("arXiv search returned %d: %s", resp.status_code, resp.text[:500])
                return

            papers = _parse_arxiv_xml(resp.text)
            if not papers:
                break

            logger.info(
                "arXiv search page: start=%d, got=%d papers",
                start, len(papers),
            )

            for paper in papers:
                if total_yielded >= max_results:
                    return

                record = _arxiv_entry_to_record(paper, self._config)

                # Year filter (arXiv API doesn't support year filter natively)
                if self._config.year_from and record.year < self._config.year_from:
                    continue
                if self._config.year_to and record.year > self._config.year_to:
                    continue

                yield record.model_dump()
                total_yielded += 1

            start += len(papers)

            # arXiv returns fewer than requested when no more results
            if len(papers) < page_size:
                break

        logger.info("arXiv search complete: %d papers yielded", total_yielded)

    def _build_arxiv_query(self) -> str:
        """Build arXiv search query string."""
        query = self._config.query.strip()

        # If arXiv categories specified, add category filter
        if self._config.arxiv_categories:
            cat_query = " OR ".join(
                f"cat:{cat}" for cat in self._config.arxiv_categories
            )
            if query:
                return f"all:{query} AND ({cat_query})"
            return cat_query

        # Default: search all fields
        return f"all:{query}"

    # ------------------------------------------------------------------
    # Get Paper mode
    # ------------------------------------------------------------------

    async def _get_paper(self) -> AsyncGenerator[dict, None]:
        """Look up a single paper by ID via Semantic Scholar."""
        query = self._config.query.strip()
        id_type, normalized = detect_paper_id_type(query)

        if id_type == "unknown":
            # Try treating it as a Semantic Scholar search with limit 1
            logger.info("Unknown ID format '%s', trying S2 search with limit 1", query)
            old_max = self._config.max_results
            self._config.max_results = 1
            async for record in self._s2_search():
                yield record
            self._config.max_results = old_max
            return

        paper_id = s2_paper_id(id_type, normalized)
        logger.info("Looking up paper: %s (type=%s)", paper_id, id_type)

        resp = await self._s2_request(
            f"{_S2_BASE}/paper/{quote(paper_id, safe=':')}",
            params={"fields": _S2_PAPER_FIELDS},
        )
        if resp is None:
            return

        if resp.status_code == 404:
            logger.warning("Paper not found: %s", paper_id)
            yield PaperRecord(
                title=f"Paper not found: {query}",
                source="semantic_scholar",
                scraped_at=_now_iso(),
            ).model_dump()
            return

        if resp.status_code != 200:
            logger.error("S2 paper lookup returned %d: %s", resp.status_code, resp.text[:500])
            return

        paper = resp.json()
        record = _s2_paper_to_record(paper, self._config)
        yield record.model_dump()

    # ------------------------------------------------------------------
    # Citations mode
    # ------------------------------------------------------------------

    async def _get_citations(self) -> AsyncGenerator[dict, None]:
        """Get papers that cite or are cited by a given paper."""
        query = self._config.query.strip()
        id_type, normalized = detect_paper_id_type(query)

        if id_type == "unknown":
            logger.error(
                "Cannot look up citations for unknown ID format: '%s'. "
                "Provide a DOI, arXiv ID, PubMed ID, or Semantic Scholar ID.",
                query,
            )
            return

        paper_id = s2_paper_id(id_type, normalized)
        direction = self._config.citation_direction
        max_results = self._config.max_results

        # S2 endpoint: /paper/{id}/citations or /paper/{id}/references
        if direction == "citing":
            endpoint = f"{_S2_BASE}/paper/{quote(paper_id, safe=':')}/citations"
        else:
            endpoint = f"{_S2_BASE}/paper/{quote(paper_id, safe=':')}/references"

        logger.info(
            "Citations mode: paper=%s, direction=%s, max=%d",
            paper_id, direction, max_results,
        )

        offset = 0
        total_yielded = 0

        # S2 citation fields -- nested under citingPaper/citedPaper
        citation_fields = _S2_PAPER_FIELDS

        while total_yielded < max_results:
            page_size = min(_S2_PAGE_SIZE, max_results - total_yielded)
            params: dict[str, str | int] = {
                "offset": offset,
                "limit": page_size,
                "fields": citation_fields,
            }

            resp = await self._s2_request(endpoint, params=params)
            if resp is None:
                return

            if resp.status_code == 404:
                logger.warning("Paper not found for citations: %s", paper_id)
                return

            if resp.status_code != 200:
                logger.error("S2 citations returned %d: %s", resp.status_code, resp.text[:500])
                return

            data = resp.json()
            entries = data.get("data", [])

            if not entries:
                break

            logger.info(
                "Citations page: offset=%d, got=%d entries",
                offset, len(entries),
            )

            for entry in entries:
                if total_yielded >= max_results:
                    return

                # Citations endpoint nests under 'citingPaper' or 'citedPaper'
                paper_key = "citingPaper" if direction == "citing" else "citedPaper"
                paper = entry.get(paper_key)
                if not paper:
                    continue

                # Skip papers with no title (ghost entries)
                if not paper.get("title"):
                    continue

                record = _s2_paper_to_record(paper, self._config)
                yield record.model_dump()
                total_yielded += 1

            offset += len(entries)

            # If we got fewer than requested, no more pages
            if len(entries) < page_size:
                break

        logger.info("Citations fetch complete: %d papers yielded", total_yielded)


# ---------------------------------------------------------------------------
# S2 response → PaperRecord
# ---------------------------------------------------------------------------


def _s2_paper_to_record(paper: dict, config: ScraperInput) -> PaperRecord:
    """Convert a Semantic Scholar API paper object to a PaperRecord."""
    ext_ids = paper.get("externalIds") or {}
    journal_info = paper.get("journal") or {}
    oa_pdf = paper.get("openAccessPdf") or {}
    tldr_info = paper.get("tldr") or {}
    authors_list = paper.get("authors") or []

    # Build journal string
    journal_str = ""
    if journal_info:
        name = journal_info.get("name", "")
        volume = journal_info.get("volume", "")
        pages = journal_info.get("pages", "")
        parts = [name]
        if volume:
            parts.append(f"vol. {volume}")
        if pages:
            parts.append(f"pp. {pages}")
        journal_str = ", ".join(p for p in parts if p)

    # Build external URLs
    urls: dict[str, str] = {}
    s2_id = paper.get("paperId", "")
    if s2_id:
        urls["semantic_scholar"] = f"https://www.semanticscholar.org/paper/{s2_id}"
    doi = ext_ids.get("DOI", "")
    if doi:
        urls["doi_url"] = f"https://doi.org/{doi}"
    arxiv_id = ext_ids.get("ArXiv", "")
    if arxiv_id:
        urls["arxiv_abs"] = f"https://arxiv.org/abs/{arxiv_id}"
        urls["arxiv_pdf"] = f"https://arxiv.org/pdf/{arxiv_id}"

    return PaperRecord(
        title=paper.get("title", "") or "",
        authors=[a.get("name", "") for a in authors_list if a.get("name")],
        year=paper.get("year") or 0,
        publication_date=paper.get("publicationDate", "") or "",
        venue=paper.get("venue", "") or "",
        journal=journal_str,
        abstract=paper.get("abstract", "") or "" if config.include_abstract else "",
        tldr=tldr_info.get("text", "") or "" if config.include_tldr else "",
        doi=doi,
        arxiv_id=arxiv_id,
        pubmed_id=str(ext_ids.get("PubMed", "")) if ext_ids.get("PubMed") else "",
        semantic_scholar_id=s2_id,
        corpus_id=ext_ids.get("CorpusId", 0) or 0,
        fields_of_study=paper.get("fieldsOfStudy") or [],
        publication_types=paper.get("publicationTypes") or [],
        citation_count=paper.get("citationCount", 0) or 0 if config.include_citation_counts else 0,
        reference_count=paper.get("referenceCount", 0) or 0 if config.include_citation_counts else 0,
        influential_citation_count=paper.get("influentialCitationCount", 0) or 0 if config.include_citation_counts else 0,
        is_open_access=paper.get("isOpenAccess", False) or False,
        open_access_pdf_url=oa_pdf.get("url", "") or "",
        external_urls=urls,
        source="semantic_scholar",
        scraped_at=_now_iso(),
    )


# ---------------------------------------------------------------------------
# arXiv XML parsing
# ---------------------------------------------------------------------------


def _parse_arxiv_xml(xml_text: str) -> list[dict]:
    """Parse arXiv Atom XML response into a list of entry dicts."""
    entries: list[dict] = []
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as exc:
        logger.error("Failed to parse arXiv XML: %s", exc)
        return []

    for entry in root.findall(f"{{{_ATOM_NS}}}entry"):
        parsed: dict = {}

        # Title
        title_el = entry.find(f"{{{_ATOM_NS}}}title")
        parsed["title"] = _clean_text(title_el.text or "" if title_el is not None else "")

        # Abstract (summary)
        summary_el = entry.find(f"{{{_ATOM_NS}}}summary")
        parsed["abstract"] = _clean_text(summary_el.text or "" if summary_el is not None else "")

        # Authors
        authors = []
        for author_el in entry.findall(f"{{{_ATOM_NS}}}author"):
            name_el = author_el.find(f"{{{_ATOM_NS}}}name")
            if name_el is not None and name_el.text:
                authors.append(name_el.text.strip())
        parsed["authors"] = authors

        # Published date
        published_el = entry.find(f"{{{_ATOM_NS}}}published")
        parsed["published"] = published_el.text.strip() if published_el is not None and published_el.text else ""

        # Updated date
        updated_el = entry.find(f"{{{_ATOM_NS}}}updated")
        parsed["updated"] = updated_el.text.strip() if updated_el is not None and updated_el.text else ""

        # arXiv ID (from <id> element: http://arxiv.org/abs/YYMM.NNNNN[vN])
        id_el = entry.find(f"{{{_ATOM_NS}}}id")
        raw_id = id_el.text.strip() if id_el is not None and id_el.text else ""
        # Extract just the arxiv ID from the URL
        arxiv_id = raw_id.replace("http://arxiv.org/abs/", "").replace("https://arxiv.org/abs/", "")
        parsed["arxiv_id"] = arxiv_id

        # Links (abs page + PDF)
        links: dict[str, str] = {}
        for link_el in entry.findall(f"{{{_ATOM_NS}}}link"):
            rel = link_el.get("rel", "")
            href = link_el.get("href", "")
            link_type = link_el.get("type", "")
            title = link_el.get("title", "")
            if title == "pdf" or link_type == "application/pdf":
                links["pdf"] = href
            elif rel == "alternate":
                links["abs"] = href
        parsed["links"] = links

        # Categories
        categories = []
        for cat_el in entry.findall(f"{{{_ATOM_NS}}}category"):
            term = cat_el.get("term", "")
            if term:
                categories.append(term)
        parsed["categories"] = categories

        # Primary category
        primary_cat_el = entry.find(f"{{{_ARXIV_NS}}}primary_category")
        parsed["primary_category"] = primary_cat_el.get("term", "") if primary_cat_el is not None else ""

        # DOI
        doi_el = entry.find(f"{{{_ARXIV_NS}}}doi")
        parsed["doi"] = doi_el.text.strip() if doi_el is not None and doi_el.text else ""

        # Journal ref
        journal_el = entry.find(f"{{{_ARXIV_NS}}}journal_ref")
        parsed["journal_ref"] = journal_el.text.strip() if journal_el is not None and journal_el.text else ""

        # Comment
        comment_el = entry.find(f"{{{_ARXIV_NS}}}comment")
        parsed["comment"] = comment_el.text.strip() if comment_el is not None and comment_el.text else ""

        entries.append(parsed)

    return entries


def _arxiv_entry_to_record(entry: dict, config: ScraperInput) -> PaperRecord:
    """Convert a parsed arXiv entry to a PaperRecord."""
    published = entry.get("published", "")
    year = 0
    pub_date = ""
    if published:
        try:
            dt = datetime.fromisoformat(published.replace("Z", "+00:00"))
            year = dt.year
            pub_date = dt.strftime("%Y-%m-%d")
        except ValueError:
            pass

    arxiv_id = entry.get("arxiv_id", "")
    doi = entry.get("doi", "")
    links = entry.get("links", {})

    # Build external URLs
    urls: dict[str, str] = {}
    if links.get("abs"):
        urls["arxiv_abs"] = links["abs"]
    if links.get("pdf"):
        urls["arxiv_pdf"] = links["pdf"]
    if doi:
        urls["doi_url"] = f"https://doi.org/{doi}"

    # arXiv papers are always open access
    pdf_url = links.get("pdf", "")

    return PaperRecord(
        title=entry.get("title", ""),
        authors=entry.get("authors", []),
        year=year,
        publication_date=pub_date,
        venue="arXiv",
        journal=entry.get("journal_ref", ""),
        abstract=entry.get("abstract", "") if config.include_abstract else "",
        tldr="",  # arXiv doesn't provide TLDR
        doi=doi,
        arxiv_id=arxiv_id,
        pubmed_id="",
        semantic_scholar_id="",
        corpus_id=0,
        fields_of_study=_arxiv_cats_to_fields(entry.get("categories", [])),
        publication_types=["Preprint"],
        citation_count=0,  # arXiv doesn't provide citation counts
        reference_count=0,
        influential_citation_count=0,
        is_open_access=True,
        open_access_pdf_url=pdf_url,
        external_urls=urls,
        source="arxiv",
        scraped_at=_now_iso(),
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _clean_text(text: str) -> str:
    """Clean whitespace from text (arXiv abstracts have lots of newlines)."""
    if not text:
        return ""
    # Replace multiple whitespace with single space
    return " ".join(text.split()).strip()


def _arxiv_cats_to_fields(categories: list[str]) -> list[str]:
    """Map arXiv category prefixes to broad field names."""
    field_map: dict[str, str] = {
        "cs": "Computer Science",
        "math": "Mathematics",
        "physics": "Physics",
        "astro-ph": "Physics",
        "cond-mat": "Physics",
        "gr-qc": "Physics",
        "hep-ex": "Physics",
        "hep-lat": "Physics",
        "hep-ph": "Physics",
        "hep-th": "Physics",
        "nucl-ex": "Physics",
        "nucl-th": "Physics",
        "quant-ph": "Physics",
        "nlin": "Physics",
        "stat": "Mathematics",
        "q-bio": "Biology",
        "q-fin": "Economics",
        "econ": "Economics",
        "eess": "Engineering",
    }
    fields: list[str] = []
    seen: set[str] = set()
    for cat in categories:
        prefix = cat.split(".")[0] if "." in cat else cat
        field = field_map.get(prefix, "")
        if field and field not in seen:
            seen.add(field)
            fields.append(field)
    return fields
