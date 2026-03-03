"""
title: Exa Neural Web Search
author: Stylishseahorse
version: 1.0.0
description: Neural web search powered by Exa.ai. Set EXA_API_KEY in the tool valves to activate. Get a free key at https://dashboard.exa.ai
"""

from __future__ import annotations

import asyncio
import aiohttp
from typing import Any, Awaitable, Callable, Optional

from pydantic import BaseModel, Field


class Tools:
    class Valves(BaseModel):
        EXA_API_KEY: str = Field(
            default="",
            description="Your Exa API key. Get one free at https://dashboard.exa.ai",
        )
        MAX_RESULTS: int = Field(
            default=5,
            description="Number of search results to return (1–10).",
        )
        USE_AUTOPROMPT: bool = Field(
            default=True,
            description="Let Exa automatically optimise your query for neural search.",
        )
        INCLUDE_CONTENTS: bool = Field(
            default=True,
            description="Fetch and include page text content in each result.",
        )
        CONTENTS_MAX_CHARS: int = Field(
            default=1500,
            description="Maximum characters of page content to include per result.",
        )
        SEARCH_TYPE: str = Field(
            default="auto",
            description=(
                "Search mode:\n"
                "  auto    - Exa chooses the best type automatically (recommended)\n"
                "  neural  - semantic / meaning-based search\n"
                "  keyword - traditional keyword search"
            ),
        )
        INCLUDE_DOMAINS: str = Field(
            default="",
            description=(
                "Comma-separated list of domains to restrict results to "
                "(e.g. 'arxiv.org, github.com'). Leave empty for unrestricted search."
            ),
        )
        EXCLUDE_DOMAINS: str = Field(
            default="",
            description=(
                "Comma-separated list of domains to exclude from results "
                "(e.g. 'pinterest.com, quora.com'). Leave empty to exclude nothing."
            ),
        )

    def __init__(self):
        self.valves = self.Valves()

    async def search(
        self,
        query: str,
        __event_emitter__: Optional[Callable[[dict[str, Any]], Awaitable[Any]]] = None,
    ) -> str:
        """
        Search the web using Exa's neural search API and return rich results.

        :param query: The search query or question to look up.
        :return: Formatted search results with titles, URLs, dates, and content snippets.
        """
        exa_key = self.valves.EXA_API_KEY
        if not exa_key:
            return (
                "⚠️ Exa API key is not set. Enter it in the **EXA_API_KEY** valve "
                "in the Exa Search tool settings. "
                "Get a free key at https://dashboard.exa.ai"
            )

        if __event_emitter__:
            await __event_emitter__(
                {
                    "type": "status",
                    "data": {"description": f"Searching Exa: {query}", "done": False},
                }
            )

        headers = {
            "x-api-key": exa_key,
            "Content-Type": "application/json",
        }

        exa_payload: dict[str, Any] = {
            "query": query,
            "numResults": max(1, min(10, self.valves.MAX_RESULTS)),
            "useAutoprompt": self.valves.USE_AUTOPROMPT,
        }

        if self.valves.SEARCH_TYPE and self.valves.SEARCH_TYPE != "auto":
            exa_payload["type"] = self.valves.SEARCH_TYPE

        include_domains = [
            d.strip() for d in self.valves.INCLUDE_DOMAINS.split(",") if d.strip()
        ]
        exclude_domains = [
            d.strip() for d in self.valves.EXCLUDE_DOMAINS.split(",") if d.strip()
        ]
        if include_domains:
            exa_payload["includeDomains"] = include_domains
        if exclude_domains:
            exa_payload["excludeDomains"] = exclude_domains

        if self.valves.INCLUDE_CONTENTS:
            exa_payload["contents"] = {
                "text": {"maxCharacters": self.valves.CONTENTS_MAX_CHARS},
                "highlights": {"numSentences": 2, "highlightsPerUrl": 1},
            }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    "https://api.exa.ai/search",
                    headers=headers,
                    json=exa_payload,
                    timeout=aiohttp.ClientTimeout(total=30),
                ) as resp:
                    if resp.status != 200:
                        error_body = await resp.text()
                        if __event_emitter__:
                            await __event_emitter__(
                                {
                                    "type": "status",
                                    "data": {
                                        "description": "Exa search failed.",
                                        "done": True,
                                    },
                                }
                            )
                        return f"Exa search failed (HTTP {resp.status}): {error_body}"
                    exa_data = await resp.json()
        except asyncio.TimeoutError:
            return "Exa search timed out after 30 seconds."
        except Exception as exc:
            return f"Exa search error: {exc}"

        results = exa_data.get("results", [])

        if not results:
            if __event_emitter__:
                await __event_emitter__(
                    {
                        "type": "status",
                        "data": {"description": "No results found.", "done": True},
                    }
                )
            return f'No results found for "{query}".'

        if __event_emitter__:
            await __event_emitter__(
                {
                    "type": "status",
                    "data": {
                        "description": f"Found {len(results)} result(s) for: {query}",
                        "done": True,
                    },
                }
            )

        lines: list[str] = [f"## Exa Search Results\n**Query:** {query}\n"]

        for i, r in enumerate(results, 1):
            title = r.get("title") or "Untitled"
            url = r.get("url") or ""
            published = r.get("publishedDate") or r.get("published_date") or ""
            author = r.get("author") or ""
            score = r.get("score")

            highlights = r.get("highlights") or []
            text = " … ".join(highlights) if highlights else (r.get("text") or "")
            if text and len(text) > self.valves.CONTENTS_MAX_CHARS:
                text = text[: self.valves.CONTENTS_MAX_CHARS] + " …"

            header = f"### {i}. [{title}]({url})"
            meta_parts: list[str] = []
            if published:
                meta_parts.append(f"📅 {published[:10]}")
            if author:
                meta_parts.append(f"✍️ {author}")
            if score is not None:
                meta_parts.append(f"relevance: {score:.3f}")
            meta = (
                "  \n" + " &nbsp;·&nbsp; ".join(meta_parts) if meta_parts else ""
            )

            entry = header + meta
            if text:
                entry += f"\n\n{text}"

            lines.append(entry)

        return "\n\n---\n\n".join(lines)
