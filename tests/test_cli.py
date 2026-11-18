"""Unit tests for doc2ctx HTML-to-Markdown conversion, token budgeting, and CLI."""

from __future__ import annotations

import urllib.error
from pathlib import Path

import pytest

from doc2ctx import cli
from doc2ctx.cli import DocHTMLParser, estimate_tokens, main, truncate_to_tokens


SAMPLE_HTML = """<!doctype html>
<html>
  <head>
    <title>Sample Docs</title>
    <style>body { color: red; }</style>
  </head>
  <body>
    <nav><a href="/home">Navigation Link</a></nav>
    <main>
      <h1>Getting Started</h1>
      <p>Install via <code>uv</code> and read the <a href="/guide/intro">Intro Guide</a>.</p>
      <ul>
        <li>First item</li>
        <li>Second item</li>
      </ul>
      <pre><code class="language-python">print("hello")</code></pre>
    </main>
    <footer>Copyright 2026</footer>
  </body>
</html>
"""


def test_doc_html_parser_strips_boilerplate_and_converts_markdown() -> None:
    parser = DocHTMLParser(base_url="https://docs.example.com/start")
    parser.feed(SAMPLE_HTML)
    md = parser.get_markdown()

    assert "# Sample Docs" in md
    assert "> Source: https://docs.example.com/start" in md
    assert "# Getting Started" in md
    assert "`uv`" in md
    assert "[Intro Guide](https://docs.example.com/guide/intro)" in md
    assert "- First item" in md
    assert "```python\nprint(\"hello\")\n```" in md
    assert "Navigation Link" not in md
    assert "Copyright 2026" not in md
    assert "color: red" not in md


def test_estimate_tokens() -> None:
    assert estimate_tokens("") == 0
    assert estimate_tokens("abcd") == 1
    assert estimate_tokens("a" * 400) == 100


def test_truncate_to_tokens() -> None:
    text = "\n".join(f"Line {i}: " + ("x" * 40) for i in range(50))
    unchanged, was_truncated = truncate_to_tokens(text, max_tokens=10_000)
    assert not was_truncated
    assert unchanged == text

    cut, was_truncated = truncate_to_tokens(text, max_tokens=50)
    assert was_truncated is True
    assert "Output truncated to fit --max-tokens limit" in cut
    assert estimate_tokens(cut) <= 55


def test_cli_writes_to_file_without_network(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(cli, "fetch_html", lambda url, timeout=15.0: SAMPLE_HTML)
    out_file = tmp_path / "out.md"

    rc = main(["https://docs.example.com/start", "-o", str(out_file)])
    assert rc == 0
    assert out_file.exists()
    content = out_file.read_text(encoding="utf-8")
    assert "# Sample Docs" in content
    assert "Wrote" in capsys.readouterr().err


def test_cli_stdout_and_max_tokens(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    long_html = "<html><head><title>Long</title></head><body>" + ("<p>" + "word " * 100 + "</p>") * 10 + "</body></html>"
    monkeypatch.setattr(cli, "fetch_html", lambda url, timeout=15.0: long_html)

    rc = main(["https://docs.example.com/long", "--max-tokens", "60"])
    captured = capsys.readouterr()
    assert rc == 0
    assert "Output truncated to fit --max-tokens limit" in captured.out
    assert "truncated" in captured.err


def test_cli_handles_fetch_error(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    def _fail(url: str, timeout: float = 15.0) -> str:
        raise urllib.error.URLError("offline")

    monkeypatch.setattr(cli, "fetch_html", _fail)
    rc = main(["https://docs.example.com/unreachable"])
    assert rc == 1
    assert "Error fetching" in capsys.readouterr().err
