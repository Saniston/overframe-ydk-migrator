@echo off
rem Assistente para migrar os decks do EDOPro para as cartas Overframe.
rem Uso: de dois cliques neste arquivo, ou arraste a pasta de decks sobre ele.
setlocal EnableDelayedExpansion
chcp 65001 >nul
cd /d "%~dp0"

set "LAYOUT=%~dp0layout_migracao.txt"

echo ============================================
echo   Migrador de decks EDOPro - Overframe
echo ============================================
echo.

rem --- Aviso de responsabilidade ---
echo ATENCAO:
echo  - Este programa ALTERA os arquivos .ydk da pasta informada.
echo  - Leia o codigo (main.py e migrador.py) se quiser saber exatamente o que sera executado.
echo  - Faca uma COPIA DE SEGURANCA da pasta de decks inteira antes de continuar.
echo  - Voce e responsavel por qualquer dado corrompido ou perdido.
echo.
set "OK="
set /p "OK=Li o aviso e fiz backup da pasta de decks. Continuar? (S/N): "
set "OK=!OK:~0,1!"
if /i not "!OK!"=="S" (
    echo.
    echo Cancelado. Nenhum deck foi alterado.
    goto fim
)
echo.

rem --- Procura o Python ---
call :achar_python
if defined PY goto python_ok

echo Python nao foi encontrado neste computador.
echo Ele e necessario para executar a migracao.
echo.
set "INST="
set /p "INST=Deseja instalar o Python agora? (S/N): "
set "INST=!INST:~0,1!"
if /i not "!INST!"=="S" (
    echo.
    echo Sem o Python nao e possivel continuar.
    echo Voce pode instalar manualmente em https://www.python.org/downloads/
    echo marcando a opcao "Add Python to PATH".
    goto fim
)

where winget >nul 2>nul
if errorlevel 1 (
    echo.
    echo O instalador automatico ^(winget^) nao esta disponivel neste Windows.
    echo Abrindo a pagina de download. Instale marcando "Add Python to PATH"
    echo e depois execute este arquivo novamente.
    start "" "https://www.python.org/downloads/"
    goto fim
)

echo.
echo Instalando o Python com o winget. Aguarde e aceite os pedidos do Windows...
winget install -e --id Python.Python.3.12 --accept-package-agreements --accept-source-agreements
call :achar_python
if not defined PY (
    echo.
    echo Instalacao concluida ou interrompida, mas o Python ainda nao foi detectado.
    echo FECHE esta janela e execute o migrar.bat novamente.
    goto fim
)
echo.
echo Python instalado com sucesso.

:python_ok

rem --- Pasta dos decks: argumento (arrastar e soltar) ou pergunta ---
echo.
set "PASTA=%~1"
if not defined PASTA (
    echo Informe a pasta onde estao os decks .ydk
    echo Exemplo: C:\ProjectIgnis\deck
    echo.
    set /p "PASTA=Pasta: "
)
if not defined PASTA (
    echo.
    echo ERRO: nenhuma pasta foi informada.
    goto fim
)
rem Remove aspas que o usuario possa ter colado
set "PASTA=!PASTA:"=!"

if not exist "!PASTA!\" (
    echo.
    echo ERRO: pasta nao encontrada: !PASTA!
    goto fim
)

rem --- Atualizacao opcional do layout (Yugipedia + YGOPRODeck + EDOPro) ---
echo.
echo O layout de migracao pode ser gerado de novo automaticamente:
echo  - a lista de cartas com extended art vem da Yugipedia;
echo  - os codigos vem da API do YGOPRODeck;
echo  - cada codigo Overframe (codigo legado + 1) e confirmado no seu EDOPro.
echo A pasta do EDOPro e deduzida a partir da pasta de decks e voce confirma
echo (ou informa outra). Cartas nao confirmadas vao para o arquivo
echo "layout_migracao_pendencias.txt". Serao gerados decks sample na pasta
echo "samples" dentro da pasta de decks, para voce conferir no editor de decks
echo do EDOPro antes de gravar o novo layout.
echo O layout atual vai para "backup_layout". Requer internet.
echo.
set "ATU="
set /p "ATU=Deseja atualizar o layout agora? (S/N): "
set "ATU=!ATU:~0,1!"
if /i "!ATU!"=="S" (
    echo.
    %PY% main.py --pasta "!PASTA!" --layout "%LAYOUT%" --atualizar-layout --somente-layout
    if errorlevel 1 (
        echo.
        echo O layout nao foi atualizado.
        set "CONT="
        set /p "CONT=Deseja continuar a migracao com o layout atual? (S/N): "
        set "CONT=!CONT:~0,1!"
        if /i not "!CONT!"=="S" (
            echo.
            echo Cancelado. Nenhum deck foi alterado.
            goto fim
        )
    )
)
echo.

if not exist "%LAYOUT%" (
    echo ERRO: arquivo de layout nao encontrado:
    echo %LAYOUT%
    goto fim
)

rem --- Simulacao (nao altera nada) ---
echo --- SIMULACAO: nenhum arquivo sera alterado ---
echo.
%PY% main.py --pasta "!PASTA!" --layout "%LAYOUT%" --simular
if errorlevel 1 (
    echo.
    echo Ocorreu um erro. Nada foi alterado.
    goto fim
)

echo.
set "RESP="
set /p "RESP=Deseja aplicar essas alteracoes? Sera criada uma copia de cada deck alterado na pasta bak. (S/N): "
set "RESP=!RESP:~0,1!"
if /i not "!RESP!"=="S" (
    echo.
    echo Cancelado. Nenhum deck foi alterado.
    goto fim
)

echo.
echo --- APLICANDO ---
echo.
%PY% main.py --pasta "!PASTA!" --layout "%LAYOUT%" --backup
if errorlevel 1 (
    echo.
    echo Ocorreu um erro durante a migracao.
    goto fim
)

echo.
echo Pronto. Copias dos decks alterados: !PASTA!\bak
echo Para desfazer, copie o arquivo .bak de volta para a pasta de decks e remova o ".bak" do nome.
if exist "%~dp0layout_migracao_pendencias.txt" (
    echo.
    echo Algumas cartas com extended art nao foram migradas por falta de confirmacao no EDOPro.
    echo Veja o arquivo layout_migracao_pendencias.txt na pasta do migrador.
)

:fim
echo.
pause
endlocal
exit /b

:achar_python
set "PY="
where py >nul 2>nul && set "PY=py -3"
if not defined PY (
    where python >nul 2>nul && set "PY=python"
)
exit /b 0
