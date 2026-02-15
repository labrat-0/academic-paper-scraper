"""
Pydantic models for Academic Paper Scraper input and output.

All output fields have defaults -- no missing keys in output.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ScraperInput(BaseModel):
    """Validated scraper configuration parsed from actor input."""

    mode: str = "search"  # search, get_paper, citations
    query: str = ""
    source: str = "auto"  # auto, semantic_scholar, arxiv
    citation_direction: str = "citing"  # citing, cited_by

    # Filters
    year_from: int | None = None
    year_to: int | None = None
    fields_of_study: list[str] = Field(default_factory=list)
    open_access_only: bool = False
    arxiv_categories: list[str] = Field(default_factory=list)

    # Output settings
    max_results: int = Field(default=100, ge=1, le=500)
    include_abstract: bool = True
    include_tldr: bool = True
    include_citation_counts: bool = True
    sort_by: str = "relevance"  # relevance, date

    # Advanced
    request_interval_secs: float = Field(default=3.0, ge=0.5, le=10.0)

    @classmethod
    def from_actor_input(cls, raw: dict[str, Any]) -> ScraperInput:
        """Map camelCase actor input keys to snake_case model fields."""
        return cls(
            mode=raw.get("mode", "search"),
            query=raw.get("query", ""),
            source=raw.get("source", "auto"),
            citation_direction=raw.get("citationDirection", "citing"),
            year_from=raw.get("yearFrom"),
            year_to=raw.get("yearTo"),
            fields_of_study=raw.get("fieldsOfStudy", []),
            open_access_only=raw.get("openAccessOnly", False),
            arxiv_categories=raw.get("arxivCategories", []),
            max_results=raw.get("maxResults", 100),
            include_abstract=raw.get("includeAbstract", True),
            include_tldr=raw.get("includeTldr", True),
            include_citation_counts=raw.get("includeCitationCounts", True),
            sort_by=raw.get("sortBy", "relevance"),
            request_interval_secs=raw.get("requestIntervalSecs", 3.0),
        )

    def validate_input(self) -> str | None:
        """Return error string if input is invalid, else None."""
        if not self.query.strip():
            return "Provide a search query or paper ID in the 'query' field."

        if self.mode not in ("search", "get_paper", "citations"):
            return f"Invalid mode: '{self.mode}'. Use 'search', 'get_paper', or 'citations'."

        if self.source not in ("auto", "semantic_scholar", "arxiv"):
            return f"Invalid source: '{self.source}'. Use 'auto', 'semantic_scholar', or 'arxiv'."

        if self.citation_direction not in ("citing", "cited_by"):
            return f"Invalid citationDirection: '{self.citation_direction}'. Use 'citing' or 'cited_by'."

        if self.year_from and self.year_to and self.year_from > self.year_to:
            return f"yearFrom ({self.year_from}) cannot be greater than yearTo ({self.year_to})."

        return None

    def resolve_source(self) -> str:
        """Resolve 'auto' source to a concrete source based on input.

        Returns 'semantic_scholar' or 'arxiv'.
        """
        if self.source != "auto":
            return self.source

        # If arXiv categories are specified, use arXiv
        if self.arxiv_categories:
            return "arxiv"

        # If query looks like an arXiv ID, use Semantic Scholar (it indexes arXiv)
        # For general search, Semantic Scholar is the better default
        return "semantic_scholar"


class PaperRecord(BaseModel):
    """One academic paper.

    Every field has a default -- output never has missing keys.
    """

    schema_version: str = "1.0"
    type: str = "academic_paper"

    # Core metadata
    title: str = ""
    authors: list[str] = Field(default_factory=list)
    year: int = 0
    publication_date: str = ""  # YYYY-MM-DD
    venue: str = ""  # conference or journal name
    journal: str = ""  # journal name + volume/pages

    # Content
    abstract: str = ""
    tldr: str = ""  # AI-generated summary (Semantic Scholar)

    # Identifiers
    doi: str = ""
    arxiv_id: str = ""
    pubmed_id: str = ""
    semantic_scholar_id: str = ""
    corpus_id: int = 0  # Semantic Scholar Corpus ID

    # Classification
    fields_of_study: list[str] = Field(default_factory=list)
    publication_types: list[str] = Field(default_factory=list)

    # Impact metrics
    citation_count: int = 0
    reference_count: int = 0
    influential_citation_count: int = 0

    # Access
    is_open_access: bool = False
    open_access_pdf_url: str = ""

    # External links
    external_urls: dict[str, str] = Field(default_factory=dict)
    # e.g. {"semantic_scholar": "...", "arxiv_abs": "...", "doi_url": "..."}

    # Metadata
    source: str = ""  # semantic_scholar, arxiv
    scraped_at: str = ""
