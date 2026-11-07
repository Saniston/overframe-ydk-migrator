import io
import json
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest import mock

import main
from layout_api import (
    CABECALHO,
    Carta,
    buscar_cartas,
    gerar_layout,
    gerar_samples,
    gravar_layout,
    gravar_samples,
    validar,
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
            self.assertTrue((d / "a.ydk.bak").exists())

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

    def test_buscar_cartas(self):
        dados = {"data": [{"id": 10, "name": "X", "frameType": "link"}, {"id": 10, "name": "X"}]}
        resposta = io.BytesIO(json.dumps(dados).encode())
        with mock.patch("urllib.request.urlopen", return_value=resposta) as m:
            self.assertEqual(buscar_cartas(), [Carta("10", "X", "link")])
        self.assertIn("rarity=Grand+Master+Rare", m.call_args[0][0].full_url)

    def test_cancelar_nao_grava_layout(self):
        with tempfile.TemporaryDirectory() as d:
            layout = Path(d) / "l.txt"
            layout.write_text("velho\n", encoding="utf-8")
            with mock.patch("main.buscar_cartas", return_value=[Carta("10", "A", "effect")]), \
                    mock.patch("builtins.input", return_value="n"), \
                    mock.patch("sys.stdout", io.StringIO()):
                rc = main.main(["--layout", str(layout), "--atualizar-layout"])
            self.assertEqual(rc, 1)
            self.assertEqual(layout.read_text(encoding="utf-8"), "velho\n")
            self.assertTrue((Path(d) / "samples" / "sample_01.ydk").exists())
            self.assertFalse((Path(d) / "backup_layout").exists())


if __name__ == "__main__":
    unittest.main()
