/* ===========================================================================
   Painel Comercial SEIBT — logica do velocimetro
   ---------------------------------------------------------------------------
   Le os numeros de dados.json, que e regravado automaticamente pelo
   atualizador que roda na empresa. A pagina busca esse arquivo de tempo em
   tempo, entao ela se atualiza sozinha sem ninguem apertar nada.
   =========================================================================== */

const ARQUIVO_DADOS = "dados.json";
const INTERVALO_SEGUNDOS = 60;   // de quanto em quanto tempo procura numero novo
const MINUTOS_PARA_AVISAR = 30;  // se o dado for mais velho que isso, avisa na tela

/* --- Constantes copiadas das medidas do Power BI --------------------------- */
const META_ANUAL      = 43100000;
const META_MENSAL     = META_ANUAL / 12;
const META_TRIMESTRAL = META_ANUAL / 4;
const PE_MENSAL       = 2650000;
const PE_TRIMESTRAL   = PE_MENSAL * 3;
const MAX_MENSAL      = 6000000;
const MAX_TRIMESTRAL  = 18000000;

const GAUGES = [
  { id: "g_pedidos_mes",           campo: "pedidos_mes",           meta: META_MENSAL,     pe: PE_MENSAL,     max: MAX_MENSAL },
  { id: "g_faturamento_mes",       campo: "faturamento_mes",       meta: META_MENSAL,     pe: PE_MENSAL,     max: MAX_MENSAL },
  { id: "g_pedidos_trimestre",     campo: "pedidos_trimestre",     meta: META_TRIMESTRAL, pe: PE_TRIMESTRAL, max: MAX_TRIMESTRAL },
  { id: "g_faturamento_trimestre", campo: "faturamento_trimestre", meta: META_TRIMESTRAL, pe: PE_TRIMESTRAL, max: MAX_TRIMESTRAL }
];

const DEMO = {
  atualizado_em: null,
  pedidos_mes: 3093006.84,
  pedidos_trimestre: 8340943.123,
  faturamento_mes: 2716482.69,
  faturamento_trimestre: 4118154.73
};

/* --- Formatacao ----------------------------------------------------------- */
function milhoes(v, casas) {
  return (v / 1e6).toFixed(casas).replace(".", ",");
}
function metaTexto(v) {
  const mi = v / 1e6;
  return "R$ " + (mi >= 10 ? Math.round(mi).toString() : mi.toFixed(1).replace(".", ",")) + " Mi";
}
function cor(valor, pe, meta) {
  if (valor < pe)   return "var(--vermelho)";
  if (valor < meta) return "var(--verde)";
  return "var(--azul)";
}
function carimboTexto(iso) {
  const d = iso ? new Date(iso) : new Date();
  const p = n => String(n).padStart(2, "0");
  return `${p(d.getDate())}/${p(d.getMonth() + 1)}/${d.getFullYear()} ` +
         `${p(d.getHours())}:${p(d.getMinutes())}:${p(d.getSeconds())}`;
}

/* --- Desenho do gauge ----------------------------------------------------- */
const CX = 200, CY = 200, R = 145, ESPESSURA = 42;
const COMPRIMENTO_ARCO = Math.PI * R;

function pontoNoAngulo(raio, graus) {
  const rad = graus * Math.PI / 180;
  return [CX + raio * Math.cos(rad), CY - raio * Math.sin(rad)];
}

/* Numeros de 2 digitos de milhao (ex: "R$ 10,888 Mi") ficam mais largos que o
   vao interno do arco e vazavam por cima da barra. Encolhe a fonte so nesses
   casos, mantendo o tamanho cheio para os numeros normais. */
const LIMITE_CARACTERES = 11;
function tamanhoDaFonte(texto) {
  return (46 * Math.min(1, LIMITE_CARACTERES / texto.length)).toFixed(1);
}

