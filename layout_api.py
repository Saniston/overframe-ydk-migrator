"""Geração do layout de migração e de decks sample.

Fontes, nesta ordem:
1. Yugipedia (página "Extended_art"): lista oficial das cartas com extended art /
   Overframe, lida pela API do MediaWiki.
2. YGOPRODeck: traduz cada nome no código padrão (legado) e no frameType.
3. Banco de cartas do EDOPro instalado (.cdb, SQLite): confirma que existe a
   versão Overframe com código legado + 1 (mesma carta base pelo campo alias).

Cartas não confirmadas no EDOPro não entram no layout; vão para o arquivo de
pendências com as artes alternativas encontradas como sugestão. O frameType
define em qual seção do deck a carta fica nos samples, que servem para o usuário
conferir no EDOPro os códigos antes de gravar o layout.
"""

import html
import json
import re
import shutil
import sqlite3
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

USER_AGENT = "overframe-ydk-migrator"
URL_WIKI = "https://yugipedia.com/api.php"
PAGINA_WIKI = "Extended_art"
SECAO_WIKI = "List of cards with extended art"
URL_API = "https://db.ygoprodeck.com/api/v7/cardinfo.php"
LOTE_API = 40  # nomes por consulta (name=A|B|C...), para a URL não ficar longa demais

CABECALHO = "# nome do card|código legado|código novo"
PASTA_BACKUP = "backup_layout"
PASTA_SAMPLES = "samples"
SUFIXO_PENDENCIAS = "_pendencias"

# Locais comuns de instalação do EDOPro, usados quando a pasta não é deduzida dos decks.
LOCAIS_EDOPRO = (r"C:\ProjectIgnis", r"D:\ProjectIgnis", r"C:\EDOPro", r"D:\EDOPro")

# frameTypes que vão para o Extra Deck (ex.: "fusion", "synchro_pendulum", "link").
TIPOS_EXTRA = ("fusion", "synchro", "xyz", "link")
MAX_MAIN = 60  # limite do Main Deck
MAX_EXTRA = 14  # limite do Extra Deck é 15; o sample usa 14 (pares legado/Overframe)


@dataclass(frozen=True)
class Carta:
    codigo: str
    nome: str
    frame_type: str = ""

    @property
    def codigo_novo(self):
        return str(int(self.codigo) + 1)

    @property
    def extra(self):
        tipo = self.frame_type.lower()
        return any(t in tipo for t in TIPOS_EXTRA)


@dataclass(frozen=True)
class Pendencia:
    carta: Carta
    motivo: str
    sugestoes: tuple = ()  # outras artes da mesma carta no EDOPro


# --- Yugipedia ---------------------------------------------------------------

