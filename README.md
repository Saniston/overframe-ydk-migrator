# YDK Card Migrator

Serviço simples em Python que migra as cartas dos decks do **EDOPro** para as versões de **arte estendida / Overframe**, substituindo automaticamente os códigos antigos (legados) pelos novos em todos os arquivos `.ydk` de uma pasta.

## O que a aplicação faz

1. Lê o **arquivo de layout de migração**, que mapeia cada carta do código legado para o código novo.
2. Percorre os arquivos `.ydk` da **pasta informada** (subpastas são ignoradas).
3. Em cada deck, substitui as linhas cujo texto completo seja igual a um código legado pelo código novo correspondente.
4. Grava o resultado e exibe um resumo do que foi alterado.

Assim, o usuário não precisa trocar manualmente carta por carta em cada deck.

## O que é um arquivo `.ydk`

O `.ydk` é o arquivo que armazena as informações de **um baralho (deck) específico do usuário**. É um arquivo de texto em que **cada linha representa uma carta do deck**, identificada pelo seu código.

```
#created by ...
#main
46986414
89631139
#extra
...
!side
...
```

As linhas de marcação de seção (`#main`, `#extra`, `!side`) e os comentários não são códigos de carta e permanecem intactos.

## Layout do arquivo de migração

Arquivo de texto em que cada linha tem **3 textos separados por `|`**:

```
nome do card|código legado|código novo
```

| Campo | Descrição |
|---|---|
| Nome do card | Nome da carta, apenas para referência e legibilidade do arquivo. |
| Código legado | Código da carta atualmente usada nos decks. |
| Código novo | Código da versão de arte estendida / Overframe. |

### Comentário de título

O arquivo pode ter uma linha de comentário no início, que serve como guia de preenchimento. Linhas de comentário e linhas em branco são **ignoradas** pela aplicação.

### Exemplo

```
# nome do card|código legado|código novo
Dark Magician|46986414|900000001
Blue-Eyes White Dragon|89631139|900000002
```

> Os códigos novos acima são **ilustrativos**. Use os códigos reais das versões Overframe presentes no seu EDOPro.

## Regra de substituição

A comparação é feita pelo **texto completo da linha**, nunca por trecho. Uma linha do deck só é alterada quando seu conteúdo, sem espaços nas extremidades, é **exatamente igual** ao código legado.

| Linha no deck | Código legado no layout | Resultado |
|---|---|---|
| `46986414` | `46986414` | Substituída pelo código novo |
| `146986414` | `46986414` | Não alterada (apenas contém o código) |
| `#main` | `46986414` | Não alterada |

Isso evita erros de substituição parcial. Como cada linha é uma carta, cada ocorrência do código legado no deck é substituída individualmente, inclusive quando a mesma carta aparece mais de uma vez (cópias).

## Requisitos

- Python 3.9 ou superior
- Nenhuma dependência externa (apenas biblioteca padrão)

## Instalação

```bash
git clone [URL-DO-REPOSITORIO]
cd [NOME-DO-PROJETO]
```

## Uso

```bash
python main.py --pasta "C:\EDOPro\deck" --layout "layout_migracao.txt"
```

| Parâmetro | Descrição |
|---|---|
| `--pasta` | Pasta onde estão os arquivos `.ydk`. **Somente esta pasta é processada; subpastas são ignoradas.** |
| `--layout` | Caminho do arquivo de layout de migração. |
| `--backup` | [Opcional] Cria cópia `.bak` de cada deck antes de alterar. |
| `--simular` | [Opcional] Apenas mostra o que seria alterado, sem gravar. |

> Os parâmetros opcionais são sugestões. Remova da tabela os que não implementar.

## Uso simplificado (Windows)

Para quem não quer usar a linha de comando, basta usar o `migrar.bat`:

1. Dê **dois cliques** em `migrar.bat` (ou **arraste a pasta de decks** sobre o arquivo).
2. Leia o **aviso de responsabilidade** e confirme com `S` que fez backup da pasta de decks.
3. Se o **Python não estiver instalado**, o assistente pergunta se deseja instalá-lo (via `winget`; sem o `winget`, abre a página de download). Após instalar, pode ser preciso fechar a janela e abrir o `migrar.bat` de novo.
4. Se não arrastou a pasta, digite o caminho dela (ex.: `C:\EDOPro\deck`).
5. O assistente mostra primeiro uma **simulação**, sem alterar nada.
6. Responda `S` para aplicar. Uma cópia `.bak` de cada deck alterado é criada.

Ele usa o `layout_migracao.txt` da própria pasta do projeto e exige o Python (o próprio assistente oferece a instalação). Para desfazer, remova o `.bak` do nome do arquivo de backup, substituindo o deck alterado.

## Exemplo de saída

```
Layout carregado: 2 mapeamentos
Decks encontrados: 3

meu_deck_1.ydk  -> 5 cartas substituídas
meu_deck_2.ydk  -> 0 cartas substituídas
meu_deck_3.ydk  -> 2 cartas substituídas

Concluído: 7 substituições em 2 decks.
```

## Boas práticas

- **Faça backup dos decks** antes da primeira execução, ou use a opção `--backup`.
- Linhas do layout com formato inválido (número de campos diferente de 3) são **ignoradas e reportadas**, sem interromper a execução.
- Códigos legados duplicados no layout geram um **aviso**, pois o resultado seria ambíguo.
- A leitura e a gravação preservam a **codificação** e as **quebras de linha** originais dos decks.

## Estrutura sugerida do projeto

```
.
├── main.py                  # ponto de entrada (argumentos e orquestração)
├── migrador.py              # leitura do layout e substituição nos decks
├── layout_migracao.txt      # arquivo de mapeamento (exemplo)
├── migrar.bat               # assistente para usuários leigos (Windows)
└── README.md
```

## Limitações

- A aplicação não valida se o código novo existe no EDOPro. Um código incorreto no layout produzirá um deck com carta inexistente.
- Subpastas da pasta informada **não** são processadas.
- Códigos legados que não constem no layout permanecem inalterados.

## Licença e responsabilidade

O uso desta aplicação é **livre**. Ela existe apenas para auxiliar na migração de dados de outra aplicação (EDOPro) e é fornecida **"como está"**, sem garantias de qualquer tipo.

Antes de executar, observe:

- **Leia o código** (`main.py` e `migrador.py`) para ter certeza do que está prestes a executar. Ele é curto e usa apenas a biblioteca padrão do Python.
- **Faça backup da pasta de decks inteira** antes de rodar, mesmo usando a opção `--backup` ou o `migrar.bat`.
- **A responsabilidade por quaisquer dados corrompidos ou perdidos é exclusivamente de quem executa** a aplicação. Os autores não respondem por danos decorrentes do uso.
