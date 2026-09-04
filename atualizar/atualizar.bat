@echo off
REM Atualiza os numeros do painel e envia para o GitHub.
title Atualizar Painel SEIBT
cd /d "%~dp0"
python "%~dp0atualizar_dados.py"
if errorlevel 1 (
  echo.
  echo Algo deu errado. Leia a mensagem acima.
  pause
)
