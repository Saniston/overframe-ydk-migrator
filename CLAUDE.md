# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project status

Implemented per `README.md` (written in Portuguese, the spec). `main.py` handles CLI args and orchestration; `migrador.py` holds layout parsing, whole-line substitution and per-deck I/O; `layout_api.py` (`--atualizar-layout`) reads the extended-art card names from Yugipedia (MediaWiki API, page `Extended_art`), resolves them to legacy codes/`frameType` via the YGOPRODeck API (`name=A|B|...` in batches), and confirms each Overframe code against the local EDOPro `.cdb` SQLite databases; it then writes sample decks to `<deck folder>/samples/` (deck folder = `--pasta`, or `<EDOPro>/deck`; subfolder so migration never touches them), asks the user to confirm them, and regenerates the layout (previous file moved to `backup_layout/`, timestamped) plus `<layout>_pendencias.txt`; `layout_migracao.txt` is a sample mapping. No lint/build tooling. Keep user-facing language (CLI output, messages, docs) in Portuguese.

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
- Layout update: no rarity filter; the card list comes only from Yugipedia. A card enters the layout only if the EDOPro `.cdb` has `legacy + 1` with the same base card (`alias or id`); Overframe code is then legacy + 1. Unconfirmed cards (and names not found in YGOPRODeck) go to the pendências file (`nome|legado|` with a `#` comment giving the reason and other art codes as suggestions), never into the layout; the file is written only with the layout and removed when empty. The EDOPro folder comes from `--edopro` or is deduced (parent of `--pasta`, then common install paths) and the user is always asked to confirm the deduced folder or type another; without a folder containing `.cdb` files the update aborts. Samples pair each legacy code with its Overframe code on consecutive lines; `#main` holds at most 60 lines, `#extra` at most 14 (game limit is 15) and only cards whose `frameType` contains `fusion`/`synchro`/`xyz`/`link`; `!side` stays empty. The layout is written only after the user confirms the samples (declining leaves it untouched and returns 1). Backups are never overwritten; `--simular` writes nothing and does not ask to confirm samples (it still asks for the EDOPro folder unless `--edopro` is given).
- Deck migration does not validate that new codes exist in EDOPro (only the layout update does); unmapped codes remain unchanged.
- Output is a per-deck summary (`arquivo.ydk -> N cartas substituídas`) followed by a total (`Concluído: X substituições em Y decks.`).
