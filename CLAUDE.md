# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project status

Implemented per `README.md` (written in Portuguese, the spec). `main.py` handles CLI args and orchestration; `migrador.py` holds layout parsing, whole-line substitution and per-deck I/O; `layout_migracao.txt` is a sample mapping. No lint/build tooling. Keep user-facing language (CLI output, messages, docs) in Portuguese.

Tests (stdlib `unittest`):

```
python -m unittest                                  # all
python -m unittest test_migrador.TestMigrador.test_simular_nao_grava   # single test
```

## What it is

A Python 3.9+ standard-library-only CLI that rewrites EDOPro `.ydk` deck files, replacing legacy card codes with Overframe / extended-art codes according to a mapping file.

Intended invocation:

```
python main.py --pasta "C:\EDOPro\deck" --layout "layout_migracao.txt" [--backup] [--simular]
```

`--backup` (write `.bak` copy before modifying) and `--simular` (dry run, no writes) are optional and described in the README as suggestions.

## Behavior that must be preserved

- **Layout file**: one mapping per line, `nome do card|código legado|código novo` (3 fields split on `|`). Blank lines and `#` comment lines are ignored. Lines with a field count other than 3 are skipped and reported without aborting. Duplicate legacy codes produce a warning (ambiguous).
- **Whole-line matching only**: a deck line is replaced only if its stripped content is exactly equal to a legacy code (so `146986414` must not match `46986414`, and `#main` / `!side` / `#created by ...` lines are never touched). Every occurrence is replaced individually, so duplicate copies are all migrated.
- **Only the given folder's `.ydk` files** are processed; subfolders are ignored.
- **Preserve each deck's original encoding and line endings** on read/write.
- Does not validate that new codes exist in EDOPro; unmapped codes remain unchanged.
- Output is a per-deck summary (`arquivo.ydk -> N cartas substituídas`) followed by a total (`Concluído: X substituições em Y decks.`).
