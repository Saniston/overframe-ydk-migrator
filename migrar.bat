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

if not exist "%LAYOUT%" (
    echo ERRO: arquivo de layout nao encontrado:
    echo %LAYOUT%
    goto fim
)

rem --- Pasta dos decks: argumento (arrastar e soltar) ou pergunta ---
set "PASTA=%~1"
if not defined PASTA (
    echo Informe a pasta onde estao os decks .ydk
    echo Exemplo: C:\EDOPro\deck
    echo.
    set /p "PASTA=Pasta: "
)
rem Remove aspas que o usuario possa ter colado
set "PASTA=!PASTA:"=!"

if not exist "!PASTA!\" (
    echo.
    echo ERRO: pasta nao encontrada: !PASTA!
    goto fim
)

rem --- Simulacao (nao altera nada) ---
echo.
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
set /p "RESP=Deseja aplicar essas alteracoes? Sera criada uma copia .bak de cada deck alterado. (S/N): "
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
echo Pronto. Para desfazer, restaure os arquivos .bak (remova o ".bak" do nome).

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
