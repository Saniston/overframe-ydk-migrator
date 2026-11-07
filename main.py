"""Migra cartas de decks .ydk do EDOPro para as versões Overframe."""

import argparse
import sys
from pathlib import Path

from migrador import carregar_layout, listar_decks, migrar_deck


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--pasta", required=True, help="Pasta com os arquivos .ydk (subpastas ignoradas)")
    ap.add_argument("--layout", required=True, help="Arquivo de layout de migração")
    ap.add_argument("--backup", action="store_true", help="Cria cópia .bak de cada deck alterado")
    ap.add_argument("--simular", action="store_true", help="Mostra o que seria alterado, sem gravar")
    args = ap.parse_args(argv)

    pasta = Path(args.pasta)
    if not pasta.is_dir():
        print(f"Erro: pasta não encontrada: {pasta}", file=sys.stderr)
        return 1
    if not Path(args.layout).is_file():
        print(f"Erro: layout não encontrado: {args.layout}", file=sys.stderr)
        return 1

    mapa, avisos = carregar_layout(args.layout)
    for aviso in avisos:
        print(f"AVISO: {aviso}", file=sys.stderr)

    decks = listar_decks(pasta)
    print(f"Layout carregado: {len(mapa)} mapeamentos")
    print(f"Decks encontrados: {len(decks)}\n")

    total = alterados = 0
    for deck in decks:
        try:
            r = migrar_deck(deck, mapa, backup=args.backup, simular=args.simular)
        except OSError as e:
            print(f"{deck.name}  -> ERRO: {e}", file=sys.stderr)
            continue
        print(f"{deck.name}  -> {r.substituicoes} cartas substituídas")
        total += r.substituicoes
        alterados += 1 if r.substituicoes else 0

    prefixo = "Simulação concluída" if args.simular else "Concluído"
    print(f"\n{prefixo}: {total} substituições em {alterados} decks.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
