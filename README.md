# Academic Paper Scraper

Search and retrieve academic papers from Semantic Scholar (226M+ papers) and arXiv. Get titles, abstracts, AI summaries, citation counts, DOIs, and open-access PDFs as clean JSON. Batch search across multiple queries in one run. No API key, no browser, no proxies.

## What does it do?

Academic Paper Scraper queries the Semantic Scholar Graph API and arXiv API to find, retrieve, and analyze academic literature. It unifies results from both sources into a consistent schema — same fields regardless of where the paper came from.

**v1.1.0:** Added batch search (`queriesList`) — run multiple queries in a single job with automatic deduplication by paper ID.

## Who uses this

- **AI/LLM builders** — collect topic-specific abstracts, TLDRs, and metadata to build RAG pipelines, fine-tune models, or power research assistants without manually downloading papers
- **Systematic review and meta-analysis teams** — gather hundreds of papers across multiple search queries in one run, deduplicated and ready for screening
- **Pharma and biotech researchers** — map the drug discovery literature, track clinical trial publications, pull genomics papers by field and date range
- **Research intelligence teams** — monitor what competitors and academia are publishing; track emerging topics by citation velocity
- **Developers building research tools** — programmatic access to academic literature via REST API, Python/JS clients, or MCP for AI agent integration

## Features

- **3 scraping modes:** keyword search, paper lookup by ID, citation graph traversal
- **Batch search:** run multiple queries in one job — results merged and deduplicated by paper ID
- **226M+ papers via Semantic Scholar** — covers all academic fields, with citation metrics and AI-generated TLDRs
- **2.4M+ preprints via arXiv** — all open access, best for physics, CS, math, and adjacent fields
- **Filters:** publication year range, fields of study, open-access only, arXiv categories
- **Citation graph:** get all papers citing a work, or the full reference list of any paper
- **AI summaries (TLDR):** one-sentence AI-generated summaries for ~40% of Semantic Scholar papers
- **Open access links:** direct PDF URLs when available
- **No API key required** — works out of the box against public APIs
- **No proxy costs** — API-based, no browser rendering, no bot detection issues

---

## Scraping modes

### Mode 1: Search by keywords

```json
{
    "mode": "search",
    "query": "transformer attention mechanism",
    "yearFrom": 2020,
    "openAccessOnly": true,
    "maxResults": 50
}
```

### Mode 1b: Batch search (v1.1.0)

Run multiple queries in a single job — results merged and deduplicated across all queries:

```json
{
    "mode": "search",
    "queriesList": ["CRISPR gene editing", "base editing", "prime editing"],
    "yearFrom": 2022,
    "fieldsOfStudy": ["Biology"],
    "maxResults": 150
}
```

`queriesList` overrides `query` when provided. Ideal for systematic reviews, competitive landscape analysis, and multi-topic monitoring.

### Mode 2: Get paper by ID

Look up any paper by DOI, arXiv ID, PubMed ID, or Semantic Scholar ID. The actor auto-detects the ID type.

```json
{
    "mode": "get_paper",
    "query": "10.48550/arXiv.1706.03762"
}
```

Accepted ID formats: `10.1234/...` (DOI), `2301.12345` (arXiv), `PMID:12345678` (PubMed), 40-char hex (Semantic Scholar).

### Mode 3: Citation graph

Get all papers that cite a given paper (`citing`), or all papers it references (`cited_by`):

```json
{
    "mode": "citations",
    "query": "1706.03762",
    "citationDirection": "citing",
    "yearFrom": 2023,
    "maxResults": 100
}
```

### Mode 1c: arXiv category search

```json
{
    "mode": "search",
    "query": "large language models",
    "source": "arxiv",
    "arxivCategories": ["cs.AI", "cs.CL"],
    "sortBy": "date",
    "maxResults": 50
}
```

---

