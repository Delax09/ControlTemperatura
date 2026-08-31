/* ==== Modal de detalle de puerta / centro de alertas ====
   Se abre al hacer click en una card del muro. Todo lo que muestra se deriva
   de los datos reales de `estado` (dashboard.js); los campos que el backend
   todavía no entrega se marcan explícitamente como pendientes en vez de
   inventar valores. */

/* ---- Reglas de escalamiento ----
   Los umbrales se toman de las constantes de dashboard.js para que exista
   una sola fuente de verdad con los colores y la barra del muro. */
const REGLAS_ESCALAMIENTO = [
  { t: 60,           titulo: 'Aviso en tablero',
    detalle: 'Se marca la puerta en el muro de control y en la app del operador de zona.' },
  { t: UMBRAL_WARN,  titulo: 'Notificación al operador',
    detalle: 'Push al HT del operador responsable de la zona y tono en el andén.' },
  { t: UMBRAL_SER,   titulo: 'Escalamiento a supervisor',
    detalle: 'Llamado por radio y WhatsApp al supervisor de turno.' },
  { t: UMBRAL_CRIT,  titulo: 'Escalamiento a jefe de planta',
    detalle: 'Se abre incidente formal y queda registro para revisión HACCP.' },
  { t: 900,          titulo: 'Alerta de cadena de frío',
    detalle: 'Se notifica a Aseguramiento de Calidad y se marca el lote expuesto.' },
];

const NIVEL_NOMBRE = { crit:'Cadena de frío', serious:'Crítica', warn:'Alta', open:'Media', ok:'Normal' };

/* ---- Estado del modal ---- */
const dlg = document.getElementById('modal-alerta');
let puertaSel = null;          // id de la puerta abierta en el modal
let tickModal = null;          // intervalo del cronómetro
const notasPorPuerta = {};     // notas locales, solo frontend (como `ack`)

/* ---- Helpers ---- */
const hhmm = d => d.toLocaleTimeString('es-CL', { hour12:false }).slice(0,5);

// Segundos abiertos "en vivo": el dato del backend más lo transcurrido desde
// que llegó, para que el cronómetro no se congele entre polls de 5 s.
function segundosEnVivo(e){
  if(!e.abierta) return 0;
  const desfase = (Date.now() - (window.ultimaActualizacion || Date.now())) / 1000;
  return e.segundos_abierta + Math.max(0, desfase);
}

function nivelDe(segundos, abierta){
  if(!abierta) return 'ok';
  if(segundos >= UMBRAL_CRIT) return 'crit';
  if(segundos >= UMBRAL_SER)  return 'serious';
  if(segundos >= UMBRAL_WARN) return 'warn';
  return 'open';
}

/* ---- Apertura y cierre ---- */
function abrirModalAlerta(id){
  puertaSel = id;
  pintarModal();
  if(!dlg.open) dlg.showModal();
  clearInterval(tickModal);
  tickModal = setInterval(pintarVivo, 1000);
}

function cerrarModalAlerta(){
  clearInterval(tickModal);
  tickModal = null;
  puertaSel = null;
  if(dlg.open) dlg.close();
}

// Llamado desde render() cuando llegan datos nuevos de la API.
function refrescarModalAlerta(){
  if(dlg.open && puertaSel) pintarModal();
}

/* ---- Render completo ---- */
function pintarModal(){
  const e = estado.find(x => x.id === puertaSel);
  if(!e){ cerrarModalAlerta(); return; }

  const seg = segundosEnVivo(e);
  const n = nivelDe(seg, e.abierta);
  const deriva = e.temp_actual - e.temp_objetivo;

  document.getElementById('m-titulo').innerHTML =
    `${e.nombre} <span class="id">· ${e.id}</span>`;
  document.getElementById('m-zona').textContent =
    `${e.zona} · set point ${e.temp_objetivo} °C · cámara ${e.cam || '—'}`;

  document.getElementById('m-chips').innerHTML = [
    `<span class="m-chip" style="border-color:${COLOR[n]};color:${COLOR[n]}">▲ ${NIVEL_NOMBRE[n]}</span>`,
    `<span class="m-chip">${e.abierta ? 'Abierta' : 'Cerrada'}</span>`,
    `<span class="m-chip">Δt ${deriva >= 0 ? '+' : ''}${deriva.toFixed(1)}°</span>`,
    `<span class="m-chip">${e.aperturas_hoy} aperturas hoy</span>`,
    e.offline ? '<span class="m-chip" style="border-color:var(--crit);color:var(--crit)">Sin señal</span>' : '',
    '<span class="m-chip pend">Causa: pendiente</span>',
  ].filter(Boolean).join('');

  pintarEscalera(seg, e.abierta);
  pintarBitacora(e, seg);
  renderGraficoTemp(document.getElementById('m-grafico'), serieDe(e), e.temp_objetivo);
  pintarTemperatura(e);
  pintarHistorial(e);

  document.getElementById('m-nota').value = notasPorPuerta[e.id] || '';
  document.getElementById('m-foot').textContent =
    'Escalera y bitácora derivadas del tiempo real de apertura. Las acciones son de demostración.';

  pintarVivo();
}

