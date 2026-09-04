/* ===========================================================================
   Guarda a pagina no aparelho, para abrir rapido e funcionar sem internet.
   ---------------------------------------------------------------------------
   REGRA IMPORTANTE: o arquivo de dados (dados.json) NUNCA e servido da copia
   guardada quando ha internet. Se fosse, o painel mostraria numero velho
   parecendo atual — o pior defeito possivel aqui. A copia so entra em cena
   quando a internet cai, e nesse caso a propria tela avisa.
   =========================================================================== */

const VERSAO = "v1";
const CACHE_APP   = `seibt-app-${VERSAO}`;
const CACHE_DADOS = `seibt-dados-${VERSAO}`;

const ARQUIVOS_DO_APP = [
  "./",
  "./index.html",
  "./estilo.css",
  "./app.js",
  "./manifest.json",
  "./icone-192.png",
  "./icone-512.png"
];

self.addEventListener("install", evento => {
  evento.waitUntil(
    caches.open(CACHE_APP)
      .then(c => c.addAll(ARQUIVOS_DO_APP))
      .then(() => self.skipWaiting())
  );
});

self.addEventListener("activate", evento => {
  evento.waitUntil(
    caches.keys()
      .then(nomes => Promise.all(
        nomes.filter(n => n !== CACHE_APP && n !== CACHE_DADOS)
             .map(n => caches.delete(n))
      ))
      .then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", evento => {
  const req = evento.request;
  if (req.method !== "GET") return;

  const url = new URL(req.url);

  // Dados: sempre tenta a internet primeiro. So usa a copia se falhar.
  if (url.pathname.endsWith("dados.json")) {
    evento.respondWith(
      fetch(req)
        .then(resp => {
          const copia = resp.clone();
          caches.open(CACHE_DADOS).then(c => c.put("dados.json", copia));
          return resp;
        })
        .catch(() => caches.open(CACHE_DADOS).then(c => c.match("dados.json")))
    );
    return;
  }

  // Resto da pagina: usa a copia guardada (abre instantaneo) e busca
  // atualizacao em segundo plano para a proxima vez.
  evento.respondWith(
    caches.match(req).then(guardado => {
      const daRede = fetch(req).then(resp => {
        if (resp && resp.status === 200 && resp.type === "basic") {
          const copia = resp.clone();
          caches.open(CACHE_APP).then(c => c.put(req, copia));
        }
        return resp;
      }).catch(() => guardado);
      return guardado || daRede;
    })
  );
});
