"""CLI entry point and HTML-to-Markdown converter for doc2ctx."""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
import urllib.error
import urllib.request
from html.parser import HTMLParser
from pathlib import Path
from typing import Iterable
from urllib.parse import urljoin

from doc2ctx import __version__


SKIP_TAGS = {
    "script",
    "style",
    "noscript",
    "nav",
    "footer",
    "header",
    "aside",
    "svg",
    "iframe",
    "form",
    "button",
    "template",
}

HEADING_TAGS = {"h1", "h2", "h3", "h4", "h5", "h6"}


class DocHTMLParser(HTMLParser):
    """Lightweight stdlib HTML parser that extracts clean Markdown from doc pages."""

    def __init__(self, base_url: str) -> None:
        super().__init__(convert_charrefs=True)
        self.base_url = base_url
        self.title: str = ""
        self._in_title = False

        self._skip_depth = 0
        self._in_pre = False
        self._in_code = False
        self._code_lang = ""
        self._in_blockquote = False

        self._list_stack: list[tuple[str, int]] = []  # (tag, counter)
        self._link_href: str | None = None
        self._link_text: list[str] = []

        self._chunks: list[str] = []

    def _emit(self, text: str) -> None:
        if self._link_href is not None:
            self._link_text.append(text)
        else:
            self._chunks.append(text)

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        attr_map = dict(attrs)

        if tag == "title":
            self._in_title = True
            return

        if tag in SKIP_TAGS:
            self._skip_depth += 1
            return
        if self._skip_depth > 0:
            return

        if tag in HEADING_TAGS:
            level = int(tag[1])
            self._emit(f"\n\n{'#' * level} ")
        elif tag == "p":
            self._emit("\n\n")
        elif tag == "br":
            self._emit("\n")
        elif tag == "hr":
            self._emit("\n\n---\n\n")
        elif tag == "blockquote":
            self._in_blockquote = True
            self._emit("\n\n> ")
        elif tag in {"ul", "ol"}:
            self._list_stack.append((tag, 0))
            if len(self._list_stack) == 1:
                self._emit("\n")
        elif tag == "li":
            indent = "  " * max(0, len(self._list_stack) - 1)
            if self._list_stack and self._list_stack[-1][0] == "ol":
                kind, count = self._list_stack[-1]
                count += 1
                self._list_stack[-1] = (kind, count)
                self._emit(f"\n{indent}{count}. ")
            else:
                self._emit(f"\n{indent}- ")
        elif tag == "pre":
            self._in_pre = True
            self._code_lang = ""
            self._emit("\n\n```")
        elif tag == "code":
            self._in_code = True
            if self._in_pre:
                cls = attr_map.get("class") or ""
                m = re.search(r"(?:language-|lang-)([A-Za-z0-9_+-]+)", cls)
                if m:
                    self._code_lang = m.group(1)
                    self._emit(self._code_lang)
                self._emit("\n")
            else:
                self._emit("`")
        elif tag in {"strong", "b"}:
            if not self._in_pre:
                self._emit("**")
        elif tag in {"em", "i"}:
            if not self._in_pre:
                self._emit("*")
        elif tag == "a":
            href = (attr_map.get("href") or "").strip()
            if href and not href.startswith(("#", "javascript:", "mailto:")):
                self._link_href = urljoin(self.base_url, href)
                self._link_text = []

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()

        if tag == "title":
            self._in_title = False
            return

        if tag in SKIP_TAGS:
            if self._skip_depth > 0:
                self._skip_depth -= 1
            return
        if self._skip_depth > 0:
            return

        if tag in HEADING_TAGS or tag == "p":
            self._emit("\n\n")
        elif tag == "blockquote":
            self._in_blockquote = False
            self._emit("\n\n")
        elif tag in {"ul", "ol"}:
            if self._list_stack:
                self._list_stack.pop()
            if not self._list_stack:
                self._emit("\n\n")
        elif tag == "pre":
            self._in_pre = False
            self._emit("\n```\n\n")
        elif tag == "code":
            if not self._in_pre:
                self._emit("`")
            self._in_code = False
        elif tag in {"strong", "b"}:
            if not self._in_pre:
                self._emit("**")
        elif tag in {"em", "i"}:
            if not self._in_pre:
                self._emit("*")
        elif tag == "a":
            if self._link_href is not None:
                label = re.sub(r"\s+", " ", "".join(self._link_text)).strip()
                href = self._link_href
                self._link_href = None
                self._link_text = []
                if label:
                    self._emit(f"[{label}]({href})")

    def handle_data(self, data: str) -> None:
        if self._in_title:
            self.title += data
            return
        if self._skip_depth > 0:
            return

        if self._in_pre:
            self._emit(data)
        else:
            collapsed = re.sub(r"[ \t\r\n]+", " ", data)
            if collapsed:
                self._emit(collapsed)

    def get_markdown(self) -> str:
        raw = "".join(self._chunks)
        # Clean up excessive blank lines and trailing whitespace
        lines = [line.rstrip() for line in raw.splitlines()]
        cleaned = "\n".join(lines)
        cleaned = re.sub(r"\n{3,}", "\n\n", cleaned).strip()

        title = re.sub(r"\s+", " ", self.title).strip() or self.base_url
        header = f"# {title}\n\n> Source: {self.base_url}\n\n"
        if cleaned.startswith(f"# {title}"):
            return f"> Source: {self.base_url}\n\n{cleaned}\n"
        return f"{header}{cleaned}\n"


