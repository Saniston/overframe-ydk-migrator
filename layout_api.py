"""Geração do layout de migração e de decks sample a partir da API do YGOPRODeck.

A API fornece o código padrão (legado), o nome e o frameType de cada carta. O
código Overframe é sempre o código legado + 1. O frameType define em qual seção
do deck a carta fica (main ou extra) nos samples, que servem para o usuário
conferir no EDOPro se os códigos estão corretos antes de gravar o layout.
"""

import json
import shutil
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

URL_API = "https://db.ygoprodeck.com/api/v7/cardinfo.php"
RARIDADE_PADRAO = "Grand Master Rare"
CABECALHO = "# nome do card|código legado|código novo"
PASTA_BACKUP = "backup_layout"
PASTA_SAMPLES = "samples"

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


def buscar_cartas(raridade=RARIDADE_PADRAO, timeout=30):
    """Consulta a API e retorna as cartas sem repetição, ordenadas por nome."""
    url = URL_API + "?" + urllib.parse.urlencode({"rarity": raridade})
    req = urllib.request.Request(url, headers={"User-Agent": "overframe-ydk-migrator"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        dados = json.load(resp)
    if not isinstance(dados, dict) or "data" not in dados:
        erro = dados.get("error") if isinstance(dados, dict) else None
        raise ValueError(erro or "resposta inesperada da API")
    cartas = {}
    for c in dados["data"]:
        carta = Carta(str(int(c["id"])), str(c["name"]), str(c.get("frameType") or ""))
        cartas.setdefault(carta.codigo, carta)
    return sorted(cartas.values(), key=lambda c: c.nome.lower())


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


def gerar_layout(cartas):
    linhas = [CABECALHO]
    linhas += [f"{c.nome.replace('|', '/')}|{c.codigo}|{c.codigo_novo}" for c in cartas]
    return "\n".join(linhas) + "\n"


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