## Input parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `mode` | string | `search` | `search`, `get_paper`, or `citations` |
| `query` | string | required | Keywords (search mode) or paper ID (get_paper/citations mode) |
| `queriesList` | string[] | `[]` | Multiple search queries — merged and deduplicated. Overrides `query`. Search mode only. |
| `source` | string | `auto` | `auto`, `semantic_scholar`, or `arxiv` |
| `citationDirection` | string | `citing` | `citing` (who cited it) or `cited_by` (its references). Citations mode only. |
| `yearFrom` | integer | — | Filter: published on or after this year |
| `yearTo` | integer | — | Filter: published on or before this year |
| `fieldsOfStudy` | string[] | `[]` | Filter by field: `Computer Science`, `Medicine`, `Physics`, `Biology`, etc. (S2 only) |
| `openAccessOnly` | boolean | `false` | Only return papers with a free PDF available |
| `arxivCategories` | string[] | `[]` | Filter by arXiv category: `cs.AI`, `cs.LG`, `q-bio.NC`, etc. (arXiv source only) |
| `maxResults` | integer | `100` | Max papers to return (1–500). Free tier capped at 25. |
| `includeAbstract` | boolean | `true` | Include full abstracts in output |
| `includeTldr` | boolean | `true` | Include AI-generated summaries (S2 only) |
| `includeCitationCounts` | boolean | `true` | Include citation, reference, and influential citation counts |
| `sortBy` | string | `relevance` | `relevance` or `date` (newest first) |
| `requestIntervalSecs` | number | `3.0` | Seconds between API requests (0.5–10) |

---

## Output

Results are saved to the default dataset. Download as JSON, CSV, Excel, or XML from the Output tab.

### Paper fields

| Field | Type | Description |
|-------|------|-------------|
| `title` | string | Paper title |
| `authors` | string[] | Author names |
| `year` | integer | Publication year |
| `publication_date` | string | Full date (YYYY-MM-DD) |
| `venue` | string | Conference or journal name |
| `journal` | string | Journal with volume and page numbers |
| `abstract` | string | Full abstract text |
| `tldr` | string | AI-generated one-sentence summary (S2 only, ~40% coverage) |
| `doi` | string | Digital Object Identifier |
| `arxiv_id` | string | arXiv preprint ID |
| `pubmed_id` | string | PubMed ID |
| `semantic_scholar_id` | string | Semantic Scholar paper ID |
| `corpus_id` | integer | Semantic Scholar Corpus ID |
| `fields_of_study` | string[] | Academic fields (e.g. `Computer Science`, `Medicine`) |
| `publication_types` | string[] | Type: `JournalArticle`, `Conference`, `Preprint`, etc. |
| `citation_count` | integer | Total citations received |
| `reference_count` | integer | Number of references in the paper |
| `influential_citation_count` | integer | Citations that significantly impacted the citing paper |
| `is_open_access` | boolean | Whether a free full-text PDF is available |
| `open_access_pdf_url` | string | Direct PDF link (when available) |
| `external_urls` | object | Links to Semantic Scholar, arXiv, DOI resolver |
| `source` | string | Which API provided this result: `semantic_scholar` or `arxiv` |
| `scraped_at` | string | ISO 8601 UTC timestamp |

### Example output

```json
{
    "schema_version": "1.0",
    "type": "academic_paper",
    "title": "Attention is All you Need",
    "authors": ["Ashish Vaswani", "Noam Shazeer", "Niki Parmar", "Jakob Uszkoreit"],
    "year": 2017,
    "publication_date": "2017-06-12",
    "venue": "Neural Information Processing Systems",
    "journal": "",
    "abstract": "The dominant sequence transduction models are based on complex recurrent or convolutional neural networks...",
    "tldr": "A new simple network architecture, the Transformer, based solely on attention mechanisms, dispensing with recurrence and convolutions entirely.",
    "doi": "10.48550/arXiv.1706.03762",
    "arxiv_id": "1706.03762",
    "pubmed_id": "",
    "semantic_scholar_id": "204e3073870fae3d05bcbc2f6a8e263d9b72e776",
    "corpus_id": 13756489,
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
    "scraped_at": "2025-03-01T12:00:00+00:00"
}
```

---

## Data sources

### Semantic Scholar (default)

- **226M+ papers** across every academic field
- Citation counts, reference counts, and **influential citation counts**
- **AI-generated TLDR summaries** for ~40% of papers
- Accepts DOI, arXiv ID, PubMed ID, and Semantic Scholar ID for direct lookup
- Rate limit: 1 req/sec without an API key (built-in compliance)

### arXiv

- **2.4M+ preprints** in physics, math, CS, quantitative biology, finance, statistics, and engineering
- All papers are open access with direct PDF links
- Best for finding the latest preprints before peer review
- Category filtering: `cs.AI`, `cs.LG`, `physics.hep-th`, `q-bio.NC`, etc.
- No citation data (use Semantic Scholar for citation metrics)

**When to use each:** Use `auto` (default). It picks Semantic Scholar for general queries and arXiv when you specify `arxivCategories`. Override to `arxiv` explicitly when you need preprints or category-specific filtering.

