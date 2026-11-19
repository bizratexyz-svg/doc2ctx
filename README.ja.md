# doc2ctx

[English](README.md) | **日本語**

[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

Web ドキュメントの URL を取得し、トークン数の見積もり付きでクリーンな AI 向け Markdown（`llms.txt` スタイル）に変換する、外部依存ゼロの Python CLI ツールです。

## 主な機能

- **外部依存ゼロ**: Python 標準ライブラリの `urllib.request` と `html.parser` のみを使用します。
- **不要要素の除去**: `nav`、`footer`、`header`、`aside`、`script`、`style`、`svg`、`iframe`、`form` などの定型要素を自動で取り除きます。
- **クリーンな Markdown 変換**: 見出し、段落、リスト、リンク、引用、コードブロックを `llms.txt` スタイルの Markdown に変換します。
- **トークン数管理**: トークン数（`~chars/4`）を概算し、`--max-tokens` による安全な切り詰めに対応しています。
- **クリップボード＆ファイル出力**: macOS の `--copy`（`pbcopy`）および `-o/--output <file>` に対応しています。

## クイックスタート

Python 3.11 以上と [uv](https://docs.astral.sh/uv/) が必要です。

```bash
# ドキュメントを取得してクリーンな Markdown を標準出力に表示
uv run doc2ctx https://docs.python.org/3/library/pathlib.html

# 約 2000 トークンに制限してクリップボードへ直接コピー（macOS）
uv run doc2ctx https://docs.python.org/3/library/pathlib.html --max-tokens 2000 --copy

# ファイルに保存
uv run doc2ctx https://docs.python.org/3/library/pathlib.html -o pathlib-docs.md
```

## CLI オプション

| オプション | 説明 |
| :--- | :--- |
| `url` | 取得・変換するドキュメントの URL |
| `-o, --output FILE` | 標準出力の代わりにファイルへ Markdown を書き出し |
| `--copy` | macOS の `pbcopy` 経由で Markdown 出力をクリップボードにコピー |
| `--max-tokens N` | 出力を約 `N` トークン（`~chars/4`）に切り詰め |
| `--timeout SEC` | HTTP リクエストのタイムアウト秒数（デフォルト: `15`） |
| `--version` | バージョンを表示して終了 |

## 出力例

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

## ライセンス

MIT