/* ---- Cronómetro y estados que cambian cada segundo ---- */
function pintarVivo(){
  const e = estado.find(x => x.id === puertaSel);
  if(!e) return;

  const seg = segundosEnVivo(e);
  const n = nivelDe(seg, e.abierta);

  const t = document.getElementById('m-timer');
  t.textContent = e.abierta ? mmss(seg) : '—';
  t.style.color = e.abierta ? COLOR[n] : 'var(--ink-2)';
  document.getElementById('m-timer-lbl').textContent =
    e.abierta ? 'puerta abierta ahora' : 'puerta cerrada';

  // Si cruzó un escalón nuevo, se repinta la escalera y la bitácora.
  const escalones = REGLAS_ESCALAMIENTO.filter(r => seg > r.t).length;
  if(pintarVivo._esc !== escalones){
    if(pintarVivo._esc !== undefined && escalones > pintarVivo._esc && e.abierta){
      toast('Escalamiento: ' + REGLAS_ESCALAMIENTO[escalones-1].titulo + ' · ' + e.nombre);
    }
    pintarVivo._esc = escalones;
    pintarEscalera(seg, e.abierta);
    pintarBitacora(e, seg);
  }
}

/* ---- Escalera de escalamiento ---- */
function pintarEscalera(seg, abierta){
  const alcanzado = REGLAS_ESCALAMIENTO.filter(r => seg > r.t);
  const ultimo = alcanzado.length ? Math.max(...alcanzado.map(r => r.t)) : null;

  document.getElementById('m-ladder').innerHTML = REGLAS_ESCALAMIENTO.map(r => {
    const hecho = seg > r.t;
    const activo = hecho && r.t === ultimo && abierta;
    const clase = activo ? 'active' : hecho ? 'done' : 'pend';
    return `<div class="m-step ${clase}">
      <b>${mmss(r.t)} · ${r.titulo}</b>
      <span>${r.detalle}${hecho ? '' : ' — no alcanzado'}</span>
    </div>`;
  }).join('');
}

/* ---- Bitácora derivada del tiempo de apertura ---- */
function pintarBitacora(e, seg){
  if(!e.abierta){
    document.getElementById('m-log').innerHTML =
      '<div><time>—</time><span>La puerta está cerrada. Sin evento en curso.</span></div>';
    return;
  }

  const t0 = new Date(Date.now() - seg * 1000);
  const filas = [[hhmm(t0), 'Visión computacional detecta <em>puerta abierta</em>']];

  REGLAS_ESCALAMIENTO.forEach(r => {
    const momento = new Date(+t0 + r.t * 1000);
    const alcanzado = seg > r.t;
    filas.push([
      alcanzado ? hhmm(momento) : '··:··',
      (alcanzado ? '' : '<span class="fut">') + r.titulo + (alcanzado ? '' : '</span>'),
    ]);
  });

  (notasPorPuerta[e.id + '_log'] || []).forEach(nt => {
    filas.push([nt[0], 'Nota del turno: <em>' + nt[1] + '</em>']);
  });

  document.getElementById('m-log').innerHTML =
    filas.map(([t, x]) => `<div><time>${t}</time><span>${x}</span></div>`).join('');
}

