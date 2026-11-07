"""Migra cartas de decks .ydk do EDOPro para as versões Overframe."""

import argparse
import sys
from pathlib import Path

from layout_api import (
    PASTA_SAMPLES,
    buscar_cartas,
    caminho_backup,
    gerar_layout,
    gerar_samples,
    gravar_layout,
    gravar_samples,
    validar,
)
from migrador import carregar_layout, listar_decks, migrar_deck


def _confirmar(pergunta):
    try:
        resposta = input(pergunta)
    except EOFError:
        return False
    return resposta.strip().lower() in ("s", "sim")


def _atualizar_layout(caminho, simular):
    """Busca as cartas na API, gera os samples, pede confirmação e grava o layout."""
    try:
        cartas = buscar_cartas()
    except (OSError, ValueError, KeyError, TypeError) as e:
        print(f"Erro ao consultar a API do YGOPRODeck: {e}", file=sys.stderr)
        return False
    for aviso in validar(cartas):
        print(f"AVISO: {aviso}", file=sys.stderr)

    caminho = Path(caminho)
    extra = sum(1 for c in cartas if c.extra)
    samples = gerar_samples(cartas)
    pasta_samples = caminho.parent / PASTA_SAMPLES
    backup = caminho_backup(caminho)
    print(f"API: {len(cartas)} cartas ({len(cartas) - extra} do Main Deck, {extra} do Extra Deck).")
    print("Código Overframe = código legado + 1.")

    if simular:
        print(f"Simulação: seriam gerados {len(samples)} samples em {pasta_samples}")
        print(f"e o layout {caminho}" + (f" (anterior movido para {backup})." if backup else "."))
        print("Nada foi gravado.")
        return True

    try:
        arquivos = gravar_samples(pasta_samples, samples)
    except OSError as e:
        print(f"Erro ao gravar os samples: {e}", file=sys.stderr)
        return False
    print(f"\nSamples gerados em {pasta_samples}:")
    for arquivo in arquivos:
        print(f"  {arquivo.name}")
    print(
        "\nCopie os samples para a pasta de decks do EDOPro e abra-os no editor de decks.\n"
        "Cada carta legado aparece seguida da sua versão Overframe. Se alguma carta\n"
        "Overframe estiver ausente, em branco ou diferente da legado, o código está errado.\n"
    )
    if not _confirmar("Os samples estão corretos? Gravar o novo layout? (S/N): "):
        print("Cancelado. O layout não foi alterado.")
        return False

    try:
        backup = gravar_layout(caminho, gerar_layout(cartas))
    except OSError as e:
        print(f"Erro ao gravar o layout: {e}", file=sys.stderr)
        return False
    print(f"Layout gerado: {caminho} ({len(cartas)} cartas).")
    if backup:
        print(f"Layout anterior movido para: {backup}")
    return True


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--pasta", help="Pasta com os arquivos .ydk (subpastas ignoradas)")
    ap.add_argument("--layout", required=True, help="Arquivo de layout de migração")
    ap.add_argument("--backup", action="store_true", help="Cria cópia .bak de cada deck alterado")
    ap.add_argument("--simular", action="store_true", help="Mostra o que seria alterado, sem gravar")
    ap.add_argument(
        "--atualizar-layout",
        action="store_true",
        help="Gera decks sample e, após confirmação, um novo layout com as cartas Grand Master "
        "Rare da API do YGOPRODeck (o anterior vai para a pasta backup_layout)",
    )
    args = ap.parse_args(argv)

    if not args.pasta and not args.atualizar_layout:
        ap.error("informe --pasta e/ou --atualizar-layout")

    if args.atualizar_layout:
        if not _atualizar_layout(args.layout, args.simular):
            return 1
        if not args.pasta:
            return 0
        print()

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
