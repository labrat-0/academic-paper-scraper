# Academic Paper Scraper

Search and retrieve academic papers from Semantic Scholar (226M+ papers) and arXiv. Get titles, authors, abstracts, AI-generated summaries, citation counts, DOIs, and open access PDFs as clean JSON. API-based -- no browser needed, no bot detection issues, fast and reliable. MCP-ready for AI agent integration.

## What does it do?

Academic Paper Scraper queries the Semantic Scholar Graph API and arXiv API to find, retrieve, and analyze academic papers. It unifies results into a consistent schema regardless of source.

**Three modes:**

- **Search** -- keyword search across 226M+ papers (Semantic Scholar) or arXiv preprints
- **Get Paper** -- look up a specific paper by DOI, arXiv ID, PubMed ID, or Semantic Scholar ID
- **Citations** -- traverse the citation graph: find papers that cite a given paper, or papers it references

## Use cases

- **Literature review** -- quickly find all papers on a topic with citation counts and AI summaries
- **Citation analysis** -- map influence networks by traversing citing/cited papers
- **Research monitoring** -- track new publications in your field
- **Meta-analysis** -- gather paper metadata at scale for systematic reviews
- **AI agent tooling** -- give AI agents access to the academic literature via MCP
- **Competitive research intelligence** -- track what competitors are publishing

## What data does it extract?

Each record represents one academic paper:

| Field | Description |
|-------|-------------|
| `title` | Paper title |
| `authors` | List of author names |
| `year` | Publication year |
| `publication_date` | Full date (YYYY-MM-DD) |
| `venue` | Conference or journal name |
| `journal` | Journal with volume/pages |
| `abstract` | Full abstract text |
| `tldr` | AI-generated one-sentence summary (Semantic Scholar, ~40% of papers) |
| `doi` | Digital Object Identifier |
| `arxiv_id` | arXiv preprint ID |
| `pubmed_id` | PubMed ID |
| `semantic_scholar_id` | Semantic Scholar paper ID |
| `fields_of_study` | Academic fields (e.g. "Computer Science", "Medicine") |
| `publication_types` | Type (JournalArticle, Conference, Preprint, etc.) |
| `citation_count` | Number of citations |
| `reference_count` | Number of references |
| `influential_citation_count` | Citations that significantly impacted the citing paper |
| `is_open_access` | Whether free full-text is available |
| `open_access_pdf_url` | Direct PDF link (when available) |
| `external_urls` | Links to Semantic Scholar, arXiv, DOI resolver |
| `source` | Which API provided this result |

## Input

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `mode` | string | `search` | `search`, `get_paper`, or `citations` |
| `query` | string | required | Search keywords or paper ID (DOI, arXiv ID, PMID, S2 ID) |
| `source` | string | `auto` | `auto`, `semantic_scholar`, or `arxiv` |
| `citationDirection` | string | `citing` | For citations mode: `citing` or `cited_by` |
| `yearFrom` | integer | - | Filter by publication year (from) |
| `yearTo` | integer | - | Filter by publication year (to) |
| `fieldsOfStudy` | array | `[]` | Filter by field (e.g. "Computer Science") |
| `openAccessOnly` | boolean | `false` | Only return papers with free PDFs |
| `arxivCategories` | array | `[]` | arXiv category filter (e.g. "cs.AI", "physics.hep-th") |
| `maxResults` | integer | `100` | Max papers to return (1-500) |
| `includeAbstract` | boolean | `true` | Include full abstracts |
| `includeTldr` | boolean | `true` | Include AI summaries |
| `includeCitationCounts` | boolean | `true` | Include citation metrics |
| `sortBy` | string | `relevance` | `relevance` or `date` |
| `requestIntervalSecs` | number | `1.5` | Min seconds between API requests |

### Example: Search for papers

```json
{
    "mode": "search",
    "query": "transformer attention mechanism",
    "maxResults": 20,
    "yearFrom": 2020,
    "openAccessOnly": true
}
```

### Example: Look up a paper by DOI

```json
{
    "mode": "get_paper",
    "query": "10.48550/arXiv.1706.03762"
}
```

### Example: Get citations for "Attention Is All You Need"

```json
{
    "mode": "citations",
    "query": "1706.03762",
    "citationDirection": "citing",
    "maxResults": 50,
    "yearFrom": 2023
}
```

### Example: Search arXiv by category

```json
{
    "mode": "search",
    "query": "large language models",
    "source": "arxiv",
    "arxivCategories": ["cs.AI", "cs.CL"],
    "sortBy": "date",
    "maxResults": 30
}
```

## Output

### Example: Search results (Semantic Scholar)

```json
[
    {
        "schema_version": "1.0",
        "type": "academic_paper",
        "title": "Attention is All you Need",
        "authors": ["Ashish Vaswani", "Noam Shazeer", "Niki Parmar", "Jakob Uszkoreit", "Llion Jones", "Aidan N. Gomez", "Lukasz Kaiser", "Illia Polosukhin"],
        "year": 2017,
        "publication_date": "2017-06-12",
        "venue": "Neural Information Processing Systems",
        "journal": "",
        "abstract": "The dominant sequence transduction models are based on complex recurrent or convolutional neural networks...",
        "tldr": "A new simple network architecture, the Transformer, based solely on attention mechanisms, dispensing with recurrence and convolutions entirely, is proposed.",
        "doi": "10.48550/arXiv.1706.03762",
        "arxiv_id": "1706.03762",
        "pubmed_id": "",
        "semantic_scholar_id": "204e3073870fae3d05bcbc2f6a8e263d9b72e776",
        "fields_of_study": ["Computer Science"],
        "publication_types": ["JournalArticle", "Conference"],
        "citation_count": 140000,
        "reference_count": 41,
        "influential_citation_count": 12000,
        "is_open_access": true,
        "open_access_pdf_url": "https://arxiv.org/pdf/1706.03762",
        "external_urls": {
            "semantic_scholar": "https://www.semanticscholar.org/paper/204e3073870fae3d05bcbc2f6a8e263d9b72e776",
            "doi_url": "https://doi.org/10.48550/arXiv.1706.03762",
            "arxiv_abs": "https://arxiv.org/abs/1706.03762",
            "arxiv_pdf": "https://arxiv.org/pdf/1706.03762"
        },
        "source": "semantic_scholar",
        "scraped_at": "2025-01-15T12:00:00+00:00"
    }
]
```

