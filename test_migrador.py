import io
import json
import sqlite3
import tempfile
import unittest
import urllib.error
from datetime import datetime
from pathlib import Path
from unittest import mock

import main
from layout_api import (
    CABECALHO,
    URL_API,
    Carta,
    Pendencia,
    buscar_cartas,
    caminho_pendencias,
    carregar_aliases,
    deduzir_pasta_edopro,
    extrair_nomes,
    gerar_layout,
    gerar_pendencias,
    gerar_samples,
    gravar_layout,
    gravar_pendencias,
    gravar_samples,
    validar,
    verificar_overframe,
)
from migrador import carregar_layout, listar_decks, migrar_deck, substituir_conteudo


class TestMigrador(unittest.TestCase):
    def test_linha_inteira_apenas(self):
        mapa = {"46986414": "900000001"}
        texto = "#main\n46986414\n146986414\n46986414\n"
        novo, qtd = substituir_conteudo(texto, mapa)
        self.assertEqual(novo, "#main\n900000001\n146986414\n900000001\n")
        self.assertEqual(qtd, 2)

    def test_layout_invalido_e_duplicado(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "l.txt"
            p.write_text("# c\n\nA|1|2\nruim|1\nB|1|3\n", encoding="utf-8")
            mapa, avisos = carregar_layout(p)
        self.assertEqual(mapa, {"1": "2"})
        self.assertEqual(len(avisos), 2)

    def test_preserva_crlf_bom_e_ignora_subpastas(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            deck = d / "a.ydk"
            deck.write_bytes(b"\xef\xbb\xbf#main\r\n1\r\n!side\r\n")
            (d / "sub").mkdir()
            (d / "sub" / "b.ydk").write_bytes(b"1\n")
            self.assertEqual(listar_decks(d), [deck])
            r = migrar_deck(deck, {"1": "2"}, backup=True)
            self.assertEqual(r.substituicoes, 1)
            self.assertEqual(deck.read_bytes(), b"\xef\xbb\xbf#main\r\n2\r\n!side\r\n")
            bak = d / "bak" / "a.ydk.bak"
            self.assertEqual(bak.read_bytes(), b"\xef\xbb\xbf#main\r\n1\r\n!side\r\n")
            self.assertFalse((d / "a.ydk.bak").exists())
            self.assertEqual(listar_decks(d), [deck])  # pasta bak ignorada

    def test_simular_nao_grava(self):
        with tempfile.TemporaryDirectory() as d:
            deck = Path(d) / "a.ydk"
            deck.write_bytes(b"1\n")
            r = migrar_deck(deck, {"1": "2"}, simular=True)
            self.assertEqual(r.substituicoes, 1)
            self.assertEqual(deck.read_bytes(), b"1\n")


    def test_layout_pendente_sem_codigo_novo(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "l.txt"
            p.write_text("A|1|2\nB|3|\nC|4|\n", encoding="utf-8")
            mapa, avisos = carregar_layout(p)
        self.assertEqual(mapa, {"1": "2"})
        self.assertEqual(len(avisos), 1)
        self.assertIn("2 carta(s)", avisos[0])


class TestLayoutApi(unittest.TestCase):
    def test_carta_codigo_novo_e_secao(self):
        self.assertEqual(Carta("46986414", "DM", "normal").codigo_novo, "46986415")
        for tipo in ("fusion", "synchro_pendulum", "xyz", "link"):
            self.assertTrue(Carta("1", "x", tipo).extra, tipo)
        for tipo in ("effect", "effect_pendulum", "ritual", "spell", ""):
            self.assertFalse(Carta("1", "x", tipo).extra, tipo)

    def test_gerar_layout(self):
        texto = gerar_layout([Carta("10", "Z|x", "effect")])
        self.assertEqual(texto, CABECALHO + "\nZ/x|10|11\n")

    def test_validar(self):
        avisos = validar([Carta("10", "A", "effect"), Carta("11", "B", "")])
        self.assertEqual(len(avisos), 2)  # 10+1 colide com B; B sem frameType

    def test_samples_respeitam_limites(self):
        main = [Carta(str(100 + 2 * i), f"M{i:02d}", "effect") for i in range(31)]
        extra = [Carta(str(500 + 2 * i), f"E{i:02d}", "xyz") for i in range(15)]
        samples = gerar_samples(main + extra)
        self.assertEqual(len(samples), 3)  # 15 extras / 7 por sample
        for s in samples:
            linhas = s.splitlines()
            i_main, i_extra, i_side = linhas.index("#main"), linhas.index("#extra"), linhas.index("!side")
            self.assertLessEqual(i_extra - i_main - 1, 60)
            self.assertLessEqual(i_side - i_extra - 1, 14)
            self.assertEqual(i_side, len(linhas) - 1)  # side vazio
        primeiro = samples[0].splitlines()
        self.assertEqual(primeiro[2:4], ["100", "101"])  # legado seguido da Overframe
        self.assertEqual(primeiro[primeiro.index("#extra") + 1:][:2], ["500", "501"])
        self.assertEqual(samples[1].splitlines()[2:4], ["160", "161"])

    def test_gravar_samples_remove_antigos(self):
        with tempfile.TemporaryDirectory() as d:
            pasta = Path(d) / "samples"
            pasta.mkdir()
            (pasta / "sample_09.ydk").write_text("x")
            arquivos = gravar_samples(pasta, ["a\n", "b\n"])
            self.assertEqual(sorted(p.name for p in pasta.iterdir()), ["sample_01.ydk", "sample_02.ydk"])
            self.assertEqual(arquivos[1].read_text(), "b\n")

    def test_gravar_layout_move_anterior_para_backup(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "l.txt"
            p.write_text("velho\n", encoding="utf-8")
            agora = datetime(2026, 1, 2, 3, 4, 5)
            bkp = Path(d) / "backup_layout" / "l_20260102-030405.txt"
            self.assertEqual(gravar_layout(p, "novo\n", agora=agora), bkp)
            self.assertEqual(p.read_text(encoding="utf-8"), "novo\n")
            self.assertEqual(bkp.read_text(encoding="utf-8"), "velho\n")
            # mesmo segundo: não sobrescreve o backup anterior
            segundo = gravar_layout(p, "novo2\n", agora=agora)
            self.assertEqual(segundo.name, "l_20260102-030405_2.txt")
            self.assertEqual(bkp.read_text(encoding="utf-8"), "velho\n")
            self.assertIsNone(gravar_layout(Path(d) / "n.txt", "x\n"))

    def test_extrair_nomes(self):
        wikitext = (
            "intro\n* \"[[Fora da Lista]]\"\n"
            "== List of cards with extended art ==\n"
            "{| class=\"wikitable\"\n|-\n| \n"
            "* \"[[Dark Magician, the Pharaoh's Servant]]\"\n"
            "* \"[[Kuriboh - Multiply!|Kuriboh]]\"\n"
            "* \"[[Ultimate Sky‎]]\"\n"
            "* \"[[CHAOS ORIGINS (card)]]\"\n"
            "* \"[[Ash &amp; Spring]]\"\n"
            "* \"[[Kuriboh - Multiply!]]\"\n"
            "| ''[[Limit Over Collection: The Heroes]]''\n"
            "|}\n== See also ==\n* \"[[Depois da Lista]]\"\n"
        )
        self.assertEqual(
            extrair_nomes(wikitext),
            ["Dark Magician, the Pharaoh's Servant", "Kuriboh - Multiply!", "Ultimate Sky",
             "CHAOS ORIGINS", "Ash & Spring"],
        )
        with self.assertRaises(ValueError):
            extrair_nomes("sem a seção")

    def test_buscar_cartas_em_lotes(self):
        respostas = [
            {"data": [{"id": 10, "name": "A", "frameType": "link"}, {"id": 20, "name": "B"}]},
            urllib.error.HTTPError(URL_API, 400, "Bad Request", {}, None),
        ]

        def falso(req, timeout):
            r = respostas.pop(0)
            if isinstance(r, Exception):
                raise r
            return io.BytesIO(json.dumps(r).encode())

        with mock.patch("urllib.request.urlopen", side_effect=falso) as m:
            cartas, faltando = buscar_cartas(["a", "B", "C"], lote=2)
        self.assertEqual(cartas, [Carta("10", "A", "link"), Carta("20", "B", "")])
        self.assertEqual(faltando, ["C"])
        self.assertIn("name=a%7CB", m.call_args_list[0][0][0].full_url)

    def test_verificar_overframe(self):
        aliases = {10: 0, 11: 10, 20: 0, 22: 20, 30: 99, 31: 99, 99: 0, 40: 0, 41: 0}
        cartas = [Carta(str(c), f"C{c}") for c in (10, 20, 30, 40, 50)]
        confirmadas, pendencias = verificar_overframe(cartas, aliases)
        self.assertEqual([c.codigo for c in confirmadas], ["10", "30"])  # 30: mesma carta base
        self.assertEqual([(p.carta.codigo, p.sugestoes) for p in pendencias],
                         [("20", ("22",)), ("40", ()), ("50", ())])  # 41 é outra carta
        self.assertIn("não existe no EDOPro", pendencias[2].motivo)

    def _criar_edopro(self, raiz, linhas_por_banco):
        for relativo, linhas in linhas_por_banco.items():
            banco = Path(raiz) / relativo
            banco.parent.mkdir(parents=True, exist_ok=True)
            con = sqlite3.connect(banco)
            con.execute("CREATE TABLE datas (id INTEGER PRIMARY KEY, alias INTEGER)")
            con.executemany("INSERT INTO datas VALUES (?, ?)", linhas)
            con.commit()
            con.close()

    def test_carregar_aliases_e_deduzir_pasta(self):
        with tempfile.TemporaryDirectory() as d:
            raiz = Path(d) / "Projeto Ignis"
            self._criar_edopro(raiz, {
                "expansions/cards.cdb": [(10, 0), (11, 0)],
                "repositories/delta/cards.delta.cdb": [(11, 10)],
            })
            (raiz / "deck" / "torneio").mkdir(parents=True)
            self.assertEqual(carregar_aliases(raiz), {10: 0, 11: 10})  # repositório prevalece
            self.assertEqual(deduzir_pasta_edopro(raiz / "deck"), raiz.resolve())
            self.assertEqual(deduzir_pasta_edopro(raiz / "deck" / "torneio"), raiz.resolve())
            with mock.patch("layout_api.LOCAIS_EDOPRO", (str(raiz),)):
                self.assertIsNone(deduzir_pasta_edopro(Path(d)))  # decks fora do EDOPro
                self.assertEqual(deduzir_pasta_edopro(), raiz)  # sem decks: locais comuns

    def test_pendencias(self):
        pend = [Pendencia(Carta("20", "B|x"), "motivo", ("22",))]
        texto = gerar_pendencias(pend, ["Sem Codigo"])
        linhas = texto.splitlines()
        self.assertIn("# outras artes desta carta no EDOPro: 22", linhas)
        self.assertIn("B/x|20|", linhas)
        self.assertEqual(linhas[-1], "Sem Codigo||")
        self.assertEqual(gerar_pendencias([], []), "")
        self.assertEqual(caminho_pendencias(Path("x") / "l.txt"), Path("x") / "l_pendencias.txt")
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "l_pendencias.txt"
            gravar_pendencias(p, texto)
            self.assertEqual(p.read_text(encoding="utf-8"), texto)
            gravar_pendencias(p, "")
            self.assertFalse(p.exists())

    def _atualizar(self, d, respostas, extra_args=()):
        """Executa --atualizar-layout com as fontes simuladas e o EDOPro em d/edopro."""
        self._criar_edopro(Path(d) / "edopro", {"expansions/cards.cdb": [(10, 0), (11, 10), (20, 0)]})
        layout = Path(d) / "l.txt"
        layout.write_text("velho\n", encoding="utf-8")
        cartas = [Carta("10", "A", "effect"), Carta("20", "B", "effect")]
        saida = io.StringIO()
        with mock.patch("main.buscar_nomes_wiki", return_value=["A", "B", "C"]), \
                mock.patch("main.buscar_cartas", return_value=(cartas, ["C"])), \
                mock.patch("main.deduzir_pasta_edopro", return_value=Path(d) / "edopro"), \
                mock.patch("builtins.input", side_effect=respostas) as entrada, \
                mock.patch("sys.stdout", saida), mock.patch("sys.stderr", io.StringIO()):
            rc = main.main(["--layout", str(layout), "--atualizar-layout", *extra_args])
        return rc, layout, entrada

    def test_atualizar_grava_layout_e_pendencias(self):
        with tempfile.TemporaryDirectory() as d:
            rc, layout, entrada = self._atualizar(d, ["s", "s"])
            self.assertEqual(rc, 0)
            self.assertIn("Pasta do EDOPro encontrada", entrada.call_args_list[0][0][0])
            self.assertEqual(layout.read_text(encoding="utf-8"), CABECALHO + "\nA|10|11\n")
            pend = (Path(d) / "l_pendencias.txt").read_text(encoding="utf-8").splitlines()
            self.assertIn("B|20|", pend)
            self.assertIn("C||", pend)
            self.assertTrue((Path(d) / "backup_layout").exists())

    def test_atualizar_pasta_edopro_recusada_e_invalida(self):
        with tempfile.TemporaryDirectory() as d:
            rc, layout, _ = self._atualizar(d, ["n", str(Path(d) / "nao_existe")])
            self.assertEqual(rc, 1)
            self.assertEqual(layout.read_text(encoding="utf-8"), "velho\n")
            self.assertFalse((Path(d) / "edopro" / "deck").exists())

    def test_samples_na_pasta_de_decks_informada(self):
        with tempfile.TemporaryDirectory() as d:
            decks = Path(d) / "meus decks"
            decks.mkdir()
            (decks / "a.ydk").write_text("10\n", encoding="utf-8")
            rc, _, _ = self._atualizar(d, ["s", "s"], ["--pasta", str(decks), "--somente-layout"])
            self.assertEqual(rc, 0)
            self.assertTrue((decks / "samples" / "sample_01.ydk").exists())
            self.assertFalse((Path(d) / "edopro" / "deck").exists())
            self.assertEqual((decks / "a.ydk").read_text(encoding="utf-8"), "10\n")  # não migrou

    def test_somente_layout_exige_atualizar(self):
        with mock.patch("sys.stderr", io.StringIO()), self.assertRaises(SystemExit):
            main.main(["--layout", "l.txt", "--pasta", ".", "--somente-layout"])

    def test_atualizar_pasta_edopro_informada_manualmente(self):
        with tempfile.TemporaryDirectory() as d:
            rc, _, entrada = self._atualizar(d, ["n", f'"{Path(d) / "edopro"}"', "s"])
            self.assertEqual(rc, 0)
            self.assertEqual(entrada.call_count, 3)

    def test_cancelar_nao_grava_layout(self):
        with tempfile.TemporaryDirectory() as d:
            rc, layout, _ = self._atualizar(d, ["s", "n"])
            self.assertEqual(rc, 1)
            self.assertEqual(layout.read_text(encoding="utf-8"), "velho\n")
            # sem --pasta: samples na pasta de decks do EDOPro
            self.assertTrue((Path(d) / "edopro" / "deck" / "samples" / "sample_01.ydk").exists())
            self.assertFalse((Path(d) / "samples").exists())
            self.assertFalse((Path(d) / "backup_layout").exists())
            self.assertFalse((Path(d) / "l_pendencias.txt").exists())

    def test_simular_nao_grava_layout(self):
        with tempfile.TemporaryDirectory() as d:
            rc, layout, entrada = self._atualizar(d, [], ["--simular", "--edopro", str(Path(d) / "edopro")])
            self.assertEqual(rc, 0)
            self.assertEqual(entrada.call_count, 0)  # --edopro informado: nada a perguntar
            self.assertEqual(layout.read_text(encoding="utf-8"), "velho\n")
            self.assertFalse((Path(d) / "edopro" / "deck").exists())


if __name__ == "__main__":
    unittest.main()
