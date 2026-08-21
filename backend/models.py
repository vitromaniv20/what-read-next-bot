from dataclasses import dataclass
from typing import Optional
import html


@dataclass
class Book:
    id: int
    title: str
    author: str
    genre: str
    is_famous: int
    description: str
    goodreads_query: str
    cover_url: Optional[str] = None
    rating: Optional[float] = None
    pages: Optional[int] = None

    @property
    def goodreads_url(self) -> str:
        return f"https://www.goodreads.com/search?q={self.goodreads_query}"

    @property
    def short_description(self) -> str:
        """Returns an HTML-escaped, truncated description safe for Telegram."""
        max_len = 600
        desc = self.description[:max_len] + "..." if len(self.description) > max_len else self.description
        # Strip raw HTML-like tags from source CSV data, then escape for Telegram HTML
        clean = desc.replace("<", "").replace(">", "")
        return html.escape(clean)