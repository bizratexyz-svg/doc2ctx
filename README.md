# doc2ctx

[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

A zero-dependency Python CLI tool that fetches web documentation URLs and converts them into clean, AI-ready Markdown (`llms.txt` style) with token estimation.

## Features

- **Zero External Dependencies**: Uses Python's stdlib `urllib.request` and `html.parser` only.
- **Boilerplate Stripping**: Automatically removes `nav`, `footer`, `header`, `aside`, `script`, `style`, `svg`, `iframe`, and `form` elements.
- **Clean Markdown**: Converts headings, paragraphs, lists, links, blockquotes, and fenced code blocks into `llms.txt`-style Markdown.
- **Token Budgeting**: Estimates token count (`~chars/4`) and supports clean truncation with `--max-tokens`.
- **Clipboard & File Output**: Supports macOS `--copy` (`pbcopy`) and `-o/--output <file>`.

## Quick Start

Requires Python 3.11+ and [uv](https://docs.astral.sh/uv/).

```bash
# Fetch and print clean Markdown to stdout
uv run doc2ctx https://docs.python.org/3/library/pathlib.html

# Limit to ~2000 tokens and copy directly to clipboard (macOS)
uv run doc2ctx https://docs.python.org/3/library/pathlib.html --max-tokens 2000 --copy

# Save to a file
uv run doc2ctx https://docs.python.org/3/library/pathlib.html -o pathlib-docs.md
```

## CLI Options

| Option | Description |
| :--- | :--- |
| `url` | Documentation URL to fetch and convert |
| `-o, --output FILE` | Write Markdown output to a file instead of stdout |
| `--copy` | Copy Markdown output to clipboard via macOS `pbcopy` |
| `--max-tokens N` | Truncate output to approximately `N` tokens (`~chars/4`) |
| `--timeout SEC` | HTTP request timeout in seconds (default: `15`) |
| `--version` | Show version and exit |

## Example Output

```text
$ uv run doc2ctx https://docs.python.org/3/library/pathlib.html --max-tokens 150
# pathlib — Object-oriented filesystem paths

> Source: https://docs.python.org/3/library/pathlib.html

This module offers classes representing filesystem paths with semantics
appropriate for different operating systems.

## Basic use

```python
from pathlib import Path
p = Path('.')
[x for x in p.iterdir() if x.is_dir()]
```

<!-- [doc2ctx] Output truncated to fit --max-tokens limit -->

[doc2ctx] ~148 tokens (590 chars, truncated)
```

## License

MIT
