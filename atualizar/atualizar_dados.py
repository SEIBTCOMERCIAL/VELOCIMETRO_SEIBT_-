# -*- coding: utf-8 -*-
"""
=============================================================================
ATUALIZADOR DO PAINEL COMERCIAL SEIBT
=============================================================================
Roda dentro da empresa, numa maquina que enxerga o Oracle. Faz tres coisas:

  1. Consulta os numeros de pedidos e faturamento (as mesmas duas consultas
     do VELOCIMETRO.pbix)
  2. Grava o resultado em docs/dados.json
  3. Envia para o GitHub

O painel publicado no GitHub le esse arquivo e se atualiza sozinho.

COMO USAR: rode o atualizar.bat. Para atualizar automaticamente de tempo em
tempo, agende o atualizar.bat no Agendador de Tarefas do Windows (o passo a
passo esta no LEIA-ME.md).
=============================================================================
"""

import configparser
import json
import os
import subprocess
import sys
from datetime import datetime

try:
    import oracledb
except ImportError:
    sys.exit("Falta um componente. Rode:  python -m pip install oracledb")

PASTA = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(PASTA)
CONFIG_INI = os.path.join(PASTA, "config.ini")
ARQUIVO_SAIDA = os.path.join(RAIZ, "docs", "dados.json")

# =============================================================================
# CONSULTAS — copia fiel das que estao no VELOCIMETRO.pbix, ja com a correcao
# de 26/08/2026 (naturezas 640/111/123 fora, por serem remessa de
# demonstracao/troca/garantia, e nao venda)
# =============================================================================

SQL_PEDIDOS = """
WITH parametros AS (
    SELECT TRUNC(SYSDATE, 'MM')                AS inicio_mes,
           TRUNC(ADD_MONTHS(SYSDATE, 1), 'MM') AS fim_mes,
           TRUNC(SYSDATE, 'Q')                 AS inicio_trim,
           TRUNC(ADD_MONTHS(SYSDATE, 3), 'Q')  AS fim_trim
    FROM DUAL
)
SELECT
    SUM(CASE WHEN PV.DT_PEDIDO >= p.inicio_mes AND PV.DT_PEDIDO < p.fim_mes
             THEN PVI.VL_LIQUIDO_ITEM_PEDIDO + NVL(PVI.VL_IPI, 0) ELSE 0 END) AS VALOR_MES,
    SUM(CASE WHEN PV.DT_PEDIDO >= p.inicio_trim AND PV.DT_PEDIDO < p.fim_trim
             THEN PVI.VL_LIQUIDO_ITEM_PEDIDO + NVL(PVI.VL_IPI, 0) ELSE 0 END) AS VALOR_TRIMESTRE
FROM DESENV.PEDIDO_VENDA PV
JOIN DESENV.CLIENTE_FORNECEDOR_GERAL CFG ON CFG.CD_CLIENTE_FORNECEDOR = PV.CD_CLIENTE_FORNECEDOR
JOIN DESENV.PEDIDO_VENDA_ITEM PVI ON PVI.CD_PEDIDO = PV.CD_PEDIDO
CROSS JOIN parametros p
WHERE UPPER(CFG.FANTASIA) NOT LIKE '%SEIBT%'
  AND PV.IN_SITUACAO_PEDIDO_GERAL IN ('TAT', 'TPE', 'PEN')
  AND PVI.CD_NATUREZA_OPERACAO IN (100, 101, 102, 104, 109, 141, 171, 172, 190, 194, 196, 300)
  AND PV.CD_PEDIDO NOT IN (21993, 22004)
  AND PV.DT_PEDIDO >= p.inicio_trim AND PV.DT_PEDIDO < p.fim_trim
"""