function desenhaGauge(cfg, valor) {
  const fracao = Math.max(0, Math.min(1, valor / cfg.max));
  const anguloMeta = 180 - (Math.min(1, cfg.meta / cfg.max) * 180);

  // O risco da meta comeca e termina nas bordas da barra, sem sobrar ponta
  const [mx1, my1] = pontoNoAngulo(R - ESPESSURA / 2, anguloMeta);
  const [mx2, my2] = pontoNoAngulo(R + ESPESSURA / 2, anguloMeta);
  const [lx,  ly ] = pontoNoAngulo(R + ESPESSURA / 2 + 16, anguloMeta);
  const ancora = anguloMeta > 90 ? "end" : "start";

  const textoValor = `R$ ${milhoes(valor, 3)} Mi`;

  return `
  <svg viewBox="0 0 400 250" preserveAspectRatio="xMidYMid meet">
    <path d="M ${CX - R} ${CY} A ${R} ${R} 0 0 1 ${CX + R} ${CY}"
          fill="none" stroke="var(--trilho)" stroke-width="${ESPESSURA}"/>
    <path d="M ${CX - R} ${CY} A ${R} ${R} 0 0 1 ${CX + R} ${CY}"
          fill="none" stroke="${cor(valor, cfg.pe, cfg.meta)}" stroke-width="${ESPESSURA}"
          stroke-dasharray="${fracao * COMPRIMENTO_ARCO} ${COMPRIMENTO_ARCO}"
          style="transition: stroke-dasharray .6s ease, stroke .6s ease"/>
    <line x1="${mx1}" y1="${my1}" x2="${mx2}" y2="${my2}"
          stroke="var(--meta-linha)" stroke-width="2.5"/>
    <text class="escala" x="${lx}" y="${ly}" text-anchor="${ancora}">${metaTexto(cfg.meta)}</text>
    <text class="valor" x="${CX}" y="${CY - 12}" text-anchor="middle"
          style="font-size:${tamanhoDaFonte(textoValor)}px">${textoValor}</text>
    <text class="escala" x="${CX - R - 22}" y="${CY + 28}" text-anchor="start">R$ 0,000 Mi</text>
    <text class="escala" x="${CX + R + 22}" y="${CY + 28}" text-anchor="end">R$ ${milhoes(cfg.max, 2)} Mi</text>
  </svg>`;
}

/* --- Tela ----------------------------------------------------------------- */
function mostraAviso(html) {
  const el = document.getElementById("aviso");
  if (html) { el.innerHTML = html; el.classList.add("visivel"); document.body.classList.add("off"); }
  else      { el.classList.remove("visivel");                   document.body.classList.remove("off"); }
}

function desenha(dados) {
  GAUGES.forEach(cfg => {
    document.getElementById(cfg.id).innerHTML = desenhaGauge(cfg, dados[cfg.campo] ?? 0);
  });
  document.getElementById("carimbo").textContent = carimboTexto(dados.atualizado_em);
}

/** Minutos desde a geracao do dado. Null se nao houver data. */
function idadeEmMinutos(iso) {
  if (!iso) return null;
  const t = new Date(iso).getTime();
  if (isNaN(t)) return null;
  return (Date.now() - t) / 60000;
}

let jaTeveDado = false;

async function atualiza() {
  try {
    // Marca de tempo na URL: garante numero novo mesmo se o navegador
    // (ou o GitHub) tiver guardado uma copia antiga do arquivo.
    const r = await fetch(`${ARQUIVO_DADOS}?t=${Date.now()}`, { cache: "no-store" });
    if (!r.ok) throw new Error("HTTP " + r.status);
    const dados = await r.json();

    desenha(dados);
    jaTeveDado = true;

    const idade = idadeEmMinutos(dados.atualizado_em);
    if (idade !== null && idade > MINUTOS_PARA_AVISAR) {
      // O atualizador na empresa parou de rodar. Sem esse aviso, a tela
      // mostraria numero velho parecendo atual — pior que mostrar erro.
      const horas = Math.floor(idade / 60);
      const quanto = horas >= 1 ? `${horas} h` : `${Math.round(idade)} min`;
      mostraAviso(`<b>Estes números estão parados há ${quanto}.</b> ` +
                  `A atualização automática pode ter sido interrompida. ` +
                  `Último número recebido: ${carimboTexto(dados.atualizado_em)}.`);
    } else {
      mostraAviso(null);
    }

  } catch (e) {
    if (!jaTeveDado) {
      desenha(DEMO);
      mostraAviso("<b>Estes números são de demonstração, não são reais.</b> " +
                  "Não foi possível carregar os dados. Verifique sua conexão " +
                  "e atualize a página.");
    } else {
      mostraAviso("<b>Sem conexão.</b> Mostrando os últimos números recebidos, " +
                  "que podem estar desatualizados.");
    }
  }
}

atualiza();
setInterval(atualiza, INTERVALO_SEGUNDOS * 1000);

// Voltou a olhar a tela depois de um tempo: busca numero novo na hora,
// sem esperar o proximo ciclo.
document.addEventListener("visibilitychange", () => {
  if (!document.hidden) atualiza();
});

// Registra o funcionamento offline (guarda a pagina no aparelho)
if ("serviceWorker" in navigator) {
  window.addEventListener("load", () => {
    navigator.serviceWorker.register("sw.js").catch(() => {});
  });
}
