"""Leitura do layout de migração e substituição de códigos em decks .ydk."""

import shutil
from dataclasses import dataclass
from pathlib import Path


def _decodificar(dados: bytes):
    """Decodifica bytes devolvendo (texto, codificação) para regravar igual."""
    if dados.startswith(b"\xef\xbb\xbf"):
        return dados.decode("utf-8-sig"), "utf-8-sig"
    try:
        return dados.decode("utf-8"), "utf-8"
    except UnicodeDecodeError:
        return dados.decode("cp1252", errors="replace"), "cp1252"


def carregar_layout(caminho):
    """Lê o layout. Retorna (mapa legado->novo, avisos)."""
    texto, _ = _decodificar(Path(caminho).read_bytes())
    mapa = {}
    avisos = []
    pendentes = 0
    for numero, linha in enumerate(texto.splitlines(), start=1):
        linha = linha.strip()
        if not linha or linha.startswith("#"):
            continue
        campos = [c.strip() for c in linha.split("|")]
        if len(campos) != 3:
            avisos.append(
                f"Layout linha {numero} ignorada (esperados 3 campos, encontrados {len(campos)}): {linha}"
            )
            continue
        nome, legado, novo = campos
        if legado and not novo:
            # Carta aguardando o preenchimento do código novo.
            pendentes += 1
            continue
        if not legado:
            avisos.append(f"Layout linha {numero} ignorada (código vazio): {linha}")
            continue
        if legado in mapa:
            avisos.append(
                f"Layout linha {numero}: código legado duplicado {legado} "
                f"({nome}); mantido o primeiro mapeamento ({mapa[legado]})."
            )
            continue
        mapa[legado] = novo
    if pendentes:
        avisos.append(f"{pendentes} carta(s) do layout sem código novo foram ignoradas (pendentes).")
    return mapa, avisos


def substituir_conteudo(texto, mapa):
    """Substitui linhas inteiras iguais a um código legado. Retorna (texto, qtd)."""
    saida = []
    qtd = 0
    for linha in texto.splitlines(keepends=True):
        corpo = linha.rstrip("\r\n")
        fim = linha[len(corpo):]
        novo = mapa.get(corpo.strip())
        if novo is not None:
            saida.append(novo + fim)
            qtd += 1
        else:
            saida.append(linha)
    return "".join(saida), qtd


def listar_decks(pasta):
    """Arquivos .ydk apenas da pasta informada (subpastas ignoradas)."""
    return sorted(
        p for p in Path(pasta).iterdir() if p.is_file() and p.suffix.lower() == ".ydk"
    )


@dataclass
class ResultadoDeck:
    arquivo: Path
    substituicoes: int


def migrar_deck(caminho, mapa, backup=False, simular=False):
    caminho = Path(caminho)
    dados = caminho.read_bytes()
    texto, codificacao = _decodificar(dados)
    novo_texto, qtd = substituir_conteudo(texto, mapa)
    if qtd and not simular:
        if backup:
            shutil.copy2(caminho, caminho.with_name(caminho.name + ".bak"))
        # Escrita binária preserva as quebras de linha originais.
        caminho.write_bytes(novo_texto.encode(codificacao))
    return ResultadoDeck(caminho, qtd)
