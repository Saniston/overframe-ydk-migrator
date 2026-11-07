# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project status

Implemented per `README.md` (written in Portuguese, the spec). `main.py` handles CLI args and orchestration; `migrador.py` holds layout parsing, whole-line substitution and per-deck I/O; `layout_api.py` fetches Grand Master Rare cards from the YGOPRODeck API (`--atualizar-layout`), writes sample decks to `samples/`, asks the user to confirm them, then regenerates the layout (previous file moved to `backup_layout/`, timestamped); `layout_migracao.txt` is a sample mapping. No lint/build tooling. Keep user-facing language (CLI output, messages, docs) in Portuguese.

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
- Layout lines with a legacy code but empty new code are "pending": ignored in migration, reported as one aggregate warning.
- API update: Overframe code is always legacy code + 1. Samples pair each legacy code with its Overframe code on consecutive lines; `#main` holds at most 60 lines, `#extra` at most 14 (game limit is 15) and only cards whose `frameType` contains `fusion`/`synchro`/`xyz`/`link`; `!side` stays empty. The layout is written only after the user confirms the samples (declining leaves it untouched and returns 1). Backups are never overwritten; `--simular` writes nothing and does not prompt.
- Does not validate that new codes exist in EDOPro; unmapped codes remain unchanged.
- Output is a per-deck summary (`arquivo.ydk -> N cartas substituídas`) followed by a total (`Concluído: X substituições em Y decks.`).
