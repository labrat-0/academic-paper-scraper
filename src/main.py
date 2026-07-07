"""
Apify Actor entry point for Academic Paper Scraper.

Handles actor lifecycle, free tier enforcement,
batch push with max_results guard, and state persistence.
"""

from __future__ import annotations

import logging
import os

import httpx
from apify import Actor

from .models import ScraperInput
from .scraper import AcademicPaperScraper

logger = logging.getLogger("src")

# Free tier: 25 results max for non-paying users
_FREE_TIER_LIMIT = 25
_BATCH_SIZE = 25


async def main() -> None:
    async with Actor:
        actor_input = await Actor.get_input() or {}
        config = ScraperInput.from_actor_input(actor_input)

        # Validate input
        validation_error = config.validate_input()
        if validation_error:
            logger.error("Input validation failed: %s", validation_error)
            await Actor.set_status_message(f"Error: {validation_error}")
            await Actor.fail(status_message=validation_error)
            return

        # Determine result limit (free tier enforcement)
        is_at_home = os.getenv("APIFY_IS_AT_HOME", "").lower() in ("1", "true")
        is_paying = os.getenv("APIFY_USER_IS_PAYING", "").lower() in ("1", "true")
        max_results = config.max_results
        if is_at_home and not is_paying:
            max_results = min(max_results, _FREE_TIER_LIMIT)
            logger.info(
                "Free tier: limiting to %d results. Subscribe for up to 500.",
                max_results,
            )

        # Status message
        source = config.resolve_source()
        mode_desc = {
            "search": f"Searching {source} for '{config.query}'",
            "get_paper": f"Looking up paper: {config.query}",
            "citations": f"Fetching {'citing' if config.citation_direction == 'citing' else 'cited'} papers for: {config.query}",
        }
        await Actor.set_status_message(
            f"{mode_desc.get(config.mode, 'Processing')} (max {max_results} results)..."
        )

        dataset = await Actor.open_dataset()

        # State persistence for resume
        state = await Actor.use_state(default_value={"total_pushed": 0})
        total_pushed: int = state.get("total_pushed", 0)
        batch: list[dict] = []

        async with httpx.AsyncClient(
            follow_redirects=True,
            limits=httpx.Limits(max_connections=10, max_keepalive_connections=5),
        ) as http_client:
            scraper = AcademicPaperScraper(config, http_client)

            try:
                async for record in scraper.run():
                    if total_pushed >= max_results:
                        logger.info(
                            "Reached max results (%d), stopping", max_results
                        )
                        break

                    batch.append(record)

                    if len(batch) >= _BATCH_SIZE:
                        # Guard: don't exceed max_results
                        remaining = max_results - total_pushed
                        flush = batch[:remaining]
                        await dataset.push_data(flush)
                        total_pushed += len(flush)
                        state["total_pushed"] = total_pushed
                        await Actor.set_status_message(
                            f"Found {total_pushed} paper(s)..."
                        )
                        logger.info(
                            "Pushed batch of %d (total: %d)",
                            len(flush),
                            total_pushed,
                        )
                        batch = []

                        if total_pushed >= max_results:
                            break
            except Exception as exc:
                logger.exception("Unhandled exception during scraping: %s", exc)
                await Actor.set_status_message(f"Error: {exc}")
                # Flush anything we've accumulated before the crash
                if batch:
                    await dataset.push_data(batch)
                    total_pushed += len(batch)
                if total_pushed > 0:
                    state["total_pushed"] = total_pushed
                return

        # Flush remaining
        if batch and total_pushed < max_results:
            remaining = max_results - total_pushed
            flush = batch[:remaining]
            await dataset.push_data(flush)
            total_pushed += len(flush)
            state["total_pushed"] = total_pushed

        logger.info("Scraping complete. Total records: %d", total_pushed)

        # Report 0 results without hard-failing - API sources may be rate-limited
        if total_pushed == 0:
            err_msg = "All API sources returned 0 results (rate-limited or unreachable)."
            logger.warning(err_msg)
            await Actor.set_status_message(status_message=err_msg)
            return

        done_msg = f"Done! Found {total_pushed} paper(s)."
        if is_at_home and not is_paying and total_pushed >= _FREE_TIER_LIMIT:
            done_msg += f" Free tier limit ({_FREE_TIER_LIMIT}) reached. Subscribe for up to 500 results."
        await Actor.set_status_message(done_msg)