def _baixar_json(url, params, timeout):
    req = urllib.request.Request(
        url + "?" + urllib.parse.urlencode(params), headers={"User-Agent": USER_AGENT}
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.load(resp)


def extrair_nomes(wikitext):
    """Nomes das cartas da tabela de extended art, sem repetição e na ordem da página."""
    inicio = re.search(r"^==\s*" + re.escape(SECAO_WIKI) + r"\s*==\s*$", wikitext, re.M)
    if not inicio:
        raise ValueError(f"seção '{SECAO_WIKI}' não encontrada na página da Yugipedia")
    secao = wikitext[inicio.end():]
    fim = re.search(r"^==[^=]", secao, re.M)
    if fim:
        secao = secao[:fim.start()]
    nomes = []
    for alvo in re.findall(r'^\*\s*"\[\[([^\]|]+)(?:\|[^\]]*)?\]\]"', secao, re.M):
        nome = html.unescape(alvo)
        nome = re.sub(r"[\u200e\u200f\u200b]", "", nome)  # marcas invisíveis de direção
        nome = re.sub(r"\s*\(card\)$", "", nome).strip()  # desambiguação da wiki
        if nome and nome not in nomes:
            nomes.append(nome)
    return nomes


def buscar_nomes_wiki(timeout=30):
    """Baixa a página de extended art da Yugipedia e retorna os nomes das cartas."""
    dados = _baixar_json(
        URL_WIKI,
        {"action": "parse", "page": PAGINA_WIKI, "prop": "wikitext", "format": "json"},
        timeout,
    )
    try:
        wikitext = dados["parse"]["wikitext"]["*"]
    except (KeyError, TypeError):
        erro = dados.get("error", {}).get("info") if isinstance(dados, dict) else None
        raise ValueError(erro or "resposta inesperada da Yugipedia")
    return extrair_nomes(wikitext)


# --- YGOPRODeck --------------------------------------------------------------

def _consultar_nomes(nomes, timeout):
    try:
        dados = _baixar_json(URL_API, {"name": "|".join(nomes)}, timeout)
    except urllib.error.HTTPError as e:
        if e.code == 400:  # nenhum nome do lote encontrado
            e.close()
            return []
        raise
    if not isinstance(dados, dict) or "data" not in dados:
        erro = dados.get("error") if isinstance(dados, dict) else None
        raise ValueError(erro or "resposta inesperada da API do YGOPRODeck")
    return dados["data"]


def buscar_cartas(nomes, timeout=30, lote=LOTE_API):
    """Consulta os nomes no YGOPRODeck. Retorna (cartas ordenadas por nome, não encontrados)."""
    validos = [n for n in nomes if "|" not in n]  # "|" é o separador da consulta
    por_nome = {}
    for i in range(0, len(validos), lote):
        for c in _consultar_nomes(validos[i:i + lote], timeout):
            carta = Carta(str(int(c["id"])), str(c["name"]), str(c.get("frameType") or ""))
            por_nome.setdefault(carta.nome.casefold(), carta)
    nao_encontrados = [n for n in nomes if n.casefold() not in por_nome]
    cartas = {c.codigo: c for c in por_nome.values()}
    return sorted(cartas.values(), key=lambda c: c.nome.lower()), nao_encontrados


# --- EDOPro ------------------------------------------------------------------

def bancos_edopro(pasta):
    """Arquivos .cdb do EDOPro: expansions/ primeiro, depois os repositórios (mais novos)."""
    pasta = Path(pasta)
    return sorted((pasta / "expansions").glob("*.cdb")) + sorted(
        (pasta / "repositories").rglob("*.cdb")
    )


def deduzir_pasta_edopro(pasta_decks=None):
    """Sugere a pasta do EDOPro.

    Com a pasta de decks, procura a instalação que a contém (ela mesma ou uma pasta
    acima, ex.: C:\\ProjectIgnis\\deck -> C:\\ProjectIgnis); sem ela, um local comum.
    """
    if pasta_decks:
        pasta = Path(pasta_decks).resolve()
        candidatos = [pasta, *pasta.parents]
    else:
        candidatos = [Path(p) for p in LOCAIS_EDOPRO]
    for pasta in candidatos:
        if pasta.is_dir() and bancos_edopro(pasta):
            return pasta
    return None


def carregar_aliases(pasta):
    """Lê todos os .cdb e retorna {código: alias} (alias 0 = carta base)."""
    aliases = {}
    for banco in bancos_edopro(pasta):
        uri = "file:" + urllib.parse.quote(banco.resolve().as_posix()) + "?mode=ro"
        con = sqlite3.connect(uri, uri=True)
        try:
            aliases.update(con.execute("SELECT id, alias FROM datas"))
        finally:
            con.close()
    return aliases


def verificar_overframe(cartas, aliases):
    """Separa as cartas cuja versão legado + 1 existe no EDOPro. Retorna (confirmadas, pendências)."""
    def base(codigo):
        return aliases.get(codigo) or codigo

    artes = {}
    for codigo in aliases:
        artes.setdefault(base(codigo), []).append(codigo)

    confirmadas, pendencias = [], []
    for carta in cartas:
        legado = int(carta.codigo)
        if legado not in aliases:
            pendencias.append(Pendencia(carta, "código legado não existe no EDOPro"))
            continue
        novo = legado + 1
        if novo in aliases and base(novo) == base(legado):
            confirmadas.append(carta)
            continue
        outras = tuple(str(c) for c in sorted(artes.get(base(legado), [])) if c != legado)
        pendencias.append(Pendencia(carta, "código legado + 1 não existe no EDOPro", outras))
    return confirmadas, pendencias


# --- Layout, pendências e samples --------------------------------------------

def validar(cartas):
    """Retorna avisos sobre dados que podem gerar códigos errados."""
    avisos = []
    legados = {c.codigo: c for c in cartas}
    for c in cartas:
        if not c.frame_type:
            avisos.append(f"{c.nome} ({c.codigo}) sem frameType; considerada carta do Main Deck.")
        outra = legados.get(c.codigo_novo)
        if outra:
            avisos.append(
                f"Código Overframe de {c.nome} ({c.codigo_novo}) é o código legado de {outra.nome}."
            )
    return avisos


def _nome_layout(nome):
    return nome.replace("|", "/")


def gerar_layout(cartas):
    linhas = [CABECALHO]
    linhas += [f"{_nome_layout(c.nome)}|{c.codigo}|{c.codigo_novo}" for c in cartas]
    return "\n".join(linhas) + "\n"


def caminho_pendencias(layout):
    layout = Path(layout)
    return layout.with_name(f"{layout.stem}{SUFIXO_PENDENCIAS}{layout.suffix}")


def gerar_pendencias(pendencias, nao_encontrados):
    """Texto do arquivo de pendências ("" se não houver nenhuma)."""
    if not pendencias and not nao_encontrados:
        return ""
    linhas = [
        "# Pendências do layout de migração (gerado automaticamente; não é lido pela migração).",
        "# Cartas com extended art (Yugipedia) cuja versão Overframe não foi confirmada no EDOPro.",
        "# Para migrar uma delas, confira o código no EDOPro, preencha o código novo",
        "# e mova a linha para o layout.",
        CABECALHO,
    ]
    for p in pendencias:
        linhas.append("")
        linhas.append(f"# {p.motivo}")
        if p.sugestoes:
            linhas.append(f"# outras artes desta carta no EDOPro: {', '.join(p.sugestoes)}")
        linhas.append(f"{_nome_layout(p.carta.nome)}|{p.carta.codigo}|")
    if nao_encontrados:
        linhas.append("")
        linhas.append("# Não encontradas no YGOPRODeck (sem código legado):")
        linhas += [f"{_nome_layout(n)}||" for n in nao_encontrados]
    return "\n".join(linhas) + "\n"


def gravar_pendencias(caminho, texto):
    """Grava o arquivo de pendências; sem pendências, remove o de uma geração anterior."""
    caminho = Path(caminho)
    if texto:
        caminho.write_text(texto, encoding="utf-8", newline="")
    elif caminho.exists():
        caminho.unlink()


def gerar_samples(cartas):
    """Monta os textos dos decks sample: cada carta legado seguida da sua Overframe."""
    main = [c for c in cartas if not c.extra]
    extra = [c for c in cartas if c.extra]
    por_main, por_extra = MAX_MAIN // 2, MAX_EXTRA // 2
    qtd = max(-(-len(main) // por_main), -(-len(extra) // por_extra))
    samples = []
    for i in range(qtd):
        linhas = [f"#created by overframe-ydk-migrator - sample {i + 1}/{qtd} (legado, Overframe)"]
        linhas.append("#main")
        for c in main[i * por_main:(i + 1) * por_main]:
            linhas += [c.codigo, c.codigo_novo]
        linhas.append("#extra")
        for c in extra[i * por_extra:(i + 1) * por_extra]:
            linhas += [c.codigo, c.codigo_novo]
        linhas.append("!side")
        samples.append("\n".join(linhas) + "\n")
    return samples


def gravar_samples(pasta, samples):
    """Grava sample_NN.ydk na pasta, removendo samples de gerações anteriores."""
    pasta = Path(pasta)
    pasta.mkdir(parents=True, exist_ok=True)
    for antigo in pasta.glob("sample_*.ydk"):
        antigo.unlink()
    arquivos = []
    for i, texto in enumerate(samples, start=1):
        arquivo = pasta / f"sample_{i:02d}.ydk"
        arquivo.write_text(texto, encoding="utf-8", newline="")
        arquivos.append(arquivo)
    return arquivos


def caminho_backup(caminho, agora=None):
    """Destino do backup do layout atual (None se ele não existir); nunca repete um nome."""
    caminho = Path(caminho)
    if not caminho.exists():
        return None
    pasta = caminho.parent / PASTA_BACKUP
    carimbo = (agora or datetime.now()).strftime("%Y%m%d-%H%M%S")
    backup = pasta / f"{caminho.stem}_{carimbo}{caminho.suffix}"
    n = 1
    while backup.exists():
        n += 1
        backup = pasta / f"{caminho.stem}_{carimbo}_{n}{caminho.suffix}"
    return backup


def gravar_layout(caminho, texto, agora=None):
    """Move o layout atual para a pasta de backup e grava o novo. Retorna o backup."""
    caminho = Path(caminho)
    backup = caminho_backup(caminho, agora)
    if backup is not None:
        backup.parent.mkdir(exist_ok=True)
        shutil.move(str(caminho), str(backup))
    caminho.write_text(texto, encoding="utf-8", newline="")
    return backup