SQL_FATURAMENTO = """
WITH parametros AS (
    SELECT TRUNC(SYSDATE, 'MM')                AS inicio_mes,
           TRUNC(ADD_MONTHS(SYSDATE, 1), 'MM') AS fim_mes,
           TRUNC(SYSDATE, 'Q')                 AS inicio_trim,
           TRUNC(ADD_MONTHS(SYSDATE, 3), 'Q')  AS fim_trim
    FROM DUAL
)
SELECT
    SUM(CASE WHEN NFSI.DT_EMISSAO >= p.inicio_mes AND NFSI.DT_EMISSAO < p.fim_mes
             THEN NFSI.VL_FATURADO + NVL(NFSI.VL_IPI_ITEM, 0) ELSE 0 END) AS VALOR_MES,
    SUM(CASE WHEN NFSI.DT_EMISSAO >= p.inicio_trim AND NFSI.DT_EMISSAO < p.fim_trim
             THEN NFSI.VL_FATURADO + NVL(NFSI.VL_IPI_ITEM, 0) ELSE 0 END) AS VALOR_TRIMESTRE
FROM DESENV.NOTA_FISCAL_SAIDA_ITEM NFSI
JOIN DESENV.NOTA_FISCAL_SAIDA NFS
  ON NFS.CD_EMPRESA = NFSI.CD_EMPRESA
 AND NFS.CD_FILIAL  = NFSI.CD_FILIAL
 AND NFS.NR_NOTA    = NFSI.NR_NOTA
 AND NFS.SERIE_NFS  = NFSI.SERIE_NFS
JOIN DESENV.CLIENTE_FORNECEDOR_GERAL CFG ON CFG.CD_CLIENTE_FORNECEDOR = NFS.CD_CLIENTE_FORNECEDOR
JOIN DESENV.NATUREZA_OPERACAO NOP
  ON NOP.CD_NATUREZA_OPERACAO = NFSI.CD_NATUREZA_OPERACAO
 AND NOP.IN_FATURAMENTO = 'S'
CROSS JOIN parametros p
WHERE NFS.DT_CANCELAMENTO IS NULL
  AND UPPER(CFG.FANTASIA) NOT LIKE '%SEIBT%'
  AND NFSI.CD_NATUREZA_OPERACAO <> 105
  AND NFSI.DT_EMISSAO >= p.inicio_trim AND NFSI.DT_EMISSAO < p.fim_trim
"""

MODELO_INI = """; Configuracao do atualizador do painel.

[oracle]
dsn = 10.50.1.251:1526/prod.seibt
usuario =
senha =

; Pasta do Oracle Instant Client 64 bits. Necessaria neste banco.
client_dir = C:\\Users\\felipe.molinos\\Desktop\\instantclient-basic-windows.x64-21.22.0.0.0dbru\\instantclient_21_22

[github]
; true  = envia sozinho para o GitHub depois de gerar os numeros
; false = so grava o arquivo aqui, sem enviar
enviar = true
"""

AJUDA_DPY3015 = """
ERRO DPY-3015 — a senha deste usuario esta gravada no Oracle num formato
antigo, que o programa nao le sem ajuda. Nao e senha errada.

Solucao: no config.ini, aponte 'client_dir' para a pasta do Oracle Instant
Client 64 bits. Se ainda nao tiver, baixe o "Basic" em:
https://www.oracle.com/database/technologies/instant-client/winx64-64-downloads.html
"""


def carrega_config():
    if not os.path.exists(CONFIG_INI):
        with open(CONFIG_INI, "w", encoding="utf-8") as fh:
            fh.write(MODELO_INI)
        sys.exit(f"Criei o arquivo de configuracao:\n  {CONFIG_INI}\n\n"
                 "Preencha usuario e senha e rode de novo.")

    cfg = configparser.ConfigParser()
    cfg.read(CONFIG_INI, encoding="utf-8")

    usuario = cfg.get("oracle", "usuario", fallback="").strip()
    senha = cfg.get("oracle", "senha", fallback="").strip()
    if not usuario or not senha:
        sys.exit(f"Preencha usuario e senha em:\n  {CONFIG_INI}")

    return {
        "dsn": cfg.get("oracle", "dsn", fallback="10.50.1.251:1526/prod.seibt").strip(),
        "usuario": usuario,
        "senha": senha,
        "client_dir": cfg.get("oracle", "client_dir", fallback="").strip(),
        "enviar": cfg.getboolean("github", "enviar", fallback=True),
    }


