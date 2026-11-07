import tempfile
import unittest
from pathlib import Path

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


if __name__ == "__main__":
    unittest.main()