---

## Cost

This actor uses **pay-per-event (PPE) pricing** — you pay only for results you get.

- **$0.50 per 1,000 results** ($0.0005 per paper)
- **No proxy costs** — API-based, no browser, no residential proxies needed
- **Free tier: 25 results per run** — no subscription required
- **Paid tier: up to 500 results per run**

Typical run: 100 papers takes about 10 seconds. Cost: **$0.05**.

---

## MCP Integration

This actor works as an MCP tool via Apify's hosted MCP server. AI agents can query academic literature directly — no custom server setup required.

- **Endpoint:** `https://mcp.apify.com?tools=labrat011/academic-paper-scraper`
- **Auth:** `Authorization: Bearer <APIFY_TOKEN>`
- **Transport:** Streamable HTTP
- **Works with:** Claude Desktop, Cursor, VS Code, Windsurf, Warp, Gemini CLI

**Claude Desktop / Cursor config:**

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

**Example agent prompts:**

- "Find the 20 most-cited papers on CRISPR base editing published since 2021"
- "Search for papers on 'retrieval augmented generation' and 'knowledge graphs' — combine the results"
- "Look up the paper at DOI 10.1038/s41586-021-03819-2 and summarize its key findings"
- "What papers cite 'Attention Is All You Need'? Show me the top 30 by citation count from 2023 onward"
- "Search arXiv for recent cs.AI and cs.CL papers on instruction tuning, sorted by date"
- "Gather all open-access papers on mRNA vaccine efficacy from 2020–2024 for a literature review"

---

## Technical details

- Python 3.12, async with `httpx.AsyncClient`
- Semantic Scholar Graph API v1 (no credentials required)
- arXiv Atom API with XML parsing (`xml.etree.ElementTree`)
- Automatic paper ID detection: DOI, arXiv ID, PubMed ID, Corpus ID, S2 ID
- Paginated fetching with configurable rate limiting
- Batch push (25 items) for memory efficiency
- State persistence for resumable runs across Apify platform migrations

---

## Limitations

- **S2 rate limits** may slow large requests. The scraper respects the 1 req/sec limit but Semantic Scholar may throttle during peak times — built-in retry with exponential backoff handles this.
- **arXiv has no citation data.** Citation counts, reference counts, and TLDR summaries are only available from Semantic Scholar.
- **TLDR coverage is ~40%.** Not available for all papers in Semantic Scholar.
- **Year filtering on arXiv is client-side** — arXiv's API does not support native year ranges, so the scraper fetches extra pages and filters locally.
- **Max 500 results per run** — Semantic Scholar's API imposes practical limits on unauthenticated bulk access.
- **`get_paper` and `citations` modes require a single query** — batch via `queriesList` applies to search mode only.

---

## FAQ

### Which source should I use?

Use `auto` (the default). It picks Semantic Scholar for general searches and arXiv when you set `arxivCategories`. Override to `arxiv` only when you need preprints or arXiv-specific category filtering.

### How does batch search work?

Set `queriesList` to an array of search terms. The actor runs each query sequentially and merges results into a single dataset, removing duplicates matched by Semantic Scholar paper ID, arXiv ID, DOI, or title. This is the recommended approach for systematic reviews (run all your PICO terms at once) and research monitoring (track multiple topics in a scheduled daily run).

### Can I search by author?

Yes — include the author name in your query: `"Yann LeCun deep learning"`. Semantic Scholar's relevance ranking considers author names. For a precise author search, add the name in quotes: `"\"Yoshua Bengio\" neural networks"`.

### How do I look up a specific paper?

Use `get_paper` mode with any identifier: DOI (`10.1038/...`), arXiv ID (`2301.12345`), PubMed ID (`PMID:12345678`), or Semantic Scholar ID (40-char hex). The actor auto-detects the format.

### What's the difference between `citing` and `cited_by`?

- `citing` — returns papers that **cite** your target (who referenced it afterward)
- `cited_by` — returns papers that your target **cites** (its own bibliography)

Use `citing` to find follow-on work and measure influence. Use `cited_by` to trace a paper's intellectual lineage.

### Can I use this with the Apify API?

Yes. Call the actor via the Apify REST API, poll for results, and download in JSON, CSV, Excel, or XML. Works with the Apify Python and JavaScript client libraries.

---

## Feedback

Found a bug or have a feature request? Open an issue on the Issues tab in Apify Console.