def consulta_oracle(cfg):
    if cfg["client_dir"]:
        if not os.path.isdir(cfg["client_dir"]):
            sys.exit(f"A pasta indicada em 'client_dir' nao existe:\n  {cfg['client_dir']}")
        try:
            oracledb.init_oracle_client(lib_dir=cfg["client_dir"])
        except Exception as erro:
            sys.exit(f"Nao consegui carregar o Oracle Client de:\n  {cfg['client_dir']}\n\n{erro}")

    try:
        con = oracledb.connect(user=cfg["usuario"], password=cfg["senha"], dsn=cfg["dsn"])
    except oracledb.Error as erro:
        if "DPY-3015" in str(erro):
            sys.exit(AJUDA_DPY3015)
        raise

    with con:
        cur = con.cursor()
        cur.execute(SQL_PEDIDOS)
        ped_mes, ped_tri = cur.fetchone()
        cur.execute(SQL_FATURAMENTO)
        fat_mes, fat_tri = cur.fetchone()

    return {
        "atualizado_em": datetime.now().astimezone().isoformat(timespec="seconds"),
        "pedidos_mes": float(ped_mes or 0),
        "pedidos_trimestre": float(ped_tri or 0),
        "faturamento_mes": float(fat_mes or 0),
        "faturamento_trimestre": float(fat_tri or 0),
    }


def grava(dados):
    os.makedirs(os.path.dirname(ARQUIVO_SAIDA), exist_ok=True)
    # Grava num arquivo temporario e so entao renomeia: assim ninguem
    # consegue ler um arquivo pela metade.
    temporario = ARQUIVO_SAIDA + ".tmp"
    with open(temporario, "w", encoding="utf-8") as fh:
        json.dump(dados, fh, ensure_ascii=False, indent=2)
    os.replace(temporario, ARQUIVO_SAIDA)


def envia_para_github():
    def git(*args):
        return subprocess.run(["git", *args], cwd=RAIZ,
                              capture_output=True, text=True, encoding="utf-8", errors="replace")

    if git("rev-parse", "--git-dir").returncode != 0:
        print("  (esta pasta ainda nao esta ligada ao GitHub — arquivo gerado, nada enviado)")
        return

    git("add", "docs/dados.json")

    # Sem mudanca no conteudo, nao ha o que enviar
    if git("diff", "--cached", "--quiet", "--", "docs/dados.json").returncode == 0:
        print("  numeros iguais aos do envio anterior, nada a enviar")
        return

    carimbo = datetime.now().strftime("%d/%m/%Y %H:%M")
    r = git("commit", "-m", f"Atualiza numeros do painel - {carimbo}")
    if r.returncode != 0:
        print("  nao consegui registrar a alteracao:", (r.stderr or r.stdout).strip()[:200])
        return

    r = git("push")
    if r.returncode != 0:
        print("  nao consegui enviar para o GitHub:", (r.stderr or r.stdout).strip()[:300])
        return

    print("  enviado para o GitHub")


def main():
    cfg = carrega_config()

    print(f"[{datetime.now():%d/%m/%Y %H:%M:%S}] consultando o Oracle...")
    dados = consulta_oracle(cfg)

    print(f"  Pedidos mes:      R$ {dados['pedidos_mes']:>15,.2f}")
    print(f"  Pedidos trim.:    R$ {dados['pedidos_trimestre']:>15,.2f}")
    print(f"  Faturamento mes:  R$ {dados['faturamento_mes']:>15,.2f}")
    print(f"  Faturam. trim.:   R$ {dados['faturamento_trimestre']:>15,.2f}")

    grava(dados)
    print(f"  gravado em docs/dados.json")

    if cfg["enviar"]:
        envia_para_github()
    else:
        print("  envio ao GitHub desligado no config.ini")

    print("  pronto.")


if __name__ == "__main__":
    main()