/* ---- Panel de temperatura ---- */
function pintarTemperatura(e){
  const serie = serieDe(e);
  const vals = serie.map(p => p.v);
  const min = Math.min(...vals), max = Math.max(...vals);
  const fuera = serie.filter(p => Math.abs(p.v - e.temp_objetivo) > 1.2).length;

  // La lectura actual es el último punto de la serie: el mismo donde termina el
  // gráfico, para que el número y la curva nunca se contradigan.
  const lectura = serie[serie.length - 1];
  const actual = lectura.v;
  const deriva = actual - e.temp_objetivo;
  const fueraDeRango = Math.abs(deriva) > 1.2;

  // La barra representa la deriva sobre un rango de referencia de 6 °C.
  const pct = Math.min(100, Math.abs(deriva) / 6 * 100);
  const color = Math.abs(deriva) > 3 ? 'var(--crit)'
              : fueraDeRango ? 'var(--serious)' : 'var(--good)';

  // Tendencia respecto de la lectura anterior.
  const previo = serie.length > 1 ? serie[serie.length - 2].v : actual;
  const delta = actual - previo;
  const flecha = Math.abs(delta) < 0.05 ? '→' : delta > 0 ? '↑' : '↓';
  const tendColor = Math.abs(delta) < 0.05 ? 'var(--muted)'
                  : delta > 0 ? 'var(--serious)' : 'var(--good)';

  document.getElementById('m-temp').innerHTML = `
    <div class="row">
      <span>Actual <small style="color:var(--muted)">· lectura ${hhmm(lectura.t)}</small></span>
      <span>
        <b class="${fueraDeRango ? 'drift' : ''}">${actual.toFixed(1)} °C</b>
        <b style="color:${tendColor};font-weight:500;margin-left:6px">${flecha} ${delta >= 0 ? '+' : ''}${delta.toFixed(1)}</b>
      </span>
    </div>
    <div class="m-gauge"><i style="width:${pct}%;background:${color}"></i></div>
    <div class="row">
      <span>Set point ${e.temp_objetivo} °C</span>
      <span>Deriva <b class="${fueraDeRango ? 'drift' : ''}">${deriva >= 0 ? '+' : ''}${deriva.toFixed(1)} °C</b></span>
    </div>
    <div class="row">
      <span>Mín. ${min.toFixed(1)} °C · máx. ${max.toFixed(1)} °C</span>
      <span>${fuera} de ${serie.length} min fuera de rango</span>
    </div>
    <div class="m-pending">
      <b>Serie simulada</b> (ver <code>temp-sim.js</code>): el backend solo entrega el valor
      actual, no el histórico. El número de arriba es el último punto del gráfico, así que
      ambos coinciden siempre. Siguen pendientes la causa de la apertura, la confianza de
      la detección y el acuse.
    </div>`;
}

/* ---- Historial de aperturas (dato real) ---- */
function pintarHistorial(e){
  const h = e.historial_aperturas || [];
  const cont = document.getElementById('m-hist');
  const foot = document.getElementById('m-hist-foot');

  if(!h.length){
    cont.innerHTML = '';
    foot.innerHTML = '<span>Sin aperturas registradas</span>';
    return;
  }

  const max = Math.max(...h);
  cont.innerHTML = h.map(s => {
    const c = s >= UMBRAL_CRIT ? 'var(--crit)'
            : s >= UMBRAL_SER  ? 'var(--serious)'
            : s >= UMBRAL_WARN ? 'var(--warn)' : '#3a3a37';
    return `<div style="height:${Math.max(6, s / max * 60)}px;background:${c}" title="${mmss(s)}"></div>`;
  }).join('');

  const prom = h.reduce((a, b) => a + b, 0) / h.length;
  foot.innerHTML = `<span>${h.length} aperturas · promedio ${mmss(prom)}</span>
                    <span>máx. ${mmss(max)}</span>`;
}

/* ---- Toast ---- */
function toast(msg){
  const t = document.getElementById('toast');
  t.textContent = msg;
  t.classList.add('on');
  clearTimeout(t._x);
  t._x = setTimeout(() => t.classList.remove('on'), 2600);
}

/* ---- Interacciones ---- */

// Click en una card abre el modal (salvo que sea un botón dentro de la card).
grid.addEventListener('click', ev => {
  if(ev.target.closest('.btn')) return;
  const card = ev.target.closest('.card');
  if(card) abrirModalAlerta(card.dataset.id);
});

// Enter o espacio sobre una card también la abre.
grid.addEventListener('keydown', ev => {
  if(ev.key !== 'Enter' && ev.key !== ' ') return;
  const card = ev.target.closest('.card');
  if(card && !ev.target.closest('.btn')){
    ev.preventDefault();
    abrirModalAlerta(card.dataset.id);
  }
});

document.getElementById('m-close').addEventListener('click', cerrarModalAlerta);

// Click en el backdrop cierra el modal.
dlg.addEventListener('click', ev => { if(ev.target === dlg) cerrarModalAlerta(); });

// Escape lo cierra solo (<dialog> nativo); limpiamos el intervalo.
dlg.addEventListener('close', () => { clearInterval(tickModal); tickModal = null; puertaSel = null; });

// Botones de acción de demostración.
dlg.querySelectorAll('[data-accion]').forEach(b => {
  b.addEventListener('click', () => toast(b.dataset.accion));
});

document.getElementById('m-silenciar').addEventListener('click', () => {
  const e = estado.find(x => x.id === puertaSel);
  if(!e) return;
  e.ack = Date.now() + 300000;
  resumen();
  toast('Alerta silenciada 5 minutos · ' + e.nombre);
});

document.getElementById('m-guardar-nota').addEventListener('click', () => {
  const v = document.getElementById('m-nota').value.trim();
  if(!v || !puertaSel) return;
  notasPorPuerta[puertaSel] = v;
  notasPorPuerta[puertaSel + '_log'] = notasPorPuerta[puertaSel + '_log'] || [];
  notasPorPuerta[puertaSel + '_log'].push([hhmm(new Date()), v]);
  const e = estado.find(x => x.id === puertaSel);
  if(e) pintarBitacora(e, segundosEnVivo(e));
  toast('Nota guardada en el incidente');
});
