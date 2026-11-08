"""Migra cartas de decks .ydk do EDOPro para as versões Overframe."""

import argparse
import sqlite3
import sys
from pathlib import Path

from layout_api import (
    PASTA_SAMPLES,
    bancos_edopro,
    buscar_cartas,
    buscar_nomes_wiki,
    caminho_backup,
    caminho_pendencias,
    carregar_aliases,
    deduzir_pasta_edopro,
    gerar_layout,
    gerar_pendencias,
    gerar_samples,
    gravar_layout,
    gravar_pendencias,
    gravar_samples,
    validar,
    verificar_overframe,
)
from migrador import carregar_layout, listar_decks, migrar_deck


def _perguntar(pergunta):
    try:
        return input(pergunta).strip()
    except EOFError:
        return ""


def _confirmar(pergunta):
    return _perguntar(pergunta).lower() in ("s", "sim")


def _escolher_pasta_edopro(explicita, pasta_decks):
    """Pasta do EDOPro: a informada em --edopro ou a deduzida, sempre confirmada pelo usuário."""
    if explicita:
        pasta = Path(explicita)
    else:
        pasta = deduzir_pasta_edopro(pasta_decks)
        if pasta and _confirmar(f"Pasta do EDOPro encontrada: {pasta}\nUsar esta pasta? (S/N): "):
            return pasta
        if not pasta and pasta_decks:
            print(f"A pasta de decks não está dentro de uma instalação do EDOPro: {pasta_decks}")
        elif not pasta:
            print("A pasta do EDOPro não foi encontrada automaticamente.")
        resposta = _perguntar("Informe a pasta do EDOPro (onde fica o EDOPro.exe): ").strip('"')
        if not resposta:
            print("Erro: nenhuma pasta do EDOPro foi informada.", file=sys.stderr)
            return None
        pasta = Path(resposta)
    if not pasta.is_dir() or not bancos_edopro(pasta):
        print(f"Erro: nenhum banco de cartas (.cdb) do EDOPro encontrado em: {pasta}", file=sys.stderr)
        return None
    return pasta


def _atualizar_layout(caminho, simular, pasta_decks=None, edopro=None):
    """Monta o layout (Yugipedia + YGOPRODeck + EDOPro), gera os samples e grava após confirmação."""
    pasta_edopro = _escolher_pasta_edopro(edopro, pasta_decks)
    if pasta_edopro is None:
        return False

    try:
        nomes = buscar_nomes_wiki()
    except (OSError, ValueError, KeyError, TypeError) as e:
        print(f"Erro ao consultar a Yugipedia: {e}", file=sys.stderr)
        return False
    try:
        cartas, nao_encontrados = buscar_cartas(nomes)
    except (OSError, ValueError, KeyError, TypeError) as e:
        print(f"Erro ao consultar a API do YGOPRODeck: {e}", file=sys.stderr)
        return False
    try:
        aliases = carregar_aliases(pasta_edopro)
    except sqlite3.Error as e:
        print(f"Erro ao ler os bancos de cartas do EDOPro: {e}", file=sys.stderr)
        return False

    confirmadas, pendencias = verificar_overframe(cartas, aliases)
    for aviso in validar(confirmadas):
        print(f"AVISO: {aviso}", file=sys.stderr)

    print(f"Yugipedia: {len(nomes)} cartas com extended art.")
    print(f"YGOPRODeck: {len(cartas)} encontradas, {len(nao_encontrados)} não encontradas.")
    print(f"EDOPro ({pasta_edopro}): {len(confirmadas)} confirmadas (código legado + 1 ou + 2), "
          f"{len(pendencias)} não confirmadas.")
    if not confirmadas:
        print("Erro: nenhuma carta confirmada no EDOPro; o layout não foi alterado.", file=sys.stderr)
        return False

    caminho = Path(caminho)
    arquivo_pendencias = caminho_pendencias(caminho)
    texto_pendencias = gerar_pendencias(pendencias, nao_encontrados)
    extra = sum(1 for c in confirmadas if c.extra)
    samples = gerar_samples(confirmadas)
    # Dentro da pasta de decks, para aparecerem direto no editor de decks do EDOPro
    # (a migração ignora subpastas, então os samples nunca são migrados).
    pasta_samples = Path(pasta_decks or pasta_edopro / "deck") / PASTA_SAMPLES
    backup = caminho_backup(caminho)
    print(f"Layout: {len(confirmadas)} cartas ({len(confirmadas) - extra} do Main Deck, "
          f"{extra} do Extra Deck).")
    if texto_pendencias:
        print(f"Pendências: {len(pendencias) + len(nao_encontrados)} cartas em {arquivo_pendencias}")

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
        f"\nAbra os samples no editor de decks do EDOPro (pasta \"{PASTA_SAMPLES}\" da lista de decks).\n"
        "Cada carta legado aparece seguida da sua versão Overframe. Se alguma carta\n"
        "Overframe estiver ausente, em branco ou diferente da legado, o código está errado.\n"
    )
    if not _confirmar("Os samples estão corretos? Gravar o novo layout? (S/N): "):
        print("Cancelado. O layout não foi alterado.")
        return False

    try:
        backup = gravar_layout(caminho, gerar_layout(confirmadas))
        gravar_pendencias(arquivo_pendencias, texto_pendencias)
    except OSError as e:
        print(f"Erro ao gravar o layout: {e}", file=sys.stderr)
        return False
    print(f"Layout gerado: {caminho} ({len(confirmadas)} cartas).")
    if backup:
        print(f"Layout anterior movido para: {backup}")
    if texto_pendencias:
        print(f"Pendências gravadas em: {arquivo_pendencias}")
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
        help="Gera decks sample e, após confirmação, um novo layout com as cartas de extended art "
        "da Yugipedia confirmadas no EDOPro (o anterior vai para a pasta backup_layout)",
    )
    ap.add_argument(
        "--edopro",
        help="Pasta do EDOPro usada por --atualizar-layout (sem ela, a pasta é deduzida e confirmada)",
    )
    ap.add_argument(
        "--somente-layout",
        action="store_true",
        help="Com --atualizar-layout, usa --pasta só para deduzir o EDOPro e gravar os samples, sem migrar",
    )
    args = ap.parse_args(argv)

    if not args.pasta and not args.atualizar_layout:
        ap.error("informe --pasta e/ou --atualizar-layout")
    if args.somente_layout and not args.atualizar_layout:
        ap.error("--somente-layout exige --atualizar-layout")

    if args.atualizar_layout:
        if not _atualizar_layout(args.layout, args.simular, args.pasta, args.edopro):
            return 1
        if not args.pasta or args.somente_layout:
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