def fetch_html(url: str, timeout: float = 15.0, user_agent: str | None = None) -> str:
    ua = user_agent or f"doc2ctx/{__version__} (+https://github.com/doc2ctx)"
    req = urllib.request.Request(url, headers={"User-Agent": ua, "Accept": "text/html,application/xhtml+xml"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        charset = resp.headers.get_content_charset() or "utf-8"
        return resp.read().decode(charset, errors="replace")


def estimate_tokens(text: str) -> int:
    """Rough token estimate (~4 characters per token)."""
    return max(1, (len(text) + 3) // 4) if text else 0


def truncate_to_tokens(text: str, max_tokens: int) -> tuple[str, bool]:
    """Truncate text cleanly to fit within max_tokens (~chars/4)."""
    if max_tokens <= 0 or estimate_tokens(text) <= max_tokens:
        return text, False
    char_budget = max_tokens * 4
    notice = "\n\n<!-- [doc2ctx] Output truncated to fit --max-tokens limit -->\n"
    usable = max(0, char_budget - len(notice))
    cut = text[:usable]
    # Prefer cutting on a newline boundary
    last_nl = cut.rfind("\n")
    if last_nl > usable // 2:
        cut = cut[:last_nl]
    return cut.rstrip() + notice, True


def copy_to_clipboard(text: str) -> bool:
    """Copy text to clipboard using macOS pbcopy."""
    try:
        proc = subprocess.run(["pbcopy"], input=text.encode("utf-8"), check=False)
        return proc.returncode == 0
    except FileNotFoundError:
        return False


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="doc2ctx",
        description="Fetch a web documentation URL and convert it into clean AI-ready Markdown (llms.txt style).",
    )
    parser.add_argument("url", help="Documentation URL to fetch and convert.")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=None,
        help="Write Markdown output to a file instead of stdout.",
    )
    parser.add_argument(
        "--copy",
        action="store_true",
        help="Copy Markdown output to clipboard (uses macOS pbcopy).",
    )
    parser.add_argument(
        "--max-tokens",
        type=int,
        default=None,
        metavar="N",
        help="Truncate output to approximately N tokens (~chars/4).",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=15.0,
        help="HTTP request timeout in seconds (default: 15).",
    )
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)

    try:
        html = fetch_html(args.url, timeout=args.timeout)
    except (urllib.error.URLError, TimeoutError, ValueError) as exc:
        print(f"Error fetching {args.url}: {exc}", file=sys.stderr)
        return 1

    html_parser = DocHTMLParser(base_url=args.url)
    html_parser.feed(html)
    markdown = html_parser.get_markdown()

    truncated = False
    if args.max_tokens is not None:
        markdown, truncated = truncate_to_tokens(markdown, args.max_tokens)

    tokens = estimate_tokens(markdown)

    if args.output:
        args.output.write_text(markdown, encoding="utf-8")
        print(
            f"Wrote {args.output} (~{tokens} tokens{', truncated' if truncated else ''})",
            file=sys.stderr,
        )
    else:
        sys.stdout.write(markdown)
        print(
            f"\n[doc2ctx] ~{tokens} tokens ({len(markdown)} chars{', truncated' if truncated else ''})",
            file=sys.stderr,
        )

    if args.copy:
        if copy_to_clipboard(markdown):
            print("[doc2ctx] Copied to clipboard via pbcopy.", file=sys.stderr)
        else:
            print("[doc2ctx] Warning: pbcopy not available; could not copy to clipboard.", file=sys.stderr)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
