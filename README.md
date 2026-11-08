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
- Internet e o EDOPro instalado apenas para a opção `--atualizar-layout`

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
| `--atualizar-layout` | [Opcional] Gera decks sample e, após confirmação, um novo layout com as cartas de extended art da Yugipedia confirmadas no EDOPro, movendo o anterior para `backup_layout` (veja abaixo). Com ele, `--pasta` passa a ser opcional. |
| `--edopro` | [Opcional] Pasta de instalação do EDOPro usada por `--atualizar-layout`. Sem ela, a pasta é deduzida e o usuário confirma. |

## Atualizar o layout automaticamente

```bash
python main.py --layout "layout_migracao.txt" --atualizar-layout [--edopro "C:\ProjectIgnis"] [--simular]
```

O layout é montado cruzando três fontes, para que o usuário não precise preencher os códigos à mão:

| Fonte | Uso |
|---|---|
| [Yugipedia — Extended art](https://yugipedia.com/wiki/Extended_art) | Lista das cartas com extended art / Overframe, lida pela API do MediaWiki (`api.php?action=parse&page=Extended_art&prop=wikitext`). |
| [API do YGOPRODeck](https://db.ygoprodeck.com/api-guide/) | Converte cada nome em `id` (código legado) e `frameType` (seção do deck nos samples), consultando vários nomes por requisição (`name=A\|B\|C`). |
| Banco de cartas do EDOPro (`expansions/*.cdb` e `repositories/**/*.cdb`) | Confirma que a versão Overframe existe: o código **legado + 1** precisa existir e ser a mesma carta (campo `alias`). |

Exemplo de linha gerada:

```
Borreload Liberator Dragon|27096833|27096834
```

### Pasta do EDOPro

Sem `--edopro`, a aplicação procura a pasta do EDOPro (a pasta acima de `--pasta`, ou `C:\ProjectIgnis`, `D:\ProjectIgnis`, `C:\EDOPro`, `D:\EDOPro`) e **sempre pergunta** se deve usá-la. Respondendo `N`, ou se nada for encontrado, o usuário digita o caminho. Sem uma pasta com bancos `.cdb`, o layout não é alterado.

### Pendências

Cartas que não puderam ser confirmadas **não entram no layout**. Elas vão para o arquivo `layout_migracao_pendencias.txt`, ao lado do layout, no mesmo formato, com o código novo em branco e um comentário com o motivo:

```
# código legado + 1 não existe no EDOPro
# outras artes desta carta no EDOPro: 54577951
Witness of the Ancient|54577949|
```

- **código legado + 1 não existe no EDOPro**: a Overframe pode usar outro código (veja as outras artes sugeridas) ou ainda não existir no EDOPro.
- **código legado não existe no EDOPro**: a carta pode estar no EDOPro com código de pré-lançamento ou ainda não ter sido adicionada.
- **Não encontradas no YGOPRODeck**: nome sem código legado (carta só OCG, nome diferente ou página que não é carta).

Para migrar uma pendência, confira o código no EDOPro, preencha o código novo e mova a linha para o layout. O arquivo de pendências é regenerado a cada atualização (e removido quando não há pendências) e não é lido pela migração.

### Etapas

1. **Decks sample**: são gerados os arquivos `sample_01.ydk`, `sample_02.ydk`, ... na subpasta `samples` **da pasta de decks**: a de `--pasta`, quando informada, ou a pasta `deck` do EDOPro (ex.: `C:\ProjectIgnis\deck\samples`). Samples anteriores são removidos. Em cada sample, **cada carta legado aparece seguida da sua versão Overframe**, para comparação lado a lado. Como a migração ignora subpastas, os samples nunca são migrados.
2. **Conferência**: abra os samples no editor de decks do EDOPro (pasta `samples` da lista de decks). Se alguma carta Overframe estiver ausente, em branco ou diferente da legado, o código está errado.
3. **Confirmação**: a aplicação pergunta se os samples estão corretos. Respondendo `S`, o novo layout e as pendências são gravados e o layout anterior é **movido para a pasta `backup_layout`** com data e hora no nome (ex.: `backup_layout/layout_migracao_20261107-153000.txt`). Respondendo `N`, nada é alterado.

### Regras dos samples

| Seção | Regra |
|---|---|
| `#main` | Até 60 linhas (30 pares legado/Overframe). Cartas cujo `frameType` não é de Extra Deck. |
| `#extra` | Até 14 linhas (7 pares; o limite do jogo é 15). Somente cartas cujo `frameType` contém `fusion`, `synchro`, `xyz` ou `link`. |
| `!side` | Vazio. |

São gerados quantos samples forem necessários para incluir todas as cartas.

### Observações

- O novo layout contém **somente** as cartas confirmadas; linhas do layout anterior ficam apenas no backup.
- Cartas sem `frameType` vão para o Main Deck e geram aviso. Também há aviso quando o código Overframe de uma carta coincide com o código legado de outra.
- Com `--simular`, apenas informa o que seria gerado, sem gravar samples, layout nem pendências e sem pedir a confirmação dos samples (a pasta do EDOPro continua sendo perguntada, pois os bancos são lidos).
- Pode ser combinado com `--pasta`: após a confirmação, a migração dos decks segue com o novo layout. Se a confirmação for negada, a execução termina sem migrar.
- Requer acesso à internet e o EDOPro instalado.

## Uso simplificado (Windows)

Para quem não quer usar a linha de comando, basta usar o `migrar.bat`:

1. Dê **dois cliques** em `migrar.bat` (ou **arraste a pasta de decks** sobre o arquivo).
2. Leia o **aviso de responsabilidade** e confirme com `S` que fez backup da pasta de decks.
3. Se o **Python não estiver instalado**, o assistente pergunta se deseja instalá-lo (via `winget`; sem o `winget`, abre a página de download). Após instalar, pode ser preciso fechar a janela e abrir o `migrar.bat` de novo.
4. O assistente pergunta se deseja **atualizar o layout automaticamente** (veja [Atualizar o layout automaticamente](#atualizar-o-layout-automaticamente)). Respondendo `S`, confirme ou informe a pasta do EDOPro; são gerados os decks sample na pasta `deck\samples` do EDOPro; confira-os no editor de decks e confirme para gravar o novo layout (e as pendências). Se a atualização for cancelada ou falhar, o assistente pergunta se deseja continuar a migração com o layout atual.
5. Se não arrastou a pasta, digite o caminho dela (ex.: `C:\EDOPro\deck`).
6. O assistente mostra primeiro uma **simulação**, sem alterar nada.
7. Responda `S` para aplicar. Uma cópia `.bak` de cada deck alterado é criada.

Ele usa o `layout_migracao.txt` da própria pasta do projeto (e grava ali a pasta `backup_layout` e o arquivo de pendências, quando o layout é atualizado) e exige o Python (o próprio assistente oferece a instalação). Para desfazer, remova o `.bak` do nome do arquivo de backup, substituindo o deck alterado.

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
├── layout_api.py            # geração do layout, das pendências e dos samples (Yugipedia, YGOPRODeck, EDOPro)
├── layout_migracao.txt      # arquivo de mapeamento (exemplo)
├── layout_migracao_pendencias.txt  # cartas não confirmadas (gerado pela atualização do layout)
├── migrar.bat               # assistente para usuários leigos (Windows)
└── README.md
```

## Limitações

- A migração não valida se o código novo existe no EDOPro (só a atualização do layout valida). Um código incorreto preenchido à mão no layout produzirá um deck com carta inexistente.
- Subpastas da pasta informada **não** são processadas.
- Códigos legados que não constem no layout permanecem inalterados.

## Licença e responsabilidade

O uso desta aplicação é **livre**. Ela existe apenas para auxiliar na migração de dados de outra aplicação (EDOPro) e é fornecida **"como está"**, sem garantias de qualquer tipo.

Antes de executar, observe:

- **Leia o código** (`main.py` e `migrador.py`) para ter certeza do que está prestes a executar. Ele é curto e usa apenas a biblioteca padrão do Python.
- **Faça backup da pasta de decks inteira** antes de rodar, mesmo usando a opção `--backup` ou o `migrar.bat`.
- **A responsabilidade por quaisquer dados corrompidos ou perdidos é exclusivamente de quem executa** a aplicação. Os autores não respondem por danos decorrentes do uso.