Output is trimmed for readability. Each record includes all fields from the schema.

## Data sources

### Semantic Scholar (default)

- **226M+ papers** across all academic fields
- Best for general searches and citation analysis
- Provides AI-generated TLDR summaries, citation counts, influential citation counts
- Accepts DOI, arXiv ID, PubMed ID, and Semantic Scholar ID for lookups
- Rate limit: 1 req/sec (no API key needed)

### arXiv

- **2.4M+ preprints** in physics, math, CS, quantitative biology, finance, statistics, and engineering
- Best for finding the latest preprints and category-specific searches
- All papers are open access with direct PDF links
- Rate limit: 3 sec between requests recommended

## Limitations

- **Semantic Scholar rate limits** may slow down large requests. The scraper respects the 1 req/sec limit but S2 may throttle during peak times.
- **arXiv has no citation data.** Citation counts, reference counts, and TLDR summaries are only available via Semantic Scholar.
- **TLDR coverage is ~40%.** The AI summary is not available for all papers in Semantic Scholar.
- **Year filtering on arXiv** is done client-side (arXiv API does not support year ranges natively), so the scraper may need to fetch extra pages to fill the result set.
- **PubMed direct search is not implemented** in v1. However, Semantic Scholar indexes PubMed papers, so PubMed content is searchable via the Semantic Scholar source. Direct PubMed ID lookup via `get_paper` mode works.

## Cost

This actor uses **pay-per-event (PPE) pricing**. You pay only for the results you get.

- **$0.50 per 1,000 results** ($0.0005 per result)
- **No proxy costs** -- API-based, no browser needed
- Free tier: **25 results per run** (no subscription required)

Typical run: searching for 100 papers takes about 10 seconds. Cost: $0.05.

---

## MCP Integration

This actor works as an MCP tool through Apify's hosted MCP server. No custom server needed.

- **Endpoint:** `https://mcp.apify.com?tools=labrat011/academic-paper-scraper`
- **Auth:** `Authorization: Bearer <APIFY_TOKEN>`
- **Transport:** Streamable HTTP
- **Works with:** Claude Desktop, Cursor, VS Code, Windsurf, Warp, Gemini CLI

**Example MCP config (Claude Desktop / Cursor):**

```json
{
    "mcpServers": {
        "academic-paper-scraper": {
            "url": "https://mcp.apify.com?tools=labrat011/academic-paper-scraper",
            "headers": {
                "Authorization": "Bearer <APIFY_TOKEN>"
            }
        }
    }
}
```

**Agent prompt examples:**

- "Find the 10 most cited papers on CRISPR gene editing published since 2020"
- "Look up the paper with DOI 10.1038/s41586-021-03819-2 and summarize its findings"
- "What papers cite 'Attention Is All You Need'? Show me the top 20 by citation count"
- "Search arXiv for recent papers on quantum error correction in the cs.AI and quant-ph categories"

The agent calls this tool, gets structured JSON with titles, authors, abstracts, citation counts, and AI summaries, and can synthesize literature reviews or identify research trends programmatically.

---

## Technical details

- Python 3.12, async architecture with `httpx.AsyncClient`
- Semantic Scholar Graph API v1 (no API key required)
- arXiv Atom API with XML parsing (`xml.etree.ElementTree`)
- Automatic paper ID detection: DOI, arXiv ID, PubMed ID, Corpus ID, S2 ID
- Paginated fetching with rate limiting
- Batch push (25 items) for memory efficiency
- State persistence for resumable runs

---

## FAQ

### Which source should I use?

Use `auto` (the default). It picks Semantic Scholar for general searches (largest corpus, richest metadata) and arXiv when you specify arXiv categories. Override to `arxiv` if you specifically want preprints or need arXiv-specific category filtering.

### Can I search by author?

Yes. Include the author name in your search query, e.g. `"Yann LeCun deep learning"`. Semantic Scholar's relevance ranking considers author names.

### How do I find a specific paper?

Use `get_paper` mode with any identifier: DOI (`10.1038/...`), arXiv ID (`2301.12345`), PubMed ID (`PMID:12345678`), or Semantic Scholar ID (40-char hex). The scraper auto-detects the ID type.

### What's the difference between `citing` and `cited_by` in citations mode?

- `citing` returns papers that **cite** your target paper (who referenced it later)
- `cited_by` returns papers that your target paper **references** (its bibliography)

### Can I use this with the Apify API?

Yes. Call the actor via the Apify API and retrieve results programmatically in JSON, CSV, or other formats. Works with the Apify Python and JavaScript clients.

---

## Feedback

Found a bug or have a feature request? Open an issue on the actor's Issues tab in Apify Console.
