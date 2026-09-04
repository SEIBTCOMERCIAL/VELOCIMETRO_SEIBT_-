# -*- coding: utf-8 -*-
"""
Confere se o painel esta inteiro e correto antes de publicar.
Rode:  python testes\\testar.py
"""
import json
import os
import re
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOCS = os.path.join(RAIZ, "docs")

falhas = []
def checa(nome, ok, detalhe=""):
    print(("  OK    " if ok else "  FALHA ") + nome + (f"  -> {detalhe}" if detalhe and not ok else ""))
    if not ok:
        falhas.append(nome)

def ler(nome):
    with open(os.path.join(DOCS, nome), encoding="utf-8") as fh:
        return fh.read()


print("=== 1. Arquivos obrigatorios ===")
for arq in ("index.html", "app.js", "estilo.css", "manifest.json", "sw.js",
            "dados.json", "icone-192.png", "icone-512.png", ".nojekyll"):
    checa(f"existe docs/{arq}", os.path.exists(os.path.join(DOCS, arq)))
checa("existe atualizar/atualizar_dados.py",
      os.path.exists(os.path.join(RAIZ, "atualizar", "atualizar_dados.py")))
checa("existe .gitignore", os.path.exists(os.path.join(RAIZ, ".gitignore")))


print("\n=== 2. Configuracao ficha fora do GitHub ===")
gi = open(os.path.join(RAIZ, ".gitignore"), encoding="utf-8").read()
checa("config.ini esta no .gitignore", "atualizar/config.ini" in gi)


print("\n=== 3. Ficha do aplicativo (manifest) ===")
man = json.loads(ler("manifest.json"))
for campo in ("name", "short_name", "start_url", "display", "icons", "theme_color"):
    checa(f"manifest tem '{campo}'", campo in man)
checa("abre como aplicativo", man.get("display") == "standalone", man.get("display"))
tamanhos = {i.get("sizes") for i in man.get("icons", [])}
checa("tem icone 192x192", "192x192" in tamanhos, tamanhos)
checa("tem icone 512x512", "512x512" in tamanhos, tamanhos)
checa("tem icone 'maskable' (Android)",
      any(i.get("purpose") == "maskable" for i in man.get("icons", [])))
for icone in man.get("icons", []):
    checa(f"icone existe: {icone['src']}", os.path.exists(os.path.join(DOCS, icone["src"])))
checa("caminhos sao relativos (funciona em subpasta do GitHub)",
      man["start_url"].startswith("./") and man.get("scope", "./").startswith("./"),
      man["start_url"])


print("\n=== 4. Pagina ===")
html = ler("index.html")
checa("liga o manifest", 'rel="manifest"' in html)
checa("liga o estilo", 'href="estilo.css"' in html)
checa("liga o programa", 'src="app.js"' in html)
checa("tem cor da barra do celular", 'name="theme-color"' in html)
checa("ajusta para celular (viewport)", 'name="viewport"' in html)
checa("tem icone para iPhone", 'rel="apple-touch-icon"' in html)
checa("logo embutido na propria pagina", "data:image/png;base64," in html)
for ident in ("g_pedidos_mes", "g_faturamento_mes", "g_pedidos_trimestre",
              "g_faturamento_trimestre", "carimbo", "aviso"):
    checa(f"tem o espaco '{ident}'", f'id="{ident}"' in html)


print("\n=== 5. Funcionamento offline ===")
sw = ler("sw.js")
checa("guarda a pagina no aparelho", "caches.open" in sw and "addAll" in sw)
checa("NUNCA serve numero velho quando ha internet",
      "dados.json" in sw and re.search(r"fetch\(req\)[\s\S]{0,400}?catch", sw) is not None)
checa("limpa versoes antigas", "caches.delete" in sw)
checa("assume o controle na hora", "skipWaiting" in sw and "clients.claim" in sw)


print("\n=== 6. Arquivo de numeros ===")
dados = json.loads(ler("dados.json"))
for campo in ("atualizado_em", "pedidos_mes", "pedidos_trimestre",
              "faturamento_mes", "faturamento_trimestre"):
    checa(f"dados.json tem '{campo}'", campo in dados)
checa("os quatro numeros sao numericos",
      all(isinstance(dados.get(c), (int, float)) for c in
          ("pedidos_mes", "pedidos_trimestre", "faturamento_mes", "faturamento_trimestre")))


print("\n=== 7. Regras do painel (mesmas do Power BI) ===")
app = ler("app.js")
checa("meta anual 43,1 milhoes", "43100000" in app)
checa("ponto de equilibrio 2,65 milhoes", "2650000" in app)
checa("maximo do mes 6 milhoes", "6000000" in app)
checa("maximo do trimestre 18 milhoes", "18000000" in app)
checa("cor vermelha abaixo do equilibrio", "--vermelho" in app)
checa("cor verde entre equilibrio e meta", "--verde" in app)
checa("cor azul acima da meta", "--azul" in app)
checa("procura numero novo sozinho", "setInterval" in app)
checa("evita numero guardado pelo navegador", "no-store" in app and "?t=" in app)
checa("avisa quando o numero esta velho", "MINUTOS_PARA_AVISAR" in app)

# Confere a regra de cor exatamente como esta escrita
m = re.search(r"function cor\(valor, pe, meta\)\s*\{([\s\S]*?)\}", app)
regra = m.group(1) if m else ""
checa("regra de cor na ordem certa",
      regra.index("valor < pe") < regra.index("valor < meta") if
      ("valor < pe" in regra and "valor < meta" in regra) else False)

# Confere que o risco da meta fica dentro da barra
checa("risco da meta contido na barra",
      "pontoNoAngulo(R - ESPESSURA / 2, anguloMeta)" in app and
      "pontoNoAngulo(R + ESPESSURA / 2, anguloMeta)" in app)


print("\n=== 8. Atualizador ===")
atu = open(os.path.join(RAIZ, "atualizar", "atualizar_dados.py"), encoding="utf-8").read()
checa("usa as consultas de pedidos e faturamento",
      "SQL_PEDIDOS" in atu and "SQL_FATURAMENTO" in atu)
checa("mantem a correcao das naturezas (sem 640/111/123)",
      "(100, 101, 102, 104, 109, 141, 171, 172, 190, 194, 196, 300)" in atu)
checa("nao usa mais as naturezas removidas",
      "640" not in atu.split("MODELO_INI")[0].split("SQL_PEDIDOS")[1].split("SQL_FATURAMENTO")[0])
checa("grava sem deixar arquivo pela metade", "os.replace" in atu)
checa("envia para o GitHub sozinho", "push" in atu)
checa("nao envia se o numero nao mudou", "--cached" in atu and "--quiet" in atu)


print("\n" + "=" * 62)
if falhas:
    print(f"{len(falhas)} PROBLEMA(S):")
    for f in falhas:
        print("  -", f)
    sys.exit(1)
print("TODOS OS TESTES PASSARAM — o painel esta pronto para publicar.")
