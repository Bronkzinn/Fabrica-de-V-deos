@echo off
chcp 65001 > nul
title Automação Chefinho Gastro - Execução Única

echo ========================================================
echo   Iniciando Execução Única da Rotina de Postagem...
echo ========================================================
echo.

:: Garante o posicionamento no diretório do script
cd /d "%~dp0"

:: Garante que a pasta de logs existe
if not exist "logs" (
    mkdir logs
)

:: Executa o script de postagem com a flag --run-once
python rotina_diaria.py --run-once

echo.
echo ========================================================
echo   Processo finalizado. Verifique as mensagens acima.
echo ========================================================
echo.
pause
